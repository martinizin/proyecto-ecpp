"""
Views for the Asistencia bounded context.

Sprint 2: Attendance registration (HU08), history view.
"""

from datetime import date

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.academico.infrastructure.models import Paralelo
from apps.asistencia.application.services import RegistroAsistenciaAppService
from apps.usuarios.presentation.permissions import MultiRolRequeridoMixin, RolRequeridoMixin


class SeleccionarParaleloView(MultiRolRequeridoMixin, View):
    """
    Select a paralelo to take attendance.
    Docente sees only their paralelos. Inspector sees all.
    """

    roles_permitidos = ["docente", "inspector"]
    template_name = "asistencia/seleccionar_paralelo.html"

    def get(self, request):
        service = RegistroAsistenciaAppService()

        if request.user.rol == "docente":
            paralelos = service.obtener_paralelos_docente(request.user.id)
        else:
            paralelos = service.obtener_todos_paralelos_activos()

        return render(request, self.template_name, {"paralelos": paralelos})


class RegistrarAsistenciaView(MultiRolRequeridoMixin, View):
    """
    GET: Show attendance form with checkboxes for enrolled students.
    POST: Save attendance records (checked = present, unchecked = absent).
    """

    roles_permitidos = ["docente", "inspector"]
    template_name = "asistencia/registrar_asistencia.html"

    def get(self, request, paralelo_id):
        paralelo = get_object_or_404(
            Paralelo.objects.select_related("asignatura", "periodo", "docente"),
            pk=paralelo_id,
        )

        # Docente can only access their own paralelos
        if (
            request.user.rol == "docente"
            and paralelo.docente_id != request.user.id
        ):
            messages.error(request, "No tiene permiso para este paralelo.")
            return redirect("asistencia:seleccionar_paralelo")

        service = RegistroAsistenciaAppService()
        matriculas = service.obtener_estudiantes_matriculados(paralelo_id)

        # Get date from query param or default to today
        fecha_str = request.GET.get("fecha")
        if fecha_str:
            try:
                fecha = date.fromisoformat(fecha_str)
            except ValueError:
                fecha = date.today()
        else:
            fecha = date.today()

        # Check if attendance already exists for this date (for pre-filling)
        asistencia_existente = service.obtener_asistencia_existente(
            paralelo_id, fecha
        )
        presentes_ids = set(
            asistencia_existente.filter(
                estado__in=["presente", "justificado"]
            ).values_list("estudiante_id", flat=True)
        )
        ya_registrada = asistencia_existente.exists()

        return render(
            request,
            self.template_name,
            {
                "paralelo": paralelo,
                "matriculas": matriculas,
                "fecha": fecha,
                "presentes_ids": presentes_ids,
                "ya_registrada": ya_registrada,
            },
        )

    def post(self, request, paralelo_id):
        paralelo = get_object_or_404(
            Paralelo.objects.select_related("asignatura", "periodo", "docente"),
            pk=paralelo_id,
        )

        # Docente can only access their own paralelos
        if (
            request.user.rol == "docente"
            and paralelo.docente_id != request.user.id
        ):
            messages.error(request, "No tiene permiso para este paralelo.")
            return redirect("asistencia:seleccionar_paralelo")

        fecha_str = request.POST.get("fecha", "")
        try:
            fecha = date.fromisoformat(fecha_str)
        except ValueError:
            messages.error(request, "Fecha inválida.")
            return redirect(
                "asistencia:registrar_asistencia", paralelo_id=paralelo_id
            )

        # Get list of student IDs marked as present
        estudiantes_presentes_ids = [
            int(sid)
            for sid in request.POST.getlist("presentes")
            if sid.isdigit()
        ]

        service = RegistroAsistenciaAppService()
        resultado = service.registrar_asistencia(
            paralelo_id=paralelo_id,
            fecha=fecha,
            estudiantes_presentes_ids=estudiantes_presentes_ids,
            registrado_por_id=request.user.id,
        )

        # Success message
        messages.success(
            request,
            f"Asistencia registrada para {paralelo.asignatura.nombre} "
            f"- {paralelo.nombre} ({fecha.strftime('%d/%m/%Y')}). "
            f"{resultado['registros_creados']} registros guardados.",
        )

        # Alert warnings for at-risk students
        for alerta in resultado["alertas"]:
            from apps.usuarios.infrastructure.models import Usuario

            estudiante = Usuario.objects.get(pk=alerta["estudiante_id"])
            messages.warning(
                request,
                f"ALERTA: {estudiante.get_full_name()} tiene "
                f"{alerta['porcentaje_inasistencia']}% de inasistencia "
                f"en {paralelo.asignatura.nombre}.",
            )

        return redirect(
            "asistencia:registrar_asistencia", paralelo_id=paralelo_id
        )


class HistorialAsistenciaView(MultiRolRequeridoMixin, View):
    """View attendance history for a paralelo."""

    roles_permitidos = ["docente", "inspector"]
    template_name = "asistencia/historial_asistencia.html"

    def get(self, request, paralelo_id):
        paralelo = get_object_or_404(
            Paralelo.objects.select_related("asignatura", "periodo", "docente"),
            pk=paralelo_id,
        )

        # Docente can only access their own paralelos
        if (
            request.user.rol == "docente"
            and paralelo.docente_id != request.user.id
        ):
            messages.error(request, "No tiene permiso para este paralelo.")
            return redirect("asistencia:seleccionar_paralelo")

        service = RegistroAsistenciaAppService()
        historial = service.obtener_historial(paralelo_id)

        return render(
            request,
            self.template_name,
            {
                "paralelo": paralelo,
                "historial": historial,
            },
        )


class DashboardAsistenciaEstudianteView(RolRequeridoMixin, View):
    """Student attendance dashboard — shows per-subject cards and general risk."""

    rol_requerido = "estudiante"
    template_name = "asistencia/mi_asistencia.html"

    def get(self, request):
        service = RegistroAsistenciaAppService()
        datos = service.obtener_datos_asistencia_estudiante(request.user.id)

        return render(
            request,
            self.template_name,
            {
                "asignaturas": datos["asignaturas"],
                "inasistencia_general": datos["inasistencia_general"],
                "riesgo_general": datos["riesgo_general"],
            },
        )
