from django.urls import path

from apps.calificaciones.presentation.views import (
    AuditoriaCalificacionesView,
    EditarEvaluacionView,
    EliminarEvaluacionView,
    EnviarValidacionView,
    GestionEvaluacionesView,
    RegistrarCalificacionesView,
    SeleccionarParaleloCalificacionesView,
)

app_name = "calificaciones"

urlpatterns = [
    path(
        "paralelos/",
        SeleccionarParaleloCalificacionesView.as_view(),
        name="seleccionar_paralelo",
    ),
    path(
        "paralelo/<int:paralelo_id>/registrar/",
        RegistrarCalificacionesView.as_view(),
        name="registrar_calificaciones",
    ),
    path(
        "paralelo/<int:paralelo_id>/evaluaciones/",
        GestionEvaluacionesView.as_view(),
        name="gestionar_evaluaciones",
    ),
    path(
        "paralelo/<int:paralelo_id>/evaluaciones/<int:evaluacion_id>/editar/",
        EditarEvaluacionView.as_view(),
        name="editar_evaluacion",
    ),
    path(
        "paralelo/<int:paralelo_id>/evaluaciones/<int:evaluacion_id>/eliminar/",
        EliminarEvaluacionView.as_view(),
        name="eliminar_evaluacion",
    ),
    path(
        "paralelo/<int:paralelo_id>/enviar-validacion/",
        EnviarValidacionView.as_view(),
        name="enviar_validacion",
    ),
    path(
        "auditoria/",
        AuditoriaCalificacionesView.as_view(),
        name="auditoria_calificaciones",
    ),
]
