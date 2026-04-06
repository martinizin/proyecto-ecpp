from django.contrib import admin

from apps.calificaciones.infrastructure.models import Calificacion, Evaluacion


@admin.register(Evaluacion)
class EvaluacionAdmin(admin.ModelAdmin):
    """Admin configuration for Evaluacion."""

    list_display = ("paralelo", "tipo", "peso", "fecha")
    list_filter = ("tipo",)
    search_fields = ("paralelo__asignatura__nombre",)


@admin.register(Calificacion)
class CalificacionAdmin(admin.ModelAdmin):
    """Admin configuration for Calificacion."""

    list_display = ("evaluacion", "estudiante", "nota", "fecha_registro")
    list_filter = ("evaluacion__tipo",)
    search_fields = ("estudiante__username", "estudiante__first_name")
