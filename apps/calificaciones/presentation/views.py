"""
Views for the Calificaciones bounded context.

Sprint 3 — HU13/HU14: Grade registration and evaluation management for teachers.
Sprint 3 — HU15: Audit log report for secretaría and inspector.
"""

import re

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.academico.infrastructure.models import Paralelo
from apps.calificaciones.application.services import (
    GestionEvaluacionesAppService,
    LibretaCalificacionesAppService,
    RegistroCalificacionAppService,
    SubNotaParcialAppService,
    ValidacionCalificacionAppService,
)
from apps.calificaciones.infrastructure.models import (
    Evaluacion,
    LogCalificacion,
    SubNotaParcial,
)
from apps.usuarios.infrastructure.models import Usuario
from apps.usuarios.presentation.permissions import MultiRolRequeridoMixin, RolRequeridoMixin


_PATRON_BUSQUEDA_ESTUDIANTE = re.compile(r"^[a-zA-ZáéíóúÁÉÍÓÚüÜñÑ0-9 \-]+$")


def _validar_cedula_ecuatoriana(cedula: str) -> bool:
    """Validates Ecuadorian natural-person cédula using the official modulo-10 algorithm."""
    if len(cedula) != 10 or not cedula.isdigit():
        return False
    provincia = int(cedula[:2])
    if not (1 <= provincia <= 24):
        return False
    if int(cedula[2]) >= 6:  # 0-5 = natural person
        return False
    coef = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    suma = sum((v - 9 if v > 9 else v) for v in (int(cedula[i]) * coef[i] for i in range(9)))
    return (10 - suma % 10) % 10 == int(cedula[9])


def _validar_busqueda_estudiante(q: str) -> str | None:
    """Returns an error message string if the search term is invalid, else None."""
    if not q:
        return None
    if len(q) < 2:
        return "Ingresa al menos 2 caracteres para buscar."
    if not _PATRON_BUSQUEDA_ESTUDIANTE.match(q):
        return "Solo se permiten letras, números, espacios y guiones."
    if q.isdigit():
        if len(q) != 10:
            return "La cédula ecuatoriana debe tener exactamente 10 dígitos."
        if not _validar_cedula_ecuatoriana(q):
            return "El número de cédula ingresado no es válido."
    return None


def _verificar_paralelo_docente(request, paralelo_id):
    """Returns (paralelo, redirect) — redirect is set if access is denied."""
    paralelo = get_object_or_404(
        Paralelo.objects.select_related("asignatura", "periodo", "docente"),
        pk=paralelo_id,
    )
    if paralelo.docente_id != request.user.id:
        messages.error(request, "No tiene permiso para acceder a este paralelo.")
        return None, redirect("calificaciones:seleccionar_paralelo")
    return paralelo, None


