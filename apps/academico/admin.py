from django.contrib import admin
from django.core.exceptions import ValidationError

from apps.academico.domain.exceptions import (
    CupoExcedidoError,
    EstadoMatriculaInvalidoError,
    MatriculaDuplicadaError,
)
from apps.academico.domain.services import MatriculaService
from apps.academico.infrastructure.models import (
    Asignatura,
    Matricula,
    Paralelo,
    Periodo,
)


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


@admin.register(Matricula)
class MatriculaAdmin(admin.ModelAdmin):
    """Admin configuration for Matricula with enrollment validations."""

    list_display = (
        "estudiante",
        "paralelo",
        "estado",
        "fecha_matricula",
        "matriculado_por",
    )
    list_filter = ("estado", "paralelo__periodo")
    search_fields = (
        "estudiante__cedula",
        "estudiante__last_name",
        "estudiante__first_name",
    )
    autocomplete_fields = ("estudiante", "paralelo")
    readonly_fields = ("fecha_matricula", "matriculado_por")

    def save_model(self, request, obj, form, change):
        """Validate enrollment rules before saving."""
        service = MatriculaService()

        # Set who registered the enrollment
        if not change:
            obj.matriculado_por = request.user

        # Validate period is active (only on creation)
        if not change:
            service.validar_periodo_activo(obj.paralelo.periodo.activo)

        # Validate no duplicate enrollment (only on creation)
        if not change:
            existe = Matricula.objects.filter(
                estudiante=obj.estudiante,
                paralelo=obj.paralelo,
            ).exists()
            service.validar_no_duplicada(existe)

        # Validate capacity (only on creation or when reactivating)
        if not change or (
            change and obj.estado == Matricula.Estado.ACTIVA
        ):
            activas = Matricula.objects.filter(
                paralelo=obj.paralelo,
                estado=Matricula.Estado.ACTIVA,
            )
            # Exclude self when editing
            if change:
                activas = activas.exclude(pk=obj.pk)
            service.validar_cupo(activas.count(), obj.paralelo.capacidad_maxima)

        # Validate state transitions (only on edit)
        if change:
            original = Matricula.objects.get(pk=obj.pk)
            if original.estado != obj.estado:
                # Map user to domain role: superusers act as secretaría
                rol_dominio = (
                    "secretaria"
                    if request.user.is_superuser
                    else request.user.rol
                )
                service.validar_transicion_estado(
                    estado_actual=original.estado,
                    nuevo_estado=obj.estado,
                    rol=rol_dominio,
                )

        super().save_model(request, obj, form, change)
