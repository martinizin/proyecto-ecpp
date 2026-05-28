from django.contrib import admin

from apps.solicitudes.infrastructure.models import (
    ArchivoSolicitud,
    CertificadoJustificacion,
    ConfiguracionJustificacion,
    Solicitud,
)


@admin.register(Solicitud)
class SolicitudAdmin(admin.ModelAdmin):
    """Admin configuration for Solicitud."""

    list_display = ("tipo", "estudiante", "estado", "fecha_creacion")
    list_filter = ("tipo", "estado")
    search_fields = ("estudiante__username", "descripcion")
    readonly_fields = ("fecha_creacion",)


@admin.register(CertificadoJustificacion)
class CertificadoJustificacionAdmin(admin.ModelAdmin):
    """Admin configuration for CertificadoJustificacion (HU20)."""

    list_display = ("solicitud", "tipo", "fecha_certificado", "institucion_emisora")
    list_filter = ("tipo",)
    search_fields = (
        "solicitud__estudiante__username",
        "institucion_emisora",
        "numero_documento",
    )
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")


@admin.register(ArchivoSolicitud)
class ArchivoSolicitudAdmin(admin.ModelAdmin):
    """Admin configuration for ArchivoSolicitud (HU20)."""

    list_display = ("solicitud", "nombre_original", "tamanio_bytes", "subido_en")
    list_filter = ("subido_en",)
    search_fields = ("solicitud__estudiante__username", "nombre_original")
    readonly_fields = ("subido_en",)


@admin.register(ConfiguracionJustificacion)
class ConfiguracionJustificacionAdmin(admin.ModelAdmin):
    """Singleton admin for ConfiguracionJustificacion (HU21).

    Enforces the singleton invariant at the admin layer: cannot add a
    second row, cannot delete the existing one. ``actualizado_en`` is
    read-only since it is ``auto_now``.
    """

    list_display = ("pk", "deadline_dias", "alerta_dias", "actualizado_en")
    readonly_fields = ("actualizado_en",)

    def has_add_permission(self, request):
        return not ConfiguracionJustificacion.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
