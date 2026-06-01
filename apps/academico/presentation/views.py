"""
Views for the Academico bounded context.
CRUD views for periods, subjects, parallels, and license types.
All write operations restricted to Inspector role via MultiRolRequeridoMixin.
"""

from collections import OrderedDict
from datetime import datetime, time, timedelta

from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView

from apps.academico.application.services import (
    AsignaturaAppService,
    ParaleloAppService,
    PeriodoAppService,
)
from apps.academico.domain.exceptions import (
    AcademicoError,
    ConflictoHorarioDocenteError,
    PeriodoActivoExistenteError,
)
from apps.academico.domain.services import AsignaturaService, HorarioConflictoService
from apps.academico.presentation.exception_mapping import to_django, _serialize_conflictos
from apps.academico.infrastructure.models import (
    Asignatura,
    BloqueHorario,
    Matricula,
    Paralelo,
    Periodo,
    TipoLicencia,
)
from apps.usuarios.infrastructure.models import Usuario
from apps.usuarios.presentation.permissions import MultiRolRequeridoMixin, RolRequeridoMixin

from .forms import (
    AsignaturaForm,
    ParaleloAsignaturaEditForm,
    ParaleloForm,
    ParaleloLoteForm,
    PeriodoForm,
)


# =============================================================================
# Período Views
# =============================================================================


class PeriodoListView(MultiRolRequeridoMixin, ListView):
    """List all academic periods — Inspector only."""

    roles_permitidos = ["inspector", "secretaria"]
    model = Periodo
    template_name = "academico/periodo_list.html"
    context_object_name = "periodos"

    def get_queryset(self):
        return Periodo.objects.select_related("tipo_licencia").all()


class PeriodoCreateView(MultiRolRequeridoMixin, ListView):
    """Create a new academic period — Inspector only."""

    roles_permitidos = ["inspector", "secretaria"]
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
                tipo_licencia_id=form.cleaned_data["tipo_licencia"].pk,
                creado_por_id=request.user.pk,
            )
        except AcademicoError as e:
            form.add_error(None, str(e))
            return render(request, self.template_name, {"form": form, "editing": False})

        messages.success(request, "Período creado exitosamente.")
        return redirect("academico:periodo_list")


class PeriodoUpdateView(MultiRolRequeridoMixin, ListView):
    """Update an academic period — Inspector only."""

    roles_permitidos = ["inspector", "secretaria"]
    template_name = "academico/periodo_form.html"
    model = Periodo  # Required by ListView but unused

    def get(self, request, pk):
        periodo = get_object_or_404(Periodo, pk=pk)
        form = PeriodoForm(instance=periodo)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "editing": True,
                "periodo": periodo,
            },
        )

    def post(self, request, pk):
        periodo = get_object_or_404(Periodo, pk=pk)
        form = PeriodoForm(request.POST, instance=periodo)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "editing": True,
                    "periodo": periodo,
                },
            )

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
                tipo_licencia_id=form.cleaned_data["tipo_licencia"].pk,
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
            periodo.refresh_from_db()
            return render(
                request,
                self.template_name,
                {
                    "form": PeriodoForm(instance=periodo),
                    "editing": True,
                    "periodo": periodo,
                    "confirmation_needed": True,
                    "confirmation_message": str(e),
                },
            )
        except AcademicoError as e:
            form.add_error(None, str(e))
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "editing": True,
                    "periodo": periodo,
                },
            )

        messages.success(request, "Período actualizado exitosamente.")
        return redirect("academico:periodo_list")


class PeriodoDesactivarView(MultiRolRequeridoMixin, View):
    """Deactivate an active period — Inspector/Secretaría."""

    roles_permitidos = ["inspector", "secretaria"]

    def post(self, request, pk):
        service = PeriodoAppService()
        try:
            service.desactivar(periodo_id=pk, usuario_id=request.user.pk)
            messages.success(request, "Período desactivado exitosamente.")
        except AcademicoError as e:
            messages.error(request, str(e))
        return redirect("academico:periodo_list")


# =============================================================================
# Asignatura Views
# =============================================================================


def _parse_licencias_from_post(post_data, tipos_licencia_qs):
    """Parse tipo_licencia_{id}/horas_{id} pairs from POST data.

    Returns list of {"tipo_licencia_id": int, "horas_lectivas": int}.
    """
    licencias = []
    for tl in tipos_licencia_qs:
        if post_data.get(f"tipo_licencia_{tl.pk}"):
            try:
                horas = int(post_data.get(f"horas_{tl.pk}", 0))
            except (ValueError, TypeError):
                horas = 0
            licencias.append({"tipo_licencia_id": tl.pk, "horas_lectivas": horas})
    return licencias


def _build_tipos_licencia_data(tipos_licencia_qs, asignatura=None):
    """Build context list for template with checked/horas state."""
    existing = {}
    if asignatura:
        for al in asignatura.asignatura_licencias.select_related("tipo_licencia").all():
            existing[al.tipo_licencia_id] = al.horas_lectivas
    return [
        {
            "id": tl.pk,
            "codigo": tl.codigo,
            "nombre": tl.nombre,
            "checked": tl.pk in existing,
            "horas": existing.get(tl.pk, 40),
        }
        for tl in tipos_licencia_qs
    ]


