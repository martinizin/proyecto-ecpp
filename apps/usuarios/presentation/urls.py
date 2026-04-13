"""
URL patterns for the Usuarios bounded context.

Auth (HU01-HU03): login, logout, 2FA, dashboard, password recovery.
Profile (HU04): personal data, password change.

NOTE: Public registration was removed — users are created by staff via Django Admin.
"""

from django.urls import path

from .views import (
    CambiarContrasenaView,
    DashboardRedirectView,
    ECPPPPasswordResetCompleteView,
    ECPPPPasswordResetConfirmView,
    ECPPPPasswordResetDoneView,
    ECPPPPasswordResetView,
    LoginView,
    LogoutView,
    PerfilView,
    Verificacion2FAView,
)

app_name = "usuarios"

urlpatterns = [
    # Auth — HU02 (login / logout / 2FA)
    path("login/", LoginView.as_view(), name="login"),
    path("verificar-2fa/", Verificacion2FAView.as_view(), name="verificar_2fa"),
    path("logout/", LogoutView.as_view(), name="logout"),
    # Dashboard redirect
    path("dashboard/", DashboardRedirectView.as_view(), name="dashboard"),
    # Profile — HU04
    path("perfil/", PerfilView.as_view(), name="perfil"),
    path("perfil/cambiar-contrasena/", CambiarContrasenaView.as_view(), name="cambiar_contrasena"),
    # Password recovery — HU03 (Django built-in views with custom templates)
    path("recuperar/", ECPPPPasswordResetView.as_view(), name="password_reset"),
    path("recuperar/enviado/", ECPPPPasswordResetDoneView.as_view(), name="password_reset_done"),
    path(
        "recuperar/<uidb64>/<token>/",
        ECPPPPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path("recuperar/completo/", ECPPPPasswordResetCompleteView.as_view(), name="password_reset_complete"),
]
