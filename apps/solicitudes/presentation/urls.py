"""
URL patterns for the Solicitudes bounded context.

Sprint 3 — HU18/HU19: Solicitudes y flujo de aprobación.
Sprint 4 — HU21: Dashboard del inspector + acciones de resolución.
"""

from django.urls import path

from apps.solicitudes.presentation.views import (
    CrearJustificacionConCertificadoView,
    CrearJustificacionView,
    CrearRecalificacionView,
    InspectorJustificacionesDashboardView,
    MisSolicitudesView,
    PendientesDocenteView,
    PendientesJustificacionView,
    PendientesSecretariaView,
    ResolverSolicitudView,
    SeleccionarInasistenciaView,
    _PlaceholderInspectorView,
)

app_name = "solicitudes"

urlpatterns = [
    # --- Estudiante ---
    path(
        "recalificacion/nueva/",
        CrearRecalificacionView.as_view(),
        name="crear_recalificacion",
    ),
    # DEPRECATED Sprint 4 (HU20): kept alive for backward compatibility but
    # no longer linked from the student UI. New entry point is
    # ``solicitudes:seleccionar_inasistencia`` below.
    path(
        "justificacion/nueva/",
        CrearJustificacionView.as_view(),
        name="crear_justificacion",
    ),
    path(
        "justificacion/",
        SeleccionarInasistenciaView.as_view(),
        name="seleccionar_inasistencia",
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
    # DEPRECATED Sprint 4 (HU21): kept alive (HU18-style) until T8 swaps
    # all UI entry points to the new dashboard below.
    path(
        "justificaciones/",
        PendientesJustificacionView.as_view(),
        name="pendientes_justificacion",
    ),
    # HU21 — Inspector justifications surface.
    # ORDER MATTERS: ``bulk/`` MUST come BEFORE ``<int:pk>/`` so the static
    # segment is matched before the integer converter swallows it.
    path(
        "inspector/justificaciones/",
        InspectorJustificacionesDashboardView.as_view(),
        name="inspector_justificaciones_dashboard",
    ),
    path(
        "inspector/justificaciones/bulk/",
        _PlaceholderInspectorView.as_view(),
        name="inspector_justificaciones_bulk",
    ),
    path(
        "inspector/justificaciones/<int:pk>/",
        _PlaceholderInspectorView.as_view(),
        name="inspector_justificacion_detalle",
    ),
    path(
        "inspector/justificaciones/<int:pk>/resolver/",
        _PlaceholderInspectorView.as_view(),
        name="inspector_justificacion_resolver",
    ),
    # --- Resolver (docente / secretaría / inspector) ---
    path(
        "<int:pk>/resolver/",
        ResolverSolicitudView.as_view(),
        name="resolver_solicitud",
    ),
]
