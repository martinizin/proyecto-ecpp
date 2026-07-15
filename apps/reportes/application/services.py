"""
Servicios de aplicación para exportación de reportes (HU27).

Dos servicios orquestan la generación de archivos en memoria:

- ``ExportacionCalificacionesService`` — produce xlsx/pdf de planillas
  de calificaciones.
- ``ExportacionAsistenciaService`` — produce xlsx/pdf del agregado de
  asistencia por estudiante/paralelo.

Reglas:
- Toda la lógica de cálculo se delega a los domain services
  existentes (``CalificacionValidationService``,
  ``AsistenciaCalculoService``).
- Los archivos se generan en ``BytesIO`` y se devuelven al caller
  (la vista) sin persistencia.
"""

from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from apps.academico.infrastructure.models import Paralelo
from apps.asistencia.domain.services import AsistenciaCalculoService
from apps.calificaciones.application.services import (
    RegistroCalificacionAppService,
    SubNotaParcialAppService,
)
from apps.calificaciones.domain.services import CalificacionValidationService
from apps.calificaciones.infrastructure.models import SubNotaParcial


# ---------------------------------------------------------------------------
# Constantes de estilo (DRY entre servicios)
# ---------------------------------------------------------------------------

COLOR_HEADER_BG = "1E3A8A"  # Azul ECPP
COLOR_HEADER_FG = "FFFFFF"  # Blanco
EXCEL_FONT_HEADER = Font(bold=True, color=COLOR_HEADER_FG)
EXCEL_FILL_HEADER = PatternFill("solid", fgColor=COLOR_HEADER_BG)

PDF_TABLE_STYLE = TableStyle(
    [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(f"#{COLOR_HEADER_BG}")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]
)


def _header_block_rows(periodo, paralelo, usuario, cuando):
    """Retorna las 3 filas del header block (ECPPP, Paralelo, Generado)."""
    return [
        f"ECPPP — {periodo.nombre}",
        f"Paralelo {paralelo.nombre} — {paralelo.asignatura.nombre}",
        f"Generado: {cuando:%Y-%m-%d %H:%M} — {usuario.get_full_name()}",
    ]


# Orden canónico de los tipos de evaluación, alineado con el flujo académico
# (parciales 1-5, examen final). Usado por los servicios de exportación para
# ordenar las columnas de notas.
_TIPOS_EVALUACION_ORDEN = [
    "parcial1",
    "parcial2_10h",
    "parcial3",
    "parcial4_10h",
    "parcial5",
    "examen_final",
]


def _sort_evaluaciones(evaluaciones):
    """Ordena evaluaciones por el orden canónico del flujo académico."""
    orden = {tipo: idx for idx, tipo in enumerate(_TIPOS_EVALUACION_ORDEN)}

    def key(ev):
        return orden.get(ev.tipo, len(orden))

    return sorted(evaluaciones, key=key)


# ---------------------------------------------------------------------------
# Calificaciones
# ---------------------------------------------------------------------------


