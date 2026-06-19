"""
URL routing para el bounded context de reportes (HU27 + HU27b).
"""

from django.urls import path

from apps.reportes.presentation.views import (
    ExportarAsistenciaView,
    ExportarCalificacionesView,
    PreviewExportView,
)

app_name = "reportes"

urlpatterns = [
    # HU27b: preview JSON endpoint (20/min/user, role-aware)
    path(
        "preview/",
        PreviewExportView.as_view(),
        name="preview",
    ),
    # HU27: export endpoints (10/min/user)
    path(
        "calificaciones/exportar/",
        ExportarCalificacionesView.as_view(),
        name="exportar_calificaciones",
    ),
    path(
        "asistencia/exportar/",
        ExportarAsistenciaView.as_view(),
        name="exportar_asistencia",
    ),
]
