"""
Concrete repository implementations for the Academico bounded context.
Django ORM implementations of the abstract repositories defined in domain/.
"""

from typing import List, Optional

from django.db import transaction

from apps.academico.domain.entities import (
    AsignaturaEntity,
    ParaleloEntity,
    PeriodoEntity,
    TipoLicenciaEntity,
)
from apps.academico.domain.repositories import (
    AsignaturaRepository,
    ParaleloRepository,
    PeriodoRepository,
    TipoLicenciaRepository,
)

from .models import Asignatura, Paralelo, Periodo, TipoLicencia


class DjangoPeriodoRepository(PeriodoRepository):
    """Django ORM implementation of PeriodoRepository."""

    def _to_entity(self, obj: Periodo) -> PeriodoEntity:
        return PeriodoEntity(
            nombre=obj.nombre,
            fecha_inicio=obj.fecha_inicio,
            fecha_fin=obj.fecha_fin,
            activo=obj.activo,
            creado_por_id=obj.creado_por_id,
        )

    def get_by_id(self, periodo_id: int) -> Optional[PeriodoEntity]:
        try:
            obj = Periodo.objects.get(pk=periodo_id)
            return self._to_entity(obj)
        except Periodo.DoesNotExist:
            return None

    def get_activo(self) -> Optional[PeriodoEntity]:
        try:
            obj = Periodo.objects.get(activo=True)
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
            activo=entity.activo,
            creado_por_id=entity.creado_por_id,
        )
        return self._to_entity(obj)

    def update(self, periodo_id: int, entity: PeriodoEntity) -> PeriodoEntity:
        obj = Periodo.objects.get(pk=periodo_id)
        obj.nombre = entity.nombre
        obj.fecha_inicio = entity.fecha_inicio
        obj.fecha_fin = entity.fecha_fin
        obj.activo = entity.activo
        obj.save()
        return self._to_entity(obj)

    @transaction.atomic
    def activar(self, periodo_id: int) -> None:
        """Activate a period using select_for_update to prevent race conditions."""
        obj = Periodo.objects.select_for_update().get(pk=periodo_id)
        obj.activo = True
        obj.save(update_fields=["activo", "modificado_en"])

    def desactivar_todos(self) -> None:
        Periodo.objects.filter(activo=True).update(activo=False)


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
        return [
            self._to_entity(obj)
            for obj in TipoLicencia.objects.filter(activo=True)
        ]


class DjangoAsignaturaRepository(AsignaturaRepository):
    """Django ORM implementation of AsignaturaRepository."""

    def _to_entity(self, obj: Asignatura) -> AsignaturaEntity:
        return AsignaturaEntity(
            nombre=obj.nombre,
            codigo=obj.codigo,
            descripcion=obj.descripcion,
            horas_lectivas=obj.horas_lectivas,
            tipos_licencia_ids=list(
                obj.tipos_licencia.values_list("id", flat=True)
            ),
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
            horas_lectivas=entity.horas_lectivas,
        )
        if entity.tipos_licencia_ids:
            obj.tipos_licencia.set(entity.tipos_licencia_ids)
        return self._to_entity(obj)

    def update(
        self, asignatura_id: int, entity: AsignaturaEntity
    ) -> AsignaturaEntity:
        obj = Asignatura.objects.get(pk=asignatura_id)
        obj.nombre = entity.nombre
        obj.codigo = entity.codigo
        obj.descripcion = entity.descripcion
        obj.horas_lectivas = entity.horas_lectivas
        obj.save()
        if entity.tipos_licencia_ids:
            obj.tipos_licencia.set(entity.tipos_licencia_ids)
        return self._to_entity(obj)

    def codigo_exists(
        self, codigo: str, exclude_id: Optional[int] = None
    ) -> bool:
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
            horario=obj.horario,
            tipo_licencia_id=obj.tipo_licencia_id,
            capacidad_maxima=obj.capacidad_maxima,
        )

    def get_by_id(self, paralelo_id: int) -> Optional[ParaleloEntity]:
        try:
            obj = Paralelo.objects.select_related(
                "asignatura", "periodo", "docente"
            ).get(pk=paralelo_id)
            return self._to_entity(obj)
        except Paralelo.DoesNotExist:
            return None

    def list_by_periodo(self, periodo_nombre: str) -> List[ParaleloEntity]:
        objs = Paralelo.objects.select_related(
            "asignatura", "periodo", "docente"
        ).filter(periodo__nombre=periodo_nombre)
        return [self._to_entity(obj) for obj in objs]

    def list_all(self) -> List[ParaleloEntity]:
        objs = Paralelo.objects.select_related(
            "asignatura", "periodo", "docente"
        ).all()
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
            horario=entity.horario,
            capacidad_maxima=entity.capacidad_maxima,
        )
        return self._to_entity(obj)

    def update(
        self, paralelo_id: int, entity: ParaleloEntity
    ) -> ParaleloEntity:
        from apps.academico.infrastructure.models import Asignatura, Periodo
        from apps.usuarios.infrastructure.models import Usuario

        obj = Paralelo.objects.get(pk=paralelo_id)
        obj.asignatura = Asignatura.objects.get(codigo=entity.asignatura_codigo)
        obj.periodo = Periodo.objects.get(nombre=entity.periodo_nombre)
        obj.docente = Usuario.objects.get(username=entity.docente_username)
        obj.tipo_licencia_id = entity.tipo_licencia_id
        obj.nombre = entity.nombre
        obj.horario = entity.horario
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
