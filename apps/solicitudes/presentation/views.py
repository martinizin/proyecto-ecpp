"""
Views for the Solicitudes bounded context.

Sprint 3 — HU18/HU19: Solicitudes y flujo de aprobación.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView

from apps.academico.infrastructure.models import Paralelo
from apps.asistencia.infrastructure.models import Asistencia
from apps.solicitudes.application.services import (
    InspectorResolucionAppService,
    JustificacionCertificadoAppService,
    SolicitudAppService,
)
from apps.solicitudes.domain.exceptions import (
    ArchivoInvalidoError,
    CamposObligatoriosFaltantesError,
    FechaCertificadoInvalidaError,
    MaximoArchivosExcedidoError,
)
from apps.solicitudes.domain.services import (
    clasificar_urgencia,
    dias_habiles_transcurridos,
)
from apps.solicitudes.domain.value_objects import TipoCertificado
from apps.solicitudes.infrastructure.models import (
    ConfiguracionJustificacion,
    Solicitud,
)
from apps.solicitudes.presentation.forms import JustificacionCertificadoForm
from apps.usuarios.presentation.permissions import (
    MultiRolRequeridoMixin,
    RolRequeridoMixin,
)


class CrearRecalificacionView(RolRequeridoMixin, View):
    """Form to create a grade rectification request. Only estudiante.

    UX: the template renders two cascading selects (asignatura → evaluación)
    backed by ``asignaturas_map`` (a dict grouped by asignatura, consumed via
    ``json_script`` in the template). The POST contract is unchanged — the
    template syncs the selected evaluación id into a hidden input
    ``name="calificacion"``.
    """

    rol_requerido = "estudiante"
    template_name = "solicitudes/crear_recalificacion.html"

    @staticmethod
    def _build_asignaturas_map(calificaciones) -> dict:
        """Group calificaciones by asignatura for cascading-select UI.

        Returns a dict keyed by asignatura id (as str — json_script-safe):
            {
                "<asignatura_id>": {
                    "nombre": "Primeros Auxilios",
                    "codigo": "PA101",
                    "evaluaciones": [
                        {"id": 42, "tipo_label": "Parcial 1", "nota": "17.00"},
                        ...
                    ],
                },
                ...
            }
        """
        mapa: dict = {}
        for cal in calificaciones:
            asignatura = cal.evaluacion.paralelo.asignatura
            key = str(asignatura.pk)
            entry = mapa.setdefault(
                key,
                {
                    "nombre": asignatura.nombre,
                    "codigo": asignatura.codigo,
                    "evaluaciones": [],
                },
            )
            entry["evaluaciones"].append(
                {
                    "id": cal.pk,
                    "tipo_label": cal.evaluacion.get_tipo_display(),
                    "nota": str(cal.nota),
                }
            )
        return mapa

    def _context(self, request, *, form_data=None):
        service = SolicitudAppService()
        calificaciones = service.obtener_calificaciones_reclamables(request.user)
        ctx = {
            "calificaciones": calificaciones,
            "asignaturas_map": self._build_asignaturas_map(calificaciones),
        }
        if form_data is not None:
            ctx["form_data"] = form_data
        return ctx

    def get(self, request):
        return render(request, self.template_name, self._context(request))

    def post(self, request):
        service = SolicitudAppService()
        calificacion_id = request.POST.get("calificacion")
        descripcion = request.POST.get("descripcion", "")
        archivo = request.FILES.get("archivo_adjunto")

        resultado = service.crear_recalificacion(
            estudiante=request.user,
            calificacion_id=calificacion_id,
            descripcion=descripcion,
            archivo=archivo,
        )

        if resultado["ok"]:
            messages.success(request, "Solicitud de recalificación enviada correctamente.")
            return redirect("solicitudes:mis_solicitudes")

        messages.error(request, resultado["error"])
        return render(
            request,
            self.template_name,
            self._context(
                request,
                form_data={"calificacion": calificacion_id, "descripcion": descripcion},
            ),
        )


class CrearJustificacionView(RolRequeridoMixin, View):
    """Form to create an absence justification request. Only estudiante.

    .. deprecated:: Sprint 4 (HU20)
        Superseded by :class:`SeleccionarInasistenciaView` +
        :class:`CrearJustificacionConCertificadoView`, which implement the
        categorized-certificate flow (médico / laboral / calamidad) with
        per-type required fields and multi-file uploads.

        This view remains routed at ``/justificacion/nueva/`` for backward
        compatibility but is no longer linked from the student UI
        (dashboard / sidebar / mis-solicitudes). Slated for removal once
        HU18 historical solicitudes are migrated or archived.
    """

    rol_requerido = "estudiante"
    template_name = "solicitudes/crear_justificacion.html"

    def get(self, request):
        service = SolicitudAppService()
        inasistencias = service.obtener_inasistencias_justificables(request.user)
        return render(request, self.template_name, {"inasistencias": inasistencias})

    def post(self, request):
        service = SolicitudAppService()
        asistencia_id = request.POST.get("asistencia")
        descripcion = request.POST.get("descripcion", "")
        archivo = request.FILES.get("archivo_adjunto")

        resultado = service.crear_justificacion(
            estudiante=request.user,
            asistencia_id=asistencia_id,
            descripcion=descripcion,
            archivo=archivo,
        )

        if resultado["ok"]:
            messages.success(request, "Solicitud de justificación enviada correctamente.")
            return redirect("solicitudes:mis_solicitudes")

        messages.error(request, resultado["error"])
        inasistencias = service.obtener_inasistencias_justificables(request.user)
        return render(
            request,
            self.template_name,
            {
                "inasistencias": inasistencias,
                "form_data": {
                    "asistencia": asistencia_id,
                    "descripcion": descripcion,
                },
            },
        )


class MisSolicitudesView(RolRequeridoMixin, View):
    """List of all requests made by the student. Only estudiante."""

    rol_requerido = "estudiante"
    template_name = "solicitudes/mis_solicitudes.html"

    def get(self, request):
        service = SolicitudAppService()
        tipo_filtro = request.GET.get("tipo", "")
        solicitudes = service.obtener_mis_solicitudes(request.user, tipo=tipo_filtro or None)
        return render(
            request,
            self.template_name,
            {
                "solicitudes": solicitudes,
                "tipo_filtro": tipo_filtro,
                "tipos": Solicitud.TipoSolicitud.choices,
            },
        )


# ── HU19: Vistas de gestión para docente / secretaría / inspector ─────


class PendientesDocenteView(RolRequeridoMixin, View):
    """Solicitudes de recalificación pendientes para el docente."""

    rol_requerido = "docente"
    template_name = "solicitudes/pendientes_docente.html"

    def get(self, request):
        service = SolicitudAppService()
        solicitudes = service.obtener_pendientes_docente(request.user)
        return render(request, self.template_name, {"solicitudes": solicitudes})


class PendientesSecretariaView(RolRequeridoMixin, View):
    """Solicitudes que requieren validación de secretaría.

    Includes: 2da+ recalificaciones + justificaciones.
    """

    rol_requerido = "secretaria"
    template_name = "solicitudes/pendientes_secretaria.html"

    def get(self, request):
        service = SolicitudAppService()
        recalificaciones = service.obtener_pendientes_secretaria()
        justificaciones = service.obtener_pendientes_justificacion()
        return render(
            request,
            self.template_name,
            {
                "recalificaciones": recalificaciones,
                "justificaciones": justificaciones,
            },
        )


class PendientesJustificacionView(RolRequeridoMixin, View):
    """Solicitudes de justificación pendientes para el inspector."""

    rol_requerido = "inspector"
    template_name = "solicitudes/pendientes_justificacion.html"

    def get(self, request):
        service = SolicitudAppService()
        solicitudes = service.obtener_pendientes_justificacion()
        return render(request, self.template_name, {"solicitudes": solicitudes})


class ResolverSolicitudView(MultiRolRequeridoMixin, View):
    """Detail + resolve (approve/reject) a solicitud.

    Accessible by docente, secretaría, and inspector.
    """

    roles_permitidos = ["docente", "secretaria", "inspector"]
    template_name = "solicitudes/resolver_solicitud.html"

    def get(self, request, pk):
        solicitud = get_object_or_404(
            Solicitud.objects.select_related(
                "estudiante",
                "calificacion__evaluacion__paralelo__asignatura",
                "calificacion__evaluacion__paralelo__docente",
                "asistencia__paralelo__asignatura",
                "resuelto_por",
            ),
            pk=pk,
        )
        historial = solicitud.historial.select_related("cambiado_por").all()
        return render(
            request,
            self.template_name,
            {"solicitud": solicitud, "historial": historial},
        )

    def post(self, request, pk):
        accion = request.POST.get("accion", "")
        comentario = request.POST.get("comentario", "")
        nueva_nota = request.POST.get("nueva_nota")
        service = SolicitudAppService()

        # Escalar a docente (secretaría validates 2da+)
        if accion == "escalar":
            resultado = service.escalar_a_docente(pk, request.user, comentario)
        # Aprobar / Rechazar
        else:
            resultado = service.resolver_solicitud(
                solicitud_id=pk,
                usuario=request.user,
                accion=accion,
                comentario=comentario,
                nueva_nota=nueva_nota,
            )

        if resultado["ok"]:
            msg = {
                "escalar": "Solicitud escalada al docente.",
                "aprobar": "Solicitud aprobada correctamente.",
                "rechazar": "Solicitud rechazada.",
            }
            messages.success(request, msg.get(accion, "Acción realizada."))
            # Redirect back based on role
            if request.user.rol == "secretaria":
                return redirect("solicitudes:pendientes_secretaria")
            elif request.user.rol == "inspector":
                return redirect("solicitudes:pendientes_justificacion")
            else:
                return redirect("solicitudes:pendientes_docente")

        messages.error(request, resultado["error"])
        return redirect("solicitudes:resolver_solicitud", pk=pk)


# --------------------------------------------------------------------------- #
# HU20 — Justificación con certificado categorizado
# --------------------------------------------------------------------------- #


class SeleccionarInasistenciaView(LoginRequiredMixin, UserPassesTestMixin, View):
    """HU20 — Landing page that lists the estudiante's justifiable absences.

    Acts as the entry point from dashboard / sidebar / mis-solicitudes
    into the certificate-based justification form. Each absence card
    links to ``solicitudes:crear_justificacion_certificado`` for that
    specific ``Asistencia``.

    Access control matches HU20's form view:

    * Anonymous → 302 to LOGIN_URL.
    * Authenticated non-estudiante → 403 (raise_exception).
    """

    raise_exception = True
    template_name = "solicitudes/seleccionar_inasistencia.html"

    def handle_no_permission(self):
        """Anonymous → redirect to login. Authenticated non-estudiante → 403."""
        if not self.request.user.is_authenticated:
            self.raise_exception = False
            return super().handle_no_permission()
        return super().handle_no_permission()

    def test_func(self) -> bool:
        user = self.request.user
        if not user.is_authenticated:
            return False
        return user.rol == "estudiante"

    def get(self, request):
        service = SolicitudAppService()
        inasistencias = service.obtener_inasistencias_justificables(request.user)
        return render(
            request,
            self.template_name,
            {"inasistencias": inasistencias},
        )


class CrearJustificacionConCertificadoView(LoginRequiredMixin, UserPassesTestMixin, View):
    """HU20 — Estudiante owner submits a categorized certificate justification.

    Access control layered three ways:

    * ``LoginRequiredMixin`` → anonymous users get 302 to LOGIN_URL.
    * ``UserPassesTestMixin.test_func`` → authenticated non-estudiantes
      and estudiantes who do not own the ``Asistencia`` get 403
      (raise_exception=True so the default 302-to-login dance is skipped
      for already-authenticated users).
    """

    raise_exception = True  # only affects authenticated users; anonymous still hit LoginRequired
    template_name = "solicitudes/justificacion_certificado.html"

    def handle_no_permission(self):
        """Anonymous → redirect to login (302). Authenticated → 403.

        ``raise_exception=True`` alone would 403 anonymous users too, which
        breaks the standard Django auth flow. We split by ``is_authenticated``.
        """
        if not self.request.user.is_authenticated:
            # Delegate to LoginRequiredMixin's redirect-to-login behavior.
            self.raise_exception = False
            return super().handle_no_permission()
        return super().handle_no_permission()

    # ------------------------------------------------------------------ #
    # Access control
    # ------------------------------------------------------------------ #
    def test_func(self) -> bool:
        user = self.request.user
        if not user.is_authenticated:
            # LoginRequiredMixin handles redirect; we still must return
            # False here so dispatch flows correctly.
            return False
        if user.rol != "estudiante":
            return False
        asistencia_id = self.kwargs.get("asistencia_id")
        return Asistencia.objects.filter(id=asistencia_id, estudiante=user).exists()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _get_asistencia(self, asistencia_id):
        return get_object_or_404(
            Asistencia.objects.select_related("paralelo__asignatura"),
            pk=asistencia_id,
            estudiante=self.request.user,
        )

    def _render(self, request, asistencia, form):
        return render(
            request,
            self.template_name,
            {"form": form, "asistencia": asistencia},
        )

    # ------------------------------------------------------------------ #
    # HTTP verbs
    # ------------------------------------------------------------------ #
    def get(self, request, asistencia_id):
        asistencia = self._get_asistencia(asistencia_id)
        form = JustificacionCertificadoForm()
        return self._render(request, asistencia, form)

    def post(self, request, asistencia_id):
        asistencia = self._get_asistencia(asistencia_id)
        form = JustificacionCertificadoForm(data=request.POST, files=request.FILES)
        if not form.is_valid():
            return self._render(request, asistencia, form)

        service = JustificacionCertificadoAppService()
        try:
            service.crear_justificacion_con_certificado(
                asistencia=asistencia,
                estudiante=request.user,
                tipo_certificado=form.cleaned_data["tipo_certificado"],
                datos_certificado=form.datos_certificado(),
                archivos=form.cleaned_data["archivos"],
                motivo=form.cleaned_data.get("motivo", ""),
            )
        except MaximoArchivosExcedidoError as exc:
            messages.error(
                request,
                f"Máximo 5 archivos permitidos (recibiste {exc.cantidad}).",
            )
            return self._render(request, asistencia, form)
        except ArchivoInvalidoError as exc:
            messages.error(
                request,
                f"Archivo {exc.nombre}: {', '.join(exc.errores)}.",
            )
            return self._render(request, asistencia, form)
        except CamposObligatoriosFaltantesError as exc:
            for campo in exc.campos:
                form.add_error(campo, "Este campo es obligatorio para el tipo seleccionado.")
            messages.error(
                request,
                f"Faltan campos obligatorios: {', '.join(exc.campos)}.",
            )
            return self._render(request, asistencia, form)
        except FechaCertificadoInvalidaError:
            form.add_error("fecha_certificado", "La fecha no puede ser futura.")
            messages.error(request, "La fecha del certificado no puede ser futura.")
            return self._render(request, asistencia, form)

        messages.success(request, "Solicitud de justificación enviada correctamente.")
        return redirect("solicitudes:mis_solicitudes")


# --------------------------------------------------------------------------- #
# HU21 — Inspector justifications dashboard + placeholders for T5/T6/T7
# --------------------------------------------------------------------------- #


class _InspectorRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Shared access mixin for the inspector justifications surface (HU21).

    Behavior:
      * Anonymous → 302 to LOGIN_URL (via LoginRequiredMixin).
      * Authenticated, ``rol != "inspector"`` → 403.

    The 403 branch is achieved by toggling ``raise_exception`` ONLY when
    the user is authenticated; anonymous users still take the default
    redirect path. Reused by the dashboard view (T4) and the upcoming
    detalle/resolver/bulk views (T5/T6/T7).
    """

    raise_exception = False

    def test_func(self) -> bool:
        user = self.request.user
        return user.is_authenticated and user.rol in ("inspector", "director_academico")

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            # Authenticated but wrong role → 403.
            self.raise_exception = True
        return super().handle_no_permission()


