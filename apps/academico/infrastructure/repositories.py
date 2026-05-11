"""
Concrete repository implementations for the Academico bounded context.
Django ORM implementations of the abstract repositories defined in domain/.
"""

from typing import List, Optional

from django.db import transaction

from apps.academico.domain.entities import (
    AsignaturaEntity,
    MatriculaEntity,
    ParaleloEntity,
    PeriodoEntity,
    TipoLicenciaEntity,
)
from apps.academico.domain.repositories import (
    AsignaturaRepository,
    MatriculaRepository,
    ParaleloRepository,
    PeriodoRepository,
    TipoLicenciaRepository,
)

from .models import Asignatura, AsignaturaLicencia, Matricula, Paralelo, Periodo, TipoLicencia


class DjangoPeriodoRepository(PeriodoRepository):
    """Django ORM implementation of PeriodoRepository."""

    def _to_entity(self, obj: Periodo) -> PeriodoEntity:
        return PeriodoEntity(
            nombre=obj.nombre,
            fecha_inicio=obj.fecha_inicio,
            fecha_fin=obj.fecha_fin,
            tipo_licencia_id=obj.tipo_licencia_id,
            activo=obj.activo,
            creado_por_id=obj.creado_por_id,
        )

    def get_by_id(self, periodo_id: int) -> Optional[PeriodoEntity]:
        try:
            obj = Periodo.objects.get(pk=periodo_id)
            return self._to_entity(obj)
        except Periodo.DoesNotExist:
            return None

    def get_activo_por_tipo(self, tipo_licencia_id: int) -> Optional[PeriodoEntity]:
        try:
            obj = Periodo.objects.get(activo=True, tipo_licencia_id=tipo_licencia_id)
            return self._to_entity(obj)
        except Periodo.DoesNotExist:
            return None

    def list_all(self) -> List[PeriodoEntity]:
        return [self._to_entity(obj) for obj in Periodo.objects.all()]

    def create(self, entity: PeriodoEntity) -> PeriodoEntity:
        obj = Periodo.objects.create(
            nombre=entity.nombre,
            fecha_inicio=entity.fecha_inicio,
            fecha_fin=entity.fecha_fin,
            tipo_licencia_id=entity.tipo_licencia_id,
            activo=entity.activo,
            creado_por_id=entity.creado_por_id,
        )
        return self._to_entity(obj)

    def update(self, periodo_id: int, entity: PeriodoEntity) -> PeriodoEntity:
        obj = Periodo.objects.get(pk=periodo_id)
        obj.nombre = entity.nombre
        obj.fecha_inicio = entity.fecha_inicio
        obj.fecha_fin = entity.fecha_fin
        obj.tipo_licencia_id = entity.tipo_licencia_id
        obj.activo = entity.activo
        obj.save()
        return self._to_entity(obj)

    @transaction.atomic
    def activar(self, periodo_id: int) -> None:
        """Activate a period using select_for_update to prevent race conditions."""
        obj = Periodo.objects.select_for_update().get(pk=periodo_id)
        obj.activo = True
        obj.save(update_fields=["activo", "modificado_en"])

    def desactivar_por_tipo(self, tipo_licencia_id: int) -> None:
        Periodo.objects.filter(activo=True, tipo_licencia_id=tipo_licencia_id).update(activo=False)


class DjangoTipoLicenciaRepository(TipoLicenciaRepository):
    """Django ORM implementation of TipoLicenciaRepository."""

    def _to_entity(self, obj: TipoLicencia) -> TipoLicenciaEntity:
        return TipoLicenciaEntity(
            nombre=obj.nombre,
            codigo=obj.codigo,
            duracion_meses=obj.duracion_meses,
            num_asignaturas=obj.num_asignaturas,
            activo=obj.activo,
        )

    def get_by_id(self, tipo_id: int) -> Optional[TipoLicenciaEntity]:
        try:
            obj = TipoLicencia.objects.get(pk=tipo_id)
            return self._to_entity(obj)
        except TipoLicencia.DoesNotExist:
            return None

    def get_by_codigo(self, codigo: str) -> Optional[TipoLicenciaEntity]:
        try:
            obj = TipoLicencia.objects.get(codigo=codigo)
            return self._to_entity(obj)
        except TipoLicencia.DoesNotExist:
            return None

    def list_activos(self) -> List[TipoLicenciaEntity]:
        return [self._to_entity(obj) for obj in TipoLicencia.objects.filter(activo=True)]


