"""
Notification model — stores in-app notifications for users.
"""

from django.conf import settings
from django.db import models


class Notificacion(models.Model):
    class Tipo(models.TextChoices):
        ALERTA_INASISTENCIA = "alerta_inasistencia", "Alerta de inasistencia"
        SOLICITUD_RECALIFICACION = "solicitud_recalificacion", "Solicitud de recalificación"
        SOLICITUD_JUSTIFICACION = "solicitud_justificacion", "Solicitud de justificación"
        CAMBIO_ESTADO_SOLICITUD = (
            "cambio_estado_solicitud",
            "Cambio de estado de solicitud",
        )
        GENERAL = "general", "General"

    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notificaciones",
    )
    tipo = models.CharField(max_length=30, choices=Tipo.choices, default=Tipo.GENERAL)
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    leida = models.BooleanField(default=False)
    url = models.CharField(max_length=300, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["destinatario", "leida", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.titulo} → {self.destinatario}"
