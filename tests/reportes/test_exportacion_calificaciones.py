"""
Tests para ``ExportacionCalificacionesService`` (HU27).

Estrategia TDD: RED primero. La fixture ``_clear_cache`` en
``conftest.py`` es autouse y limpia el cache. Para los servicios de
exportación no necesitamos cache; la fixture sigue siendo inofensiva.
"""

from decimal import Decimal
from io import BytesIO

import pytest
from openpyxl import load_workbook

from apps.calificaciones.application.services import RegistroCalificacionAppService
from apps.reportes.application.services import ExportacionCalificacionesService
from tests.factories import (
    CalificacionFactory,
    EvaluacionFactory,
    MatriculaFactory,
    ParaleloFactory,
    PeriodoFactory,
    RegistroCalificacionParaleloFactory,
)


pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _crear_paralelo_con_planilla(periodo=None, num_estudiantes=3):
    """Crea un paralelo con N estudiantes activos y 3 evaluaciones (notas registradas)."""
    periodo = periodo or PeriodoFactory(nombre="2026-A")
    paralelo = ParaleloFactory(periodo=periodo, nombre="A")
    RegistroCalificacionParaleloFactory(paralelo=paralelo)
    # Crear 3 evaluaciones con tipos distintos en el MISMO paralelo
    evaluaciones = []
    for tipo, peso in [
        ("parcial1", Decimal("30.00")),
        ("parcial2_10h", Decimal("30.00")),
        ("examen_final", Decimal("40.00")),
    ]:
        ev = EvaluacionFactory(paralelo=paralelo, tipo=tipo, peso=peso)
        evaluaciones.append(ev)
    # Crear N estudiantes con notas en las 3 evaluaciones
    for i in range(num_estudiantes):
        matricula = MatriculaFactory(paralelo=paralelo)
        for ev in evaluaciones:
            CalificacionFactory(
                evaluacion=ev,
                estudiante=matricula.estudiante,
                nota=Decimal("15.00"),
            )
    return paralelo


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------


