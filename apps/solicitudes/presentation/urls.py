"""
URL patterns for the Solicitudes bounded context.

Sprint 3 — HU18: Solicitudes de recalificación y justificación de inasistencia.
"""

from django.urls import path

from apps.solicitudes.presentation.views import (
    CrearJustificacionView,
    CrearRecalificacionView,
    MisSolicitudesView,
)

app_name = "solicitudes"

urlpatterns = [
    path(
        "recalificacion/nueva/",
        CrearRecalificacionView.as_view(),
        name="crear_recalificacion",
    ),
    path(
        "justificacion/nueva/",
        CrearJustificacionView.as_view(),
        name="crear_justificacion",
    ),
    path(
        "mis-solicitudes/",
        MisSolicitudesView.as_view(),
        name="mis_solicitudes",
    ),
]
