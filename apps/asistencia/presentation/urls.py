"""
URL patterns for the Asistencia bounded context.

Sprint 2: Attendance registration and history views.
"""

from django.urls import path

from .views import (
    DashboardAsistenciaEstudianteView,
    HistorialAsistenciaView,
    RegistrarAsistenciaView,
    SeleccionarParaleloView,
)

app_name = "asistencia"

urlpatterns = [
    path(
        "paralelos/",
        SeleccionarParaleloView.as_view(),
        name="seleccionar_paralelo",
    ),
    path(
        "paralelo/<int:paralelo_id>/registrar/",
        RegistrarAsistenciaView.as_view(),
        name="registrar_asistencia",
    ),
    path(
        "paralelo/<int:paralelo_id>/historial/",
        HistorialAsistenciaView.as_view(),
        name="historial_asistencia",
    ),
    path(
        "mi-asistencia/",
        DashboardAsistenciaEstudianteView.as_view(),
        name="mi_asistencia",
    ),
]
