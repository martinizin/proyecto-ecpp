import os

from django.core.validators import FileExtensionValidator
from django.db import models


def solicitud_upload_path(instance, filename):
    """Upload to solicitudes/YYYY/MM/filename."""
    return os.path.join(
        "solicitudes",
        str(instance.fecha_creacion.year) if instance.fecha_creacion else "temp",
        str(instance.fecha_creacion.month) if instance.fecha_creacion else "temp",
        filename,
    )


class Solicitud(models.Model):
    """Student request for grade rectification or absence justification."""

    class TipoSolicitud(models.TextChoices):
        RECTIFICACION = "rectificacion", "Rectificación de Calificación"
        JUSTIFICACION = "justificacion", "Justificación de Inasistencia"

    class EstadoSolicitud(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EN_REVISION = "en_revision", "En Revisión"
        APROBADA = "aprobada", "Aprobada"
        RECHAZADA = "rechazada", "Rechazada"

    # --- Core fields ---
    tipo = models.CharField(max_length=20, choices=TipoSolicitud.choices)
    estudiante = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.CASCADE,
        related_name="solicitudes",
        limit_choices_to={"rol": "estudiante"},
    )
    estado = models.CharField(
        max_length=15,
        choices=EstadoSolicitud.choices,
        default=EstadoSolicitud.PENDIENTE,
    )
    descripcion = models.TextField(help_text="Motivo detallado de la solicitud.")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    resuelto_por = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitudes_resueltas",
    )
    respuesta = models.TextField(blank=True)

    # --- Recalificación: referencia a la calificación ---
    calificacion = models.ForeignKey(
        "calificaciones.Calificacion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitudes_recalificacion",
    )

    # --- Justificación: referencia a la asistencia ---
    asistencia = models.ForeignKey(
        "asistencia.Asistencia",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitudes_justificacion",
    )

    # --- Archivo adjunto (evidencia) ---
    archivo_adjunto = models.FileField(
        upload_to="solicitudes/%Y/%m/",
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["pdf", "jpg", "jpeg", "png"]),
        ],
        help_text="PDF o imagen (JPG/PNG). Máximo 5 MB.",
    )

    # --- Escalamiento ---
    requiere_secretaria = models.BooleanField(
        default=False,
        help_text="True si es la segunda solicitud o más para la misma evaluación.",
    )
    numero_solicitud = models.PositiveIntegerField(
        default=1,
        help_text="Número de solicitud para la misma evaluación/asistencia.",
    )

    class Meta:
        verbose_name = "Solicitud"
        verbose_name_plural = "Solicitudes"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"{self.get_tipo_display()} - " f"{self.estudiante} ({self.get_estado_display()})"