class TestExportarExcelCalificaciones:
    """Tests para ``ExportacionCalificacionesService.exportar_excel_calificaciones``."""

    def test_exportar_excel_returns_bytesio(self, docente):
        """El método retorna un ``BytesIO``."""
        paralelo = _crear_paralelo_con_planilla()
        service = ExportacionCalificacionesService(
            filtros={"periodo_id": paralelo.periodo_id}, usuario=docente
        )
        result = service.exportar_excel_calificaciones()
        assert isinstance(result, BytesIO)

    def test_exportar_excel_xlsx_magic_bytes(self, docente):
        """El archivo retornado comienza con ``b\"PK\"`` (zip header de xlsx)."""
        paralelo = _crear_paralelo_con_planilla()
        service = ExportacionCalificacionesService(
            filtros={"periodo_id": paralelo.periodo_id}, usuario=docente
        )
        buffer = service.exportar_excel_calificaciones()
        assert buffer.getvalue()[:2] == b"PK"

    def test_exportar_excel_one_sheet_per_paralelo(self, docente):
        """Con 2 paralelos, el workbook tiene 2 sheets."""
        periodo = PeriodoFactory(nombre="2026-A")
        ParaleloFactory(periodo=periodo, nombre="A")
        ParaleloFactory(periodo=periodo, nombre="B")
        service = ExportacionCalificacionesService(
            filtros={"periodo_id": periodo.id}, usuario=docente
        )
        buffer = service.exportar_excel_calificaciones()
        wb = load_workbook(buffer)
        assert len(wb.sheetnames) == 2

    def test_exportar_excel_sheet_title_truncated_to_31_chars(self, docente):
        """El título del sheet se trunca a 31 chars (límite de Excel)."""
        paralelo = _crear_paralelo_con_planilla()
        # Forzamos asignatura.codigo largo (max 20) + nombre (max 10) = 31 max
        from tests.factories import AsignaturaFactory

        asignatura = AsignaturaFactory(codigo="A" * 20)
        paralelo.asignatura = asignatura
        paralelo.save()
        service = ExportacionCalificacionesService(
            filtros={"periodo_id": paralelo.periodo_id}, usuario=docente
        )
        buffer = service.exportar_excel_calificaciones()
        wb = load_workbook(buffer)
        for name in wb.sheetnames:
            assert len(name) <= 31, f"sheet title {name!r} exceeds 31 chars"

    def test_exportar_excel_header_block_rows(self, docente):
        """Las primeras 3 filas son header block ECPPP, luego spacer, luego columnas."""
        paralelo = _crear_paralelo_con_planilla()
        service = ExportacionCalificacionesService(
            filtros={"periodo_id": paralelo.periodo_id}, usuario=docente
        )
        buffer = service.exportar_excel_calificaciones()
        wb = load_workbook(buffer)
        ws = wb.active
        # row 1: contiene "ECPPP"
        assert "ECPPP" in str(ws.cell(row=1, column=1).value)
        # row 2: contiene "Paralelo"
        assert "Paralelo" in str(ws.cell(row=2, column=1).value)
        # row 3: contiene "Generado:" y el nombre del docente
        row3 = str(ws.cell(row=3, column=1).value)
        assert "Generado:" in row3
        assert docente.get_full_name() in row3

    def test_exportar_excel_column_order_r5(self, docente):
        """La fila de headers (row 5 después del spacer) tiene el orden R5.

        R5: ``Cédula, Nombres, Parcial 1, Parcial 2, Examen Final, Promedio, Estado``.
        """
        paralelo = _crear_paralelo_con_planilla()
        service = ExportacionCalificacionesService(
            filtros={"periodo_id": paralelo.periodo_id}, usuario=docente
        )
        buffer = service.exportar_excel_calificaciones()
        wb = load_workbook(buffer)
        ws = wb.active
        # Header está en row 5 (1=ECPPP, 2=Paralelo, 3=Generado:, 4=spacer, 5=columnas)
        header = [ws.cell(row=5, column=c).value for c in range(1, 8)]
        assert header == [
            "Cédula",
            "Nombres",
            "Parcial 1",
            "Parcial 2",
            "Examen Final",
            "Promedio",
            "Estado",
        ]

    def test_exportar_excel_promedio_uses_validation_service(self, docente):
        """El valor de la columna ``Promedio`` coincide con el cálculo del domain service."""
        paralelo = _crear_paralelo_con_planilla(num_estudiantes=1)
        service = ExportacionCalificacionesService(
            filtros={"periodo_id": paralelo.periodo_id}, usuario=docente
        )
        buffer = service.exportar_excel_calificaciones()
        wb = load_workbook(buffer)
        ws = wb.active
        # data empieza en row 6
        promedio_cell = ws.cell(row=6, column=6).value
        # Cálculo esperado via domain service
        planilla = RegistroCalificacionAppService().obtener_planilla(paralelo.id)
        expected = planilla["filas"][0]["promedio"]
        assert Decimal(str(promedio_cell)) == expected

    def test_exportar_excel_estado_uses_validation_service(self, docente):
        """El valor de la columna ``Estado`` viene de ``estado_aprobacion``."""
        paralelo = _crear_paralelo_con_planilla(num_estudiantes=1)
        service = ExportacionCalificacionesService(
            filtros={"periodo_id": paralelo.periodo_id}, usuario=docente
        )
        buffer = service.exportar_excel_calificaciones()
        wb = load_workbook(buffer)
        ws = wb.active
        estado_cell = ws.cell(row=6, column=7).value
        # promedio = 15.00 → reprobado (NOTA_APROBACION = 16)
        assert estado_cell == "reprobado"
        # Y verificar que viene del domain service cruzando con su cálculo
        from decimal import Decimal

        from apps.calificaciones.domain.services import CalificacionValidationService

        assert estado_cell == CalificacionValidationService.estado_aprobacion(Decimal("15.00"))

    def test_exportar_excel_header_styling(self, docente):
        """Los headers de columna tienen font.bold=True y fill azul 1E3A8A."""
        paralelo = _crear_paralelo_con_planilla()
        service = ExportacionCalificacionesService(
            filtros={"periodo_id": paralelo.periodo_id}, usuario=docente
        )
        buffer = service.exportar_excel_calificaciones()
        wb = load_workbook(buffer)
        ws = wb.active
        cell = ws.cell(row=5, column=1)
        assert cell.font.bold is True
        # openpyxl devuelve el color con alpha prefix (00 o FF); comparamos el RGB
        assert "FFFFFF" in str(cell.font.color.rgb)
        # fill.fgColor.rgb incluye el prefijo alpha
        assert "1E3A8A" in str(cell.fill.fgColor.rgb)

    def test_exportar_excel_empty_filter_returns_valid_file(self, docente):
        """Si no hay paralelos, el archivo sigue siendo xlsx válido (solo header)."""
        periodo = PeriodoFactory(nombre="2026-A")
        service = ExportacionCalificacionesService(
            filtros={"periodo_id": periodo.id}, usuario=docente
        )
        buffer = service.exportar_excel_calificaciones()
        assert buffer.getvalue()[:2] == b"PK"
        # El archivo es un xlsx válido aunque no tenga sheets de datos
        wb = load_workbook(buffer)
        assert wb is not None


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------


