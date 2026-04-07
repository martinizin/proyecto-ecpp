"""
URL patterns for the Usuarios bounded context.

Auth (HU01-HU03): registration, OTP, login, logout, dashboard, password recovery.
Profile (HU04): personal data, password change.
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
    RegistroView,
    VerificacionOTPView,
)

app_name = "usuarios"

urlpatterns = [
    # Auth — HU01 (registro + OTP)
    path("registro/", RegistroView.as_view(), name="registro"),
    path("verificar-otp/", VerificacionOTPView.as_view(), name="verificar_otp"),
    # Auth — HU02 (login / logout)
    path("login/", LoginView.as_view(), name="login"),
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
