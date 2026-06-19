"""
Unit tests for the Reportes domain services (HU26).
Pure Python — no DB required.
"""

from decimal import Decimal

import pytest

from apps.reportes.domain.entities import DatosEstudianteReporte, TotalesReporte
from apps.reportes.domain.services import ReporteANTService


class TestCalcularEstadoEstudiante:
    def test_desertor_siempre_retorna_desertor(self):
        estado = ReporteANTService.calcular_estado_estudiante(
            promedio_final=Decimal("18.00"),
            porcentaje_asistencia=Decimal("90.00"),
            es_desertor=True,
        )
        assert estado == "desertor"

    def test_sin_promedio_retorna_en_curso(self):
        estado = ReporteANTService.calcular_estado_estudiante(
            promedio_final=None,
            porcentaje_asistencia=Decimal("80.00"),
        )
        assert estado == "en_curso"

    def test_aprobado_con_nota_y_asistencia_suficiente(self):
        estado = ReporteANTService.calcular_estado_estudiante(
            promedio_final=Decimal("16.00"),
            porcentaje_asistencia=Decimal("70.00"),
        )
        assert estado == "aprobado"

    def test_reprobado_por_nota_insuficiente(self):
        estado = ReporteANTService.calcular_estado_estudiante(
            promedio_final=Decimal("15.99"),
            porcentaje_asistencia=Decimal("90.00"),
        )
        assert estado == "reprobado"

    def test_reprobado_por_asistencia_insuficiente(self):
        estado = ReporteANTService.calcular_estado_estudiante(
            promedio_final=Decimal("18.00"),
            porcentaje_asistencia=Decimal("69.99"),
        )
        assert estado == "reprobado"

    def test_nota_exactamente_en_umbral_aprobacion(self):
        estado = ReporteANTService.calcular_estado_estudiante(
            promedio_final=Decimal("16.00"),
            porcentaje_asistencia=Decimal("100.00"),
        )
        assert estado == "aprobado"


class TestComputarHash:
    def test_hash_es_hexdigest_de_64_chars(self):
        resultado = ReporteANTService.computar_hash(b"contenido de prueba")
        assert len(resultado) == 64
        assert all(c in "0123456789abcdef" for c in resultado)

    def test_mismo_contenido_produce_mismo_hash(self):
        contenido = b"datos del reporte"
        assert ReporteANTService.computar_hash(contenido) == ReporteANTService.computar_hash(contenido)

    def test_contenidos_distintos_producen_hashes_distintos(self):
        h1 = ReporteANTService.computar_hash(b"reporte v1")
        h2 = ReporteANTService.computar_hash(b"reporte v2")
        assert h1 != h2

    def test_hash_bytes_vacios(self):
        resultado = ReporteANTService.computar_hash(b"")
        assert len(resultado) == 64


class TestConsolidarTotales:
    def _make_estudiante(self, estado: str) -> DatosEstudianteReporte:
        return DatosEstudianteReporte(
            cedula="1700000001",
            nombres_completos="Test User",
            paralelo_codigo="P1",
            materia_nombre="Conducción",
            porcentaje_asistencia=Decimal("90.00"),
            estado=estado,
        )

    def test_totales_vacios(self):
        totales = ReporteANTService.consolidar_totales([])
        assert totales == TotalesReporte(
            total=0, aprobados=0, reprobados=0, desertores=0, en_curso=0
        )

    def test_totales_mixtos(self):
        estudiantes = [
            self._make_estudiante("aprobado"),
            self._make_estudiante("aprobado"),
            self._make_estudiante("reprobado"),
            self._make_estudiante("desertor"),
            self._make_estudiante("en_curso"),
        ]
        totales = ReporteANTService.consolidar_totales(estudiantes)
        assert totales.total == 5
        assert totales.aprobados == 2
        assert totales.reprobados == 1
        assert totales.desertores == 1
        assert totales.en_curso == 1

    def test_totales_solo_aprobados(self):
        estudiantes = [self._make_estudiante("aprobado") for _ in range(3)]
        totales = ReporteANTService.consolidar_totales(estudiantes)
        assert totales.total == 3
        assert totales.aprobados == 3
        assert totales.reprobados == 0