def _solapamiento_interno(bloques_data):
    """Detect overlapping blocks within the same proposed list.

    Each element must be a dict with keys ``dia`` (str), ``inicio`` (time), ``fin`` (time).
    Returns a list of human-readable error strings; empty when no overlaps exist.
    """
    errores = []
    dia_choices = dict(BloqueHorario.DiaSemana.choices)
    for i in range(len(bloques_data)):
        for j in range(i + 1, len(bloques_data)):
            a, b = bloques_data[i], bloques_data[j]
            if a["dia"] == b["dia"] and a["inicio"] < b["fin"] and b["inicio"] < a["fin"]:
                dia_label = dia_choices.get(a["dia"], a["dia"])
                errores.append(
                    f"Los bloques {i + 1} y {j + 1} se solapan el {dia_label}: "
                    f"{a['inicio']:%H:%M}–{a['fin']:%H:%M} y "
                    f"{b['inicio']:%H:%M}–{b['fin']:%H:%M}."
                )
    return errores


class AsignaturaDeleteView(MultiRolRequeridoMixin, View):
    """Delete an asignatura if it has no paralelos — Inspector/Secretaría."""

    roles_permitidos = ["inspector", "secretaria"]

    def post(self, request, pk):
        service = AsignaturaAppService()
        try:
            service.eliminar_asignatura(asignatura_id=pk, usuario_id=request.user.pk)
            messages.success(request, "Asignatura eliminada exitosamente.")
        except AcademicoError as e:
            messages.error(request, str(e))
        return redirect("academico:asignatura_list")


class AsignaturaListView(MultiRolRequeridoMixin, ListView):
    """List all subjects — Inspector only."""

    roles_permitidos = ["inspector", "secretaria"]
    model = Asignatura
    template_name = "academico/asignatura_list.html"
    context_object_name = "asignaturas"

    def get_queryset(self):
        return Asignatura.objects.prefetch_related(
            "asignatura_licencias", "asignatura_licencias__tipo_licencia"
        ).all()


class AsignaturaCreateView(MultiRolRequeridoMixin, ListView):
    """Create a new subject — Inspector only."""

    roles_permitidos = ["inspector", "secretaria"]
    template_name = "academico/asignatura_form.html"
    model = Asignatura

    def _get_tipos_qs(self):
        return TipoLicencia.objects.filter(activo=True)

    def get(self, request):
        form = AsignaturaForm()
        tipos_licencia_data = _build_tipos_licencia_data(self._get_tipos_qs())
        return render(
            request,
            self.template_name,
            {"form": form, "editing": False, "tipos_licencia_data": tipos_licencia_data},
        )

    def post(self, request):
        form = AsignaturaForm(request.POST)
        tipos_qs = self._get_tipos_qs()
        licencias = _parse_licencias_from_post(request.POST, tipos_qs)
        tipos_licencia_data = _build_tipos_licencia_data(tipos_qs)

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {"form": form, "editing": False, "tipos_licencia_data": tipos_licencia_data},
            )

        # V2: Validate horas_lectivas bounds per licencia
        service_domain = AsignaturaService()
        for entrada in licencias:
            try:
                service_domain.validar_horas_lectivas(
                    horas=entrada["horas_lectivas"],
                    maximo=settings.HORAS_LECTIVAS_MAX,
                    minimo=settings.HORAS_LECTIVAS_MIN,
                )
            except AcademicoError as e:
                messages.error(request, str(e))
                return render(
                    request,
                    self.template_name,
                    {"form": form, "editing": False, "tipos_licencia_data": tipos_licencia_data},
                )

        service = AsignaturaAppService()
        try:
            service.crear(
                nombre=form.cleaned_data["nombre"],
                codigo=form.cleaned_data["codigo"],
                licencias=licencias,
                usuario_id=request.user.pk,
                descripcion=form.cleaned_data.get("descripcion", ""),
            )
        except (AcademicoError, ValueError) as e:
            form.add_error(None, str(e))
            return render(
                request,
                self.template_name,
                {"form": form, "editing": False, "tipos_licencia_data": tipos_licencia_data},
            )

        messages.success(request, "Asignatura creada exitosamente.")
        return redirect("academico:asignatura_list")


class AsignaturaUpdateView(MultiRolRequeridoMixin, ListView):
    """Update a subject — Inspector only."""

    roles_permitidos = ["inspector", "secretaria"]
    template_name = "academico/asignatura_form.html"
    model = Asignatura

    def _get_tipos_qs(self):
        return TipoLicencia.objects.filter(activo=True)

    def get(self, request, pk):
        asignatura = get_object_or_404(Asignatura, pk=pk)
        form = AsignaturaForm(instance=asignatura)
        tipos_licencia_data = _build_tipos_licencia_data(self._get_tipos_qs(), asignatura)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "editing": True,
                "asignatura": asignatura,
                "tipos_licencia_data": tipos_licencia_data,
            },
        )

    def post(self, request, pk):
        asignatura = get_object_or_404(Asignatura, pk=pk)
        form = AsignaturaForm(request.POST, instance=asignatura)
        tipos_qs = self._get_tipos_qs()
        licencias = _parse_licencias_from_post(request.POST, tipos_qs)
        tipos_licencia_data = _build_tipos_licencia_data(tipos_qs, asignatura)

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "editing": True,
                    "asignatura": asignatura,
                    "tipos_licencia_data": tipos_licencia_data,
                },
            )

        # V2: Validate horas_lectivas bounds per licencia
        service_domain = AsignaturaService()
        for entrada in licencias:
            try:
                service_domain.validar_horas_lectivas(
                    horas=entrada["horas_lectivas"],
                    maximo=settings.HORAS_LECTIVAS_MAX,
                    minimo=settings.HORAS_LECTIVAS_MIN,
                )
            except AcademicoError as e:
                messages.error(request, str(e))
                return render(
                    request,
                    self.template_name,
                    {
                        "form": form,
                        "editing": True,
                        "asignatura": asignatura,
                        "tipos_licencia_data": tipos_licencia_data,
                    },
                )

        service = AsignaturaAppService()
        try:
            service.actualizar(
                asignatura_id=pk,
                nombre=form.cleaned_data["nombre"],
                codigo=form.cleaned_data["codigo"],
                licencias=licencias,
                usuario_id=request.user.pk,
                descripcion=form.cleaned_data.get("descripcion", ""),
            )
        except (AcademicoError, ValueError) as e:
            form.add_error(None, str(e))
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "editing": True,
                    "asignatura": asignatura,
                    "tipos_licencia_data": tipos_licencia_data,
                },
            )

        messages.success(request, "Asignatura actualizada exitosamente.")
        return redirect("academico:asignatura_list")