class InspectorJustificacionesDashboardView(_InspectorRequiredMixin, ListView):
    """HU21 — Institute-wide paginated dashboard of justification requests.

    Lists every ``Solicitud(tipo=JUSTIFICACION)`` ordered by ``fecha_creacion``
    desc, paginated 20/page. Supports GET filters: ``estado``,
    ``tipo_certificado``, ``paralelo``, ``q`` (search over estudiante's
    first_name / last_name / cedula, icontains).

    Each row gets a precomputed ``urgencia`` attribute (``"normal"`` /
    ``"alerta"`` / ``"vencido"``) so the template renders the badge
    without recomputing the classifier per row.

    Stats panel exposes 4 counters: pendientes (PENDIENTE+EN_REVISION
    total), aprobadas_hoy, rechazadas_hoy, vencidas (PENDIENTE/EN_REVISION
    past the deadline).
    """

    template_name = "solicitudes/inspector/dashboard.html"
    context_object_name = "solicitudes"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            Solicitud.objects.filter(tipo=Solicitud.TipoSolicitud.JUSTIFICACION)
            .select_related(
                "estudiante",
                "asistencia__paralelo__asignatura",
                "certificado",
                "resuelto_por",
            )
            .prefetch_related("archivos")
        )
        params = self.request.GET

        estado = params.get("estado")
        if estado:
            qs = qs.filter(estado=estado)

        tipo_cert = params.get("tipo_certificado")
        if tipo_cert:
            qs = qs.filter(certificado__tipo=tipo_cert)

        paralelo = params.get("paralelo")
        if paralelo:
            qs = qs.filter(asistencia__paralelo_id=paralelo)

        q = params.get("q")
        if q:
            qs = qs.filter(
                Q(estudiante__first_name__icontains=q)
                | Q(estudiante__last_name__icontains=q)
                | Q(estudiante__cedula__icontains=q)
            )

        return qs.order_by("-fecha_creacion")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # Single config fetch — reuse both values to avoid a second round-trip.
        config, _ = ConfiguracionJustificacion.get_singleton()
        deadline_dias = config.deadline_dias
        alerta_dias = config.alerta_dias
        today = timezone.localdate()

        # Precompute urgencia per row in the current page (perf-correct
        # location per design: not inside the template).
        #
        # Bugfix post-archive: urgencia aplica SOLO a solicitudes en estado
        # PENDIENTE o EN_REVISION. Una vez resuelta (APROBADA / RECHAZADA),
        # el inspector ya cumplió su SLA y el badge ("Vencido", "Por vencer",
        # "Al día") deja de tener sentido semántico.
        pending_states = (
            Solicitud.EstadoSolicitud.PENDIENTE,
            Solicitud.EstadoSolicitud.EN_REVISION,
        )
        page_solicitudes = ctx.get("solicitudes") or []
        for sol in page_solicitudes:
            if sol.estado in pending_states:
                sol.urgencia = clasificar_urgencia(
                    sol.fecha_creacion.date(),
                    deadline_dias,
                    alerta_dias,
                    today,
                )
                sol.dias_transcurridos = dias_habiles_transcurridos(
                    sol.fecha_creacion.date(), today
                )
            else:
                sol.urgencia = None
                sol.dias_transcurridos = None

        # Stats panel — 4 cheap COUNTs over the JUSTIFICACION universe.
        base = Solicitud.objects.filter(tipo=Solicitud.TipoSolicitud.JUSTIFICACION)
        pendiente_states = [
            Solicitud.EstadoSolicitud.PENDIENTE,
            Solicitud.EstadoSolicitud.EN_REVISION,
        ]
        pendientes_qs = base.filter(estado__in=pendiente_states)

        # vencidas requires per-row classification — limited to PENDIENTE
        # which is a bounded set in practice. Documented in design as
        # acceptable for current scale.
        vencidas = sum(
            1
            for s in pendientes_qs.only("fecha_creacion")
            if clasificar_urgencia(s.fecha_creacion.date(), deadline_dias, alerta_dias, today)
            == "vencido"
        )

        ctx["stats"] = {
            "pendientes": pendientes_qs.count(),
            "aprobadas_hoy": base.filter(
                estado=Solicitud.EstadoSolicitud.APROBADA,
                fecha_resolucion__date=today,
            ).count(),
            "rechazadas_hoy": base.filter(
                estado=Solicitud.EstadoSolicitud.RECHAZADA,
                fecha_resolucion__date=today,
            ).count(),
            "vencidas": vencidas,
        }

        ctx["deadline_dias"] = deadline_dias
        ctx["alerta_dias"] = alerta_dias

        # Filter dropdown data.
        ctx["estados"] = Solicitud.EstadoSolicitud.choices
        ctx["tipos_certificado"] = TipoCertificado.choices
        ctx["paralelos"] = (
            Paralelo.objects.filter(
                asistencias__solicitudes_justificacion__tipo=Solicitud.TipoSolicitud.JUSTIFICACION
            )
            .select_related("asignatura")
            .distinct()
            .order_by("asignatura__codigo", "nombre")
        )

        # Current filter values (for re-populating the form).
        ctx["filtros"] = {
            "estado": self.request.GET.get("estado", ""),
            "tipo_certificado": self.request.GET.get("tipo_certificado", ""),
            "paralelo": self.request.GET.get("paralelo", ""),
            "q": self.request.GET.get("q", ""),
        }

        # Querystring for pagination links (drops ``page``).
        qd = self.request.GET.copy()
        qd.pop("page", None)
        ctx["query_string"] = qd.urlencode()
        ctx["es_solo_lectura"] = self.request.user.rol == "director_academico"

        return ctx


