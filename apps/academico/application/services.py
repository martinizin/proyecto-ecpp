"""
Application services (use cases) for the Academico bounded context.

These services orchestrate domain services + infrastructure (repositories, audit)
to implement complete use cases. They are the entry point from the presentation layer.
"""

from datetime import date
from typing import List, Optional

from django.db import transaction

from apps.academico.domain.entities import (
    AsignaturaEntity,
    ParaleloEntity,
    PeriodoEntity,
)
from apps.academico.domain.services import (
    AsignaturaService,
    ParaleloService,
    PeriodoService,
)
from apps.academico.infrastructure.repositories import (
    DjangoAsignaturaRepository,
    DjangoParaleloRepository,
    DjangoPeriodoRepository,
    DjangoTipoLicenciaRepository,
)
from apps.usuarios.domain.entities import RegistroAuditoriaEntity
from apps.usuarios.infrastructure.repositories import DjangoAuditoriaRepository


class PeriodoAppService:
    """
    Orchestrates academic period CRUD + activation with audit trail.
    Refs: SCN-PER-01→09
    """

    def __init__(self):
        self.periodo_repo = DjangoPeriodoRepository()
        self.periodo_service = PeriodoService()
        self.auditoria_repo = DjangoAuditoriaRepository()

    def listar(self) -> List[PeriodoEntity]:
        return self.periodo_repo.list_all()

    def obtener(self, periodo_id: int) -> Optional[PeriodoEntity]:
        return self.periodo_repo.get_by_id(periodo_id)

    def crear(
        self,
        nombre: str,
        fecha_inicio: date,
        fecha_fin: date,
        creado_por_id: int,
    ) -> PeriodoEntity:
        """
        Create a new academic period.

        Raises:
            PeriodoSolapadoError: If fecha_inicio >= fecha_fin.
        """
        self.periodo_service.validar_fechas(fecha_inicio, fecha_fin)

        entity = PeriodoEntity(
            nombre=nombre,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            activo=False,
            creado_por_id=creado_por_id,
        )
        created = self.periodo_repo.create(entity)

        self.auditoria_repo.registrar(
            RegistroAuditoriaEntity(
                accion="creacion_periodo",
                usuario_id=creado_por_id,
                detalle=f"Período creado: {nombre}",
            )
        )

        return created

    def actualizar(
        self,
        periodo_id: int,
        nombre: str,
        fecha_inicio: date,
        fecha_fin: date,
        usuario_id: int,
    ) -> PeriodoEntity:
        """
        Update an existing period.

        Raises:
            PeriodoSolapadoError: If fecha_inicio >= fecha_fin.
        """
        self.periodo_service.validar_fechas(fecha_inicio, fecha_fin)

        existing = self.periodo_repo.get_by_id(periodo_id)
        entity = PeriodoEntity(
            nombre=nombre,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            activo=existing.activo if existing else False,
            creado_por_id=existing.creado_por_id if existing else None,
        )
        updated = self.periodo_repo.update(periodo_id, entity)

        self.auditoria_repo.registrar(
            RegistroAuditoriaEntity(
                accion="actualizacion_periodo",
                usuario_id=usuario_id,
                detalle=f"Período actualizado: {nombre}",
            )
        )

        return updated

    @transaction.atomic
    def activar(
        self,
        periodo_id: int,
        usuario_id: int,
        confirmar_desactivacion: bool = False,
    ) -> bool:
        """
        Activate a period, enforcing single-active invariant.

        Args:
            periodo_id: ID of the period to activate.
            usuario_id: ID of the user performing the action.
            confirmar_desactivacion: Whether user confirmed deactivation of current active.

        Returns:
            True if activation succeeded.

        Raises:
            PeriodoActivoExistenteError: If another period is active and not confirmed.
        """
        activo = self.periodo_repo.get_activo()
        periodo_activo_nombre = activo.nombre if activo else None

        # Domain check — may raise PeriodoActivoExistenteError
        self.periodo_service.verificar_activacion(
            periodo_activo_actual=periodo_activo_nombre,
            confirmar_desactivacion=confirmar_desactivacion,
        )

        # Deactivate current if exists
        if activo:
            self.periodo_repo.desactivar_todos()
            self.auditoria_repo.registrar(
                RegistroAuditoriaEntity(
                    accion="cambio_estado_periodo",
                    usuario_id=usuario_id,
                    detalle=f"Período desactivado: {periodo_activo_nombre}",
                )
            )

        # Activate new
        self.periodo_repo.activar(periodo_id)
        nuevo = self.periodo_repo.get_by_id(periodo_id)
        self.auditoria_repo.registrar(
            RegistroAuditoriaEntity(
                accion="cambio_estado_periodo",
                usuario_id=usuario_id,
                detalle=f"Período activado: {nuevo.nombre if nuevo else periodo_id}",
            )
        )

        return True


