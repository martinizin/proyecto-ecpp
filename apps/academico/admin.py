from django.contrib import admin

from apps.academico.infrastructure.models import Asignatura, Paralelo, Periodo


@admin.register(Periodo)
class PeriodoAdmin(admin.ModelAdmin):
    """Admin configuration for Periodo."""

    list_display = ("nombre", "fecha_inicio", "fecha_fin", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)


@admin.register(Asignatura)
class AsignaturaAdmin(admin.ModelAdmin):
    """Admin configuration for Asignatura."""

    list_display = ("codigo", "nombre")
    search_fields = ("codigo", "nombre")


@admin.register(Paralelo)
class ParaleloAdmin(admin.ModelAdmin):
    """Admin configuration for Paralelo."""

    list_display = ("asignatura", "periodo", "nombre", "docente")
    list_filter = ("periodo", "asignatura")
    search_fields = ("nombre", "asignatura__nombre", "docente__username")
    filter_horizontal = ("estudiantes",)
