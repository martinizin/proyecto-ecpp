from django.db import models


class Solicitud(models.Model):
    """Student request for grade rectification or absence justification."""

    class TipoSolicitud(models.TextChoices):
        RECTIFICACION = "rectificacion", "Rectificacion de Calificacion"
        JUSTIFICACION = "justificacion", "Justificacion de Inasistencia"

    class EstadoSolicitud(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        APROBADA = "aprobada", "Aprobada"
        RECHAZADA = "rechazada", "Rechazada"

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
    descripcion = models.TextField()
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

    class Meta:
        verbose_name = "Solicitud"
        verbose_name_plural = "Solicitudes"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.estudiante} ({self.get_estado_display()})"
