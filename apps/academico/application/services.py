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
from apps.academico.domain.exceptions import AcademicoError
from apps.academico.domain.services import (
    AsignaturaService,
    ParaleloService,
    PeriodoService,
)
from apps.academico.infrastructure.repositories import (
    DjangoAsignaturaRepository,
    DjangoParaleloRepository,
    DjangoPeriodoRepository,
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
        tipo_licencia_id: int,
        creado_por_id: int,
    ) -> PeriodoEntity:
        """
        Create a new academic period linked to a license type.

        Raises:
            PeriodoSolapadoError: If fecha_inicio >= fecha_fin.
        """
        self.periodo_service.validar_fechas(fecha_inicio, fecha_fin)

        entity = PeriodoEntity(
            nombre=nombre,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            tipo_licencia_id=tipo_licencia_id,
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
        tipo_licencia_id: int | None = None,
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
            tipo_licencia_id=tipo_licencia_id or (existing.tipo_licencia_id if existing else None),
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
        Activate a period, enforcing one-active-per-tipo-licencia invariant.

        Args:
            periodo_id: ID of the period to activate.
            usuario_id: ID of the user performing the action.
            confirmar_desactivacion: Whether user confirmed deactivation of current active.

        Returns:
            True if activation succeeded.

        Raises:
            PeriodoActivoExistenteError: If another period of the same tipo_licencia
                is active and not confirmed.
        """
        periodo = self.periodo_repo.get_by_id(periodo_id)
        activo = self.periodo_repo.get_activo_por_tipo(periodo.tipo_licencia_id)
        periodo_activo_nombre = activo.nombre if activo else None

        # Domain check — may raise PeriodoActivoExistenteError
        self.periodo_service.verificar_activacion(
            periodo_activo_actual=periodo_activo_nombre,
            confirmar_desactivacion=confirmar_desactivacion,
        )

        # Deactivate current for this tipo_licencia if exists
        if activo:
            self.periodo_repo.desactivar_por_tipo(periodo.tipo_licencia_id)
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

    @transaction.atomic
    def desactivar(self, periodo_id: int, usuario_id: int) -> bool:
        """
        Deactivate a period manually.

        Args:
            periodo_id: ID of the period to deactivate.
            usuario_id: ID of the user performing the action.

        Returns:
            True if deactivation succeeded.
        """
        periodo = self.periodo_repo.get_by_id(periodo_id)
        if not periodo:
            raise AcademicoError("El período no existe.")
        if not periodo.activo:
            raise AcademicoError("El período ya se encuentra inactivo.")

        self.periodo_repo.desactivar(periodo_id)
        self.auditoria_repo.registrar(
            RegistroAuditoriaEntity(
                accion="cambio_estado_periodo",
                usuario_id=usuario_id,
                detalle=f"Período desactivado manualmente: {periodo.nombre}",
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
        licencias: List[dict],
        usuario_id: int,
        descripcion: str = "",
    ) -> AsignaturaEntity:
        """
        Create a new subject.

        Args:
            licencias: List of {"tipo_licencia_id": int, "horas_lectivas": int}.

        Raises:
            AsignaturaCodigoDuplicadoError, ValueError
        """
        self.asignatura_service.validar_datos(
            codigo=codigo,
            licencias=licencias,
            codigo_exists=self.asignatura_repo.codigo_exists(codigo),
        )

        entity = AsignaturaEntity(
            nombre=nombre,
            codigo=codigo,
            descripcion=descripcion,
            licencias=licencias,
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
        licencias: List[dict],
        usuario_id: int,
        descripcion: str = "",
    ) -> AsignaturaEntity:
        """
        Update an existing subject.

        Args:
            licencias: List of {"tipo_licencia_id": int, "horas_lectivas": int}.

        Raises:
            AsignaturaCodigoDuplicadoError, ValueError
        """
        self.asignatura_service.validar_datos(
            codigo=codigo,
            licencias=licencias,
            codigo_exists=self.asignatura_repo.codigo_exists(codigo, exclude_id=asignatura_id),
        )

        entity = AsignaturaEntity(
            nombre=nombre,
            codigo=codigo,
            descripcion=descripcion,
            licencias=licencias,
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

    def eliminar_asignatura(self, asignatura_id: int, usuario_id: int):
        """
        Delete an asignatura if it has no paralelos associated.

        Raises:
            AcademicoError: If the asignatura has paralelos.
        """
        from apps.academico.infrastructure.models import Asignatura

        try:
            asignatura = Asignatura.objects.get(pk=asignatura_id)
        except Asignatura.DoesNotExist:
            raise AcademicoError("La asignatura no existe.")

        if asignatura.paralelos.count() > 0:
            raise AcademicoError(
                "No se puede eliminar la asignatura porque tiene paralelos "
                "asociados. Elimine los paralelos primero."
            )

        codigo = asignatura.codigo
        nombre = asignatura.nombre

        self.asignatura_repo.eliminar(asignatura_id)

        self.auditoria_repo.registrar(
            RegistroAuditoriaEntity(
                accion="eliminacion_asignatura",
                usuario_id=usuario_id,
                detalle=f"Asignatura eliminada: {codigo} — {nombre}",
            )
        )


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

    def crear_lote(
        self,
        asignaturas: list,
        periodo,
        tipo_licencia,
        docente,
        nombre: str,
        capacidad_maxima: int,
        usuario_id: int,
    ):
        """
        Create one paralelo per selected asignatura (batch creation).

        Validates docente role and active period once, then checks uniqueness
        per asignatura. Skips duplicates and reports them.

        Returns:
            Tuple of (list of created ParaleloEntity, list of skipped asignatura codigos).

        Raises:
            DocenteInvalidoError, PeriodoInactivoError
        """
        self.paralelo_service.validar_docente(docente.rol)
        self.paralelo_service.validar_periodo_activo(periodo.activo)

        created_list = []
        duplicados = []

        for asignatura in asignaturas:
            if self.paralelo_repo.exists(
                periodo_id=periodo.pk,
                tipo_licencia_id=tipo_licencia.pk,
                asignatura_id=asignatura.pk,
                nombre=nombre,
            ):
                duplicados.append(asignatura.codigo)
                continue

            entity = ParaleloEntity(
                asignatura_codigo=asignatura.codigo,
                periodo_nombre=periodo.nombre,
                docente_username=docente.username,
                nombre=nombre,
                tipo_licencia_id=tipo_licencia.pk,
                capacidad_maxima=capacidad_maxima,
            )
            created = self.paralelo_repo.create(entity)
            created_list.append(created)

        if created_list:
            codigos = ", ".join(c.asignatura_codigo for c in created_list)
            self.auditoria_repo.registrar(
                RegistroAuditoriaEntity(
                    accion="creacion_paralelos_lote",
                    usuario_id=usuario_id,
                    detalle=(
                        f"Lote de {len(created_list)} paralelos creados: "
                        f"{codigos} — {nombre} ({periodo.nombre})"
                    ),
                )
            )

        return created_list, duplicados

    def actualizar(
        self,
        paralelo_id: int,
        asignatura_codigo: str,
        periodo_nombre: str,
        docente_username: str,
        docente_rol: str,
        tipo_licencia_id: int,
        nombre: str,
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

    def eliminar_paralelo(self, paralelo_id: int, usuario_id: int):
        """Delete a paralelo if it has no dependents."""
        from apps.academico.infrastructure.models import Paralelo

        try:
            paralelo = Paralelo.objects.select_related("asignatura", "periodo").get(pk=paralelo_id)
        except Paralelo.DoesNotExist:
            raise AcademicoError("El paralelo no existe.")

        bloqueos = []
        matriculas_count = paralelo.matriculas.count()
        asistencias_count = paralelo.asistencias.count()
        evaluaciones_count = paralelo.evaluaciones.count()

        if matriculas_count > 0:
            bloqueos.append(f"{matriculas_count} matrícula(s)")
        if asistencias_count > 0:
            bloqueos.append(f"{asistencias_count} asistencia(s)")
        if evaluaciones_count > 0:
            bloqueos.append(f"{evaluaciones_count} evaluación(es)")

        if bloqueos:
            raise AcademicoError(
                f"No se puede eliminar el paralelo porque tiene: " f"{', '.join(bloqueos)}."
            )

        detalle = (
            f"Paralelo eliminado: {paralelo.asignatura.codigo} "
            f"— {paralelo.nombre} ({paralelo.periodo.nombre})"
        )

        self.paralelo_repo.eliminar(paralelo_id)

        self.auditoria_repo.registrar(
            RegistroAuditoriaEntity(
                accion="eliminacion_paralelo",
                usuario_id=usuario_id,
                detalle=detalle,
            )
        )


class DashboardRendimientoAppService:
    """
    Application service that aggregates academic performance metrics
    across calificaciones and asistencia for a given periodo.
    Refs: HU23 — Dashboard de rendimiento por curso.
    """

    def obtener_metricas_por_periodo(
        self,
        periodo_id: int,
        asignatura_id: int | None = None,
        paralelo_id: int | None = None,
    ):
        """
        Returns a list of MetricasParalelo for all paralelos in the given
        periodo. Optionally filtered by asignatura and/or a specific paralelo.

        Args:
            periodo_id: ID of the academic period.
            asignatura_id: Optional ID to filter by subject.
            paralelo_id: Optional ID to filter by a specific paralelo (curso).

        Returns:
            List[MetricasParalelo]
        """
        from decimal import Decimal

        from django.db.models import Avg

        from apps.academico.infrastructure.models import Matricula, Paralelo
        from apps.asistencia.infrastructure.models import Asistencia
        from apps.calificaciones.infrastructure.models import Calificacion
        from apps.academico.domain.services import RendimientoAcademicoService
        from apps.academico.domain.value_objects import MetricasParalelo

        svc = RendimientoAcademicoService()

        paralelos = Paralelo.objects.filter(
            periodo_id=periodo_id
        ).select_related("asignatura", "docente", "periodo")

        if asignatura_id:
            paralelos = paralelos.filter(asignatura_id=asignatura_id)

        if paralelo_id:
            paralelos = paralelos.filter(id=paralelo_id)

        metricas = []
        for paralelo in paralelos:
            total_estudiantes = paralelo.matriculas.filter(
                estado=Matricula.Estado.ACTIVA
            ).count()

            estudiante_ids = list(
                paralelo.matriculas.filter(
                    estado=Matricula.Estado.ACTIVA
                ).values_list("estudiante_id", flat=True)
            )

            # Build weighted average per student
            aprobados = 0
            reprobados = 0
            for est_id in estudiante_ids:
                notas_pesos = list(
                    Calificacion.objects.filter(
                        evaluacion__paralelo=paralelo,
                        estudiante_id=est_id,
                    ).values_list("nota", "evaluacion__peso")
                )
                if not notas_pesos:
                    continue
                resultados = svc.calcular_promedios_por_estudiante(
                    [(est_id, [(Decimal(str(n)), Decimal(str(p))) for n, p in notas_pesos])]
                )
                if resultados:
                    _, promedio = resultados[0]
                    if svc.clasificar_estudiante(promedio) == "aprobado":
                        aprobados += 1
                    else:
                        reprobados += 1

            # Overall average (all individual grades in paralelo)
            todas_notas = list(
                Calificacion.objects.filter(
                    evaluacion__paralelo=paralelo
                ).values_list("nota", flat=True)
            )
            promedio_general = svc.calcular_promedio_paralelo(
                [Decimal(str(n)) for n in todas_notas]
            )

            # Attendance
            total_registros = Asistencia.objects.filter(paralelo=paralelo).count()
            presentes = Asistencia.objects.filter(
                paralelo=paralelo,
                estado__in=["presente", "justificado"],
            ).count()

            porcentaje_asistencia = svc.calcular_porcentaje_asistencia(
                presentes, total_registros
            )
            total_con_notas = aprobados + reprobados

            metricas.append(
                MetricasParalelo(
                    paralelo_id=paralelo.id,
                    paralelo_nombre=str(paralelo),
                    asignatura_nombre=paralelo.asignatura.nombre,
                    asignatura_codigo=paralelo.asignatura.codigo,
                    docente_nombre=(
                        paralelo.docente.get_full_name()
                        if paralelo.docente
                        else "—"
                    ),
                    promedio_general=promedio_general,
                    porcentaje_asistencia=porcentaje_asistencia,
                    tasa_aprobacion=svc.calcular_tasa_aprobacion(aprobados, total_estudiantes),
                    tasa_reprobacion=svc.calcular_tasa_aprobacion(reprobados, total_estudiantes),
                    total_estudiantes=total_estudiantes,
                    estudiantes_aprobados=aprobados,
                    estudiantes_reprobados=reprobados,
                    estudiantes_en_curso=max(0, total_estudiantes - total_con_notas),
                )
            )

        return metricas

    def obtener_tendencia_parciales(self, paralelo_id: int):
        """
        Returns average grade per evaluation type for a specific paralelo,
        sorted by evaluation type order for Chart.js line chart.

        Returns:
            List[dict] — [{evaluacion, tipo, promedio}, ...]
        """
        from decimal import Decimal
        from django.db.models import Avg
        from apps.calificaciones.infrastructure.models import Calificacion, Evaluacion

        ORDEN_TIPOS = [
            "parcial1", "parcial2_10h", "parcial3", "parcial4_10h",
            "proyecto", "examen_final",
        ]

        evaluaciones = Evaluacion.objects.filter(
            paralelo_id=paralelo_id
        ).order_by("tipo")

        evaluaciones_ordenadas = sorted(
            evaluaciones,
            key=lambda e: ORDEN_TIPOS.index(e.tipo) if e.tipo in ORDEN_TIPOS else 99,
        )

        tendencia = []
        for evaluacion in evaluaciones_ordenadas:
            promedio = Calificacion.objects.filter(
                evaluacion=evaluacion
            ).aggregate(avg=Avg("nota"))["avg"]

            tendencia.append({
                "evaluacion": evaluacion.get_tipo_display(),
                "tipo": evaluacion.tipo,
                "promedio": float(Decimal(str(promedio)).quantize(Decimal("0.01"))) if promedio else None,
            })

        return tendencia
