"""
Application services (use cases) for the Usuarios bounded context.

These services orchestrate domain services + infrastructure (repositories, email)
to implement complete use cases. They are the entry point from the presentation layer.
"""

from datetime import datetime
from typing import Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.usuarios.domain.entities import OTPTokenEntity, RegistroAuditoriaEntity
from apps.usuarios.domain.exceptions import OTPInvalidoError
from apps.usuarios.domain.services import LoginService, OTPService, RegistroService
from apps.usuarios.infrastructure.email_service import (
    send_lockout_notification,
    send_otp_email,
)
from apps.usuarios.infrastructure.repositories import (
    DjangoAuditoriaRepository,
    DjangoOTPTokenRepository,
    DjangoUsuarioRepository,
)

Usuario = get_user_model()


class RegistroAppService:
    """
    Orchestrates user registration flow:
    validate → create inactive user → generate OTP → send email.
    Refs: SCN-AUTH-01→05
    """

    def __init__(self):
        self.usuario_repo = DjangoUsuarioRepository()
        self.otp_repo = DjangoOTPTokenRepository()
        self.registro_service = RegistroService()
        self.otp_service = OTPService()

    def registrar(
        self,
        username: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        rol: str,
        cedula: str = "",
        telefono: str = "",
        direccion: str = "",
    ) -> int:
        """
        Register a new user (inactive until OTP verification).

        Returns:
            The created user's ID.

        Raises:
            CorreoDuplicadoError, CedulaDuplicadaError, ValueError
        """
        # Domain validation (outside transaction — read-only checks)
        self.registro_service.validar_datos_registro(
            email=email,
            cedula=cedula,
            email_exists=self.usuario_repo.email_exists(email),
            cedula_exists=self.usuario_repo.cedula_exists(cedula) if cedula else False,
        )

        # Atomic transaction: if ANY step fails (including email), rollback everything
        with transaction.atomic():
            # Create inactive user via ORM (not through repo — need full model)
            user = Usuario.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                rol=rol,
                cedula=cedula or None,
                telefono=telefono,
                direccion=direccion,
                is_active=False,
            )

            # Generate and save OTP
            now = timezone.now()
            codigo, expira_en = self.otp_service.generar(
                usuario_id=user.pk,
                now=now,
                expiration_minutes=settings.OTP_EXPIRATION_MINUTES,
            )

            self.otp_repo.create(
                OTPTokenEntity(
                    usuario_id=user.pk,
                    codigo=codigo,
                    creado_en=now,
                    expira_en=expira_en,
                )
            )

            # Send OTP email — inside transaction so failure triggers rollback
            send_otp_email(user, codigo)

        return user.pk

    def verificar_otp(self, user_id: int, codigo: str) -> None:
        """
        Verify OTP code and activate user account.

        Raises:
            OTPInvalidoError, OTPExpiradoError
        """
        token = self.otp_repo.get_valid_token(user_id, codigo)
        if token is None:
            raise OTPInvalidoError("El código OTP ingresado es incorrecto.")

        now = timezone.now()
        self.otp_service.verificar(
            codigo_ingresado=codigo,
            codigo_almacenado=token.codigo,
            expira_en=token.expira_en,
            usado=token.usado,
            now=now,
        )

        # Mark token as used
        self.otp_repo.mark_as_used(user_id, codigo)

        # Activate user
        user = Usuario.objects.get(pk=user_id)
        user.is_active = True
        user.save(update_fields=["is_active"])

    def reenviar_otp(self, user_id: int) -> None:
        """
        Invalidate previous OTPs and send a new one.
        """
        self.otp_repo.invalidate_previous(user_id)

        user = Usuario.objects.get(pk=user_id)
        now = timezone.now()
        codigo, expira_en = self.otp_service.generar(
            usuario_id=user.pk,
            now=now,
            expiration_minutes=settings.OTP_EXPIRATION_MINUTES,
        )

        self.otp_repo.create(
            OTPTokenEntity(
                usuario_id=user.pk,
                codigo=codigo,
                creado_en=now,
                expira_en=expira_en,
            )
        )

        send_otp_email(user, codigo)


