from django.contrib import admin

from apps.asistencia.infrastructure.models import Asistencia


@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    """Admin configuration for Asistencia."""

    list_display = ("estudiante", "paralelo", "fecha", "estado")
    list_filter = ("estado", "fecha")
    search_fields = ("estudiante__username", "estudiante__first_name")
    date_hierarchy = "fecha"
