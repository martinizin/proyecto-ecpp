from django.contrib import admin

from apps.solicitudes.infrastructure.models import (
    ArchivoSolicitud,
    CertificadoJustificacion,
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
