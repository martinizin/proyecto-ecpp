from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Evaluacion(models.Model):
    """Evaluation instance within a paralelo."""

    class TipoEvaluacion(models.TextChoices):
        PARCIAL_1 = "parcial1", "Parcial 1"
        PARCIAL_2_10H = "parcial2_10h", "Parcial 2 (10h)"
        PARCIAL_3 = "parcial3", "Parcial 3"
        PARCIAL_4_10H = "parcial4_10h", "Parcial 4 (10h)"
        PROYECTO = "proyecto", "Proyecto"
        EXAMEN_FINAL = "examen_final", "Examen Final"

    paralelo = models.ForeignKey(
        "academico.Paralelo", on_delete=models.CASCADE, related_name="evaluaciones"
    )
    tipo = models.CharField(max_length=20, choices=TipoEvaluacion.choices)
    peso = models.DecimalField(
        max_digits=5, decimal_places=2, help_text="Peso porcentual de la evaluacion"
    )
    fecha = models.DateField(null=True, blank=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = "Evaluacion"
        verbose_name_plural = "Evaluaciones"
        unique_together = ["paralelo", "tipo"]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.paralelo}"


class Calificacion(models.Model):
    """Individual student grade for an evaluation."""

    evaluacion = models.ForeignKey(
        Evaluacion, on_delete=models.CASCADE, related_name="calificaciones"
    )
    estudiante = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.CASCADE,
        related_name="calificaciones",
        limit_choices_to={"rol": "estudiante"},
    )
    nota = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = "Calificacion"
        verbose_name_plural = "Calificaciones"
        unique_together = ["evaluacion", "estudiante"]

    def __str__(self):
        return f"{self.estudiante} - {self.evaluacion}: {self.nota}"


class LogCalificacion(models.Model):
    """Registro inmutable de cambios en calificaciones. Nunca actualizar ni eliminar."""

    class TipoAccion(models.TextChoices):
        CREACION = "creacion", "Creación"
        MODIFICACION = "modificacion", "Modificación"
        RECALIFICACION = "recalificacion", "Recalificación"
        ELIMINACION = "eliminacion", "Eliminación"

    calificacion = models.ForeignKey(
        Calificacion,
        on_delete=models.SET_NULL,
        null=True,
        related_name="logs",
    )
    evaluacion_info = models.CharField(max_length=200)
    estudiante_info = models.CharField(max_length=200)
    accion = models.CharField(max_length=20, choices=TipoAccion.choices)
    valor_anterior = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    valor_nuevo = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    realizado_por = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        related_name="logs_calificacion",
    )
    ip = models.GenericIPAddressField(null=True, blank=True)
    motivo = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Log de Calificacion"
        verbose_name_plural = "Logs de Calificaciones"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["calificacion", "timestamp"]),
            models.Index(fields=["realizado_por", "timestamp"]),
        ]

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.get_accion_display()} — {self.estudiante_info}"


