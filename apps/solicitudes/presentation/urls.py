"""
URL patterns for the Solicitudes bounded context.

Sprint 3 — HU18/HU19: Solicitudes y flujo de aprobación.
"""

from django.urls import path

from apps.solicitudes.presentation.views import (
    CrearJustificacionConCertificadoView,
    CrearJustificacionView,
    CrearRecalificacionView,
    MisSolicitudesView,
    PendientesDocenteView,
    PendientesJustificacionView,
    PendientesSecretariaView,
    ResolverSolicitudView,
)

app_name = "solicitudes"

urlpatterns = [
    # --- Estudiante ---
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
        "justificacion/<int:asistencia_id>/certificado/",
        CrearJustificacionConCertificadoView.as_view(),
        name="crear_justificacion_certificado",
    ),
    path(
        "mis-solicitudes/",
        MisSolicitudesView.as_view(),
        name="mis_solicitudes",
    ),
    # --- Docente ---
    path(
        "pendientes/",
        PendientesDocenteView.as_view(),
        name="pendientes_docente",
    ),
    # --- Secretaría ---
    path(
        "secretaria/",
        PendientesSecretariaView.as_view(),
        name="pendientes_secretaria",
    ),
    # --- Inspector ---
    path(
        "justificaciones/",
        PendientesJustificacionView.as_view(),
        name="pendientes_justificacion",
    ),
    # --- Resolver (docente / secretaría / inspector) ---
    path(
        "<int:pk>/resolver/",
        ResolverSolicitudView.as_view(),
        name="resolver_solicitud",
    ),
]
