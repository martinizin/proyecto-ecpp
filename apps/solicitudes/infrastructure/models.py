import os

from django.core.validators import FileExtensionValidator
from django.db import models

from apps.solicitudes.domain.value_objects import TipoCertificado


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


class HistorialSolicitud(models.Model):
    """Tracks every state change of a solicitud for full traceability."""

    solicitud = models.ForeignKey(
        Solicitud,
        on_delete=models.CASCADE,
        related_name="historial",
    )
    estado_anterior = models.CharField(
        max_length=15,
        choices=Solicitud.EstadoSolicitud.choices,
    )
    estado_nuevo = models.CharField(
        max_length=15,
        choices=Solicitud.EstadoSolicitud.choices,
    )
    cambiado_por = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.SET_NULL,
        null=True,
    )
    comentario = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Historial de Solicitud"
        verbose_name_plural = "Historial de Solicitudes"
        ordering = ["-timestamp"]

    def __str__(self):
        return (
            f"{self.solicitud_id}: "
            f"{self.estado_anterior} → {self.estado_nuevo} "
            f"({self.cambiado_por})"
        )


# --------------------------------------------------------------------------- #
# HU20 — Certificados de justificación
# --------------------------------------------------------------------------- #


class CertificadoJustificacion(models.Model):
    """Categorized certificate metadata attached to a justification Solicitud.

    One certificate per Solicitud (OneToOne). The ``tipo`` discriminator
    selects which of the type-specific fields are meaningful; per-type
    required-field enforcement is handled by
    ``CertificadoValidationService`` in the domain layer.
    """

    # Re-exported so ``CertificadoJustificacion.TipoCertificado`` keeps
    # working for callers that already use it; the canonical definition
    # lives in ``apps.solicitudes.domain.value_objects``.
    TipoCertificado = TipoCertificado

    solicitud = models.OneToOneField(
        "solicitudes.Solicitud",
        on_delete=models.CASCADE,
        related_name="certificado",
    )
    tipo = models.CharField(max_length=15, choices=TipoCertificado.choices)
    institucion_emisora = models.CharField(max_length=200, blank=True)
    fecha_certificado = models.DateField()
    numero_documento = models.CharField(max_length=100, blank=True)

    # Médico-specific
    nombre_medico = models.CharField(max_length=200, blank=True)
    dias_reposo = models.PositiveIntegerField(null=True, blank=True)

    # Laboral-specific
    cargo = models.CharField(max_length=200, blank=True)

    # Calamidad-specific
    descripcion_evento = models.TextField(blank=True)
    relacion_familiar = models.CharField(max_length=100, blank=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Certificado de Justificación"
        verbose_name_plural = "Certificados de Justificación"
        indexes = [
            models.Index(fields=["tipo"]),
            models.Index(fields=["fecha_certificado"]),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.solicitud}"


class ArchivoSolicitud(models.Model):
    """Individual attachment file for a Solicitud (HU20 multi-file uploads).

    A Solicitud may have up to ``CertificadoValidationService.MAX_ARCHIVOS``
    rows. The DB enforces the 5 MB size cap via a CheckConstraint; extension
    validation lives in the domain layer because filename inspection is
    Python-side only.
    """

    solicitud = models.ForeignKey(
        "solicitudes.Solicitud",
        on_delete=models.CASCADE,
        related_name="archivos",
    )
    archivo = models.FileField(
        upload_to="solicitudes/%Y/%m/",
        validators=[
            FileExtensionValidator(allowed_extensions=["pdf", "jpg", "jpeg", "png"]),
        ],
    )
    nombre_original = models.CharField(max_length=255)
    tipo_mime = models.CharField(max_length=100, blank=True)
    tamanio_bytes = models.PositiveIntegerField()
    subido_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Archivo de Solicitud"
        verbose_name_plural = "Archivos de Solicitud"
        ordering = ["subido_en"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(tamanio_bytes__lte=5 * 1024 * 1024),
                name="archivo_max_5mb",
            ),
        ]
        indexes = [
            models.Index(fields=["solicitud"]),
        ]

    def __str__(self):
        return self.nombre_original
