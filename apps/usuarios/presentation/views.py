"""
Views for the Usuarios bounded context.
Auth views (HU02-HU03): login, logout, 2FA, dashboard, password recovery.
Profile views (HU04): personal data update, password change.

NOTE: Public registration was removed — users are created by staff via Django Admin.
"""

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import RedirectView

from apps.usuarios.application.services import LoginAppService, Login2FAService, PerfilAppService
from apps.usuarios.domain.exceptions import (
    CuentaBloqueadaError,
    OTPExpiradoError,
    OTPInvalidoError,
)

from .forms import (
    CambiarContrasenaForm,
    DatosPersonalesForm,
    ECPPPPasswordResetForm,
    ECPPPSetPasswordForm,
    LoginForm,
    VerificacionOTPForm,
)


def _get_client_ip(request) -> str:
    """Extract client IP from request."""
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


class LoginView(View):
    """Login view — email + password + tipo_usuario with lockout protection."""

    template_name = "usuarios/login.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("usuarios:dashboard")
        form = LoginForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = LoginForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        service = LoginAppService()
        ip = _get_client_ip(request)

        try:
            user = service.intentar_login(
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
                tipo_usuario=form.cleaned_data["tipo_usuario"],
                ip=ip,
            )
        except CuentaBloqueadaError as e:
            form.add_error(None, str(e))
            return render(request, self.template_name, {"form": form})

        if user is None:
            form.add_error(None, "Credenciales inválidas o tipo de usuario incorrecto.")
            return render(request, self.template_name, {"form": form})

        # 2FA for students — send OTP before completing login
        if user.rol == "estudiante":
            service_2fa = Login2FAService()
            service_2fa.generar_otp_login(user.pk)
            request.session["2fa_user_id"] = user.pk
            messages.info(
                request,
                "Se ha enviado un código de verificación a su correo electrónico.",
            )
            return redirect("usuarios:verificar_2fa")

        # Non-student roles — direct login
        login(request, user, backend="apps.usuarios.infrastructure.auth_backend.ECPPPAuthBackend")
        messages.success(request, f"Bienvenido/a, {user.get_full_name() or user.username}.")
        return redirect("usuarios:dashboard")


class LogoutView(View):
    """Logout view — clears session and redirects to login."""

    def get(self, request):
        logout(request)
        messages.info(request, "Ha cerrado sesión exitosamente.")
        return redirect("usuarios:login")

    def post(self, request):
        return self.get(request)


class Verificacion2FAView(View):
    """2FA OTP verification for students — completes login after code verification."""

    template_name = "usuarios/verificar_2fa.html"

    def get(self, request):
        if "2fa_user_id" not in request.session:
            return redirect("usuarios:login")
        form = VerificacionOTPForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        if "2fa_user_id" not in request.session:
            return redirect("usuarios:login")

        form = VerificacionOTPForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        user_id = request.session["2fa_user_id"]
        service = Login2FAService()

        try:
            service.verificar_otp_login(user_id, form.cleaned_data["codigo"])
        except (OTPInvalidoError, OTPExpiradoError) as e:
            form.add_error("codigo", str(e))
            return render(request, self.template_name, {"form": form})

        # OTP verified — complete login
        from django.contrib.auth import get_user_model
        Usuario = get_user_model()
        user = Usuario.objects.get(pk=user_id)

        del request.session["2fa_user_id"]
        login(request, user, backend="apps.usuarios.infrastructure.auth_backend.ECPPPAuthBackend")
        messages.success(request, f"Bienvenido/a, {user.get_full_name() or user.username}.")
        return redirect("usuarios:dashboard")


@method_decorator(login_required, name="dispatch")
class DashboardRedirectView(RedirectView):
    """Redirects to the appropriate dashboard based on user role."""

    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        user = self.request.user
        if user.rol == "inspector":
            return "/academico/periodos/"
        elif user.rol == "docente":
            return "/asistencia/paralelos/"
        else:
            # Estudiante — redirect to attendance dashboard
            return "/asistencia/mi-asistencia/"


# =============================================================================
# Profile Views (HU04)
# =============================================================================


@method_decorator(login_required, name="dispatch")
class PerfilView(View):
    """Profile view — display and update personal data."""

    template_name = "usuarios/perfil.html"

    def get(self, request):
        form = DatosPersonalesForm(
            initial={
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
                "telefono": request.user.telefono,
                "direccion": request.user.direccion,
            }
        )
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = DatosPersonalesForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        service = PerfilAppService()
        service.actualizar_datos(
            user_id=request.user.pk,
            first_name=form.cleaned_data["first_name"],
            last_name=form.cleaned_data["last_name"],
            telefono=form.cleaned_data["telefono"],
            direccion=form.cleaned_data["direccion"],
        )

        messages.success(request, "Datos personales actualizados correctamente.")
        return redirect("usuarios:perfil")


@method_decorator(login_required, name="dispatch")
class CambiarContrasenaView(View):
    """Password change view — validates old password, sets new one."""

    template_name = "usuarios/cambiar_contrasena.html"

    def get(self, request):
        form = CambiarContrasenaForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = CambiarContrasenaForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        service = PerfilAppService()
        success = service.cambiar_contrasena(
            user_id=request.user.pk,
            old_password=form.cleaned_data["old_password"],
            new_password=form.cleaned_data["new_password1"],
        )

        if not success:
            form.add_error("old_password", "La contraseña actual es incorrecta.")
            return render(request, self.template_name, {"form": form})

        # Clear temporary password flag if set
        if request.user.debe_cambiar_password:
            request.user.debe_cambiar_password = False
            request.user.save(update_fields=["debe_cambiar_password"])

        # Re-login to update session hash
        login(request, request.user, backend="apps.usuarios.infrastructure.auth_backend.ECPPPAuthBackend")
        messages.success(request, "Contraseña cambiada exitosamente.")
        return redirect("usuarios:perfil")


# =============================================================================
# Password Recovery — Django built-in views with custom templates
# =============================================================================


class ECPPPPasswordResetView(PasswordResetView):
    template_name = "registration/password_reset_form.html"
    email_template_name = "registration/password_reset_email.html"
    success_url = "/usuarios/recuperar/enviado/"
    form_class = ECPPPPasswordResetForm


class ECPPPPasswordResetDoneView(PasswordResetDoneView):
    template_name = "registration/password_reset_done.html"


class ECPPPPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "registration/password_reset_confirm.html"
    success_url = "/usuarios/recuperar/completo/"
    form_class = ECPPPSetPasswordForm


class ECPPPPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "registration/password_reset_complete.html"
