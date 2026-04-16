"""
Domain services for the Asistencia bounded context.
Pure Python — NO Django imports allowed in this layer.

AsistenciaCalculoService: calculates attendance percentages (HU10).
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import List

from .exceptions import AsistenciaDuplicadaError


class AsistenciaCalculoService:
    """
    Pure domain service for attendance percentage calculations.

    Formulas (from PRD Sprint 2 — D20, D21):
    - % asistencia por asignatura = (presentes + justificadas) / total_sesiones × 100
    - % asistencia general = Σ(asistidas de todas) / Σ(total de todas) × 100
    - % inasistencia = 100 - % asistencia
    - Riesgo: verde (<5% inasistencia), rojo (≥5% inasistencia)

    Umbral de riesgo: 5% de inasistencia (= 95% de asistencia requerida).
    """

    UMBRAL_INASISTENCIA = Decimal("5.00")

    def calcular_porcentaje_asistencia(
        self, sesiones_asistidas: int, total_sesiones: int
    ) -> Decimal:
        """
        Calculate attendance percentage for a single subject/paralelo.

        Args:
            sesiones_asistidas: Count of PRESENTE + JUSTIFICADO records.
            total_sesiones: Total attendance records for this paralelo.

        Returns:
            Attendance percentage (0-100), rounded to 2 decimals.
            Returns 100 if total_sesiones == 0 (no records = 0% inasistencia).
        """
        if total_sesiones == 0:
            return Decimal("100.00")
        porcentaje = (Decimal(sesiones_asistidas) / Decimal(total_sesiones)) * 100
        return porcentaje.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def calcular_porcentaje_inasistencia(
        self, sesiones_asistidas: int, total_sesiones: int
    ) -> Decimal:
        """
        Calculate absence percentage for a single subject/paralelo.

        Returns:
            Absence percentage (0-100), rounded to 2 decimals.
            Returns 0 if total_sesiones == 0.
        """
        asistencia = self.calcular_porcentaje_asistencia(
            sesiones_asistidas, total_sesiones
        )
        return (Decimal("100.00") - asistencia).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    def calcular_porcentaje_general(
        self, datos_por_asignatura: List[dict]
    ) -> Decimal:
        """
        Calculate overall attendance percentage across all subjects.

        Args:
            datos_por_asignatura: List of dicts with keys:
                - 'sesiones_asistidas': int
                - 'total_sesiones': int

        Returns:
            Overall attendance percentage (0-100), rounded to 2 decimals.
            Returns 100 if no sessions recorded at all.
        """
        total_asistidas = sum(d["sesiones_asistidas"] for d in datos_por_asignatura)
        total_sesiones = sum(d["total_sesiones"] for d in datos_por_asignatura)

        return self.calcular_porcentaje_asistencia(total_asistidas, total_sesiones)

    def calcular_inasistencia_general(
        self, datos_por_asignatura: List[dict]
    ) -> Decimal:
        """
        Calculate overall absence percentage across all subjects.

        Returns:
            Overall absence percentage (0-100), rounded to 2 decimals.
        """
        asistencia = self.calcular_porcentaje_general(datos_por_asignatura)
        return (Decimal("100.00") - asistencia).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    def evaluar_riesgo(self, porcentaje_inasistencia: Decimal) -> str:
        """
        Evaluate risk level based on absence percentage.

        Args:
            porcentaje_inasistencia: Absence percentage (0-100).

        Returns:
            "rojo" if >= 5% absence, "verde" otherwise.
        """
        if porcentaje_inasistencia >= self.UMBRAL_INASISTENCIA:
            return "rojo"
        return "verde"