class ExportacionCalificacionesService:
    """Genera Excel y PDF de planillas de calificaciones por paralelo.

    Constructor recibe ``filtros`` (dict con ``periodo_id`` requerido,
    ``materia_id``/``paralelo_id``/``estado`` opcionales) y ``usuario``
    (para el header block).
    """

    def __init__(self, filtros: dict, usuario):
        self.filtros = filtros
        self.usuario = usuario

    def exportar_excel_calificaciones(self) -> BytesIO:
        """Genera un xlsx con 1 sheet por paralelo."""
        from django.utils import timezone

        paralelos = self._filtrar_paralelos()
        wb = Workbook()
        # Removemos el sheet default; lo creamos por cada paralelo.
        # Si no hay paralelos (R10 — empty result), dejamos un sheet marcador.
        wb.remove(wb.active)

        cuando = timezone.now()
        if paralelos:
            for paralelo in paralelos:
                sheet_title = f"{paralelo.asignatura.codigo}-{paralelo.nombre}"[:31]
                ws = wb.create_sheet(title=sheet_title)
                self._llenar_sheet_calificaciones(ws, paralelo, cuando)
                desglose = self.obtener_desglose_sub_notas(paralelo)
                if desglose:
                    sub_title = f"Sub {paralelo.asignatura.codigo}-{paralelo.nombre}"[:31]
                    ws_sub = wb.create_sheet(title=sub_title)
                    self._llenar_sheet_sub_notas(ws_sub, paralelo, desglose, cuando)
        else:
            ws = wb.create_sheet(title="Sin resultados")
            ws.cell(row=1, column=1, value="ECPPP — Reporte de Calificaciones")
            ws.cell(
                row=2,
                column=1,
                value=f"Generado: {cuando:%Y-%m-%d %H:%M} — {self.usuario.get_full_name()}",
            )
            ws.cell(row=3, column=1, value="Sin paralelos para los filtros aplicados.")

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer

    def exportar_pdf_calificaciones(self) -> BytesIO:
        """Genera un PDF landscape A4 con 1 tabla por paralelo."""
        from django.utils import timezone

        paralelos = self._filtrar_paralelos()
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=1.5 * cm,
            rightMargin=1.5 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )
        styles = getSampleStyleSheet()
        elements = []
        cuando = timezone.now()

        if not paralelos:
            # R10 — empty filter result: archivo PDF válido sin tablas
            elements.append(Paragraph("ECPPP — Reporte de Calificaciones", styles["Title"]))
            elements.append(Spacer(1, 1 * cm))
            elements.append(
                Paragraph(
                    f"Generado: {cuando:%Y-%m-%d %H:%M} — {self.usuario.get_full_name()}",
                    styles["Normal"],
                )
            )
        else:
            for i, paralelo in enumerate(paralelos):
                data = self._build_pdf_data_calificaciones(paralelo, cuando)
                t = Table(data, repeatRows=1)
                t.setStyle(PDF_TABLE_STYLE)
                elements.append(t)
                if i < len(paralelos) - 1:
                    elements.append(PageBreak())

        doc.build(elements)
        buffer.seek(0)
        return buffer

    # ----- Internals ----------------------------------------------------

    def _filtrar_paralelos(self):
        """Filtra paralelos del periodo, opcionalmente por materia/paralelo/estado."""
        qs = Paralelo.objects.filter(periodo_id=self.filtros["periodo_id"])
        if "materia_id" in self.filtros and self.filtros["materia_id"]:
            qs = qs.filter(asignatura_id=self.filtros["materia_id"])
        if "paralelo_id" in self.filtros and self.filtros["paralelo_id"]:
            qs = qs.filter(id=self.filtros["paralelo_id"])
        if "estado" in self.filtros and self.filtros["estado"]:
            qs = qs.filter(registro_calificaciones__estado=self.filtros["estado"])
        return list(qs.select_related("asignatura", "periodo", "docente"))

    def _llenar_sheet_calificaciones(self, ws, paralelo, cuando):
        """Llena un sheet con header block + columnas + filas de estudiantes."""
        # Header block: 3 filas + 1 spacer
        for i, line in enumerate(
            _header_block_rows(paralelo.periodo, paralelo, self.usuario, cuando), start=1
        ):
            ws.cell(row=i, column=1, value=line)
        ws.cell(row=4, column=1, value=None)  # spacer row

        # Header de columnas (row 5)
        planilla = RegistroCalificacionAppService().obtener_planilla(paralelo.id)
        evaluaciones = _sort_evaluaciones(planilla["evaluaciones"])
        header = (
            ["Cédula", "Nombres"]
            + [ev.get_tipo_display() for ev in evaluaciones]
            + [
                "Promedio",
                "Estado",
            ]
        )
        for col_idx, value in enumerate(header, start=1):
            cell = ws.cell(row=5, column=col_idx, value=value)
            cell.font = EXCEL_FONT_HEADER
            cell.fill = EXCEL_FILL_HEADER
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Data rows (row 6 en adelante)
        for i, fila in enumerate(planilla["filas"], start=6):
            estudiante = fila["matricula"].estudiante
            ws.cell(row=i, column=1, value=estudiante.cedula)
            ws.cell(row=i, column=2, value=estudiante.get_full_name())
            for col_offset, (ev, cal) in enumerate(fila["celdas"], start=3):
                nota = cal.nota if cal else None
                ws.cell(row=i, column=col_offset, value=float(nota) if nota is not None else "")
            promedio = fila["promedio"]
            ws.cell(
                row=i,
                column=len(header) - 1,
                value=float(promedio) if promedio is not None else "",
            )
            estado = (
                CalificacionValidationService.estado_aprobacion(promedio)
                if promedio is not None
                else "sin_notas"
            )
            ws.cell(row=i, column=len(header), value=estado)

    def _build_pdf_data_calificaciones(self, paralelo, cuando) -> list:
        """Construye la matriz de datos (incluyendo header) para la tabla PDF."""
        planilla = RegistroCalificacionAppService().obtener_planilla(paralelo.id)
        evaluaciones = _sort_evaluaciones(planilla["evaluaciones"])
        header_row = (
            ["Cédula", "Nombres"]
            + [ev.get_tipo_display() for ev in evaluaciones]
            + ["Promedio", "Estado"]
        )
        data = [header_row]
        for fila in planilla["filas"]:
            estudiante = fila["matricula"].estudiante
            row = [estudiante.cedula, estudiante.get_full_name()]
            for _ev, cal in fila["celdas"]:
                row.append(f"{cal.nota:.2f}" if cal else "")
            promedio = fila["promedio"]
            row.append(f"{promedio:.2f}" if promedio is not None else "")
            estado = (
                CalificacionValidationService.estado_aprobacion(promedio)
                if promedio is not None
                else "sin_notas"
            )
            row.append(estado)
            data.append(row)
        return data

    # ----- Desglose de sub-notas (HU34) ----------------------------------

    def _llenar_sheet_sub_notas(self, ws, paralelo, desglose, cuando):
        """Llena la hoja "Sub-notas" con una fila por sub-nota (formato largo).

        Los valores identificadores (cédula, nombres, parcial) se repiten en
        cada fila para que la hoja soporte filtros y pivots de Excel.
        """
        for i, line in enumerate(
            _header_block_rows(paralelo.periodo, paralelo, self.usuario, cuando), start=1
        ):
            ws.cell(row=i, column=1, value=line)
        ws.cell(row=4, column=1, value=None)  # spacer row

        header = [
            "Cédula",
            "Nombres",
            "Parcial",
            "Sub-nota",
            "Peso (%)",
            "Nota",
            "Nota Parcial",
            "Override",
            "Justificación",
        ]
        for col_idx, value in enumerate(header, start=1):
            cell = ws.cell(row=5, column=col_idx, value=value)
            cell.font = EXCEL_FONT_HEADER
            cell.fill = EXCEL_FILL_HEADER
            cell.alignment = Alignment(horizontal="center", vertical="center")

        def _num(valor):
            return float(valor) if valor is not None else ""

        row_idx = 6
        for fila in desglose:
            for sub in fila["sub_notas"]:
                ws.cell(row=row_idx, column=1, value=fila["cedula"])
                ws.cell(row=row_idx, column=2, value=fila["nombres"])
                ws.cell(row=row_idx, column=3, value=fila["parcial"])
                ws.cell(row=row_idx, column=4, value=sub["nombre"])
                ws.cell(row=row_idx, column=5, value=_num(sub["peso"]))
                ws.cell(row=row_idx, column=6, value=_num(sub["nota"]))
                ws.cell(row=row_idx, column=7, value=_num(fila["nota_parcial"]))
                ws.cell(row=row_idx, column=8, value=_num(fila["override"]))
                ws.cell(row=row_idx, column=9, value=fila["justificacion"])
                row_idx += 1

    def obtener_desglose_sub_notas(self, paralelo) -> list[dict]:
        """Desglose de sub-notas por estudiante y parcial del paralelo (HU34).

        Retorna una fila por cada par (estudiante, parcial con sub-notas
        configuradas), en el orden de la planilla y el orden canónico de
        evaluaciones::

            {
                "cedula", "nombres", "parcial",
                "sub_notas": [{"nombre", "peso", "nota"}, ...],
                "nota_parcial", "override", "justificacion",
            }

        Si el paralelo no tiene sub-notas configuradas retorna ``[]`` (los
        renderers de Excel/PDF omiten la sección en ese caso).
        """
        planilla = RegistroCalificacionAppService().obtener_planilla(paralelo.id)
        sub_service = SubNotaParcialAppService()
        config_por_ev = {}
        for ev in _sort_evaluaciones(planilla["evaluaciones"]):
            if ev.es_parcial:
                items = sub_service.obtener_configuracion(ev.id)
                if items:
                    config_por_ev[ev.id] = items
        if not config_por_ev:
            return []

        sub_lookup = {}
        for sn in SubNotaParcial.objects.filter(evaluacion__paralelo_id=paralelo.id):
            sub_lookup[(sn.matricula_id, sn.evaluacion_id, sn.orden)] = sn

        filas_desglose = []
        for fila in planilla["filas"]:
            matricula = fila["matricula"]
            estudiante = matricula.estudiante
            for ev, cal in fila["celdas"]:
                config = config_por_ev.get(ev.id)
                if not config:
                    continue
                sub_notas = []
                override = None
                justificacion = ""
                for item in config:
                    sn = sub_lookup.get((matricula.id, ev.id, item.orden))
                    sub_notas.append(
                        {
                            "nombre": item.nombre,
                            "peso": item.peso,
                            "nota": sn.nota if sn else None,
                        }
                    )
                    if sn is not None and sn.nota_final_parcial_override is not None:
                        override = sn.nota_final_parcial_override
                        justificacion = sn.justificacion_override
                filas_desglose.append(
                    {
                        "cedula": estudiante.cedula,
                        "nombres": estudiante.get_full_name(),
                        "parcial": ev.get_tipo_display(),
                        "sub_notas": sub_notas,
                        "nota_parcial": cal.nota if cal else None,
                        "override": override,
                        "justificacion": justificacion,
                    }
                )
        return filas_desglose

    # ----- Preview (HU27b WU2) -------------------------------------------

    def obtener_count_y_muestra(self, limite: int = 3) -> tuple[int, list[dict]]:
        """Cuenta matrículas activas y retorna una muestra de hasta ``limite`` filas.

        Reutilizado por ``PreviewExportView`` (HU27b WU2) para el endpoint JSON
        ``/reportes/preview/``. NO genera archivos. NO re-implementa la
        fórmula del promedio — delega a ``CalificacionValidationService``
        (R25 / design §4.7).

        Returns:
            ``(count, sample_rows)``:
            - ``count`` = total de matrículas activas en los paralelos filtrados.
            - ``sample_rows`` = hasta ``limite`` dicts con keys
              ``cedula, nombres, promedio, estado`` (mismo shape que
              ``PreviewExportView`` retorna en WU1, para refactor transparente).
        """
        paralelos = self._filtrar_paralelos()
        if not paralelos:
            return 0, []
        count = sum(p.matriculas.filter(estado="activa").count() for p in paralelos)
        sample_rows: list[dict] = []
        for paralelo in paralelos[:1]:
            planilla = RegistroCalificacionAppService().obtener_planilla(paralelo.id)
            for fila in planilla["filas"][:limite]:
                promedio = fila["promedio"]
                sample_rows.append(
                    {
                        "cedula": fila["matricula"].estudiante.cedula,
                        "nombres": fila["matricula"].estudiante.get_full_name(),
                        "promedio": float(promedio) if promedio is not None else None,
                        "estado": (
                            CalificacionValidationService.estado_aprobacion(promedio)
                            if promedio is not None
                            else "sin_notas"
                        ),
                    }
                )
        return count, sample_rows


