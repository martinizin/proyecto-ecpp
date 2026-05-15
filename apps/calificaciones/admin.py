from django.contrib import admin

from apps.calificaciones.infrastructure.models import Calificacion, Evaluacion, LogCalificacion


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


@admin.register(LogCalificacion)
class LogCalificacionAdmin(admin.ModelAdmin):
    """Log de auditoría — solo lectura."""

    list_display = (
        "timestamp",
        "accion",
        "estudiante_info",
        "evaluacion_info",
        "valor_anterior",
        "valor_nuevo",
        "realizado_por",
        "ip",
    )
    list_filter = ("accion",)
    search_fields = ("estudiante_info", "evaluacion_info", "realizado_por__username")
    readonly_fields = (
        "calificacion",
        "evaluacion_info",
        "estudiante_info",
        "accion",
        "valor_anterior",
        "valor_nuevo",
        "realizado_por",
        "ip",
        "motivo",
        "timestamp",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