class LoginAppService:
    """
    Orchestrates login flow:
    check lockout → authenticate → audit → session.
    Refs: SCN-AUTH-06→10
    """

    def __init__(self):
        self.login_service = LoginService()
        self.auditoria_repo = DjangoAuditoriaRepository()

    def intentar_login(
        self, email: str, password: str, tipo_usuario: str, ip: Optional[str] = None
    ) -> Optional["Usuario"]:
        """
        Attempt login. Returns the user on success, None on auth failure.

        Raises:
            CuentaBloqueadaError: If account is currently locked.
        """
        from apps.usuarios.infrastructure.auth_backend import ECPPPAuthBackend

        now = timezone.now()

        # Find user by email (may not exist)
        try:
            user = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            # Audit failed attempt for unknown email
            self.auditoria_repo.registrar(
                RegistroAuditoriaEntity(
                    accion="login_fallido",
                    ip=ip,
                    detalle=f"Email no registrado: {email}",
                )
            )
            return None

        # Check lockout
        self.login_service.verificar_bloqueo(
            bloqueado_hasta=user.bloqueado_hasta,
            now=now,
        )

        # Attempt authentication
        backend = ECPPPAuthBackend()
        authenticated_user = backend.authenticate(
            request=None,
            email=email,
            password=password,
            tipo_usuario=tipo_usuario,
        )

        if authenticated_user is not None:
            # Success — reset attempts + audit
            intentos, _ = self.login_service.resetear_intentos()
            user.intentos_fallidos = intentos
            user.bloqueado_hasta = None
            user.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])

            self.auditoria_repo.registrar(
                RegistroAuditoriaEntity(
                    accion="login_exitoso",
                    usuario_id=user.pk,
                    ip=ip,
                    detalle=f"Rol: {tipo_usuario}",
                )
            )
            return authenticated_user

        # Failure — increment attempts
        nuevos_intentos, bloqueado_hasta = self.login_service.registrar_intento_fallido(
            intentos_fallidos=user.intentos_fallidos,
            max_intentos=settings.MAX_LOGIN_ATTEMPTS,
            lockout_minutes=settings.ACCOUNT_LOCKOUT_MINUTES,
            now=now,
        )

        user.intentos_fallidos = nuevos_intentos
        user.bloqueado_hasta = bloqueado_hasta
        user.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])

        if bloqueado_hasta:
            # Account locked — audit + notify
            self.auditoria_repo.registrar(
                RegistroAuditoriaEntity(
                    accion="bloqueo",
                    usuario_id=user.pk,
                    ip=ip,
                    detalle=f"Bloqueado hasta {bloqueado_hasta}. Intentos: {nuevos_intentos}",
                )
            )
            send_lockout_notification(user)
        else:
            self.auditoria_repo.registrar(
                RegistroAuditoriaEntity(
                    accion="login_fallido",
                    usuario_id=user.pk,
                    ip=ip,
                    detalle=f"Intento {nuevos_intentos}/{settings.MAX_LOGIN_ATTEMPTS}",
                )
            )

        return None


class PerfilAppService:
    """
    Orchestrates profile management:
    update personal data, change password.
    Refs: SCN-PROF-01→08
    """

    def actualizar_datos(
        self,
        user_id: int,
        first_name: str,
        last_name: str,
        telefono: str,
        direccion: str,
    ) -> None:
        """Update user's personal data."""
        user = Usuario.objects.get(pk=user_id)
        user.first_name = first_name
        user.last_name = last_name
        user.telefono = telefono
        user.direccion = direccion
        user.save(update_fields=["first_name", "last_name", "telefono", "direccion"])

    def cambiar_contrasena(
        self, user_id: int, old_password: str, new_password: str
    ) -> bool:
        """
        Change user's password after validating old password.

        Returns:
            True if password was changed, False if old password is wrong.
        """
        user = Usuario.objects.get(pk=user_id)

        if not user.check_password(old_password):
            return False

        user.set_password(new_password)
        user.save(update_fields=["password"])
        return True


class PasswordRecoveryAppService:
    """
    Wraps Django's built-in password recovery flow.
    No custom logic needed — Django handles token generation, email, and reset.
    This service exists for symmetry and future extensibility.
    """

    pass
