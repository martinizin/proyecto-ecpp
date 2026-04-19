"""URL patterns for the Secretaría module — user and enrollment management."""

from django.urls import path

from . import views

app_name = "secretaria"

urlpatterns = [
    # User management
    path("usuarios/", views.UsuarioListView.as_view(), name="usuario_list"),
    path("usuarios/crear/", views.UsuarioCreateView.as_view(), name="usuario_create"),
    path(
        "usuarios/<int:pk>/editar/",
        views.UsuarioEditView.as_view(),
        name="usuario_edit",
    ),
    path(
        "usuarios/<int:pk>/toggle-activo/",
        views.UsuarioToggleActivoView.as_view(),
        name="usuario_toggle_activo",
    ),
    # Enrollment management
    path("matriculas/", views.MatriculaListView.as_view(), name="matricula_list"),
    path("matriculas/crear/", views.MatriculaCreateView.as_view(), name="matricula_create"),
    path(
        "matriculas/<int:pk>/cambiar-estado/",
        views.MatriculaCambiarEstadoView.as_view(),
        name="matricula_cambiar_estado",
    ),
    path(
        "matriculas/<int:pk>/cambiar-paralelo/",
        views.MatriculaCambiarParaleloView.as_view(),
        name="matricula_cambiar_paralelo",
    ),
]
