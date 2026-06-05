import uuid

from django.db import models


class ConversacionCopilot(models.Model):
    """A chat session between a user and the copilot assistant."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.CASCADE,
        related_name="conversaciones_copilot",
    )
    titulo = models.CharField(max_length=200, blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    ultima_actividad = models.DateTimeField(auto_now=True)
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Conversación Copilot"
        verbose_name_plural = "Conversaciones Copilot"
        ordering = ["-ultima_actividad"]
        indexes = [
            models.Index(fields=["usuario", "-ultima_actividad"]),
        ]

    def __str__(self):
        return f"{self.usuario} — {self.titulo or 'Sin título'}"


class MensajeCopilot(models.Model):
    """A single message in a copilot conversation."""

    class Rol(models.TextChoices):
        USER = "user", "Usuario"
        ASSISTANT = "assistant", "Asistente"
        SYSTEM = "system", "Sistema"

    conversacion = models.ForeignKey(
        ConversacionCopilot,
        on_delete=models.CASCADE,
        related_name="mensajes",
    )
    rol = models.CharField(max_length=10, choices=Rol.choices)
    contenido = models.TextField()
    tokens_usados = models.PositiveIntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Mensaje Copilot"
        verbose_name_plural = "Mensajes Copilot"
        ordering = ["timestamp"]

    def __str__(self):
        return f"[{self.rol}] {self.contenido[:50]}"
