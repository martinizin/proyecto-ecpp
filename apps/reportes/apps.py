"""
AppConfig for the reportes bounded context (HU26 + HU27).

HU27: on-demand Excel/PDF export of calificaciones and asistencia,
generated in-memory and streamed directly to the client.
HU26: regulatory ANT reports (Resolucion 005-DIR-2022) persisted as
immutable snapshots with SHA-256 integrity hash.
"""

from django.apps import AppConfig


class ReportesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reportes"
    verbose_name = "Reportes ECPP"
