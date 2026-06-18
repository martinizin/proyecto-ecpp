"""
Vistas para exportación de reportes (HU27).
"""

from django.http import HttpResponse
from django.utils import timezone
from django.views import View

from apps.reportes.application.rate_limiter import ExportacionRateLimiter
from apps.reportes.application.services import (
    ExportacionAsistenciaService,
    ExportacionCalificacionesService,
)
from apps.usuarios.presentation.permissions import MultiRolRequeridoMixin


CONTENT_TYPE_EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
CONTENT_TYPE_PDF = "application/pdf"
ROLES_PERMITIDOS = ["docente", "inspector", "secretaria"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_filtros(GET):
    """Parsea los query params a un dict de filtros (todos opcionales)."""
    filtros = {}
    if GET.get("periodo"):
        filtros["periodo_id"] = int(GET["periodo"])
    if GET.get("materia"):
        filtros["materia_id"] = int(GET["materia"])
    if GET.get("paralelo"):
        filtros["paralelo_id"] = int(GET["paralelo"])
    if GET.get("estado"):
        filtros["estado"] = GET["estado"]
    return filtros


def _build_filename(tipo: str, filtros: dict, formato: str, cuando) -> str:
    """Construye el filename según R8: ``<tipo>_<periodo>_<paralelo?>_<YYYYMMDD>_<HHMMSS>.<ext>``.

    Si el periodo o paralelo no existen (raro), usa el ID como fallback.
    """
    from apps.academico.infrastructure.models import Paralelo, Periodo

    ext = "xlsx" if formato == "excel" else "pdf"
    parts = [tipo]
    if filtros.get("periodo_id"):
        try:
            periodo = Periodo.objects.get(pk=filtros["periodo_id"])
            parts.append(periodo.nombre)
        except Periodo.DoesNotExist:
            parts.append(str(filtros["periodo_id"]))
    if filtros.get("paralelo_id"):
        try:
            paralelo = Paralelo.objects.get(pk=filtros["paralelo_id"])
            parts.append(paralelo.nombre)
        except Paralelo.DoesNotExist:
            parts.append(str(filtros["paralelo_id"]))
    parts.append(cuando.strftime("%Y%m%d_%H%M%S"))
    return "_".join(parts) + f".{ext}"


# ---------------------------------------------------------------------------
# Calificaciones
# ---------------------------------------------------------------------------


class ExportarCalificacionesView(MultiRolRequeridoMixin, View):
    """GET /reportes/calificaciones/exportar/ — descarga xlsx/pdf de planilla."""

    roles_permitidos = ROLES_PERMITIDOS

    def get(self, request):
        if not ExportacionRateLimiter.check(request.user.id):
            return HttpResponse(
                "Límite de exportaciones excedido. Intente de nuevo en el siguiente minuto.",
                status=429,
                content_type="text/plain; charset=utf-8",
            )
        filtros = _parse_filtros(request.GET)
        service = ExportacionCalificacionesService(filtros, request.user)
        formato = request.GET.get("formato", "excel")
        if formato == "excel":
            buffer = service.exportar_excel_calificaciones()
            content_type = CONTENT_TYPE_EXCEL
        else:
            buffer = service.exportar_pdf_calificaciones()
            content_type = CONTENT_TYPE_PDF
        filename = _build_filename("calificaciones", filtros, formato, timezone.now())
        response = HttpResponse(buffer.read(), content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


# ---------------------------------------------------------------------------
# Asistencia
# ---------------------------------------------------------------------------


class ExportarAsistenciaView(MultiRolRequeridoMixin, View):
    """GET /reportes/asistencia/exportar/ — descarga xlsx/pdf de asistencia."""

    roles_permitidos = ROLES_PERMITIDOS

    def get(self, request):
        if not ExportacionRateLimiter.check(request.user.id):
            return HttpResponse(
                "Límite de exportaciones excedido. Intente de nuevo en el siguiente minuto.",
                status=429,
                content_type="text/plain; charset=utf-8",
            )
        filtros = _parse_filtros(request.GET)
        service = ExportacionAsistenciaService(filtros, request.user)
        formato = request.GET.get("formato", "excel")
        if formato == "excel":
            buffer = service.exportar_excel_asistencia()
            content_type = CONTENT_TYPE_EXCEL
        else:
            buffer = service.exportar_pdf_asistencia()
            content_type = CONTENT_TYPE_PDF
        filename = _build_filename("asistencia", filtros, formato, timezone.now())
        response = HttpResponse(buffer.read(), content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