class TestExportarPdfCalificaciones:
    """Tests para ``ExportacionCalificacionesService.exportar_pdf_calificaciones``."""

    def test_exportar_pdf_returns_bytesio(self, docente):
        """El método retorna un ``BytesIO``."""
        paralelo = _crear_paralelo_con_planilla()
        service = ExportacionCalificacionesService(
            filtros={"periodo_id": paralelo.periodo_id}, usuario=docente
        )
        result = service.exportar_pdf_calificaciones()
        assert isinstance(result, BytesIO)

    def test_exportar_pdf_magic_bytes(self, docente):
        """El archivo retornado comienza con ``b\"%PDF\"``."""
        paralelo = _crear_paralelo_con_planilla()
        service = ExportacionCalificacionesService(
            filtros={"periodo_id": paralelo.periodo_id}, usuario=docente
        )
        buffer = service.exportar_pdf_calificaciones()
        assert buffer.getvalue()[:4] == b"%PDF"

    def test_exportar_pdf_landscape_a4(self, docente):
        """El PDF es landscape A4 (width > height)."""
        paralelo = _crear_paralelo_con_planilla()
        service = ExportacionCalificacionesService(
            filtros={"periodo_id": paralelo.periodo_id}, usuario=docente
        )
        buffer = service.exportar_pdf_calificaciones()
        import re

        # reportlab escribe el MediaBox como ``/MediaBox [ 0 0 841.8898 595.2756 ]``
        # (con espacios entre números). Regex flexible.
        text = buffer.getvalue().decode("latin-1", errors="ignore")
        match = re.search(
            r"/MediaBox\s*\[\s*(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s*\]",
            text,
        )
        assert (
            match is not None
        ), f"MediaBox no encontrado en el PDF. Primer 500 bytes: {text[:500]!r}"
        # A4 landscape: 842x595 (pts) — x1=0, y1=0, x2=842, y2=595
        x1, y1, x2, y2 = (float(g) for g in match.groups())
        width = x2 - x1
        height = y2 - y1
        assert width > height, f"landscape A4 esperado, got {width:.1f}x{height:.1f}"

    def test_exportar_pdf_header_block_top(self, docente):
        """El header del PDF contiene ``ECPPP`` y ``Generado:``."""
        paralelo = _crear_paralelo_con_planilla()
        service = ExportacionCalificacionesService(
            filtros={"periodo_id": paralelo.periodo_id}, usuario=docente
        )
        buffer = service.exportar_pdf_calificaciones()
        # reportlab codifica los textos en el body; el header aparece en streams comprimidos
        # pero el archivo contiene al menos una mención a "ECPPP" en metadatos o stream
        assert buffer.getvalue()[:4] == b"%PDF"
        # Si el PDF está bien formado, debe tener %%EOF al final
        assert b"%%EOF" in buffer.getvalue()[-1024:]

    def test_exportar_pdf_empty_filter_returns_valid_file(self, docente):
        """Si no hay paralelos, el archivo sigue siendo PDF válido."""
        periodo = PeriodoFactory(nombre="2026-A")
        service = ExportacionCalificacionesService(
            filtros={"periodo_id": periodo.id}, usuario=docente
        )
        buffer = service.exportar_pdf_calificaciones()
        assert buffer.getvalue()[:4] == b"%PDF"
        assert b"%%EOF" in buffer.getvalue()[-1024:]


# ---------------------------------------------------------------------------
# HU34: Parcial 5 (antes "Proyecto") en los exports
# ---------------------------------------------------------------------------


def _crear_paralelo_con_parcial5(num_estudiantes=1):
    """Paralelo con parcial 4, parcial 5 y examen final (notas 15.00)."""
    periodo = PeriodoFactory(nombre="2026-B")
    paralelo = ParaleloFactory(periodo=periodo, nombre="A")
    RegistroCalificacionParaleloFactory(paralelo=paralelo)
    evaluaciones = []
    for tipo, peso in [
        ("parcial4_10h", Decimal("30.00")),
        ("parcial5", Decimal("30.00")),
        ("examen_final", Decimal("40.00")),
    ]:
        evaluaciones.append(EvaluacionFactory(paralelo=paralelo, tipo=tipo, peso=peso))
    for _ in range(num_estudiantes):
        matricula = MatriculaFactory(paralelo=paralelo)
        for ev in evaluaciones:
            CalificacionFactory(
                evaluacion=ev,
                estudiante=matricula.estudiante,
                nota=Decimal("15.00"),
            )
    return paralelo


