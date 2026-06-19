"""
Vistas para exportación de reportes (HU27 + HU27b).

HU27: dos endpoints de exportación de archivos (calificaciones / asistencia).
HU27b: agrega el endpoint ``/reportes/preview/`` (JSON para el hub UX) y
cambia el body de 429 de ``text/plain`` a ``application/json`` para que
el componente Alpine ``exportFlow()`` pueda mostrar un toast con
countdown.

El hub ``/reportes/`` (HU27b) se implementa en WU4; aquí solo dejamos
los stubs de ``PreviewExportView`` y la utilidad ``_rate_limit_json``.
"""

from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views import View

from apps.reportes.application.rate_limiter import (
    ExportacionPreviewRateLimiter,
    ExportacionRateLimiter,
)
from apps.reportes.application.services import (
    ExportacionAsistenciaService,
    ExportacionCalificacionesService,
)
from apps.reportes.domain.services import ReportesDisponibilidadService
from apps.usuarios.presentation.permissions import MultiRolRequeridoMixin


CONTENT_TYPE_EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
CONTENT_TYPE_PDF = "application/pdf"
ROLES_PERMITIDOS = ["docente", "inspector", "secretaria"]
TIPOS_PREVIEW = ["calificaciones", "asistencia"]


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


def _rate_limit_json() -> JsonResponse:
    """Respuesta JSON 429 estándar (HU27b R18).

    Body: ``{"error": "rate_limit", "retry_after_seconds": 60}``.
    Usado por los endpoints de export y de preview cuando el limiter rechaza.
    """
    return JsonResponse(
        {"error": "rate_limit", "retry_after_seconds": 60},
        status=429,
    )


# ---------------------------------------------------------------------------
# Calificaciones
# ---------------------------------------------------------------------------


class ExportarCalificacionesView(MultiRolRequeridoMixin, View):
    """GET /reportes/calificaciones/exportar/ — descarga xlsx/pdf de planilla."""

    roles_permitidos = ROLES_PERMITIDOS

    def get(self, request):
        if not ExportacionRateLimiter.check(request.user.id):
            return _rate_limit_json()
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
            return _rate_limit_json()
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


# ---------------------------------------------------------------------------
# Preview (HU27b)
# ---------------------------------------------------------------------------


class PreviewExportView(MultiRolRequeridoMixin, View):
    """GET /reportes/preview/ — JSON pre-visualización de export (HU27b R13, R14, R15).

    Query params:
        ``tipo`` (required): "calificaciones" | "asistencia".
        ``periodo`` (required, int): ID del período académico.
        ``paralelo`` (optional, int): ID del paralelo.
        ``materia`` (optional, int): ID de la asignatura.
        ``estado`` (optional, str): estado del registro.

    Response:
        200: ``{"count": int, "sample_rows": list[dict], "available_periodos": list[dict],
        "available_paralelos": list[dict]}``
        400: ``{"error": "invalid_tipo", "allowed": ["calificaciones", "asistencia"]}``
        403: estudiante o anónimo.
        429: ``{"error": "rate_limit", "retry_after_seconds": 60}`` (20/min/user, HU27b R15).
    """

    roles_permitidos = ROLES_PERMITIDOS

    def get(self, request):
        # 1. Rate limit (20/min/user, HU27b R15)
        if not ExportacionPreviewRateLimiter.check(request.user.id):
            return _rate_limit_json()

        # 2. Validar ``tipo`` (D3 del design)
        tipo = request.GET.get("tipo")
        if tipo not in TIPOS_PREVIEW:
            return JsonResponse(
                {"error": "invalid_tipo", "allowed": TIPOS_PREVIEW},
                status=400,
            )

        # 3. Validar ``periodo``
        periodo_id_raw = request.GET.get("periodo")
        if not periodo_id_raw:
            return JsonResponse(
                {"error": "invalid_tipo", "allowed": TIPOS_PREVIEW},
                status=400,
            )
        try:
            periodo_id = int(periodo_id_raw)
        except (TypeError, ValueError):
            return JsonResponse(
                {"error": "invalid_tipo", "allowed": TIPOS_PREVIEW},
                status=400,
            )

        # 4. Construir filtros para el export service
        filtros = {"periodo_id": periodo_id}
        for src, dst in (
            ("materia", "materia_id"),
            ("paralelo", "paralelo_id"),
            ("estado", "estado"),
        ):
            value = request.GET.get(src)
            if value:
                filtros[dst] = int(value) if dst.endswith("_id") and value.isdigit() else value

        # 5. Delegar al service de export correspondiente (reuso de servicios existentes)
        if tipo == "calificaciones":
            service = ExportacionCalificacionesService(filtros, request.user)
        else:
            service = ExportacionAsistenciaService(filtros, request.user)

        # 6. WU2 — delegación pura: el service tiene su propio
        # ``obtener_count_y_muestra()`` (no fórmula en la view, R25).
        count, sample_rows = service.obtener_count_y_muestra()

        # 7. Available periodos/paralelos (role-aware via service, D2)
        available_periodos_qs = ReportesDisponibilidadService.obtener_periodos_disponibles(
            request.user
        )
        available_periodos = [
            {"id": p.id, "nombre": p.nombre, "activo": p.activo} for p in available_periodos_qs
        ]

        # Para paralelos disponibles, necesitamos el periodo actual
        from apps.academico.infrastructure.models import Periodo as PeriodoModel

        try:
            current_periodo = PeriodoModel.objects.get(pk=periodo_id)
        except PeriodoModel.DoesNotExist:
            current_periodo = available_periodos_qs[0] if available_periodos_qs else None

        if current_periodo is not None:
            available_paralelos_qs = ReportesDisponibilidadService.obtener_paralelos_disponibles(
                request.user, current_periodo
            )
            available_paralelos = [
                {"id": p.id, "codigo": p.nombre, "materia": p.asignatura.nombre}
                for p in available_paralelos_qs
            ]
        else:
            available_paralelos = []

        return JsonResponse(
            {
                "count": count,
                "sample_rows": sample_rows,
                "available_periodos": available_periodos,
                "available_paralelos": available_paralelos,
            }
        )
