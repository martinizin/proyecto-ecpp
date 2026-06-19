"""
Application service: builds the ANT regulatory PDF with reportlab.
"""

from datetime import datetime
from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from apps.reportes.domain.entities import DatosEstudianteReporte, TotalesReporte
from apps.reportes.domain.services import ReporteANTService


class ReporteANTPDFBuilder:
    """Builds the ANT PDF bytes given pre-collected report data."""

    HEADER_COLOR = colors.HexColor("#1e3a8a")

    def __init__(self, periodo_nombre, generado_por_nombre, generado_por_cedula,
                 firma_path=None, notas=""):
        self.periodo_nombre = periodo_nombre
        self.generado_por_nombre = generado_por_nombre
        self.generado_por_cedula = generado_por_cedula
        self.firma_path = firma_path
        self.notas = notas
        self.styles = getSampleStyleSheet()

    def construir(
        self,
        estudiantes: list[DatosEstudianteReporte],
        totales: TotalesReporte,
        hash_footer: str | None = None,
    ) -> bytes:
        """Return the PDF as bytes."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )
        elements = self._elementos(estudiantes, totales, hash_footer)
        doc.build(elements)
        return buffer.getvalue()

    def _elementos(self, estudiantes, totales, hash_footer):
        s = self.styles
        elements = []

        elements.append(Paragraph("ESCUELA DE CAPACITACIÓN ECPPP", s["Title"]))
        elements.append(
            Paragraph(
                "REPORTE NORMATIVO — RESOLUCIÓN 005-DIR-2022-ANT",
                s["Heading2"],
            )
        )
        elements.append(
            Paragraph(f"Período académico: {self.periodo_nombre}", s["Normal"])
        )
        elements.append(
            Paragraph(
                f"Fecha de generación: {datetime.now():%d/%m/%Y %H:%M}",
                s["Normal"],
            )
        )
        elements.append(Spacer(1, 0.4 * cm))

        resumen = (
            f"<b>Total:</b> {totales.total} &nbsp;&nbsp; "
            f"<b>Aprobados:</b> {totales.aprobados} &nbsp;&nbsp; "
            f"<b>Reprobados:</b> {totales.reprobados} &nbsp;&nbsp; "
            f"<b>En curso:</b> {totales.en_curso} &nbsp;&nbsp; "
            f"<b>Desertores:</b> {totales.desertores}"
        )
        elements.append(Paragraph(resumen, s["Normal"]))
        elements.append(Spacer(1, 0.4 * cm))

        header_row = [
            "Cédula", "Nombres completos", "Paralelo",
            "Materia", "Promedio", "Asist. %", "Estado",
        ]
        rows = [header_row]
        for d in estudiantes:
            promedio_str = (
                f"{d.promedio_final:.2f}" if d.promedio_final is not None else "—"
            )
            rows.append([
                d.cedula,
                d.nombres_completos,
                d.paralelo_codigo,
                d.materia_nombre[:40],
                promedio_str,
                f"{d.porcentaje_asistencia:.1f}%",
                d.estado.upper(),
            ])

        table = Table(rows, repeatRows=1)
        table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), self.HEADER_COLOR),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
            ])
        )
        elements.append(table)
        elements.append(Spacer(1, 0.8 * cm))

        if self.firma_path:
            try:
                elements.append(Image(self.firma_path, width=4 * cm, height=1.5 * cm))
            except Exception:
                pass

        firma_texto = (
            f"___________________________________<br/>"
            f"<b>{self.generado_por_nombre}</b><br/>"
            f"C.C. {self.generado_por_cedula}<br/>"
            f"Director Académico ECPPP"
        )
        elements.append(Paragraph(firma_texto, s["Normal"]))

        if hash_footer:
            elements.append(Spacer(1, 0.4 * cm))
            elements.append(
                Paragraph(
                    f"<font size=7 color='grey'>"
                    f"Hash SHA-256 (integridad): {hash_footer}</font>",
                    s["Normal"],
                )
            )

        if self.notas:
            elements.append(Spacer(1, 0.4 * cm))
            elements.append(Paragraph(f"<b>Notas:</b> {self.notas}", s["Normal"]))

        return elements