class InspectorJustificacionDetalleView(_InspectorRequiredMixin, DetailView):
    """HU21 — T5: Detail view for a single justification request.

    Renders solicitud metadata, the certificado block (when present),
    historial entries, and inline previews of evidence — both the legacy
    ``Solicitud.archivo_adjunto`` (HU18) and the new ``ArchivoSolicitud``
    rows (HU20) — in a unified preview area.

    The queryset is pinned to ``TipoSolicitud.JUSTIFICACION``, so
    ``DetailView``'s default ``get_object`` will raise ``Http404`` for any
    other ``tipo`` value. This is intentional — see spec
    ``inspector-resolucion-justificacion`` R1.

    The resolution form is rendered as a skeleton here; the POST handler
    arrives in T6 (the URL still points at ``_PlaceholderInspectorView``
    until then). When the solicitud is already resolved (APROBADA or
    RECHAZADA), the form is hidden in favor of an informational message.
    """

    template_name = "solicitudes/inspector/detalle.html"
    context_object_name = "solicitud"
    queryset = (
        Solicitud.objects.filter(tipo=Solicitud.TipoSolicitud.JUSTIFICACION)
        .select_related("estudiante", "asistencia", "certificado", "resuelto_por")
        .prefetch_related("archivos", "historial")
    )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        solicitud = ctx["solicitud"]

        deadline_dias = ConfiguracionJustificacion.get_deadline_dias()
        alerta_dias = ConfiguracionJustificacion.get_alerta_dias()
        today = timezone.localdate()
        fecha_creacion_date = solicitud.fecha_creacion.date()

        # Bugfix post-archive: urgencia / dias_transcurridos solo si la
        # solicitud sigue PENDIENTE o EN_REVISION. Para resueltas el badge
        # del header y la línea "N días hábiles transcurridos" se omiten.
        pending_states = (
            Solicitud.EstadoSolicitud.PENDIENTE,
            Solicitud.EstadoSolicitud.EN_REVISION,
        )
        if solicitud.estado in pending_states:
            solicitud.urgencia = clasificar_urgencia(
                fecha_creacion_date, deadline_dias, alerta_dias, today
            )
            solicitud.dias_transcurridos = dias_habiles_transcurridos(fecha_creacion_date, today)
        else:
            solicitud.urgencia = None
            solicitud.dias_transcurridos = None

        ctx["deadline_dias"] = deadline_dias
        ctx["alerta_dias"] = alerta_dias
        ctx["solicitud_resuelta"] = solicitud.estado in (
            Solicitud.EstadoSolicitud.APROBADA,
            Solicitud.EstadoSolicitud.RECHAZADA,
        )
        ctx["es_solo_lectura"] = self.request.user.rol == "director_academico"
        return ctx


