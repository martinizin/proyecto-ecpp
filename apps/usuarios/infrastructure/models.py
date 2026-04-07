from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """
    Custom user model extending AbstractUser.
    Adds role-based access (estudiante, docente, inspector),
    Ecuadorian ID fields and account security controls.
    """

    class Rol(models.TextChoices):
        ESTUDIANTE = "estudiante", "Estudiante"
        DOCENTE = "docente", "Docente"
        INSPECTOR = "inspector", "Inspector"

    rol = models.CharField(max_length=20, choices=Rol.choices)
    cedula = models.CharField(max_length=13, unique=True, blank=True, null=True)
    telefono = models.CharField(max_length=15, blank=True)
    direccion = models.TextField(blank=True, default="")

    # Seguridad — control de intentos de login (RR022)
    intentos_fallidos = models.PositiveIntegerField(default=0)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return f"{self.get_full_name()} ({self.rol})"


class OTPToken(models.Model):
    """
    One-Time Password token for email verification during registration.
    Uses a 6-digit code with configurable expiration (D2, D7).
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="otp_tokens",
    )
    codigo = models.CharField(max_length=6)
    creado_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField()
    usado = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Token OTP"
        verbose_name_plural = "Tokens OTP"
        indexes = [
            models.Index(fields=["usuario", "usado", "expira_en"]),
        ]

    def __str__(self):
        estado = "usado" if self.usado else "pendiente"
        return f"OTP {self.codigo} ({estado}) — {self.usuario}"


class RegistroAuditoria(models.Model):
    """
    Audit log for security-relevant actions: login, logout, lockout, etc.
    Shared across bounded contexts via string FK (AD3).
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registros_auditoria",
    )
    accion = models.CharField(max_length=50)
    ip = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    detalle = models.TextField(blank=True)

    class Meta:
        verbose_name = "Registro de Auditoría"
        verbose_name_plural = "Registros de Auditoría"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["usuario", "accion", "timestamp"]),
        ]

    def __str__(self):
        user_str = self.usuario or "anónimo"
        return f"[{self.timestamp}] {self.accion} — {user_str}"