class DjangoAsignaturaRepository(AsignaturaRepository):
    """Django ORM implementation of AsignaturaRepository."""

    def _to_entity(self, obj: Asignatura) -> AsignaturaEntity:
        licencias = [
            {
                "tipo_licencia_id": al.tipo_licencia_id,
                "horas_lectivas": al.horas_lectivas,
            }
            for al in obj.asignatura_licencias.all()
        ]
        return AsignaturaEntity(
            nombre=obj.nombre,
            codigo=obj.codigo,
            descripcion=obj.descripcion,
            licencias=licencias,
        )

    def get_by_id(self, asignatura_id: int) -> Optional[AsignaturaEntity]:
        try:
            obj = Asignatura.objects.get(pk=asignatura_id)
            return self._to_entity(obj)
        except Asignatura.DoesNotExist:
            return None

    def get_by_codigo(self, codigo: str) -> Optional[AsignaturaEntity]:
        try:
            obj = Asignatura.objects.get(codigo=codigo)
            return self._to_entity(obj)
        except Asignatura.DoesNotExist:
            return None

    def list_all(self) -> List[AsignaturaEntity]:
        return [self._to_entity(obj) for obj in Asignatura.objects.all()]

    def create(self, entity: AsignaturaEntity) -> AsignaturaEntity:
        obj = Asignatura.objects.create(
            nombre=entity.nombre,
            codigo=entity.codigo,
            descripcion=entity.descripcion,
        )
        if entity.licencias:
            AsignaturaLicencia.objects.bulk_create(
                [
                    AsignaturaLicencia(
                        asignatura=obj,
                        tipo_licencia_id=lic["tipo_licencia_id"],
                        horas_lectivas=lic["horas_lectivas"],
                    )
                    for lic in entity.licencias
                ]
            )
        return self._to_entity(obj)

    def update(self, asignatura_id: int, entity: AsignaturaEntity) -> AsignaturaEntity:
        obj = Asignatura.objects.get(pk=asignatura_id)
        obj.nombre = entity.nombre
        obj.codigo = entity.codigo
        obj.descripcion = entity.descripcion
        obj.save()
        # Replace licencias
        obj.asignatura_licencias.all().delete()
        if entity.licencias:
            AsignaturaLicencia.objects.bulk_create(
                [
                    AsignaturaLicencia(
                        asignatura=obj,
                        tipo_licencia_id=lic["tipo_licencia_id"],
                        horas_lectivas=lic["horas_lectivas"],
                    )
                    for lic in entity.licencias
                ]
            )
        return self._to_entity(obj)

    def codigo_exists(self, codigo: str, exclude_id: Optional[int] = None) -> bool:
        qs = Asignatura.objects.filter(codigo=codigo)
        if exclude_id:
            qs = qs.exclude(pk=exclude_id)
        return qs.exists()