class InspectorResolverJustificacionView(_InspectorRequiredMixin, View):
    """HU21 — T6: POST handler to approve or reject a single justification.

    Delegates to :class:`InspectorResolucionAppService` (T3). Always
    redirects back to the detail view (Post/Redirect/Get pattern). Errors
    are surfaced through the messages framework — they never raise.

    Behavior:

    * ``accion="aprobar"`` → ``aprobar_justificacion``. Idempotent on
      already-resolved rows (the app service returns the solicitud
      unchanged).
    * ``accion="rechazar"`` → ``rechazar_justificacion``. Requires a
      non-empty ``comentario`` (after stripping whitespace); empty
      comentario raises ``ValueError`` in the service and we surface it
      as a message error without writing anything.
    * Any other ``accion`` (or missing) → message error, no writes.
    * Downstream errors from ``SolicitudAppService.resolver_solicitud``
      are re-raised by the wrapper as ``RuntimeError`` and surfaced as
      message errors.

    The queryset is pinned to ``TipoSolicitud.JUSTIFICACION``, so any
    other ``tipo`` (or a non-existent pk) yields a 404.
    """

    http_method_names = ["post"]

    def post(self, request, pk):
        solicitud = get_object_or_404(
            Solicitud,
            pk=pk,
            tipo=Solicitud.TipoSolicitud.JUSTIFICACION,
        )
        accion = request.POST.get("accion", "")
        comentario = request.POST.get("comentario", "").strip()
        service = InspectorResolucionAppService()
        try:
            if accion == "aprobar":
                service.aprobar_justificacion(solicitud, request.user, comentario)
                messages.success(request, "Justificación aprobada.")
            elif accion == "rechazar":
                service.rechazar_justificacion(solicitud, request.user, comentario)
                messages.success(request, "Justificación rechazada.")
            else:
                messages.error(request, "Acción inválida.")
        except ValueError as exc:
            messages.error(request, str(exc))
        except RuntimeError as exc:
            messages.error(request, str(exc))
        return redirect("solicitudes:inspector_justificacion_detalle", pk=pk)