# ---------------------------------------------------------------------------
# Asistencia
# ---------------------------------------------------------------------------


class ExportacionAsistenciaService:
    """Genera Excel y PDF del agregado de asistencia por estudiante/paralelo.

    Una fila por estudiante con el snapshot agregado (totales +
    porcentaje + estado), NO el historial sesión-por-sesión.
    """

    def __init__(self, filtros: dict, usuario):
        self.filtros = filtros
        self.usuario = usuario

    def exportar_excel_asistencia(self) -> BytesIO:
        """Genera un xlsx con 1 sheet por paralelo (snapshot por estudiante)."""
        from django.utils import timezone

        paralelos = self._filtrar_paralelos()
        wb = Workbook()
        wb.remove(wb.active)

        cuando = timezone.now()
        if paralelos:
            for paralelo in paralelos:
                sheet_title = f"{paralelo.asignatura.codigo}-{paralelo.nombre}"[:31]
                ws = wb.create_sheet(title=sheet_title)
                self._llenar_sheet_asistencia(ws, paralelo, cuando)
        else:
            ws = wb.create_sheet(title="Sin resultados")
            ws.cell(row=1, column=1, value="ECPPP — Reporte de Asistencia")
            ws.cell(
                row=2,
                column=1,
                value=f"Generado: {cuando:%Y-%m-%d %H:%M} — {self.usuario.get_full_name()}",
            )
            ws.cell(row=3, column=1, value="Sin paralelos para los filtros aplicados.")

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer

    def exportar_pdf_asistencia(self) -> BytesIO:
        """Genera un PDF portrait A4 con 1 tabla por paralelo."""
        from django.utils import timezone

        paralelos = self._filtrar_paralelos()
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,  # portrait (R7)
            leftMargin=1.5 * cm,
            rightMargin=1.5 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )
        styles = getSampleStyleSheet()
        elements = []
        cuando = timezone.now()

        if not paralelos:
            elements.append(Paragraph("ECPPP — Reporte de Asistencia", styles["Title"]))
            elements.append(Spacer(1, 1 * cm))
            elements.append(
                Paragraph(
                    f"Generado: {cuando:%Y-%m-%d %H:%M} — {self.usuario.get_full_name()}",
                    styles["Normal"],
                )
            )
        else:
            for i, paralelo in enumerate(paralelos):
                data = self._build_pdf_data_asistencia(paralelo, cuando)
                t = Table(data, repeatRows=1)
                t.setStyle(PDF_TABLE_STYLE)
                elements.append(t)
                if i < len(paralelos) - 1:
                    elements.append(PageBreak())

        doc.build(elements)
        buffer.seek(0)
        return buffer

    # ----- Internals ----------------------------------------------------

    def _filtrar_paralelos(self):
        """Filtra paralelos del periodo, opcionalmente por materia/paralelo."""
        qs = Paralelo.objects.filter(periodo_id=self.filtros["periodo_id"])
        if "materia_id" in self.filtros and self.filtros["materia_id"]:
            qs = qs.filter(asignatura_id=self.filtros["materia_id"])
        if "paralelo_id" in self.filtros and self.filtros["paralelo_id"]:
            qs = qs.filter(id=self.filtros["paralelo_id"])
        return list(qs.select_related("asignatura", "periodo", "docente"))

    def _calcular_datos_asistencia_estudiante(self, estudiante_id, paralelo_id):
        """Calcula totales y % para un estudiante en un paralelo."""
        from apps.asistencia.infrastructure.models import Asistencia

        qs = Asistencia.objects.filter(estudiante_id=estudiante_id, paralelo_id=paralelo_id)
        total = qs.count()
        presentes = qs.filter(estado=Asistencia.Estado.PRESENTE).count()
        ausentes = qs.filter(estado=Asistencia.Estado.AUSENTE).count()
        justificadas = qs.filter(estado=Asistencia.Estado.JUSTIFICADO).count()
        return {
            "total": total,
            "presentes": presentes,
            "ausentes": ausentes,
            "justificadas": justificadas,
        }

    def _estado_asistencia(self, datos):
        """Estado = evaluar_riesgo sobre el porcentaje de inasistencia."""
        calc = AsistenciaCalculoService()
        porcentaje_asistencia = calc.calcular_porcentaje_asistencia(
            datos["presentes"] + datos["justificadas"],
            datos["total"],
        )
        porcentaje_inasistencia = Decimal("100.00") - porcentaje_asistencia
        return calc.evaluar_riesgo(porcentaje_inasistencia)

    def _porcentaje_asistencia(self, datos):
        """Porcentaje de asistencia del estudiante (0–100)."""
        calc = AsistenciaCalculoService()
        return calc.calcular_porcentaje_asistencia(
            datos["presentes"] + datos["justificadas"],
            datos["total"],
        )

    def _llenar_sheet_asistencia(self, ws, paralelo, cuando):
        """Llena un sheet con header block + columnas + filas de estudiantes."""
        for i, line in enumerate(
            _header_block_rows(paralelo.periodo, paralelo, self.usuario, cuando), start=1
        ):
            ws.cell(row=i, column=1, value=line)
        ws.cell(row=4, column=1, value=None)  # spacer

        header = [
            "Cédula",
            "Nombres",
            "Total Clases",
            "Total Presentes",
            "Total Ausentes",
            "Total Justificadas",
            "Porcentaje Asistencia",
            "Estado",
        ]
        for col_idx, value in enumerate(header, start=1):
            cell = ws.cell(row=5, column=col_idx, value=value)
            cell.font = EXCEL_FONT_HEADER
            cell.fill = EXCEL_FILL_HEADER
            cell.alignment = Alignment(horizontal="center", vertical="center")

        matriculas = (
            paralelo.matriculas.filter(estado="activa")
            .select_related("estudiante")
            .order_by("estudiante__last_name", "estudiante__first_name")
        )
        for i, matricula in enumerate(matriculas, start=6):
            datos = self._calcular_datos_asistencia_estudiante(
                matricula.estudiante_id, paralelo.id
            )
            estudiante = matricula.estudiante
            ws.cell(row=i, column=1, value=estudiante.cedula)
            ws.cell(row=i, column=2, value=estudiante.get_full_name())
            ws.cell(row=i, column=3, value=datos["total"])
            ws.cell(row=i, column=4, value=datos["presentes"])
            ws.cell(row=i, column=5, value=datos["ausentes"])
            ws.cell(row=i, column=6, value=datos["justificadas"])
            ws.cell(row=i, column=7, value=float(self._porcentaje_asistencia(datos)))
            ws.cell(row=i, column=8, value=self._estado_asistencia(datos))

    def _build_pdf_data_asistencia(self, paralelo, cuando) -> list:
        """Construye la matriz de datos (incluyendo header) para la tabla PDF."""
        header_row = [
            "Cédula",
            "Nombres",
            "Total Clases",
            "Total Presentes",
            "Total Ausentes",
            "Total Justificadas",
            "Porcentaje Asistencia",
            "Estado",
        ]
        data = [header_row]
        matriculas = (
            paralelo.matriculas.filter(estado="activa")
            .select_related("estudiante")
            .order_by("estudiante__last_name", "estudiante__first_name")
        )
        for matricula in matriculas:
            datos = self._calcular_datos_asistencia_estudiante(
                matricula.estudiante_id, paralelo.id
            )
            row = [
                matricula.estudiante.cedula,
                matricula.estudiante.get_full_name(),
                datos["total"],
                datos["presentes"],
                datos["ausentes"],
                datos["justificadas"],
                f"{self._porcentaje_asistencia(datos):.2f}",
                self._estado_asistencia(datos),
            ]
            data.append(row)
        return data

    # ----- Preview (HU27b WU2) -------------------------------------------

    def obtener_count_y_muestra(self, limite: int = 3) -> tuple[int, list[dict]]:
        """Cuenta matrículas activas y retorna una muestra de hasta ``limite`` filas.

        Reutilizado por ``PreviewExportView`` (HU27b WU2) para el endpoint JSON
        ``/reportes/preview/``. NO genera archivos. NO re-implementa la
        fórmula del porcentaje — delega a ``AsistenciaCalculoService``
        (R25 / design §4.7). Reusa internamente ``_calcular_datos_asistencia_estudiante``,
        ``_porcentaje_asistencia`` y ``_estado_asistencia`` para mantener una
        sola fuente de verdad del cálculo de asistencia en este módulo.

        Returns:
            ``(count, sample_rows)``:
            - ``count`` = total de matrículas activas en los paralelos filtrados.
            - ``sample_rows`` = hasta ``limite`` dicts con keys
              ``cedula, nombres, porcentaje_asistencia, estado`` (mismo shape
              que ``PreviewExportView`` retorna en WU1, para refactor
              transparente).
        """
        paralelos = self._filtrar_paralelos()
        if not paralelos:
            return 0, []
        count = sum(p.matriculas.filter(estado="activa").count() for p in paralelos)
        sample_rows: list[dict] = []
        for paralelo in paralelos[:1]:
            matriculas = (
                paralelo.matriculas.filter(estado="activa")
                .select_related("estudiante")
                .order_by("estudiante__last_name", "estudiante__first_name")[:limite]
            )
            for matricula in matriculas:
                datos = self._calcular_datos_asistencia_estudiante(
                    matricula.estudiante_id, paralelo.id
                )
                sample_rows.append(
                    {
                        "cedula": matricula.estudiante.cedula,
                        "nombres": matricula.estudiante.get_full_name(),
                        "porcentaje_asistencia": float(self._porcentaje_asistencia(datos)),
                        "estado": self._estado_asistencia(datos),
                    }
                )
        return count, sample_rows
