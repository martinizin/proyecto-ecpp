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
    nota = models.DecimalField(max_digits=5, decimal_places=2)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = "Calificacion"
        verbose_name_plural = "Calificaciones"
        unique_together = ["evaluacion", "estudiante"]

    def __str__(self):
        return f"{self.estudiante} - {self.evaluacion}: {self.nota}"
