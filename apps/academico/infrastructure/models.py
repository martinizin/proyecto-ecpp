from django.conf import settings
from django.db import models


class Periodo(models.Model):
    """Academic period (e.g. '2026-1')."""

    nombre = models.CharField(max_length=100, unique=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    activo = models.BooleanField(default=False)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="periodos_creados",
    )
    modificado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Periodo Academico"
        verbose_name_plural = "Periodos Academicos"
        ordering = ["-fecha_inicio"]

    def __str__(self):
        return self.nombre


class TipoLicencia(models.Model):
    """License type: Conducción (C), Educación (E), Educación Convalidada (EC)."""

    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=5, unique=True)
    duracion_meses = models.PositiveIntegerField()
    num_asignaturas = models.PositiveIntegerField()
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Tipo de Licencia"
        verbose_name_plural = "Tipos de Licencia"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} — {self.nombre}"


class Asignatura(models.Model):
    """Course/subject in the curriculum."""

    nombre = models.CharField(max_length=200)
    codigo = models.CharField(max_length=20, unique=True)
    descripcion = models.TextField(blank=True)
    horas_lectivas = models.PositiveIntegerField(default=40)
    tipos_licencia = models.ManyToManyField(
        TipoLicencia,
        related_name="asignaturas",
        blank=True,
    )

    class Meta:
        verbose_name = "Asignatura"
        verbose_name_plural = "Asignaturas"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Paralelo(models.Model):
    """Class section — links a subject, period, license type, teacher, and students."""

    asignatura = models.ForeignKey(
        Asignatura, on_delete=models.CASCADE, related_name="paralelos"
    )
    periodo = models.ForeignKey(
        Periodo, on_delete=models.CASCADE, related_name="paralelos"
    )
    tipo_licencia = models.ForeignKey(
        TipoLicencia, on_delete=models.CASCADE, related_name="paralelos"
    )
    docente = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.CASCADE,
        related_name="paralelos_asignados",
        limit_choices_to={"rol": "docente"},
    )
    nombre = models.CharField(max_length=10)  # e.g. "A", "B", "GR1"
    horario = models.TextField(blank=True)
    capacidad_maxima = models.PositiveIntegerField(default=30)
    estudiantes = models.ManyToManyField(
        "usuarios.Usuario",
        related_name="paralelos_matriculados",
        blank=True,
        limit_choices_to={"rol": "estudiante"},
    )

    class Meta:
        verbose_name = "Paralelo"
        verbose_name_plural = "Paralelos"
        unique_together = ["periodo", "tipo_licencia", "asignatura", "nombre"]
        ordering = ["periodo", "asignatura__codigo", "nombre"]

    def __str__(self):
        return f"{self.asignatura.codigo} - {self.nombre} ({self.periodo})"
