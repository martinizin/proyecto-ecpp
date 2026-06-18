"""
URL routing para el bounded context de reportes (HU27).
"""

from django.urls import path

from apps.reportes.presentation.views import (
    ExportarAsistenciaView,
    ExportarCalificacionesView,
)

app_name = "reportes"

urlpatterns = [
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
