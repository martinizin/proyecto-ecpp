"""
Views for the Solicitudes bounded context.

Sprint 3 — HU18: Solicitudes de recalificación y justificación de inasistencia.
"""

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View

from apps.solicitudes.application.services import SolicitudAppService
from apps.solicitudes.infrastructure.models import Solicitud
from apps.usuarios.presentation.permissions import RolRequeridoMixin


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
            messages.success(
                request, "Solicitud de recalificación enviada correctamente."
            )
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
            messages.success(
                request, "Solicitud de justificación enviada correctamente."
            )
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
        solicitudes = service.obtener_mis_solicitudes(
            request.user, tipo=tipo_filtro or None
        )
        return render(
            request,
            self.template_name,
            {
                "solicitudes": solicitudes,
                "tipo_filtro": tipo_filtro,
                "tipos": Solicitud.TipoSolicitud.choices,
            },
        )
