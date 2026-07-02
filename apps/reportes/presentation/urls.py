"""
URL routing para el bounded context de reportes (HU26 + HU27 + HU27b).
"""

from django.urls import path

from apps.reportes.presentation.views import (
    ExportarAsistenciaView,
    ExportarCalificacionesView,
    PreviewExportView,
    ReporteANTDescargarView,
    ReporteANTGenerarView,
    ReporteANTListView,
    ReporteANTVerificarHashView,
    ReportesHubView,
)

app_name = "reportes"

urlpatterns = [
    # HU27b WU4: hub page (entry point at /reportes/)
    path(
        "",
        ReportesHubView.as_view(),
        name="hub",
    ),
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
    # HU26: reportes ANT (Resolucion 005-DIR-2022)
    path("ant/", ReporteANTListView.as_view(), name="ant_listado"),
    path("ant/generar/", ReporteANTGenerarView.as_view(), name="ant_generar"),
    path(
        "ant/<int:pk>/descargar/",
        ReporteANTDescargarView.as_view(),
        name="ant_descargar",
    ),
    path(
        "ant/<int:pk>/verificar-hash/",
        ReporteANTVerificarHashView.as_view(),
        name="ant_verificar_hash",
    ),
]
