from django.db import models


class Periodo(models.Model):
    """Academic period (e.g. '2026-1')."""

    nombre = models.CharField(max_length=100, unique=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    activo = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Periodo Academico"
        verbose_name_plural = "Periodos Academicos"
        ordering = ["-fecha_inicio"]

    def __str__(self):
        return self.nombre


class Asignatura(models.Model):
    """Course/subject in the curriculum."""

    nombre = models.CharField(max_length=200)
    codigo = models.CharField(max_length=20, unique=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = "Asignatura"
        verbose_name_plural = "Asignaturas"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Paralelo(models.Model):
    """Class section — links a subject, period, teacher, and students."""

    asignatura = models.ForeignKey(
        Asignatura, on_delete=models.CASCADE, related_name="paralelos"
    )
    periodo = models.ForeignKey(
        Periodo, on_delete=models.CASCADE, related_name="paralelos"
    )
    docente = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.CASCADE,
        related_name="paralelos_asignados",
        limit_choices_to={"rol": "docente"},
    )
    nombre = models.CharField(max_length=10)  # e.g. "A", "B", "GR1"
    horario = models.TextField(blank=True)
    estudiantes = models.ManyToManyField(
        "usuarios.Usuario",
        related_name="paralelos_matriculados",
        blank=True,
        limit_choices_to={"rol": "estudiante"},
    )

    class Meta:
        verbose_name = "Paralelo"
        verbose_name_plural = "Paralelos"
        unique_together = ["asignatura", "periodo", "nombre"]

    def __str__(self):
        return f"{self.asignatura.codigo} - {self.nombre} ({self.periodo})"
