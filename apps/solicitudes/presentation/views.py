"""
Views for the Solicitudes bounded context.

Sprint 3 — HU18/HU19: Solicitudes y flujo de aprobación.
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.solicitudes.application.services import SolicitudAppService
from apps.solicitudes.infrastructure.models import Solicitud
from apps.usuarios.presentation.permissions import (
    MultiRolRequeridoMixin,
    RolRequeridoMixin,
)


class CrearRecalificacionView(RolRequeridoMixin, View):
    """Form to create a grade rectification request. Only estudiante."""

    rol_requerido = "estudiante"
    template_name = "solicitudes/crear_recalificacion.html"

    def get(self, request):
        service = SolicitudAppService()
        calificaciones = service.obtener_calificaciones_reclamables(request.user)
        return render(request, self.template_name, {"calificaciones": calificaciones})

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
        calificaciones = service.obtener_calificaciones_reclamables(request.user)
        return render(
            request,
            self.template_name,
            {
                "calificaciones": calificaciones,
                "form_data": {
                    "calificacion": calificacion_id,
                    "descripcion": descripcion,
                },
            },
        )


class CrearJustificacionView(RolRequeridoMixin, View):
    """Form to create an absence justification request. Only estudiante."""

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
        return render(
            request, self.template_name, {"solicitudes": solicitudes}
        )


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
        return render(
            request, self.template_name, {"solicitudes": solicitudes}
        )


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
            resultado = service.escalar_a_docente(
                pk, request.user, comentario
            )
        # Tomar solicitud (PENDIENTE → EN_REVISION)
        elif accion == "tomar":
            resultado = service.tomar_solicitud(pk, request.user)
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
                "tomar": "Solicitud tomada correctamente.",
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