class AsignaturaAppService:
    """
    Orchestrates subject CRUD with validation.
    Refs: SCN-CAT-03→06
    """

    def __init__(self):
        self.asignatura_repo = DjangoAsignaturaRepository()
        self.asignatura_service = AsignaturaService()
        self.auditoria_repo = DjangoAuditoriaRepository()

    def listar(self) -> List[AsignaturaEntity]:
        return self.asignatura_repo.list_all()

    def obtener(self, asignatura_id: int) -> Optional[AsignaturaEntity]:
        return self.asignatura_repo.get_by_id(asignatura_id)

    def crear(
        self,
        nombre: str,
        codigo: str,
        horas_lectivas: int,
        tipos_licencia_ids: List[int],
        usuario_id: int,
        descripcion: str = "",
    ) -> AsignaturaEntity:
        """
        Create a new subject.

        Raises:
            AsignaturaCodigoDuplicadoError, ValueError
        """
        self.asignatura_service.validar_datos(
            codigo=codigo,
            horas_lectivas=horas_lectivas,
            tipos_licencia_ids=tipos_licencia_ids,
            codigo_exists=self.asignatura_repo.codigo_exists(codigo),
        )

        entity = AsignaturaEntity(
            nombre=nombre,
            codigo=codigo,
            descripcion=descripcion,
            horas_lectivas=horas_lectivas,
            tipos_licencia_ids=tipos_licencia_ids,
        )
        created = self.asignatura_repo.create(entity)

        self.auditoria_repo.registrar(
            RegistroAuditoriaEntity(
                accion="creacion_asignatura",
                usuario_id=usuario_id,
                detalle=f"Asignatura creada: {codigo} — {nombre}",
            )
        )

        return created

    def actualizar(
        self,
        asignatura_id: int,
        nombre: str,
        codigo: str,
        horas_lectivas: int,
        tipos_licencia_ids: List[int],
        usuario_id: int,
        descripcion: str = "",
    ) -> AsignaturaEntity:
        """
        Update an existing subject.

        Raises:
            AsignaturaCodigoDuplicadoError, ValueError
        """
        self.asignatura_service.validar_datos(
            codigo=codigo,
            horas_lectivas=horas_lectivas,
            tipos_licencia_ids=tipos_licencia_ids,
            codigo_exists=self.asignatura_repo.codigo_exists(
                codigo, exclude_id=asignatura_id
            ),
        )

        entity = AsignaturaEntity(
            nombre=nombre,
            codigo=codigo,
            descripcion=descripcion,
            horas_lectivas=horas_lectivas,
            tipos_licencia_ids=tipos_licencia_ids,
        )
        updated = self.asignatura_repo.update(asignatura_id, entity)

        self.auditoria_repo.registrar(
            RegistroAuditoriaEntity(
                accion="actualizacion_asignatura",
                usuario_id=usuario_id,
                detalle=f"Asignatura actualizada: {codigo} — {nombre}",
            )
        )

        return updated


