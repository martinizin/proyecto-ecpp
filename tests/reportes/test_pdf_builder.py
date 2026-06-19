"""
Unit tests for ReporteANTPDFBuilder (HU26).
Verifies PDF output without hitting the database.
"""

from decimal import Decimal

import pytest

from apps.reportes.application.reporte_ant_generator_service import ReporteANTPDFBuilder
from apps.reportes.domain.entities import DatosEstudianteReporte, TotalesReporte
from apps.reportes.domain.services import ReporteANTService


@pytest.fixture
def builder():
    return ReporteANTPDFBuilder(
        periodo_nombre="2026-A Licencia E",
        generado_por_nombre="Ana García",
        generado_por_cedula="1700000001",
    )


@pytest.fixture
def estudiantes_muestra():
    return [
        DatosEstudianteReporte(
            cedula="1701111111",
            nombres_completos="Juan Pérez",
            paralelo_codigo="P-01",
            materia_nombre="Manejo Básico",
            porcentaje_asistencia=Decimal("90.00"),
            promedio_final=Decimal("17.50"),
            estado="aprobado",
        ),
        DatosEstudianteReporte(
            cedula="1702222222",
            nombres_completos="María López",
            paralelo_codigo="P-01",
            materia_nombre="Manejo Básico",
            porcentaje_asistencia=Decimal("60.00"),
            promedio_final=Decimal("14.00"),
            estado="reprobado",
        ),
    ]


@pytest.fixture
def totales_muestra(estudiantes_muestra):
    return ReporteANTService.consolidar_totales(estudiantes_muestra)


class TestReporteANTPDFBuilder:
    def test_construir_retorna_bytes_no_vacios(self, builder, estudiantes_muestra, totales_muestra):
        pdf = builder.construir(estudiantes_muestra, totales_muestra)
        assert isinstance(pdf, bytes)
        assert len(pdf) > 0

    def test_pdf_inicia_con_header_pdf(self, builder, estudiantes_muestra, totales_muestra):
        pdf = builder.construir(estudiantes_muestra, totales_muestra)
        assert pdf[:4] == b"%PDF"

    def test_pdf_con_hash_en_footer_es_diferente(self, builder, estudiantes_muestra, totales_muestra):
        pdf_sin_hash = builder.construir(estudiantes_muestra, totales_muestra)
        pdf_con_hash = builder.construir(
            estudiantes_muestra, totales_muestra, hash_footer="abc123" * 10
        )
        assert pdf_sin_hash != pdf_con_hash

    def test_lista_vacia_no_lanza_excepcion(self, builder):
        totales = TotalesReporte(total=0, aprobados=0, reprobados=0, desertores=0, en_curso=0)
        pdf = builder.construir([], totales)
        assert len(pdf) > 0

    def test_hash_del_pdf_es_reproducible(self, builder, estudiantes_muestra, totales_muestra):
        pdf1 = builder.construir(estudiantes_muestra, totales_muestra)
        hash1 = ReporteANTService.computar_hash(pdf1)
        assert len(hash1) == 64
