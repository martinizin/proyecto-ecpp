from django.db import models


class Asistencia(models.Model):
    """Daily attendance record for a student in a paralelo."""

    class Estado(models.TextChoices):
        PRESENTE = "presente", "Presente"
        AUSENTE = "ausente", "Ausente"
        JUSTIFICADO = "justificado", "Justificado"

    estudiante = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.CASCADE,
        related_name="asistencias",
        limit_choices_to={"rol": "estudiante"},
    )
    paralelo = models.ForeignKey(
        "academico.Paralelo", on_delete=models.CASCADE, related_name="asistencias"
    )
    fecha = models.DateField()
    estado = models.CharField(
        max_length=15, choices=Estado.choices, default=Estado.AUSENTE
    )
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = "Asistencia"
        verbose_name_plural = "Asistencias"
        unique_together = ["estudiante", "paralelo", "fecha"]

    def __str__(self):
        return f"{self.estudiante} - {self.fecha} ({self.get_estado_display()})"
