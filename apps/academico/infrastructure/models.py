from django.conf import settings
from django.db import models


class Periodo(models.Model):
    """Academic period linked to a specific license type (e.g. '2026-A — Licencia E')."""

    nombre = models.CharField(max_length=100)
    tipo_licencia = models.ForeignKey(
        "TipoLicencia",
        on_delete=models.CASCADE,
        related_name="periodos",
    )
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
        unique_together = ["nombre", "tipo_licencia"]
        ordering = ["-fecha_inicio"]

    def __str__(self):
        return f"{self.nombre} — {self.tipo_licencia.codigo}"


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

    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE, related_name="paralelos")
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE, related_name="paralelos")
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
    capacidad_maxima = models.PositiveIntegerField(default=30)

    class Meta:
        verbose_name = "Paralelo"
        verbose_name_plural = "Paralelos"
        unique_together = ["periodo", "tipo_licencia", "asignatura", "nombre"]
        ordering = ["periodo", "asignatura__codigo", "nombre"]

    def __str__(self):
        return f"{self.asignatura.codigo} - {self.nombre} ({self.periodo})"


class BloqueHorario(models.Model):
    """A time block for a paralelo (subject-section). Supports multiple blocks per paralelo."""

    class DiaSemana(models.TextChoices):
        LUNES = "lunes", "Lunes"
        MARTES = "martes", "Martes"
        MIERCOLES = "miercoles", "Miércoles"
        JUEVES = "jueves", "Jueves"
        VIERNES = "viernes", "Viernes"
        SABADO = "sabado", "Sábado"

    paralelo = models.ForeignKey(
        Paralelo,
        on_delete=models.CASCADE,
        related_name="bloques_horario",
    )
    dia_semana = models.CharField(max_length=10, choices=DiaSemana.choices)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    class Meta:
        verbose_name = "Bloque Horario"
        verbose_name_plural = "Bloques Horarios"
        unique_together = ["paralelo", "dia_semana", "hora_inicio"]
        ordering = ["dia_semana", "hora_inicio"]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.hora_inicio and self.hora_fin and self.hora_inicio >= self.hora_fin:
            raise ValidationError("La hora de inicio debe ser anterior a la hora de fin.")

    def __str__(self):
        return f"{self.get_dia_semana_display()} {self.hora_inicio:%H:%M}-{self.hora_fin:%H:%M}"


class Matricula(models.Model):
    """Enrollment of a student in a paralelo."""

    class Estado(models.TextChoices):
        ACTIVA = "activa", "Activa"
        RETIRADA = "retirada", "Retirada"
        SUSPENDIDA = "suspendida", "Suspendida"

    estudiante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="matriculas",
        limit_choices_to={"rol": "estudiante"},
    )
    paralelo = models.ForeignKey(
        Paralelo,
        on_delete=models.CASCADE,
        related_name="matriculas",
    )
    estado = models.CharField(
        max_length=15,
        choices=Estado.choices,
        default=Estado.ACTIVA,
    )
    fecha_matricula = models.DateTimeField(auto_now_add=True)
    matriculado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="matriculas_registradas",
    )

    class Meta:
        verbose_name = "Matrícula"
        verbose_name_plural = "Matrículas"
        unique_together = ["estudiante", "paralelo"]
        ordering = ["-fecha_matricula"]

    def __str__(self):
        return (
            f"{self.estudiante.get_full_name()} — "
            f"{self.paralelo} ({self.get_estado_display()})"
        )