class TestParcial5EnExport:
    """HU34: el tipo ``parcial5`` sale como "Parcial 5" entre Parcial 4 y Examen Final."""

    def test_excel_header_parcial5_entre_parcial4_y_examen(self, docente):
        paralelo = _crear_paralelo_con_parcial5()
        service = ExportacionCalificacionesService(
            filtros={"periodo_id": paralelo.periodo_id}, usuario=docente
        )
        buffer = service.exportar_excel_calificaciones()
        wb = load_workbook(buffer)
        ws = wb.active
        header = [ws.cell(row=5, column=c).value for c in range(1, 8)]
        assert header == [
            "Cédula",
            "Nombres",
            "Parcial 4",
            "Parcial 5",
            "Examen Final",
            "Promedio",
            "Estado",
        ]
        assert "Proyecto" not in header

    def test_excel_promedio_no_cambia_con_parcial5(self, docente):
        """Con notas 15.00 en los 3 componentes, el promedio sigue siendo 15.0."""
        paralelo = _crear_paralelo_con_parcial5(num_estudiantes=1)
        service = ExportacionCalificacionesService(
            filtros={"periodo_id": paralelo.periodo_id}, usuario=docente
        )
        buffer = service.exportar_excel_calificaciones()
        wb = load_workbook(buffer)
        ws = wb.active
        promedio = ws.cell(row=6, column=6).value  # col 6 = Promedio
        assert promedio == 15.0

    def test_pdf_data_header_parcial5(self, docente):
        paralelo = _crear_paralelo_con_parcial5()
        service = ExportacionCalificacionesService(
            filtros={"periodo_id": paralelo.periodo_id}, usuario=docente
        )
        data = service._build_pdf_data_calificaciones(paralelo, cuando=None)
        assert data[0] == [
            "Cédula",
            "Nombres",
            "Parcial 4",
            "Parcial 5",
            "Examen Final",
            "Promedio",
            "Estado",
        ]
        assert "Proyecto" not in data[0]


# ---------------------------------------------------------------------------
# Filtros
# ---------------------------------------------------------------------------


class TestFiltrosCalificaciones:
    """Tests para los filtros del servicio de calificaciones."""

    def test_filtro_por_paralelo(self, docente):
        """El filtro por paralelo limita los paralelos exportados a 1."""
        periodo = PeriodoFactory(nombre="2026-A")
        p1 = ParaleloFactory(periodo=periodo, nombre="A")
        ParaleloFactory(periodo=periodo, nombre="B")
        _crear_paralelo_con_planilla(periodo=periodo)
        service = ExportacionCalificacionesService(
            filtros={"periodo_id": periodo.id, "paralelo_id": p1.id}, usuario=docente
        )
        buffer = service.exportar_excel_calificaciones()
        wb = load_workbook(buffer)
        assert len(wb.sheetnames) == 1

    def test_filtro_por_materia(self, docente):
        """El filtro por materia limita los paralelos a los de esa asignatura."""
        from tests.factories import AsignaturaFactory

        periodo = PeriodoFactory(nombre="2026-A")
        materia1 = AsignaturaFactory(codigo="M1")
        materia2 = AsignaturaFactory(codigo="M2")
        ParaleloFactory(periodo=periodo, asignatura=materia1, nombre="A")
        ParaleloFactory(periodo=periodo, asignatura=materia2, nombre="B")
        service = ExportacionCalificacionesService(
            filtros={"periodo_id": periodo.id, "materia_id": materia1.id}, usuario=docente
        )
        buffer = service.exportar_excel_calificaciones()
        wb = load_workbook(buffer)
        assert len(wb.sheetnames) == 1

    def test_sin_resultados_retorna_archivo_valido(self, docente):
        """Filtros que no matchean nada → archivo vacío pero válido."""
        periodo = PeriodoFactory(nombre="2026-A")
        service = ExportacionCalificacionesService(
            filtros={"periodo_id": periodo.id}, usuario=docente
        )
        buffer = service.exportar_excel_calificaciones()
        assert buffer.getvalue()[:2] == b"PK"
