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
    RegistroCalificacionAppService,
)
from apps.calificaciones.infrastructure.models import Evaluacion, LogCalificacion
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
        return render(
            request,
            self.template_name,
            {
                "paralelo": paralelo,
                "registro": registro,
                "puede_editar": puede_editar,
                "planilla_completa": planilla_completa,
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

        resultado = service.guardar_calificaciones(
            paralelo_id, notas_data, request.user, _get_client_ip(request)
        )

        for _, msg in resultado["errores"]:
            messages.error(request, msg)
        if resultado["guardadas"] > 0:
            messages.success(
                request,
                f"{resultado['guardadas']} calificacion(es) guardada(s) correctamente.",
            )
        elif not resultado["errores"]:
            messages.info(request, "No se realizaron cambios.")

        return redirect("calificaciones:registrar_calificaciones", paralelo_id=paralelo_id)


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
        return render(request, self.template_name, {"paralelo": paralelo, **datos})

    def post(self, request, paralelo_id):
        paralelo, redir = _verificar_paralelo_docente(request, paralelo_id)
        if redir:
            return redir

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
            request, self.template_name, {"paralelo": paralelo, "evaluacion": evaluacion}
        )

    def post(self, request, paralelo_id, evaluacion_id):
        paralelo, redir = _verificar_paralelo_docente(request, paralelo_id)
        if redir:
            return redir

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
            request, self.template_name, {"paralelo": paralelo, "evaluacion": evaluacion}
        )


class EliminarEvaluacionView(RolRequeridoMixin, View):
    """Delete an evaluacion (only if it has no grades)."""

    rol_requerido = "docente"

    def post(self, request, paralelo_id, evaluacion_id):
        paralelo, redir = _verificar_paralelo_docente(request, paralelo_id)
        if redir:
            return redir

        get_object_or_404(Evaluacion, pk=evaluacion_id, paralelo=paralelo)

        service = GestionEvaluacionesAppService()
        resultado = service.eliminar_evaluacion(evaluacion_id)

        if resultado["ok"]:
            messages.success(request, "Evaluación eliminada correctamente.")
        else:
            messages.error(request, resultado["error"])

        return redirect("calificaciones:gestionar_evaluaciones", paralelo_id=paralelo_id)


class AuditoriaCalificacionesView(MultiRolRequeridoMixin, View):
    """Reporte de auditoría — accesible para secretaría e inspector."""

    roles_permitidos = ["secretaria", "inspector"]
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
                "acciones": LogCalificacion.TipoAccion.choices,
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
        resultado = service.enviar_a_validacion(paralelo_id)
        if resultado["ok"]:
            messages.success(request, "Calificaciones enviadas a validación exitosamente.")
        else:
            messages.error(request, resultado["error"])
        return redirect("calificaciones:registrar_calificaciones", paralelo_id=paralelo_id)