class DjangoParaleloRepository(ParaleloRepository):
    """Django ORM implementation of ParaleloRepository."""

    def _to_entity(self, obj: Paralelo) -> ParaleloEntity:
        return ParaleloEntity(
            asignatura_codigo=obj.asignatura.codigo,
            periodo_nombre=obj.periodo.nombre,
            docente_username=obj.docente.username,
            nombre=obj.nombre,
            tipo_licencia_id=obj.tipo_licencia_id,
            capacidad_maxima=obj.capacidad_maxima,
        )

    def get_by_id(self, paralelo_id: int) -> Optional[ParaleloEntity]:
        try:
            obj = Paralelo.objects.select_related("asignatura", "periodo", "docente").get(
                pk=paralelo_id
            )
            return self._to_entity(obj)
        except Paralelo.DoesNotExist:
            return None

    def list_by_periodo(self, periodo_nombre: str) -> List[ParaleloEntity]:
        objs = Paralelo.objects.select_related("asignatura", "periodo", "docente").filter(
            periodo__nombre=periodo_nombre
        )
        return [self._to_entity(obj) for obj in objs]

    def list_all(self) -> List[ParaleloEntity]:
        objs = Paralelo.objects.select_related("asignatura", "periodo", "docente").all()
        return [self._to_entity(obj) for obj in objs]

    def create(self, entity: ParaleloEntity) -> ParaleloEntity:
        from apps.academico.infrastructure.models import Asignatura, Periodo
        from apps.usuarios.infrastructure.models import Usuario

        obj = Paralelo.objects.create(
            asignatura=Asignatura.objects.get(codigo=entity.asignatura_codigo),
            periodo=Periodo.objects.get(nombre=entity.periodo_nombre),
            docente=Usuario.objects.get(username=entity.docente_username),
            tipo_licencia_id=entity.tipo_licencia_id,
            nombre=entity.nombre,
            capacidad_maxima=entity.capacidad_maxima,
        )
        return self._to_entity(obj)

    def update(self, paralelo_id: int, entity: ParaleloEntity) -> ParaleloEntity:
        from apps.academico.infrastructure.models import Asignatura, Periodo
        from apps.usuarios.infrastructure.models import Usuario

        obj = Paralelo.objects.get(pk=paralelo_id)
        obj.asignatura = Asignatura.objects.get(codigo=entity.asignatura_codigo)
        obj.periodo = Periodo.objects.get(nombre=entity.periodo_nombre)
        obj.docente = Usuario.objects.get(username=entity.docente_username)
        obj.tipo_licencia_id = entity.tipo_licencia_id
        obj.nombre = entity.nombre
        obj.capacidad_maxima = entity.capacidad_maxima
        obj.save()
        return self._to_entity(obj)

    def exists(
        self,
        periodo_id: int,
        tipo_licencia_id: int,
        asignatura_id: int,
        nombre: str,
        exclude_id: Optional[int] = None,
    ) -> bool:
        qs = Paralelo.objects.filter(
            periodo_id=periodo_id,
            tipo_licencia_id=tipo_licencia_id,
            asignatura_id=asignatura_id,
            nombre=nombre,
        )
        if exclude_id:
            qs = qs.exclude(pk=exclude_id)
        return qs.exists()


class DjangoMatriculaRepository(MatriculaRepository):
    """Django ORM implementation of MatriculaRepository."""

    def _to_entity(self, obj: Matricula) -> MatriculaEntity:
        return MatriculaEntity(
            estudiante_id=obj.estudiante_id,
            paralelo_id=obj.paralelo_id,
            estado=obj.estado,
            fecha_matricula=obj.fecha_matricula.date() if obj.fecha_matricula else None,
            matriculado_por_id=obj.matriculado_por_id,
        )

    def crear(self, entity: MatriculaEntity) -> MatriculaEntity:
        obj = Matricula.objects.create(
            estudiante_id=entity.estudiante_id,
            paralelo_id=entity.paralelo_id,
            estado=entity.estado,
            matriculado_por_id=entity.matriculado_por_id,
        )
        return self._to_entity(obj)

    def cambiar_estado(self, matricula_id: int, nuevo_estado: str) -> MatriculaEntity:
        obj = Matricula.objects.get(pk=matricula_id)
        obj.estado = nuevo_estado
        obj.save(update_fields=["estado"])
        return self._to_entity(obj)

    def get_by_estudiante_paralelo(
        self, estudiante_id: int, paralelo_id: int
    ) -> Optional[MatriculaEntity]:
        try:
            obj = Matricula.objects.get(
                estudiante_id=estudiante_id,
                paralelo_id=paralelo_id,
            )
            return self._to_entity(obj)
        except Matricula.DoesNotExist:
            return None

    def contar_activas_en_paralelo(self, paralelo_id: int) -> int:
        return Matricula.objects.filter(
            paralelo_id=paralelo_id,
            estado=Matricula.Estado.ACTIVA,
        ).count()

    def exists_by_estudiante_asignatura_periodo(
        self, estudiante_id: int, asignatura_id: int, periodo_id: int
    ) -> bool:
        return Matricula.objects.filter(
            estudiante_id=estudiante_id,
            paralelo__asignatura_id=asignatura_id,
            paralelo__periodo_id=periodo_id,
            estado=Matricula.Estado.ACTIVA,
        ).exists()