class InspectorBulkActionView(_InspectorRequiredMixin, View):
    """HU21 — T7: POST handler to approve/reject several justifications.

    Delegates to :meth:`InspectorResolucionAppService.procesar_bulk_resolucion`
    (T3). Always redirects back to the dashboard (Post/Redirect/Get pattern).
    Errors surface via the messages framework — they never raise.

    Behavior:

    * ``solicitud_ids`` missing or empty → message error, no writes.
    * Non-numeric ids are silently dropped before reaching the service.
    * ``accion="aprobar"`` → bulk approve. Already-resolved rows counted
      in ``omitidas``. Non-JUSTIFICACION ids and non-existent ids are
      silently filtered out by the service.
    * ``accion="rechazar"`` → bulk reject. Requires non-empty
      ``comentario`` (after stripping). Empty comentario raises
      ``ValueError`` in the service BEFORE the loop runs, so ZERO rows
      get touched (all-or-nothing semantics).
    * Any other ``accion`` (or missing) → the service per-row try/except
      counts the row as omitida without writing.
    * Success message: ``"Procesadas: N. Omitidas (ya resueltas): M."``.
    """

    http_method_names = ["post"]

    def post(self, request):
        ids = [int(x) for x in request.POST.getlist("solicitud_ids") if x.isdigit()]
        accion = request.POST.get("accion", "")
        comentario = request.POST.get("comentario", "").strip()

        if not ids:
            messages.error(request, "Seleccioná al menos una justificación.")
            return redirect("solicitudes:inspector_justificaciones_dashboard")

        service = InspectorResolucionAppService()
        try:
            resultado = service.procesar_bulk_resolucion(ids, request.user, accion, comentario)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("solicitudes:inspector_justificaciones_dashboard")

        msg = (
            f"Procesadas: {resultado.procesadas}. "
            f"Omitidas (ya resueltas): {resultado.omitidas}."
        )
        messages.success(request, msg)
        return redirect("solicitudes:inspector_justificaciones_dashboard")