# =============================================================================
# Paralelo Views
# =============================================================================


class ParaleloListView(MultiRolRequeridoMixin, ListView):
    """List all parallels grouped by identity — Inspector only."""

    roles_permitidos = ["inspector", "secretaria"]
    model = Paralelo
    template_name = "academico/paralelo_list.html"
    context_object_name = "paralelos"

    def get_queryset(self):
        return (
            Paralelo.objects.select_related("asignatura", "periodo", "docente", "tipo_licencia")
            .prefetch_related("bloques_horario")
            .order_by(
                "periodo__nombre",
                "tipo_licencia__codigo",
                "nombre",
                "asignatura__codigo",
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paralelos = context["paralelos"]

        groups = OrderedDict()
        for p in paralelos:
            key = (p.periodo_id, p.tipo_licencia_id, p.nombre)
            if key not in groups:
                groups[key] = {
                    "nombre": p.nombre,
                    "periodo": p.periodo,
                    "tipo_licencia": p.tipo_licencia,
                    "capacidad_maxima": p.capacidad_maxima,
                    "asignaturas": [],
                }
            groups[key]["asignaturas"].append(p)

        context["paralelo_groups"] = list(groups.values())
        return context


class ParaleloCreateView(MultiRolRequeridoMixin, ListView):
    """Create a new parallel — Inspector only."""

    roles_permitidos = ["inspector", "secretaria"]
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

        # Parse bloques first so we can run the docente-conflict check BEFORE
        # creating the Paralelo row (locked decision 3 — design §9 + tasks 2.3).
        bloques_count_str = request.POST.get("bloques_count", "0")
        try:
            bloques_count = int(bloques_count_str)
        except ValueError:
            bloques_count = 0

        bloques_propuestos: list[tuple[str, time, time]] = []
        for idx in range(bloques_count):
            dia = request.POST.get(f"bloque_dia_{idx}", "").strip()
            inicio_str = request.POST.get(f"bloque_inicio_{idx}", "").strip()
            fin_str = request.POST.get(f"bloque_fin_{idx}", "").strip()
            if dia and inicio_str and fin_str:
                try:
                    h_inicio = time.fromisoformat(inicio_str)
                    h_fin = time.fromisoformat(fin_str)
                    duracion = datetime.combine(datetime.today(), h_fin) - datetime.combine(
                        datetime.today(), h_inicio
                    )
                    if h_inicio < h_fin and duracion >= timedelta(hours=1):
                        bloques_propuestos.append((dia, h_inicio, h_fin))
                except ValueError:
                    pass

        if bloques_propuestos:
            bloques_dict = [{"dia": d, "inicio": i, "fin": f} for d, i, f in bloques_propuestos]
            solapamientos = _solapamiento_interno(bloques_dict)
            if solapamientos:
                for e in solapamientos:
                    form.add_error(None, e)
                return render(request, self.template_name, {"form": form, "editing": False})

            conflictos = HorarioConflictoService.detectar_conflicto_docente(
                docente_id=docente.pk,
                periodo_id=periodo.pk,
                bloques_propuestos=bloques_propuestos,
            )
            if conflictos:
                exc = ConflictoHorarioDocenteError(conflictos)
                form.add_error(None, to_django(exc))
                return render(
                    request,
                    self.template_name,
                    {
                        "form": form,
                        "editing": False,
                        "conflictos_horario": conflictos,
                    },
                )

        # Same-group conflict check (before creating the paralelo row)
        if bloques_propuestos:
            same_group_paralelos = Paralelo.objects.filter(
                periodo_id=periodo.pk,
                tipo_licencia_id=form.cleaned_data["tipo_licencia"].pk,
                nombre=form.cleaned_data["nombre"],
            ).exclude(asignatura_id=asignatura.pk)
            errores_grupo = []
            for dia, h_inicio, h_fin in bloques_propuestos:
                conflicting_blocks = BloqueHorario.objects.filter(
                    paralelo__in=same_group_paralelos,
                    dia_semana=dia,
                    hora_inicio__lt=h_fin,
                    hora_fin__gt=h_inicio,
                ).select_related("paralelo__asignatura")
                for cb in conflicting_blocks:
                    dia_display = dict(BloqueHorario.DiaSemana.choices).get(dia, dia)
                    errores_grupo.append(
                        f"Conflicto de horario: {cb.paralelo.asignatura.nombre} "
                        f"ya tiene clase el {dia_display} de "
                        f"{cb.hora_inicio:%H:%M} a {cb.hora_fin:%H:%M}"
                    )
            if errores_grupo:
                for e in errores_grupo:
                    form.add_error(None, e)
                return render(
                    request,
                    self.template_name,
                    {"form": form, "editing": False, "errores_horario": errores_grupo},
                )

        try:
            service.crear(
                asignatura_codigo=asignatura.codigo,
                periodo_nombre=periodo.nombre,
                docente_username=docente.username,
                docente_rol=docente.rol,
                tipo_licencia_id=form.cleaned_data["tipo_licencia"].pk,
                nombre=form.cleaned_data["nombre"],
                capacidad_maxima=form.cleaned_data["capacidad_maxima"],
                periodo_id=periodo.pk,
                periodo_activo=periodo.activo,
                asignatura_id=asignatura.pk,
                usuario_id=request.user.pk,
            )
        except (AcademicoError, ValueError) as e:
            form.add_error(None, str(e))
            return render(request, self.template_name, {"form": form, "editing": False})

        created_paralelo = (
            Paralelo.objects.filter(
                asignatura=asignatura,
                periodo=periodo,
                tipo_licencia=form.cleaned_data["tipo_licencia"],
                nombre=form.cleaned_data["nombre"],
            )
            .order_by("-pk")
            .first()
        )

        if created_paralelo and bloques_propuestos:
            for dia, h_inicio, h_fin in bloques_propuestos:
                BloqueHorario.objects.create(
                    paralelo=created_paralelo,
                    dia_semana=dia,
                    hora_inicio=h_inicio,
                    hora_fin=h_fin,
                )

        messages.success(request, "Paralelo creado exitosamente.")
        return redirect("academico:paralelo_list")


class ParaleloDeleteView(MultiRolRequeridoMixin, View):
    """Delete a paralelo if it has no dependents — Inspector/Secretaría."""

    roles_permitidos = ["inspector", "secretaria"]

    def post(self, request, pk):
        service = ParaleloAppService()
        try:
            service.eliminar_paralelo(paralelo_id=pk, usuario_id=request.user.pk)
            messages.success(request, "Paralelo eliminado exitosamente.")
        except AcademicoError as e:
            messages.error(request, str(e))
        return redirect("academico:paralelo_list")


class ParaleloCreateLoteView(MultiRolRequeridoMixin, View):
    """Batch-create paralelos: one per selected asignatura — Inspector only."""

    roles_permitidos = ["inspector", "secretaria"]
    template_name = "academico/paralelo_form_lote.html"

    def get(self, request):
        form = ParaleloLoteForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = ParaleloLoteForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        service = ParaleloAppService()
        try:
            creados, duplicados = service.crear_lote(
                asignaturas=form.cleaned_data["asignaturas"],
                periodo=form.cleaned_data["periodo"],
                tipo_licencia=form.cleaned_data["tipo_licencia"],
                docente=form.cleaned_data["docente"],
                nombre=form.cleaned_data["nombre"],
                capacidad_maxima=form.cleaned_data["capacidad_maxima"],
                usuario_id=request.user.pk,
            )
        except (AcademicoError, ValueError) as e:
            form.add_error(None, str(e))
            return render(request, self.template_name, {"form": form})

        if creados:
            # Parse and create schedule blocks for each created paralelo
            horario_warnings = []
            periodo = form.cleaned_data["periodo"]
            tipo_licencia = form.cleaned_data["tipo_licencia"]
            nombre = form.cleaned_data["nombre"]
            asignaturas = form.cleaned_data["asignaturas"]

            # Map asignatura_codigo -> asignatura model for ID lookup
            asig_by_codigo = {a.codigo: a for a in asignaturas}

            for entity in creados:
                asig = asig_by_codigo.get(entity.asignatura_codigo)
                if not asig:
                    continue
                asig_id = asig.pk

                count_str = request.POST.get(f"horario_{asig_id}_count", "0")
                try:
                    count = int(count_str)
                except ValueError:
                    count = 0

                if count == 0:
                    continue

                # Find the actual Django model instance
                paralelo = (
                    Paralelo.objects.filter(
                        asignatura_id=asig_id,
                        periodo=periodo,
                        tipo_licencia=tipo_licencia,
                        nombre=nombre,
                    )
                    .order_by("-pk")
                    .first()
                )

                if not paralelo:
                    continue

                bloques_data = []
                for idx in range(count):
                    dia = request.POST.get(f"horario_{asig_id}_dia_{idx}", "").strip()
                    inicio_str = request.POST.get(f"horario_{asig_id}_inicio_{idx}", "").strip()
                    fin_str = request.POST.get(f"horario_{asig_id}_fin_{idx}", "").strip()
                    if dia and inicio_str and fin_str:
                        try:
                            h_inicio = time.fromisoformat(inicio_str)
                            h_fin = time.fromisoformat(fin_str)
                            duracion = datetime.combine(
                                datetime.today(), h_fin
                            ) - datetime.combine(datetime.today(), h_inicio)
                            if h_inicio >= h_fin or duracion < timedelta(hours=1):
                                dia_display = dict(BloqueHorario.DiaSemana.choices).get(dia, dia)
                                horario_warnings.append(
                                    f"{asig.nombre}: hora de inicio "
                                    f"({h_inicio:%H:%M}) debe ser anterior a la "
                                    f"hora de fin ({h_fin:%H:%M}) el {dia_display} "
                                    f"y el bloque debe durar al menos 1 hora."
                                )
                                continue
                            bloques_data.append({"dia": dia, "inicio": h_inicio, "fin": h_fin})
                        except ValueError:
                            pass

                # Intra-paralelo overlap check
                solapamientos = _solapamiento_interno(bloques_data)
                if solapamientos:
                    for e in solapamientos:
                        horario_warnings.append(f"{asig.nombre}: {e}")
                    continue

                # V5: docente conflict check across all paralelos of the
                # period (collect-all per asignatura; skip bloques on conflict
                # but DO NOT abort the lote — design §4 row 2 + task 2.6).
                docente = form.cleaned_data["docente"]
                if bloques_data and docente:
                    bloques_propuestos = [(b["dia"], b["inicio"], b["fin"]) for b in bloques_data]
                    docente_conflictos = HorarioConflictoService.detectar_conflicto_docente(
                        docente_id=docente.pk,
                        periodo_id=paralelo.periodo_id,
                        bloques_propuestos=bloques_propuestos,
                        paralelo_id_excluir=paralelo.pk,
                    )
                    if docente_conflictos:
                        first = docente_conflictos[0]
                        horario_warnings.append(
                            f"{asig.nombre}: conflicto de docente con "
                            f"{first.asignatura_nombre} ({first.paralelo_nombre}) "
                            f"el {first.dia_semana_label} de "
                            f"{first.hora_inicio:%H:%M} a {first.hora_fin:%H:%M}."
                        )
                        continue

                # Conflict validation against same group
                same_group = Paralelo.objects.filter(
                    periodo_id=paralelo.periodo_id,
                    tipo_licencia_id=paralelo.tipo_licencia_id,
                    nombre=paralelo.nombre,
                ).exclude(pk=paralelo.pk)

                for b in bloques_data:
                    conflicts = BloqueHorario.objects.filter(
                        paralelo__in=same_group,
                        dia_semana=b["dia"],
                        hora_inicio__lt=b["fin"],
                        hora_fin__gt=b["inicio"],
                    ).select_related("paralelo__asignatura")
                    if conflicts.exists():
                        cb = conflicts.first()
                        dia_display = dict(BloqueHorario.DiaSemana.choices).get(b["dia"], b["dia"])
                        horario_warnings.append(
                            f"{asig.nombre}: conflicto con "
                            f"{cb.paralelo.asignatura.nombre} el {dia_display} "
                            f"de {cb.hora_inicio:%H:%M} a {cb.hora_fin:%H:%M}."
                        )
                    else:
                        BloqueHorario.objects.create(
                            paralelo=paralelo,
                            dia_semana=b["dia"],
                            hora_inicio=b["inicio"],
                            hora_fin=b["fin"],
                        )

            messages.success(
                request,
                f"Se crearon {len(creados)} paralelos exitosamente.",
            )
            for w in horario_warnings:
                messages.warning(request, f"Horario omitido — {w}")
        if duplicados:
            messages.warning(
                request,
                f"Se omitieron {len(duplicados)} paralelos duplicados: {', '.join(duplicados)}.",
            )
        if not creados and not duplicados:
            messages.info(request, "No se crearon paralelos.")

        return redirect("academico:paralelo_list")


class AsignaturasPorTipoLicenciaView(MultiRolRequeridoMixin, View):
    """JSON endpoint: returns asignaturas filtered by tipo_licencia ID."""

    roles_permitidos = ["inspector", "secretaria"]

    def get(self, request):
        tipo_id = request.GET.get("tipo_licencia")
        if not tipo_id:
            return JsonResponse({"asignaturas": []})
        asignaturas = (
            Asignatura.objects.filter(asignatura_licencias__tipo_licencia_id=tipo_id)
            .distinct()
            .values("id", "codigo", "nombre")
        )
        return JsonResponse({"asignaturas": list(asignaturas)})


class ParaleloUpdateView(MultiRolRequeridoMixin, View):
    """Edit docente and schedule blocks for a paralelo — Inspector only."""

    roles_permitidos = ["inspector", "secretaria"]
    template_name = "academico/paralelo_asignatura_edit.html"

    def _get_paralelo(self, pk):
        return get_object_or_404(
            Paralelo.objects.select_related(
                "asignatura",
                "periodo",
                "tipo_licencia",
                "docente",
            ),
            pk=pk,
        )

    def get(self, request, pk):
        paralelo = self._get_paralelo(pk)
        form = ParaleloAsignaturaEditForm(instance=paralelo)
        bloques = paralelo.bloques_horario.all()
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "paralelo": paralelo,
                "bloques": bloques,
            },
        )

    def post(self, request, pk):
        paralelo = self._get_paralelo(pk)
        form = ParaleloAsignaturaEditForm(request.POST, instance=paralelo)
        if not form.is_valid():
            bloques = paralelo.bloques_horario.all()
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "paralelo": paralelo,
                    "bloques": bloques,
                },
            )

        # Parse schedule blocks from POST
        bloques_data = []
        idx = 0
        while f"bloque_dia_{idx}" in request.POST:
            dia = request.POST.get(f"bloque_dia_{idx}", "").strip()
            inicio_str = request.POST.get(f"bloque_inicio_{idx}", "").strip()
            fin_str = request.POST.get(f"bloque_fin_{idx}", "").strip()
            if dia and inicio_str and fin_str:
                try:
                    h_inicio = time.fromisoformat(inicio_str)
                    h_fin = time.fromisoformat(fin_str)
                    bloques_data.append({"dia": dia, "inicio": h_inicio, "fin": h_fin})
                except ValueError:
                    pass
            idx += 1

        # Validate blocks
        errores = []
        for b in bloques_data:
            duracion = datetime.combine(datetime.today(), b["fin"]) - datetime.combine(
                datetime.today(), b["inicio"]
            )
            if b["inicio"] >= b["fin"] or duracion < timedelta(hours=1):
                dia_display = dict(BloqueHorario.DiaSemana.choices).get(b["dia"], b["dia"])
                errores.append(
                    f"Horario inválido: la hora de inicio ({b['inicio']:%H:%M}) "
                    f"debe ser anterior a la hora de fin ({b['fin']:%H:%M}) "
                    f"el {dia_display} y el bloque debe durar al menos 1 hora."
                )

        # Intra-paralelo overlap check
        errores.extend(_solapamiento_interno(bloques_data))

        # Conflict validation: check other paralelos in the same group
        if not errores:
            same_group_paralelos = Paralelo.objects.filter(
                periodo_id=paralelo.periodo_id,
                tipo_licencia_id=paralelo.tipo_licencia_id,
                nombre=paralelo.nombre,
            ).exclude(asignatura_id=paralelo.asignatura_id)

            for b in bloques_data:
                conflicting_blocks = BloqueHorario.objects.filter(
                    paralelo__in=same_group_paralelos,
                    dia_semana=b["dia"],
                    hora_inicio__lt=b["fin"],
                    hora_fin__gt=b["inicio"],
                ).select_related("paralelo__asignatura")

                for cb in conflicting_blocks:
                    dia_display = dict(BloqueHorario.DiaSemana.choices).get(b["dia"], b["dia"])
                    errores.append(
                        f"Conflicto de horario: {cb.paralelo.asignatura.nombre} "
                        f"ya tiene clase el {dia_display} de "
                        f"{cb.hora_inicio:%H:%M} a {cb.hora_fin:%H:%M}"
                    )

        if errores:
            for e in errores:
                messages.error(request, e)
            bloques = paralelo.bloques_horario.all()
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "paralelo": paralelo,
                    "bloques": bloques,
                    "errores_horario": errores,
                },
            )

        # V5: docente cross-paralelo conflict check (decision 4 — context var).
        # Uses incoming docente.pk from the form (may differ from paralelo.docente_id
        # if the inspector is reassigning), and self-excludes the current paralelo.
        new_docente = form.cleaned_data.get("docente") or paralelo.docente
        bloques_propuestos = [(b["dia"], b["inicio"], b["fin"]) for b in bloques_data]
        if bloques_propuestos and new_docente:
            conflictos = HorarioConflictoService.detectar_conflicto_docente(
                docente_id=new_docente.pk,
                periodo_id=paralelo.periodo_id,
                bloques_propuestos=bloques_propuestos,
                paralelo_id_excluir=paralelo.pk,
            )
            if conflictos:
                exc = ConflictoHorarioDocenteError(conflictos)
                form.add_error(None, to_django(exc))
                bloques = paralelo.bloques_horario.all()
                return render(
                    request,
                    self.template_name,
                    {
                        "form": form,
                        "paralelo": paralelo,
                        "bloques": bloques,
                        "conflictos_horario": conflictos,
                    },
                )

        # Save docente
        form.save()

        # Replace schedule blocks
        paralelo.bloques_horario.all().delete()
        for b in bloques_data:
            BloqueHorario.objects.create(
                paralelo=paralelo,
                dia_semana=b["dia"],
                hora_inicio=b["inicio"],
                hora_fin=b["fin"],
            )

        messages.success(request, "Docente y horario actualizados exitosamente.")
        return redirect("academico:paralelo_list")


