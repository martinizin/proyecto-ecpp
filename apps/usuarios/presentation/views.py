"""
Views for the Usuarios bounded context.
Auth views (HU01-HU03): registration, OTP verification, login, logout, dashboard.
Password recovery wires Django's built-in views with custom templates.
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

from apps.usuarios.application.services import LoginAppService, RegistroAppService
from apps.usuarios.domain.exceptions import (
    CedulaDuplicadaError,
    CorreoDuplicadoError,
    CuentaBloqueadaError,
    OTPExpiradoError,
    OTPInvalidoError,
)

from .forms import LoginForm, RegistroForm, VerificacionOTPForm


def _get_client_ip(request) -> str:
    """Extract client IP from request."""
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


class RegistroView(View):
    """User registration — creates inactive user + sends OTP."""

    template_name = "usuarios/registro.html"

    def get(self, request):
        form = RegistroForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = RegistroForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        service = RegistroAppService()
        try:
            user_id = service.registrar(
                username=form.cleaned_data["email"],
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password1"],
                first_name=form.cleaned_data["first_name"],
                last_name=form.cleaned_data["last_name"],
                rol=form.cleaned_data["rol"],
                cedula=form.cleaned_data.get("cedula", ""),
                telefono=form.cleaned_data.get("telefono", ""),
            )
        except (CorreoDuplicadoError, CedulaDuplicadaError, ValueError) as e:
            form.add_error(None, str(e))
            return render(request, self.template_name, {"form": form})

        # Store user_id in session for OTP verification
        request.session["otp_user_id"] = user_id
        messages.success(
            request,
            "Se ha enviado un código de verificación a tu correo electrónico.",
        )
        return redirect("usuarios:verificar_otp")


class VerificacionOTPView(View):
    """OTP code verification — activates user account."""

    template_name = "usuarios/verificar_otp.html"

    def get(self, request):
        if "otp_user_id" not in request.session:
            return redirect("usuarios:registro")
        form = VerificacionOTPForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        if "otp_user_id" not in request.session:
            return redirect("usuarios:registro")

        form = VerificacionOTPForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        user_id = request.session["otp_user_id"]
        service = RegistroAppService()

        try:
            service.verificar_otp(user_id, form.cleaned_data["codigo"])
        except (OTPInvalidoError, OTPExpiradoError) as e:
            form.add_error("codigo", str(e))
            return render(request, self.template_name, {"form": form})

        # Clean session and redirect to login
        del request.session["otp_user_id"]
        messages.success(
            request,
            "Tu cuenta ha sido verificada exitosamente. Ya podés iniciar sesión.",
        )
        return redirect("usuarios:login")


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

        login(request, user, backend="apps.usuarios.infrastructure.auth_backend.ECPPPAuthBackend")
        messages.success(request, f"Bienvenido/a, {user.get_full_name() or user.username}.")
        return redirect("usuarios:dashboard")


class LogoutView(View):
    """Logout view — clears session and redirects to login."""

    def get(self, request):
        logout(request)
        messages.info(request, "Has cerrado sesión exitosamente.")
        return redirect("usuarios:login")

    def post(self, request):
        return self.get(request)


@method_decorator(login_required, name="dispatch")
class DashboardRedirectView(RedirectView):
    """Redirects to the appropriate dashboard based on user role."""

    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        user = self.request.user
        if user.rol == "inspector":
            return "/academico/periodos/"
        elif user.rol == "docente":
            return "/academico/paralelos/"
        else:
            # Estudiante — redirect to home for now (enrollment comes in Sprint 2)
            return "/"


# =============================================================================
# Password Recovery — Django built-in views with custom templates
# =============================================================================


class ECPPPPasswordResetView(PasswordResetView):
    template_name = "registration/password_reset_form.html"
    email_template_name = "registration/password_reset_email.html"
    success_url = "/usuarios/recuperar/enviado/"


class ECPPPPasswordResetDoneView(PasswordResetDoneView):
    template_name = "registration/password_reset_done.html"


class ECPPPPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "registration/password_reset_confirm.html"
    success_url = "/usuarios/recuperar/completo/"


class ECPPPPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "registration/password_reset_complete.html"
