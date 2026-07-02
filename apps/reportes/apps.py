"""
AppConfig for the reportes bounded context (HU27).

Provides on-demand Excel/PDF export of calificaciones and asistencia.
No new model is created in this app — generation is in-memory and
streamed directly to the client.
"""

from django.apps import AppConfig


class ReportesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reportes"
    verbose_name = "Reportes ECPP"
