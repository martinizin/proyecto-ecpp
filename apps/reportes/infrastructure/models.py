from django.conf import settings
from django.db import models


class ReporteANT(models.Model):
    """Regulatory report for ANT (Resolución 005-DIR-2022). Immutable snapshot."""

    periodo = models.ForeignKey(
        "academico.Periodo",
        on_delete=models.PROTECT,
        related_name="reportes_ant",
    )
    numero_resolucion = models.CharField(max_length=50, default="005-DIR-2022-ANT")
    generado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reportes_ant_generados",
    )
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    total_estudiantes = models.PositiveIntegerField(default=0)
    total_aprobados = models.PositiveIntegerField(default=0)
    total_reprobados = models.PositiveIntegerField(default=0)
    total_desertores = models.PositiveIntegerField(default=0)
    total_en_curso = models.PositiveIntegerField(default=0)
    archivo_pdf = models.FileField(upload_to="reportes/ant/%Y/%m/")
    archivo_excel = models.FileField(
        upload_to="reportes/ant/%Y/%m/", null=True, blank=True
    )
    hash_sha256 = models.CharField(max_length=64)
    firma_responsable_imagen = models.CharField(
        max_length=300,
        blank=True,
        help_text="Path relativo a la imagen de firma del responsable (PNG).",
    )
    nombre_firmante = models.CharField(max_length=200)
    cedula_firmante = models.CharField(max_length=20)
    cargo_firmante = models.CharField(
        max_length=100, default="Director Académico ECPPP"
    )
    notas = models.TextField(blank=True)

    class Meta:
        verbose_name = "Reporte ANT"
        verbose_name_plural = "Reportes ANT"
        ordering = ["-fecha_generacion"]
        indexes = [
            models.Index(fields=["periodo", "-fecha_generacion"]),
        ]

    def __str__(self):
        return f"Reporte ANT {self.periodo} — {self.fecha_generacion:%Y-%m-%d %H:%M}"