def _get_client_ip(request) -> str:
    """Extracts client IP from request, respecting X-Forwarded-For."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


class SeleccionarParaleloCalificacionesView(RolRequeridoMixin, View):
    rol_requerido = "docente"
    template_name = "calificaciones/seleccionar_paralelo.html"

    def get(self, request):
        service = RegistroCalificacionAppService()
        paralelos = service.obtener_paralelos_docente(request.user.id)
        return render(request, self.template_name, {"paralelos": paralelos})


class RegistrarCalificacionesView(RolRequeridoMixin, View):
    rol_requerido = "docente"
    template_name = "calificaciones/registrar_calificaciones.html"

    def get(self, request, paralelo_id):
        paralelo, redir = _verificar_paralelo_docente(request, paralelo_id)
        if redir:
            return redir
        service = RegistroCalificacionAppService()
        planilla = service.obtener_planilla(paralelo_id)
        registro = service.obtener_o_crear_registro(paralelo_id)
        puede_editar = service.puede_editar(paralelo_id)
        planilla_completa = service.verificar_completitud(paralelo_id)
        hay_calificaciones = service.hay_calificaciones_registradas(paralelo_id)
        self._agregar_contexto_sub_notas(paralelo_id, planilla)
        return render(
            request,
            self.template_name,
            {
                "paralelo": paralelo,
                "registro": registro,
                "puede_editar": puede_editar,
                "planilla_completa": planilla_completa,
                "hay_calificaciones": hay_calificaciones,
                **planilla,
            },
        )

    def post(self, request, paralelo_id):
        paralelo, redir = _verificar_paralelo_docente(request, paralelo_id)
        if redir:
            return redir

        service = RegistroCalificacionAppService()
        if not service.puede_editar(paralelo_id):
            messages.error(
                request,
                "Las calificaciones ya fueron enviadas y no se pueden modificar.",
            )
            return redirect("calificaciones:registrar_calificaciones", paralelo_id=paralelo_id)

        notas_data = {}
        for key, value in request.POST.items():
            if key.startswith("nota_"):
                parts = key.split("_")
                if len(parts) == 3:
                    try:
                        notas_data[(int(parts[1]), int(parts[2]))] = value
                    except ValueError:
                        pass

        sub_guardadas, sub_errores = self._procesar_sub_notas(request)

        resultado = service.guardar_calificaciones(
            paralelo_id, notas_data, request.user, _get_client_ip(request)
        )

        for _, msg in resultado["errores"]:
            messages.error(request, msg)
        if sub_guardadas > 0:
            messages.success(
                request,
                f"{sub_guardadas} parcial(es) consolidado(s) desde sub-notas.",
            )
        if resultado["guardadas"] > 0:
            messages.success(
                request,
                f"{resultado['guardadas']} calificacion(es) guardada(s) correctamente.",
            )
        elif not resultado["errores"] and sub_guardadas == 0 and sub_errores == 0:
            messages.info(request, "No se realizaron cambios.")

        return redirect("calificaciones:registrar_calificaciones", paralelo_id=paralelo_id)

    @staticmethod
    def _agregar_contexto_sub_notas(paralelo_id, planilla):
        """Adds per-cell sub-nota data (HU32) as `celdas_sub` on each fila."""
        sub_service = SubNotaParcialAppService()
        config_por_ev = {}
        for ev in planilla["evaluaciones"]:
            if ev.es_parcial:
                items = sub_service.obtener_configuracion(ev.id)
                if items:
                    config_por_ev[ev.id] = items

        sub_lookup = {}
        if config_por_ev:
            for sn in SubNotaParcial.objects.filter(evaluacion__paralelo_id=paralelo_id):
                sub_lookup[(sn.matricula_id, sn.evaluacion_id, sn.orden)] = sn

        for fila in planilla["filas"]:
            matricula = fila["matricula"]
            celdas_sub = []
            for ev, cal in fila["celdas"]:
                celda = {"ev": ev, "cal": cal, "config": None}
                config = config_por_ev.get(ev.id)
                if config:
                    items = []
                    override = None
                    justificacion = ""
                    for item in config:
                        sn = sub_lookup.get((matricula.id, ev.id, item.orden))
                        items.append(
                            {
                                "nombre": item.nombre,
                                "orden": item.orden,
                                "peso": item.peso,
                                "sub": sn,
                            }
                        )
                        if sn is not None and sn.nota_final_parcial_override is not None:
                            override = sn.nota_final_parcial_override
                            justificacion = sn.justificacion_override
                    celda["config"] = items
                    celda["override"] = override
                    celda["justificacion"] = justificacion
                celdas_sub.append(celda)
            fila["celdas_sub"] = celdas_sub

    def _procesar_sub_notas(self, request):
        """Parses subnota_/override_/just_ POST groups and registers them (HU32)."""
        sub_data = {}
        overrides = {}
        justificaciones = {}
        for key, value in request.POST.items():
            parts = key.split("_")
            try:
                if key.startswith("subnota_") and len(parts) == 4:
                    grupo = (int(parts[1]), int(parts[2]))
                    sub_data.setdefault(grupo, {})[int(parts[3])] = value
                elif key.startswith("override_") and len(parts) == 3:
                    overrides[(int(parts[1]), int(parts[2]))] = value.strip()
                elif key.startswith("just_") and len(parts) == 3:
                    justificaciones[(int(parts[1]), int(parts[2]))] = value.strip()
            except ValueError:
                pass

        sub_service = SubNotaParcialAppService()
        ip = _get_client_ip(request)
        guardadas = 0
        errores = 0
        for (matricula_id, evaluacion_id), notas_por_orden in sub_data.items():
            notas = [valor for _, valor in sorted(notas_por_orden.items())]
            override_str = overrides.get((matricula_id, evaluacion_id), "")
            if all(not (n or "").strip() for n in notas) and not override_str:
                continue
            resultado = sub_service.registrar_sub_notas(
                evaluacion_id,
                matricula_id,
                notas,
                usuario=request.user,
                ip=ip,
                override_str=override_str,
                justificacion=justificaciones.get((matricula_id, evaluacion_id), ""),
            )
            if resultado["ok"]:
                guardadas += 1
            else:
                errores += 1
                messages.error(request, resultado["error"])
        return guardadas, errores


class GestionEvaluacionesView(RolRequeridoMixin, View):
    """List evaluaciones + create new one."""

    rol_requerido = "docente"
    template_name = "calificaciones/gestionar_evaluaciones.html"

    def get(self, request, paralelo_id):
        paralelo, redir = _verificar_paralelo_docente(request, paralelo_id)
        if redir:
            return redir
        service = GestionEvaluacionesAppService()
        datos = service.obtener_evaluaciones(paralelo_id)
        puede_editar = RegistroCalificacionAppService().puede_editar(paralelo_id)
        return render(
            request,
            self.template_name,
            {"paralelo": paralelo, "puede_editar": puede_editar, **datos},
        )

    def post(self, request, paralelo_id):
        paralelo, redir = _verificar_paralelo_docente(request, paralelo_id)
        if redir:
            return redir

        if not RegistroCalificacionAppService().puede_editar(paralelo_id):
            messages.error(
                request,
                "No se pueden modificar las evaluaciones: "
                "las calificaciones ya fueron enviadas a validación.",
            )
            return redirect("calificaciones:gestionar_evaluaciones", paralelo_id=paralelo_id)

        service = GestionEvaluacionesAppService()
        resultado = service.crear_evaluacion(
            paralelo_id=paralelo_id,
            tipo=request.POST.get("tipo", ""),
            peso_str=request.POST.get("peso", ""),
        )

        if resultado["ok"]:
            ev = resultado["evaluacion"]
            messages.success(request, f"Evaluación '{ev.get_tipo_display()}' ({ev.peso}%) creada.")
        else:
            for err in resultado["errores"]:
                messages.error(request, err)

        return redirect("calificaciones:gestionar_evaluaciones", paralelo_id=paralelo_id)


class EditarEvaluacionView(RolRequeridoMixin, View):
    """Edit the weight of an existing evaluacion."""

    rol_requerido = "docente"
    template_name = "calificaciones/editar_evaluacion.html"

    def get(self, request, paralelo_id, evaluacion_id):
        paralelo, redir = _verificar_paralelo_docente(request, paralelo_id)
        if redir:
            return redir
        evaluacion = get_object_or_404(Evaluacion, pk=evaluacion_id, paralelo=paralelo)
        return render(
            request,
            self.template_name,
            {"paralelo": paralelo, "evaluacion": evaluacion},
        )

    def post(self, request, paralelo_id, evaluacion_id):
        paralelo, redir = _verificar_paralelo_docente(request, paralelo_id)
        if redir:
            return redir

        if not RegistroCalificacionAppService().puede_editar(paralelo_id):
            messages.error(
                request,
                "No se pueden modificar los pesos: "
                "las calificaciones ya fueron enviadas a validación.",
            )
            return redirect("calificaciones:gestionar_evaluaciones", paralelo_id=paralelo_id)

        service = GestionEvaluacionesAppService()
        resultado = service.actualizar_evaluacion(
            evaluacion_id=evaluacion_id,
            peso_str=request.POST.get("peso", ""),
        )

        if resultado["ok"]:
            ev = resultado["evaluacion"]
            messages.success(
                request,
                f"Peso de '{ev.get_tipo_display()}' actualizado a {ev.peso}%.",
            )
            return redirect("calificaciones:gestionar_evaluaciones", paralelo_id=paralelo_id)

        evaluacion = get_object_or_404(Evaluacion, pk=evaluacion_id)
        for err in resultado["errores"]:
            messages.error(request, err)
        return render(
            request,
            self.template_name,
            {"paralelo": paralelo, "evaluacion": evaluacion},
        )


class EliminarEvaluacionView(RolRequeridoMixin, View):
    """Delete an evaluacion (only if it has no grades)."""

    rol_requerido = "docente"

    def post(self, request, paralelo_id, evaluacion_id):
        paralelo, redir = _verificar_paralelo_docente(request, paralelo_id)
        if redir:
            return redir

        get_object_or_404(Evaluacion, pk=evaluacion_id, paralelo=paralelo)

        if not RegistroCalificacionAppService().puede_editar(paralelo_id):
            messages.error(
                request,
                "No se pueden eliminar evaluaciones: "
                "las calificaciones ya fueron enviadas a validación.",
            )
            return redirect("calificaciones:gestionar_evaluaciones", paralelo_id=paralelo_id)

        service = GestionEvaluacionesAppService()
        resultado = service.eliminar_evaluacion(evaluacion_id)

        if resultado["ok"]:
            messages.success(request, "Evaluación eliminada correctamente.")
        else:
            messages.error(request, resultado["error"])

        return redirect("calificaciones:gestionar_evaluaciones", paralelo_id=paralelo_id)


class ConfigurarSubNotasView(RolRequeridoMixin, View):
    """Configure the 3-5 sub-nota names for a parcial (HU32)."""

    rol_requerido = "docente"
    template_name = "calificaciones/configurar_sub_notas.html"

    def get(self, request, paralelo_id, evaluacion_id):
        paralelo, redir = _verificar_paralelo_docente(request, paralelo_id)
        if redir:
            return redir
        evaluacion = get_object_or_404(Evaluacion, pk=evaluacion_id, paralelo=paralelo)
        if not evaluacion.es_parcial:
            messages.error(request, "Solo los parciales admiten sub-notas.")
            return redirect("calificaciones:gestionar_evaluaciones", paralelo_id=paralelo_id)

        service = SubNotaParcialAppService()
        items = service.obtener_configuracion(evaluacion_id)
        items_iniciales = [
            {"nombre": item.nombre, "peso": str(item.peso) if item.peso is not None else ""}
            for item in (items or [])
        ]
        puede_editar = RegistroCalificacionAppService().puede_editar(paralelo_id)
        tiene_sub_notas = SubNotaParcial.objects.filter(evaluacion=evaluacion).exists()
        return render(
            request,
            self.template_name,
            {
                "paralelo": paralelo,
                "evaluacion": evaluacion,
                "items_iniciales": items_iniciales,
                "puede_editar": puede_editar,
                "tiene_sub_notas": tiene_sub_notas,
            },
        )

    def post(self, request, paralelo_id, evaluacion_id):
        paralelo, redir = _verificar_paralelo_docente(request, paralelo_id)
        if redir:
            return redir
        get_object_or_404(Evaluacion, pk=evaluacion_id, paralelo=paralelo)

        service = SubNotaParcialAppService()
        resultado = service.configurar_sub_notas(
            evaluacion_id,
            request.POST.getlist("nombre"),
            pesos=request.POST.getlist("peso"),
        )
        if resultado["ok"]:
            msg = "Sub-notas configuradas correctamente."
            if resultado.get("sub_notas_eliminadas"):
                msg += (
                    f" Se eliminaron {resultado['sub_notas_eliminadas']} "
                    "sub-notas registradas con la configuración anterior."
                )
            messages.success(request, msg)
            return redirect("calificaciones:gestionar_evaluaciones", paralelo_id=paralelo_id)

        messages.error(request, resultado["error"])
        return redirect(
            "calificaciones:configurar_sub_notas",
            paralelo_id=paralelo_id,
            evaluacion_id=evaluacion_id,
        )


class AuditoriaCalificacionesView(MultiRolRequeridoMixin, View):
    """Reporte de auditoría — accesible para secretaría e inspector."""

    roles_permitidos = ["secretaria", "inspector", "director_academico"]
    template_name = "calificaciones/auditoria_calificaciones.html"

    def get(self, request):
        qs = LogCalificacion.objects.select_related(
            "calificacion__evaluacion__paralelo__asignatura",
            "realizado_por",
        ).order_by("-timestamp")

        fecha_inicio = request.GET.get("fecha_inicio", "").strip()
        fecha_fin = request.GET.get("fecha_fin", "").strip()
        accion = request.GET.get("accion", "").strip()
        docente_id = request.GET.get("docente", "").strip()
        estudiante_q = request.GET.get("estudiante", "").strip()

        if fecha_inicio:
            qs = qs.filter(timestamp__date__gte=fecha_inicio)
        if fecha_fin:
            qs = qs.filter(timestamp__date__lte=fecha_fin)
        if accion:
            qs = qs.filter(accion=accion)
        if docente_id:
            if docente_id.isdigit():
                qs = qs.filter(realizado_por_id=docente_id)
            else:
                docente_id = ""

        error_estudiante = _validar_busqueda_estudiante(estudiante_q)
        if estudiante_q and not error_estudiante:
            qs = qs.filter(estudiante_info__icontains=estudiante_q)

        docentes = Usuario.objects.filter(rol="docente").order_by("last_name", "first_name")

        LIMITE = 500
        total_logs = qs.count()
        truncado = total_logs > LIMITE

        return render(
            request,
            self.template_name,
            {
                "logs": qs[:LIMITE],
                "total_logs": total_logs,
                "truncado": truncado,
                "limite": LIMITE,
                "acciones": [
                    c
                    for c in LogCalificacion.TipoAccion.choices
                    if c[0] not in ("creacion", "modificacion", "eliminacion")
                ],
                "docentes": docentes,
                "filtros": {
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin,
                    "accion": accion,
                    "docente": docente_id,
                    "estudiante": estudiante_q,
                },
                "errores_filtros": {
                    "estudiante": error_estudiante,
                },
            },
        )


class EnviarValidacionView(RolRequeridoMixin, View):
    """Submit grades for secretaría validation."""

    rol_requerido = "docente"

    def post(self, request, paralelo_id):
        paralelo, redir = _verificar_paralelo_docente(request, paralelo_id)
        if redir:
            return redir
        service = RegistroCalificacionAppService()
        resultado = service.enviar_a_validacion(paralelo_id, usuario=request.user)
        if resultado["ok"]:
            messages.success(request, "Calificaciones enviadas a validación exitosamente.")
        else:
            messages.error(request, resultado["error"])
        return redirect("calificaciones:registrar_calificaciones", paralelo_id=paralelo_id)


# ---------------------------------------------------------------------------
# HU16: Validación de calificaciones por secretaría
# ---------------------------------------------------------------------------


class PendientesValidacionView(RolRequeridoMixin, View):
    """List paralelos pending validation. Only secretaria."""

    rol_requerido = "secretaria"
    template_name = "calificaciones/pendientes_validacion.html"

    def get(self, request):
        service = ValidacionCalificacionAppService()
        pendientes = service.obtener_pendientes()
        return render(request, self.template_name, {"pendientes": pendientes})


class DetalleValidacionView(RolRequeridoMixin, View):
    """Readonly planilla + approve/reject actions. Only secretaria."""

    rol_requerido = "secretaria"
    template_name = "calificaciones/detalle_validacion.html"

    def get(self, request, paralelo_id):
        service = ValidacionCalificacionAppService()
        datos = service.obtener_detalle_validacion(paralelo_id)
        if datos is None:
            messages.error(request, "Registro no encontrado o no está pendiente de validación.")
            return redirect("calificaciones:pendientes_validacion")
        return render(request, self.template_name, datos)


# =============================================================================
# HU17 — Libreta de calificaciones (Estudiante)
# =============================================================================


class MiLibretaView(RolRequeridoMixin, View):
    """Student grade report — read-only view of all subjects and grades."""

    rol_requerido = "estudiante"

    def get(self, request):
        libreta = LibretaCalificacionesAppService.obtener_libreta(request.user)
        return render(request, "calificaciones/mi_libreta.html", libreta)


class AprobarCalificacionesView(RolRequeridoMixin, View):
    """Approve grades. Only secretaria."""

    rol_requerido = "secretaria"

    def post(self, request, paralelo_id):
        service = ValidacionCalificacionAppService()
        resultado = service.aprobar(paralelo_id, request.user)
        if resultado["ok"]:
            messages.success(request, "Calificaciones aprobadas exitosamente.")
        else:
            messages.error(request, resultado["error"])
        return redirect("calificaciones:pendientes_validacion")


class RechazarCalificacionesView(RolRequeridoMixin, View):
    """Reject grades with observations. Only secretaria."""

    rol_requerido = "secretaria"

    def post(self, request, paralelo_id):
        service = ValidacionCalificacionAppService()
        observaciones = request.POST.get("observaciones", "")
        resultado = service.rechazar(paralelo_id, request.user, observaciones)
        if resultado["ok"]:
            messages.success(request, "Calificaciones rechazadas. El docente ha sido notificado.")
        else:
            messages.error(request, resultado["error"])
        return redirect("calificaciones:pendientes_validacion")


# ---------------------------------------------------------------------------
# Supervisión de calificaciones (Inspector)
# ---------------------------------------------------------------------------


class SupervisionCalificacionesView(MultiRolRequeridoMixin, View):
    """Redirect to unified supervision view with calificaciones tab active."""

    roles_permitidos = ["inspector", "director_academico"]

    def get(self, request):
        return redirect("/asistencia/supervision/?tab=calificaciones")


# ---------------------------------------------------------------------------
# Reporte de Auditoría (HU27b follow-up 2026-06-24)
# ---------------------------------------------------------------------------


def _parse_auditoria_filtros(GET):
    """Parsea query params para el export de auditoría.

    Todos los filtros son opcionales (a diferencia de los export de
    calificaciones/asistencia que requieren ?periodo=). Si no se
    pasan filtros, se exportan todos los logs (hasta el límite de
    1000 para no generar archivos enormes).
    """
    filtros = {}
    fecha_inicio = (GET.get("fecha_inicio") or "").strip()
    if fecha_inicio:
        filtros["fecha_inicio"] = fecha_inicio
    fecha_fin = (GET.get("fecha_fin") or "").strip()
    if fecha_fin:
        filtros["fecha_fin"] = fecha_fin
    accion = (GET.get("accion") or "").strip()
    if accion:
        filtros["accion"] = accion
    docente = (GET.get("docente") or "").strip()
    if docente:
        filtros["docente"] = docente
    estudiante = (GET.get("estudiante") or "").strip()
    if estudiante:
        filtros["estudiante"] = estudiante
    return filtros


class ExportarAuditoriaView(MultiRolRequeridoMixin, View):
    """GET /calificaciones/auditoria/exportar/ — Reporte de Auditoría.

    Queryea ``LogCalificacion`` (NO ``Calificacion``) con los mismos
    filtros de la página de auditoría y genera un archivo Excel/PDF
    titulado "ECPPP — Reporte de Auditoría".
    """

    LIMITE = 1000  # máximo de filas para evitar archivos enormes
    # Director Académico agregado: el view del listado (line 293) ya
    # lo incluye, pero el endpoint de export se olvidó. Inconsistencia
    # que rompía el inline button en la página de auditoría.
    roles_permitidos = ["secretaria", "inspector", "director_academico"]

    def get(self, request):
        from django.http import HttpResponse

        from apps.calificaciones.application.services import (
            ExportarAuditoriaService,
        )
        from apps.reportes.application.rate_limiter import (
            ExportacionRateLimiter,
        )
        from apps.reportes.presentation.views import _rate_limit_json

        # 1. Rate limit (10/min/user, reusado de reportes)
        if not ExportacionRateLimiter.check(request.user.id):
            return _rate_limit_json()

        # 2. Parse filters
        filtros = _parse_auditoria_filtros(request.GET)

        # Si el queryset excede LIMITE, igual generamos el archivo pero
        # con un warning en el header. El export NO pagina — si el usuario
        # necesita más, puede refinar los filtros.
        filtros["_limite"] = self.LIMITE

        # 4. Build service
        service = ExportarAuditoriaService(filtros)

        # 5. Generate file
        formato = request.GET.get("formato", "excel")
        if formato == "excel":
            buffer = service.exportar_excel()
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            buffer = service.exportar_pdf()
            content_type = "application/pdf"

        # 6. Filename
        filename = service._filename(formato)

        response = HttpResponse(buffer.read(), content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
