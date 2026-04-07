"""
Views for the Academico bounded context.
CRUD views for periods, subjects, parallels, and license types.
All write operations restricted to Inspector role via RolRequeridoMixin.
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView

from apps.academico.application.services import (
    AsignaturaAppService,
    ParaleloAppService,
    PeriodoAppService,
)
from apps.academico.domain.exceptions import (
    AcademicoError,
    PeriodoActivoExistenteError,
)
from apps.academico.infrastructure.models import (
    Asignatura,
    Paralelo,
    Periodo,
    TipoLicencia,
)
from apps.usuarios.presentation.permissions import RolRequeridoMixin

from .forms import AsignaturaForm, ParaleloForm, PeriodoForm


# =============================================================================
# Período Views
# =============================================================================


class PeriodoListView(RolRequeridoMixin, ListView):
    """List all academic periods — Inspector only."""

    rol_requerido = "inspector"
    model = Periodo
    template_name = "academico/periodo_list.html"
    context_object_name = "periodos"


class PeriodoCreateView(RolRequeridoMixin, ListView):
    """Create a new academic period — Inspector only."""

    rol_requerido = "inspector"
    template_name = "academico/periodo_form.html"
    model = Periodo  # Required by ListView but unused

    def get(self, request):
        form = PeriodoForm()
        return render(request, self.template_name, {"form": form, "editing": False})

    def post(self, request):
        form = PeriodoForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "editing": False})

        service = PeriodoAppService()
        try:
            service.crear(
                nombre=form.cleaned_data["nombre"],
                fecha_inicio=form.cleaned_data["fecha_inicio"],
                fecha_fin=form.cleaned_data["fecha_fin"],
                creado_por_id=request.user.pk,
            )
        except AcademicoError as e:
            form.add_error(None, str(e))
            return render(request, self.template_name, {"form": form, "editing": False})

        messages.success(request, "Período creado exitosamente.")
        return redirect("academico:periodo_list")


class PeriodoUpdateView(RolRequeridoMixin, ListView):
    """Update an academic period — Inspector only."""

    rol_requerido = "inspector"
    template_name = "academico/periodo_form.html"
    model = Periodo  # Required by ListView but unused

    def get(self, request, pk):
        periodo = get_object_or_404(Periodo, pk=pk)
        form = PeriodoForm(instance=periodo)
        return render(request, self.template_name, {
            "form": form,
            "editing": True,
            "periodo": periodo,
        })

    def post(self, request, pk):
        periodo = get_object_or_404(Periodo, pk=pk)
        form = PeriodoForm(request.POST, instance=periodo)
        if not form.is_valid():
            return render(request, self.template_name, {
                "form": form,
                "editing": True,
                "periodo": periodo,
            })

        service = PeriodoAppService()

        # Handle activation toggle
        activar = request.POST.get("activar") == "1"
        confirmar = request.POST.get("confirmar_desactivacion") == "1"

        try:
            service.actualizar(
                periodo_id=pk,
                nombre=form.cleaned_data["nombre"],
                fecha_inicio=form.cleaned_data["fecha_inicio"],
                fecha_fin=form.cleaned_data["fecha_fin"],
                usuario_id=request.user.pk,
            )

            if activar:
                service.activar(
                    periodo_id=pk,
                    usuario_id=request.user.pk,
                    confirmar_desactivacion=confirmar,
                )
                messages.success(request, "Período activado exitosamente.")

        except PeriodoActivoExistenteError as e:
            # Return to form with confirmation needed
            return render(request, self.template_name, {
                "form": PeriodoForm(instance=periodo),
                "editing": True,
                "periodo": periodo,
                "confirmation_needed": True,
                "confirmation_message": str(e),
            })
        except AcademicoError as e:
            form.add_error(None, str(e))
            return render(request, self.template_name, {
                "form": form,
                "editing": True,
                "periodo": periodo,
            })

        messages.success(request, "Período actualizado exitosamente.")
        return redirect("academico:periodo_list")


# =============================================================================
# Asignatura Views
# =============================================================================


class AsignaturaListView(RolRequeridoMixin, ListView):
    """List all subjects — Inspector only."""

    rol_requerido = "inspector"
    model = Asignatura
    template_name = "academico/asignatura_list.html"
    context_object_name = "asignaturas"


class AsignaturaCreateView(RolRequeridoMixin, ListView):
    """Create a new subject — Inspector only."""

    rol_requerido = "inspector"
    template_name = "academico/asignatura_form.html"
    model = Asignatura

    def get(self, request):
        form = AsignaturaForm()
        return render(request, self.template_name, {"form": form, "editing": False})

    def post(self, request):
        form = AsignaturaForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "editing": False})

        service = AsignaturaAppService()
        try:
            service.crear(
                nombre=form.cleaned_data["nombre"],
                codigo=form.cleaned_data["codigo"],
                horas_lectivas=form.cleaned_data["horas_lectivas"],
                tipos_licencia_ids=list(
                    form.cleaned_data["tipos_licencia"].values_list("id", flat=True)
                ),
                usuario_id=request.user.pk,
                descripcion=form.cleaned_data.get("descripcion", ""),
            )
        except (AcademicoError, ValueError) as e:
            form.add_error(None, str(e))
            return render(request, self.template_name, {"form": form, "editing": False})

        messages.success(request, "Asignatura creada exitosamente.")
        return redirect("academico:asignatura_list")


class AsignaturaUpdateView(RolRequeridoMixin, ListView):
    """Update a subject — Inspector only."""

    rol_requerido = "inspector"
    template_name = "academico/asignatura_form.html"
    model = Asignatura

    def get(self, request, pk):
        asignatura = get_object_or_404(Asignatura, pk=pk)
        form = AsignaturaForm(instance=asignatura)
        return render(request, self.template_name, {
            "form": form,
            "editing": True,
            "asignatura": asignatura,
        })

    def post(self, request, pk):
        asignatura = get_object_or_404(Asignatura, pk=pk)
        form = AsignaturaForm(request.POST, instance=asignatura)
        if not form.is_valid():
            return render(request, self.template_name, {
                "form": form,
                "editing": True,
                "asignatura": asignatura,
            })

        service = AsignaturaAppService()
        try:
            service.actualizar(
                asignatura_id=pk,
                nombre=form.cleaned_data["nombre"],
                codigo=form.cleaned_data["codigo"],
                horas_lectivas=form.cleaned_data["horas_lectivas"],
                tipos_licencia_ids=list(
                    form.cleaned_data["tipos_licencia"].values_list("id", flat=True)
                ),
                usuario_id=request.user.pk,
                descripcion=form.cleaned_data.get("descripcion", ""),
            )
        except (AcademicoError, ValueError) as e:
            form.add_error(None, str(e))
            return render(request, self.template_name, {
                "form": form,
                "editing": True,
                "asignatura": asignatura,
            })

        messages.success(request, "Asignatura actualizada exitosamente.")
        return redirect("academico:asignatura_list")


# =============================================================================
# Paralelo Views
# =============================================================================


class ParaleloListView(RolRequeridoMixin, ListView):
    """List all parallels — Inspector only."""

    rol_requerido = "inspector"
    model = Paralelo
    template_name = "academico/paralelo_list.html"
    context_object_name = "paralelos"

    def get_queryset(self):
        return Paralelo.objects.select_related(
            "asignatura", "periodo", "docente", "tipo_licencia"
        ).all()


class ParaleloCreateView(RolRequeridoMixin, ListView):
    """Create a new parallel — Inspector only."""

    rol_requerido = "inspector"
    template_name = "academico/paralelo_form.html"
    model = Paralelo

    def get(self, request):
        form = ParaleloForm()
        return render(request, self.template_name, {"form": form, "editing": False})

    def post(self, request):
        form = ParaleloForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "editing": False})

        service = ParaleloAppService()
        docente = form.cleaned_data["docente"]
        periodo = form.cleaned_data["periodo"]
        asignatura = form.cleaned_data["asignatura"]

        try:
            service.crear(
                asignatura_codigo=asignatura.codigo,
                periodo_nombre=periodo.nombre,
                docente_username=docente.username,
                docente_rol=docente.rol,
                tipo_licencia_id=form.cleaned_data["tipo_licencia"].pk,
                nombre=form.cleaned_data["nombre"],
                horario=form.cleaned_data.get("horario", ""),
                capacidad_maxima=form.cleaned_data["capacidad_maxima"],
                periodo_id=periodo.pk,
                periodo_activo=periodo.activo,
                asignatura_id=asignatura.pk,
                usuario_id=request.user.pk,
            )
        except (AcademicoError, ValueError) as e:
            form.add_error(None, str(e))
            return render(request, self.template_name, {"form": form, "editing": False})

        messages.success(request, "Paralelo creado exitosamente.")
        return redirect("academico:paralelo_list")


class ParaleloUpdateView(RolRequeridoMixin, ListView):
    """Update a parallel — Inspector only."""

    rol_requerido = "inspector"
    template_name = "academico/paralelo_form.html"
    model = Paralelo

    def get(self, request, pk):
        paralelo = get_object_or_404(Paralelo, pk=pk)
        form = ParaleloForm(instance=paralelo)
        return render(request, self.template_name, {
            "form": form,
            "editing": True,
            "paralelo": paralelo,
        })

    def post(self, request, pk):
        paralelo = get_object_or_404(
            Paralelo.objects.select_related("asignatura", "periodo", "docente"),
            pk=pk,
        )
        form = ParaleloForm(request.POST, instance=paralelo)
        if not form.is_valid():
            return render(request, self.template_name, {
                "form": form,
                "editing": True,
                "paralelo": paralelo,
            })

        service = ParaleloAppService()
        docente = form.cleaned_data["docente"]
        periodo = form.cleaned_data["periodo"]
        asignatura = form.cleaned_data["asignatura"]

        try:
            service.actualizar(
                paralelo_id=pk,
                asignatura_codigo=asignatura.codigo,
                periodo_nombre=periodo.nombre,
                docente_username=docente.username,
                docente_rol=docente.rol,
                tipo_licencia_id=form.cleaned_data["tipo_licencia"].pk,
                nombre=form.cleaned_data["nombre"],
                horario=form.cleaned_data.get("horario", ""),
                capacidad_maxima=form.cleaned_data["capacidad_maxima"],
                periodo_id=periodo.pk,
                periodo_activo=periodo.activo,
                asignatura_id=asignatura.pk,
                usuario_id=request.user.pk,
            )
        except (AcademicoError, ValueError) as e:
            form.add_error(None, str(e))
            return render(request, self.template_name, {
                "form": form,
                "editing": True,
                "paralelo": paralelo,
            })

        messages.success(request, "Paralelo actualizado exitosamente.")
        return redirect("academico:paralelo_list")


# =============================================================================
# TipoLicencia Views (read-only)
# =============================================================================


class TipoLicenciaListView(RolRequeridoMixin, ListView):
    """List all license types — Inspector only, read-only."""

    rol_requerido = "inspector"
    model = TipoLicencia
    template_name = "academico/tipo_licencia_list.html"
    context_object_name = "tipos_licencia"

    def get_queryset(self):
        return TipoLicencia.objects.all()