class ParaleloAppService:
    """
    Orchestrates parallel CRUD with docente/period/uniqueness validation.
    Refs: SCN-CAT-07→10
    """

    def __init__(self):
        self.paralelo_repo = DjangoParaleloRepository()
        self.paralelo_service = ParaleloService()
        self.periodo_repo = DjangoPeriodoRepository()
        self.auditoria_repo = DjangoAuditoriaRepository()

    def listar(self) -> List[ParaleloEntity]:
        return self.paralelo_repo.list_all()

    def obtener(self, paralelo_id: int) -> Optional[ParaleloEntity]:
        return self.paralelo_repo.get_by_id(paralelo_id)

    def crear(
        self,
        asignatura_codigo: str,
        periodo_nombre: str,
        docente_username: str,
        docente_rol: str,
        tipo_licencia_id: int,
        nombre: str,
        horario: str,
        capacidad_maxima: int,
        periodo_id: int,
        periodo_activo: bool,
        asignatura_id: int,
        usuario_id: int,
    ) -> ParaleloEntity:
        """
        Create a new parallel.

        Raises:
            DocenteInvalidoError, PeriodoInactivoError, ParaleloDuplicadoError
        """
        self.paralelo_service.validar_datos(
            docente_rol=docente_rol,
            periodo_activo=periodo_activo,
            combinacion_exists=self.paralelo_repo.exists(
                periodo_id=periodo_id,
                tipo_licencia_id=tipo_licencia_id,
                asignatura_id=asignatura_id,
                nombre=nombre,
            ),
        )

        entity = ParaleloEntity(
            asignatura_codigo=asignatura_codigo,
            periodo_nombre=periodo_nombre,
            docente_username=docente_username,
            nombre=nombre,
            horario=horario,
            tipo_licencia_id=tipo_licencia_id,
            capacidad_maxima=capacidad_maxima,
        )
        created = self.paralelo_repo.create(entity)

        self.auditoria_repo.registrar(
            RegistroAuditoriaEntity(
                accion="creacion_paralelo",
                usuario_id=usuario_id,
                detalle=f"Paralelo creado: {asignatura_codigo} — {nombre} ({periodo_nombre})",
            )
        )

        return created

    def actualizar(
        self,
        paralelo_id: int,
        asignatura_codigo: str,
        periodo_nombre: str,
        docente_username: str,
        docente_rol: str,
        tipo_licencia_id: int,
        nombre: str,
        horario: str,
        capacidad_maxima: int,
        periodo_id: int,
        periodo_activo: bool,
        asignatura_id: int,
        usuario_id: int,
    ) -> ParaleloEntity:
        """
        Update an existing parallel.

        Raises:
            DocenteInvalidoError, PeriodoInactivoError, ParaleloDuplicadoError
        """
        self.paralelo_service.validar_datos(
            docente_rol=docente_rol,
            periodo_activo=periodo_activo,
            combinacion_exists=self.paralelo_repo.exists(
                periodo_id=periodo_id,
                tipo_licencia_id=tipo_licencia_id,
                asignatura_id=asignatura_id,
                nombre=nombre,
                exclude_id=paralelo_id,
            ),
        )

        entity = ParaleloEntity(
            asignatura_codigo=asignatura_codigo,
            periodo_nombre=periodo_nombre,
            docente_username=docente_username,
            nombre=nombre,
            horario=horario,
            tipo_licencia_id=tipo_licencia_id,
            capacidad_maxima=capacidad_maxima,
        )
        updated = self.paralelo_repo.update(paralelo_id, entity)

        self.auditoria_repo.registrar(
            RegistroAuditoriaEntity(
                accion="actualizacion_paralelo",
                usuario_id=usuario_id,
                detalle=f"Paralelo actualizado: {asignatura_codigo} — {nombre} ({periodo_nombre})",
            )
        )

        return updated