class ParaleloHorarioUpdateView(View):
    """AJAX endpoint to update schedule blocks for a paralelo."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"ok": False, "errors": ["No autenticado."]}, status=401)
        rol = getattr(request.user, "rol", None)
        if rol not in ("inspector", "secretaria"):
            return JsonResponse(
                {"ok": False, "errors": ["No tiene permisos para esta acción."]},
                status=403,
            )
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk):
        import json

        paralelo = get_object_or_404(
            Paralelo.objects.select_related("asignatura", "periodo", "tipo_licencia"),
            pk=pk,
        )

        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"ok": False, "errors": ["JSON inválido."]}, status=400)

        raw_bloques = body.get("bloques", [])
        if not isinstance(raw_bloques, list):
            return JsonResponse(
                {"ok": False, "errors": ["'bloques' debe ser una lista."]}, status=400
            )

        dias_validos = {c[0] for c in BloqueHorario.DiaSemana.choices}
        bloques_data = []
        errores = []

        for i, b in enumerate(raw_bloques):
            dia = b.get("dia", "")
            inicio_str = b.get("inicio", "")
            fin_str = b.get("fin", "")

            if dia not in dias_validos:
                errores.append(f"Bloque {i + 1}: día inválido '{dia}'.")
                continue

            try:
                inicio = time(*map(int, inicio_str.split(":")))
                fin = time(*map(int, fin_str.split(":")))
            except (ValueError, TypeError):
                errores.append(f"Bloque {i + 1}: formato de hora inválido.")
                continue

            if inicio >= fin:
                dia_display = dict(BloqueHorario.DiaSemana.choices).get(dia, dia)
                errores.append(
                    f"Bloque {i + 1}: la hora de inicio ({inicio:%H:%M}) "
                    f"debe ser anterior a la hora de fin ({fin:%H:%M}) "
                    f"el {dia_display}."
                )
                continue

            if (
                datetime.combine(datetime.today(), fin)
                - datetime.combine(datetime.today(), inicio)
            ) < timedelta(hours=1):
                errores.append(
                    f"Bloque {i + 1}: el horario debe durar al menos 1 hora "
                    f"({inicio:%H:%M} – {fin:%H:%M})."
                )
                continue

            bloques_data.append({"dia": dia, "inicio": inicio, "fin": fin})

        errores.extend(_solapamiento_interno(bloques_data))

        if errores:
            return JsonResponse({"ok": False, "errors": errores}, status=400)

        # V5: docente cross-paralelo conflict (JSON contract, design §5.3).
        bloques_propuestos = [(b["dia"], b["inicio"], b["fin"]) for b in bloques_data]
        if bloques_propuestos and paralelo.docente_id:
            docente_conflictos = HorarioConflictoService.detectar_conflicto_docente(
                docente_id=paralelo.docente_id,
                periodo_id=paralelo.periodo_id,
                bloques_propuestos=bloques_propuestos,
                paralelo_id_excluir=paralelo.pk,
            )
            if docente_conflictos:
                exc = ConflictoHorarioDocenteError(docente_conflictos)
                return JsonResponse(
                    {
                        "ok": False,
                        "errors": [str(exc)],
                        "conflictos": _serialize_conflictos(exc) or [],
                    },
                    status=400,
                )

        # Conflict validation against same group
        same_group_paralelos = Paralelo.objects.filter(
            periodo_id=paralelo.periodo_id,
            tipo_licencia_id=paralelo.tipo_licencia_id,
            nombre=paralelo.nombre,
        ).exclude(asignatura_id=paralelo.asignatura_id)

        for b in bloques_data:
            conflicting_blocks = BloqueHorario.objects.filter(
                paralelo__in=same_group_paralelos,
                dia_semana=b["dia"],
                hora_inicio__lt=b["fin"],
                hora_fin__gt=b["inicio"],
            ).select_related("paralelo__asignatura")

            for cb in conflicting_blocks:
                dia_display = dict(BloqueHorario.DiaSemana.choices).get(b["dia"], b["dia"])
                errores.append(
                    f"Conflicto: {cb.paralelo.asignatura.nombre} "
                    f"ya tiene clase el {dia_display} de "
                    f"{cb.hora_inicio:%H:%M} a {cb.hora_fin:%H:%M}"
                )

        if errores:
            return JsonResponse({"ok": False, "errors": errores}, status=400)

        # Replace blocks atomically
        paralelo.bloques_horario.all().delete()
        for b in bloques_data:
            BloqueHorario.objects.create(
                paralelo=paralelo,
                dia_semana=b["dia"],
                hora_inicio=b["inicio"],
                hora_fin=b["fin"],
            )

        # Build display string
        dia_abrev = {
            "lunes": "Lun",
            "martes": "Mar",
            "miercoles": "Mié",
            "jueves": "Jue",
            "viernes": "Vie",
            "sabado": "Sáb",
        }
        display_parts = []
        for b in bloques_data:
            display_parts.append(
                f"{dia_abrev.get(b['dia'], b['dia'])} " f"{b['inicio']:%H:%M}-{b['fin']:%H:%M}"
            )
        bloques_display = " · ".join(display_parts)

        return JsonResponse(
            {
                "ok": True,
                "message": "Horario actualizado exitosamente.",
                "bloques_display": bloques_display,
            }
        )


# =============================================================================
# TipoLicencia Views (read-only)
# =============================================================================


class TipoLicenciaListView(MultiRolRequeridoMixin, ListView):
    """List all license types — Inspector only, read-only."""

    roles_permitidos = ["inspector", "secretaria"]
    model = TipoLicencia
    template_name = "academico/tipo_licencia_list.html"
    context_object_name = "tipos_licencia"

    def get_queryset(self):
        return TipoLicencia.objects.all()


# =============================================================================
# Paralelo Grupo Edit View
# =============================================================================


class ParaleloGrupoEditView(MultiRolRequeridoMixin, View):
    """Edit a paralelo group: manage asignaturas and capacidad_maxima — Inspector only."""

    roles_permitidos = ["inspector", "secretaria"]
    template_name = "academico/paralelo_grupo_edit.html"

    def _get_group_context(self, periodo_id, tipo_licencia_id, nombre):
        """Build common context for GET and POST."""
        periodo = get_object_or_404(Periodo, pk=periodo_id)
        tipo_licencia = get_object_or_404(TipoLicencia, pk=tipo_licencia_id)

        # All Paralelo rows in this group
        group_rows = Paralelo.objects.filter(
            periodo_id=periodo_id,
            tipo_licencia_id=tipo_licencia_id,
            nombre=nombre,
        ).select_related("asignatura", "docente")

        # All asignaturas for this tipo_licencia
        all_asignaturas = (
            Asignatura.objects.filter(asignatura_licencias__tipo_licencia=tipo_licencia)
            .distinct()
            .order_by("codigo")
        )

        # IDs already in the group
        existing_asignatura_ids = set(group_rows.values_list("asignatura_id", flat=True))

        # Current capacidad from any row (they share the value)
        capacidad_maxima = group_rows.first().capacidad_maxima if group_rows.exists() else 30

        # Docentes for the default docente select
        docentes = Usuario.objects.filter(rol="docente", is_active=True).order_by(
            "last_name", "first_name"
        )

        return {
            "periodo": periodo,
            "tipo_licencia": tipo_licencia,
            "nombre": nombre,
            "group_rows": group_rows,
            "all_asignaturas": all_asignaturas,
            "existing_asignatura_ids": existing_asignatura_ids,
            "capacidad_maxima": capacidad_maxima,
            "docentes": docentes,
        }

    def get(self, request, periodo_id, tipo_licencia_id, nombre):
        ctx = self._get_group_context(periodo_id, tipo_licencia_id, nombre)
        return render(request, self.template_name, ctx)

    def post(self, request, periodo_id, tipo_licencia_id, nombre):
        ctx = self._get_group_context(periodo_id, tipo_licencia_id, nombre)

        selected_ids = set(int(x) for x in request.POST.getlist("asignaturas") if x.isdigit())
        new_capacidad = request.POST.get("capacidad_maxima", "30")
        default_docente_id = request.POST.get("docente_default", "")

        # Validate capacidad
        try:
            new_capacidad = int(new_capacidad)
            if new_capacidad < 1:
                raise ValueError
        except (ValueError, TypeError):
            new_capacidad = 30

        existing_ids = ctx["existing_asignatura_ids"]
        errors = []

        # --- Remove deselected asignaturas ---
        to_remove = existing_ids - selected_ids
        for asig_id in to_remove:
            row = ctx["group_rows"].filter(asignatura_id=asig_id).first()
            if row:
                active_matriculas = Matricula.objects.filter(
                    paralelo=row, estado=Matricula.Estado.ACTIVA
                ).exists()
                if active_matriculas:
                    asig = row.asignatura
                    errors.append(
                        f"No se puede quitar {asig.nombre} ({asig.codigo}) "
                        f"porque tiene matrículas activas."
                    )
                else:
                    row.delete()

        if errors:
            # Re-fetch context after partial deletes
            ctx = self._get_group_context(periodo_id, tipo_licencia_id, nombre)
            ctx["errors"] = errors
            ctx["selected_ids"] = selected_ids
            ctx["capacidad_maxima"] = new_capacidad
            return render(request, self.template_name, ctx)

        # --- Add newly selected asignaturas ---
        to_add = selected_ids - existing_ids
        if to_add:
            if not default_docente_id:
                ctx = self._get_group_context(periodo_id, tipo_licencia_id, nombre)
                ctx["errors"] = ["Debe seleccionar un docente para las nuevas asignaturas."]
                ctx["selected_ids"] = selected_ids
                ctx["capacidad_maxima"] = new_capacidad
                return render(request, self.template_name, ctx)

            docente = get_object_or_404(Usuario, pk=default_docente_id, rol="docente")
            for asig_id in to_add:
                Paralelo.objects.create(
                    asignatura_id=asig_id,
                    periodo_id=periodo_id,
                    tipo_licencia_id=tipo_licencia_id,
                    docente=docente,
                    nombre=nombre,
                    capacidad_maxima=new_capacidad,
                )

        # --- Update capacidad_maxima on all rows ---
        Paralelo.objects.filter(
            periodo_id=periodo_id,
            tipo_licencia_id=tipo_licencia_id,
            nombre=nombre,
        ).update(capacidad_maxima=new_capacidad)

        messages.success(request, f"Paralelo {nombre} actualizado exitosamente.")
        return redirect("academico:paralelo_list")


# ─────────────────────────────────────────────────────────────────────────────
# Horarios (vista provisional, solo lectura) — HU futuro
# ─────────────────────────────────────────────────────────────────────────────


def _construir_grilla_horario(bloques):
    """Build a weekly schedule grid from a list of BloqueHorario.

    Returns a dict with:
      - dias: list of (key, label) tuples in canonical order
      - rows: list of {"hora": "HH:00", "celdas": [list_per_day]} where each
              cell is a list of bloque dicts (asignatura, paralelo, docente, etc.)
      - vacio: True if there are no blocks
    """
    dias = [
        (BloqueHorario.DiaSemana.LUNES, "Lunes"),
        (BloqueHorario.DiaSemana.MARTES, "Martes"),
        (BloqueHorario.DiaSemana.MIERCOLES, "Miércoles"),
        (BloqueHorario.DiaSemana.JUEVES, "Jueves"),
        (BloqueHorario.DiaSemana.VIERNES, "Viernes"),
        (BloqueHorario.DiaSemana.SABADO, "Sábado"),
    ]
    dia_keys = [d[0] for d in dias]

    # Index: dict[(dia_key, hora_int)] -> list[bloque_dict]
    index: dict = {}
    horas_set: set = set()

    for b in bloques:
        hora_ini = b.hora_inicio.hour
        # Only place the block in its START hour cell; duration shown in the card.
        horas_set.add(hora_ini)
        bloque_data = {
            "asignatura": b.paralelo.asignatura.nombre,
            "codigo": b.paralelo.asignatura.codigo,
            "paralelo": b.paralelo.nombre,
            "docente": b.paralelo.docente.get_full_name() if b.paralelo.docente else "—",
            "hora_inicio": b.hora_inicio,
            "hora_fin": b.hora_fin,
        }
        index.setdefault((b.dia_semana, hora_ini), []).append(bloque_data)

    horas = sorted(horas_set) if horas_set else list(range(8, 18))

    rows = []
    for h in horas:
        celdas = [index.get((dk, h), []) for dk in dia_keys]
        rows.append({"hora": f"{h:02d}:00", "celdas": celdas})

    return {"dias": dias, "rows": rows, "vacio": not bloques}


class HorarioDocenteView(RolRequeridoMixin, View):
    """Read-only weekly schedule for the logged-in docente (active period only)."""

    rol_requerido = "docente"
    template_name = "academico/horarios/mi_horario.html"

    def get(self, request):
        bloques = (
            BloqueHorario.objects.filter(
                paralelo__docente=request.user,
                paralelo__periodo__activo=True,
            )
            .select_related(
                "paralelo__asignatura",
                "paralelo__periodo",
                "paralelo__docente",
            )
            .order_by("dia_semana", "hora_inicio")
        )

        contexto = _construir_grilla_horario(list(bloques))
        contexto["titulo"] = "Mi Horario de Clases"
        contexto["subtitulo"] = "Período académico vigente"
        return render(request, self.template_name, contexto)


class HorarioEstudianteView(RolRequeridoMixin, View):
    """Read-only weekly schedule for the logged-in estudiante (active matrículas only)."""

    rol_requerido = "estudiante"
    template_name = "academico/horarios/mi_horario.html"

    def get(self, request):
        bloques = (
            BloqueHorario.objects.filter(
                paralelo__matriculas__estudiante=request.user,
                paralelo__matriculas__estado=Matricula.Estado.ACTIVA,
                paralelo__periodo__activo=True,
            )
            .select_related(
                "paralelo__asignatura",
                "paralelo__periodo",
                "paralelo__docente",
            )
            .order_by("dia_semana", "hora_inicio")
            .distinct()
        )

        contexto = _construir_grilla_horario(list(bloques))
        contexto["titulo"] = "Mi Horario de Clases"
        contexto["subtitulo"] = "Período académico vigente"
        return render(request, self.template_name, contexto)
