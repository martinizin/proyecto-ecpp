"""
Domain services for the Reportes bounded context.
Pure Python — NO Django imports allowed in this layer.
"""

import hashlib
from decimal import Decimal

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
