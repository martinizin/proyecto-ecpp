"""
Servicios de dominio para el bounded context de reportes.

- ``ReporteANTService`` (HU26): lógica pura de cálculo para el reporte
  normativo ANT (estado del estudiante, hash de integridad, totales).
- ``ReportesDisponibilidadService`` (HU27b): filtrado role-aware de
  ``Periodo``, ``Paralelo`` y ``Asignatura`` para el hub y el endpoint
  ``/reportes/preview/``. Mantiene la vista delgada y la DDD layering
  limpia (sin ``HttpResponse`` ni ``View``).
"""

import hashlib
from decimal import Decimal

from apps.academico.infrastructure.models import Asignatura, Paralelo, Periodo
from apps.reportes.domain.entities import DatosEstudianteReporte, TotalesReporte

NOTA_APROBACION = Decimal("16.00")
PORCENTAJE_ASISTENCIA_MINIMO = Decimal("70.00")


class ReporteANTService:
    """Pure domain logic for ANT report calculations."""

    @staticmethod
    def calcular_estado_estudiante(
        promedio_final: Decimal | None,
        porcentaje_asistencia: Decimal,
        es_desertor: bool = False,
    ) -> str:
        """Determine the student's final state for the report."""
        if es_desertor:
            return "desertor"
        if promedio_final is None:
            return "en_curso"
        if (
            promedio_final >= NOTA_APROBACION
            and porcentaje_asistencia >= PORCENTAJE_ASISTENCIA_MINIMO
        ):
            return "aprobado"
        return "reprobado"

    @staticmethod
    def computar_hash(contenido_bytes: bytes) -> str:
        """Return the SHA-256 hex digest of the given bytes."""
        return hashlib.sha256(contenido_bytes).hexdigest()

    @staticmethod
    def consolidar_totales(
        estudiantes: list[DatosEstudianteReporte],
    ) -> TotalesReporte:
        """Aggregate counters for the report header."""
        return TotalesReporte(
            total=len(estudiantes),
            aprobados=sum(1 for e in estudiantes if e.estado == "aprobado"),
            reprobados=sum(1 for e in estudiantes if e.estado == "reprobado"),
            desertores=sum(1 for e in estudiantes if e.estado == "desertor"),
            en_curso=sum(1 for e in estudiantes if e.estado == "en_curso"),
        )


class ReportesDisponibilidadService:
    """Role-aware list of ``Periodo``, ``Paralelo`` and ``Asignatura``
    for the export UX.

    Spec concern #2 (HU27b): keep DDD layering clean — view delegates,
    doesn't query. The service is pure read-only static methods.

    Reglas:
    - ``docente``: solo períodos/paralelos donde enseña (asignado al Paralelo).
    - ``inspector`` / ``secretaria``: todos los períodos/paralelos.
    - ``estudiante``: NO se llama al servicio; la vista rechaza con 403 antes.
    """

    @staticmethod
    def obtener_periodos_disponibles(usuario) -> list:
        """Retorna los períodos disponibles para el ``usuario`` según su rol.

        Para ``docente`` retorna los períodos donde tiene al menos un
        paralelo asignado. Para ``inspector`` / ``secretaria`` retorna
        todos los períodos ordenados por ``-fecha_inicio``.
        """
        if getattr(usuario, "rol", None) == "docente":
            return list(
                Periodo.objects.filter(paralelos__docente=usuario)
                .distinct()
                .order_by("-fecha_inicio")
            )
        # Inspector, secretaria, otros roles con permiso
        return list(Periodo.objects.all().order_by("-fecha_inicio"))

    @staticmethod
    def obtener_paralelos_disponibles(usuario, periodo) -> list:
        """Retorna los paralelos del ``periodo`` disponibles para el ``usuario`` según su rol.

        Para ``docente`` retorna solo los paralelos donde enseña en ese
        período. Para ``inspector`` / ``secretaria`` retorna todos los
        paralelos del período (con ``asignatura`` seleccionado para
        evitar N+1 en el template).
        """
        if getattr(usuario, "rol", None) == "docente":
            return list(
                Paralelo.objects.filter(periodo=periodo, docente=usuario).select_related(
                    "asignatura"
                )
            )
        return list(Paralelo.objects.filter(periodo=periodo).select_related("asignatura"))

    @staticmethod
    def obtener_materias_disponibles(usuario, periodo) -> list:
        """Retorna las asignaturas (materias) del ``periodo`` disponibles
        para el ``usuario`` según su rol.

        Para ``docente`` retorna las materias donde enseña en ese período
        (únicas). Para ``inspector`` / ``secretaria`` retorna todas las
        asignaturas del período. Se usa para poblar el filtro "Materia"
        del hub (3er paso del cascade Periodo > Curso > Materia).
        """
        if getattr(usuario, "rol", None) == "docente":
            return list(
                Asignatura.objects.filter(
                    paralelos__periodo=periodo,
                    paralelos__docente=usuario,
                )
                .distinct()
                .order_by("codigo")
            )
        return list(
            Asignatura.objects.filter(paralelos__periodo=periodo).distinct().order_by("codigo")
        )

    @staticmethod
    def obtener_todos_los_paralelos_para_filtros(usuario) -> list:
        """Retorna TODOS los paralelos del usuario (todos los periodos) para
        popular el JSON que se carga en el hub y se filtra client-side.

        Shape del dict (igual al patrón del módulo de rendimiento):
        ``{id, nombre, periodo_id, asignatura_id, asignatura_nombre}``.

        Para ``docente`` retorna solo sus paralelos. Para
        ``inspector`` / ``secretaria`` retorna todos.
        """
        qs = Paralelo.objects.select_related("asignatura", "periodo")
        if getattr(usuario, "rol", None) == "docente":
            qs = qs.filter(docente=usuario)
        return list(qs.order_by("periodo__fecha_inicio", "asignatura__codigo", "nombre"))
