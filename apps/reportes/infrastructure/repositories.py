"""
Django ORM implementation of the Reportes repository interfaces.
"""

from apps.reportes.domain.repositories import IReporteANTRepository
from apps.reportes.infrastructure.models import ReporteANT


class DjangoReporteANTRepository(IReporteANTRepository):
    """Concrete repository backed by Django ORM."""

    def guardar(self, reporte_data: dict) -> ReporteANT:
        return ReporteANT.objects.create(**reporte_data)

    def listar_por_periodo(self, periodo_id: int):
        return ReporteANT.objects.filter(periodo_id=periodo_id).order_by(
            "-fecha_generacion"
        )

    def obtener_por_id(self, reporte_id: int):
        return ReporteANT.objects.filter(pk=reporte_id).first()
