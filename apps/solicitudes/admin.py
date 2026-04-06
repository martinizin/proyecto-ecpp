from django.contrib import admin

from apps.solicitudes.infrastructure.models import Solicitud


@admin.register(Solicitud)
class SolicitudAdmin(admin.ModelAdmin):
    """Admin configuration for Solicitud."""

    list_display = ("tipo", "estudiante", "estado", "fecha_creacion")
    list_filter = ("tipo", "estado")
    search_fields = ("estudiante__username", "descripcion")
    readonly_fields = ("fecha_creacion",)
