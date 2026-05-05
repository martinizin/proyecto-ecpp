"""
Views for the Secretaría bounded context.
CRUD views for user management.
All operations restricted to Secretaría role via RolRequeridoMixin.
"""

from collections import OrderedDict

from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.crypto import get_random_string
from django.views import View

from apps.usuarios.infrastructure.models import Usuario
from apps.usuarios.presentation.permissions import RolRequeridoMixin

from apps.academico.domain.exceptions import (
    CupoExcedidoError,
    EstadoMatriculaInvalidoError,
    MatriculaAsignaturaDuplicadaError,
    MatriculaDuplicadaError,
    PeriodoInactivoError,
)
from apps.academico.infrastructure.models import Matricula

from .forms import CrearMatriculaForm, CrearUsuarioForm, EditarUsuarioForm
from .services import GestionMatriculasService, GestionUsuariosService


# =============================================================================
# Usuario Views
# =============================================================================


class UsuarioListView(RolRequeridoMixin, View):
    """List all users with search and role filter — Secretaría only."""

    rol_requerido = "secretaria"
    template_name = "secretaria/usuario_list.html"

    def get(self, request):
        service = GestionUsuariosService()
        search_query = request.GET.get("q", "").strip()
        rol_filter = request.GET.get("rol", "").strip()

        usuarios = service.listar_usuarios(
            search=search_query or None,
            rol_filter=rol_filter or None,
        )

        return render(request, self.template_name, {
            "usuarios": usuarios,
            "search_query": search_query,
            "rol_filter": rol_filter,
            "roles": Usuario.Rol.choices,
        })


class UsuarioCreateView(RolRequeridoMixin, View):
    """Create a new user — Secretaría only."""

    rol_requerido = "secretaria"
    template_name = "secretaria/usuario_form.html"

    def get(self, request):
        form = CrearUsuarioForm()
        return render(request, self.template_name, {
            "form": form,
            "editing": False,
        })

    def post(self, request):
        form = CrearUsuarioForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {
                "form": form,
                "editing": False,
            })

        service = GestionUsuariosService()
        usuario, temp_password, email_sent = service.crear_usuario(
            email=form.cleaned_data["email"],
            first_name=form.cleaned_data["first_name"],
            last_name=form.cleaned_data["last_name"],
            rol=form.cleaned_data["rol"],
            cedula=form.cleaned_data["cedula"],
            telefono=form.cleaned_data.get("telefono", ""),
        )

        if email_sent:
            messages.success(
                request,
                f"Usuario creado exitosamente. Las credenciales fueron enviadas a {usuario.email}.",
            )
        else:
            messages.warning(
                request,
                f"Usuario creado, pero no se pudo enviar el correo. "
                f"Contraseña temporal: {temp_password}",
            )

        return redirect("secretaria:usuario_list")


class UsuarioEditView(RolRequeridoMixin, View):
    """Edit an existing user — Secretaría only."""

    rol_requerido = "secretaria"
    template_name = "secretaria/usuario_form.html"

    def get(self, request, pk):
        service = GestionUsuariosService()
        usuario = service.obtener_usuario(pk)
        form = EditarUsuarioForm(initial={
            "first_name": usuario.first_name,
            "last_name": usuario.last_name,
            "rol": usuario.rol,
            "telefono": usuario.telefono,
            "direccion": usuario.direccion,
        })
        return render(request, self.template_name, {
            "form": form,
            "editing": True,
            "usuario": usuario,
        })

    def post(self, request, pk):
        service = GestionUsuariosService()
        usuario = service.obtener_usuario(pk)
        form = EditarUsuarioForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {
                "form": form,
                "editing": True,
                "usuario": usuario,
            })

        service.editar_usuario(
            usuario_id=pk,
            first_name=form.cleaned_data["first_name"],
            last_name=form.cleaned_data["last_name"],
            rol=form.cleaned_data["rol"],
            telefono=form.cleaned_data["telefono"],
            direccion=form.cleaned_data["direccion"],
        )

        messages.success(request, "Usuario actualizado exitosamente.")
        return redirect("secretaria:usuario_list")


class UsuarioToggleActivoView(RolRequeridoMixin, View):
    """Toggle user active status — Secretaría only."""

    rol_requerido = "secretaria"

    def post(self, request, pk):
        service = GestionUsuariosService()
        usuario = service.toggle_activo(pk)

        estado = "activado" if usuario.is_active else "desactivado"
        messages.success(
            request,
            f"El usuario {usuario.get_full_name()} ha sido {estado}.",
        )
        return redirect("secretaria:usuario_list")


class ResetearPasswordEstudianteView(RolRequeridoMixin, View):
    """Reset a student's password to a temporary one — Secretaría only."""

    rol_requerido = "secretaria"
    template_name = "secretaria/resetear_password.html"

    ALLOWED_CHARS = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"

    def get(self, request, pk):
        estudiante = get_object_or_404(Usuario, pk=pk)
        if estudiante.rol != "estudiante":
            return HttpResponseForbidden("Solo se puede resetear la contraseña de estudiantes.")
        return render(request, self.template_name, {"estudiante": estudiante})

    def post(self, request, pk):
        estudiante = get_object_or_404(Usuario, pk=pk)
        if estudiante.rol != "estudiante":
            return HttpResponseForbidden("Solo se puede resetear la contraseña de estudiantes.")

        temp_password = get_random_string(length=8, allowed_chars=self.ALLOWED_CHARS)
        estudiante.set_password(temp_password)
        estudiante.debe_cambiar_password = True
        estudiante.save()

        messages.success(
            request,
            f"Contraseña temporal generada: {temp_password}. "
            f"El estudiante deberá cambiarla en su próximo inicio de sesión.",
        )
        return redirect("secretaria:resetear_password_estudiante", pk=pk)


# =============================================================================
# Matrícula Views
# =============================================================================


class MatriculaListView(RolRequeridoMixin, View):
    """List all enrollments with filters — Secretaría only."""

    rol_requerido = "secretaria"
    template_name = "secretaria/matricula_list.html"

    def get(self, request):
        service = GestionMatriculasService()
        search_query = request.GET.get("q", "").strip()
        paralelo_filter = request.GET.get("paralelo", "").strip()
        estado_filter = request.GET.get("estado", "").strip()

        matriculas = service.listar_matriculas(
            paralelo_filter=paralelo_filter or None,
            estado_filter=estado_filter or None,
            search=search_query or None,
        )

        # Group matriculas: {estudiante: {tipo_licencia: [matriculas]}}
        grouped = OrderedDict()
        for m in matriculas:
            est = m.estudiante
            tl = m.paralelo.tipo_licencia
            if est.pk not in grouped:
                grouped[est.pk] = {
                    "estudiante": est,
                    "licencias": OrderedDict(),
                }
            tl_key = tl.pk
            if tl_key not in grouped[est.pk]["licencias"]:
                grouped[est.pk]["licencias"][tl_key] = {
                    "tipo_licencia": tl,
                    "periodo": m.paralelo.periodo,
                    "matriculas": [],
                }
            grouped[est.pk]["licencias"][tl_key]["matriculas"].append(m)

        return render(request, self.template_name, {
            "grouped": grouped,
            "matriculas_count": len(matriculas),
            "search_query": search_query,
            "paralelo_filter": paralelo_filter,
            "estado_filter": estado_filter,
            "paralelos": service.obtener_paralelos_activos(),
            "estados": Matricula.Estado.choices,
        })


class MatriculaCreateView(RolRequeridoMixin, View):
    """Create a new enrollment — Secretaría only."""

    rol_requerido = "secretaria"
    template_name = "secretaria/matricula_form.html"

    def get(self, request):
        service = GestionMatriculasService()
        form = CrearMatriculaForm()
        return render(request, self.template_name, {
            "form": form,
            "estudiantes": service.obtener_estudiantes_disponibles(),
            "periodos": service.obtener_periodos_activos(),
        })

    def post(self, request):
        service = GestionMatriculasService()
        form = CrearMatriculaForm(request.POST)

        if not form.is_valid():
            return render(request, self.template_name, {
                "form": form,
                "estudiantes": service.obtener_estudiantes_disponibles(),
                "periodos": service.obtener_periodos_activos(),
            })

        try:
            service.crear_matricula(
                estudiante_id=form.cleaned_data["estudiante"],
                paralelo_id=form.cleaned_data["paralelo"],
                registrado_por_id=request.user.pk,
            )
            messages.success(request, "Matrícula registrada exitosamente.")
            return redirect("secretaria:matricula_list")
        except (CupoExcedidoError, MatriculaDuplicadaError, MatriculaAsignaturaDuplicadaError, PeriodoInactivoError) as e:
            form.add_error(None, str(e))
            return render(request, self.template_name, {
                "form": form,
                "estudiantes": service.obtener_estudiantes_disponibles(),
                "periodos": service.obtener_periodos_activos(),
            })


class ParalelosPorPeriodoView(RolRequeridoMixin, View):
    """JSON endpoint: return paralelos for a given periodo."""

    rol_requerido = "secretaria"

    def get(self, request):
        periodo_id = request.GET.get("periodo_id", "").strip()
        if not periodo_id:
            return JsonResponse({"paralelos": []})

        service = GestionMatriculasService()
        paralelos = service.obtener_paralelos_por_periodo(int(periodo_id))
        data = [
            {
                "id": p.id,
                "asignatura_codigo": p.asignatura.codigo,
                "asignatura_nombre": p.asignatura.nombre,
                "nombre": p.nombre,
                "docente": p.docente.get_full_name() if p.docente else "",
                "capacidad_maxima": p.capacidad_maxima,
                "tipo_licencia_codigo": p.tipo_licencia.codigo if p.tipo_licencia else "",
                "tipo_licencia_nombre": p.tipo_licencia.nombre if p.tipo_licencia else "",
            }
            for p in paralelos
        ]
        return JsonResponse({"paralelos": data})


class MatriculaLoteView(RolRequeridoMixin, View):
    """Batch enrollment: select student + period, then pick paralelos."""

    rol_requerido = "secretaria"
    template_name = "secretaria/matricula_form_lote.html"

    def get(self, request):
        service = GestionMatriculasService()
        return render(request, self.template_name, {
            "estudiantes": service.obtener_estudiantes_disponibles(),
            "periodos": service.obtener_periodos_activos(),
        })

    def post(self, request):
        service = GestionMatriculasService()
        estudiante_id = request.POST.get("estudiante", "").strip()
        paralelo_ids = request.POST.getlist("paralelos")

        if not estudiante_id:
            messages.error(request, "Debe seleccionar un estudiante.")
            return render(request, self.template_name, {
                "estudiantes": service.obtener_estudiantes_disponibles(),
                "periodos": service.obtener_periodos_activos(),
            })

        if not paralelo_ids:
            messages.error(request, "Debe seleccionar al menos un paralelo.")
            return render(request, self.template_name, {
                "estudiantes": service.obtener_estudiantes_disponibles(),
                "periodos": service.obtener_periodos_activos(),
            })

        creados, omitidos = service.matricular_en_lote(
            estudiante_id=int(estudiante_id),
            paralelo_ids=[int(pid) for pid in paralelo_ids],
            registrado_por_id=request.user.pk,
        )

        if creados:
            messages.success(request, f"Se crearon {creados} matrícula(s) exitosamente.")
        if omitidos:
            messages.warning(
                request,
                f"Se omitieron {len(omitidos)} paralelo(s): {'; '.join(omitidos)}",
            )
        if not creados and not omitidos:
            messages.info(request, "No se realizaron cambios.")

        return redirect("secretaria:matricula_list")


class MatriculaCambiarParaleloView(RolRequeridoMixin, View):
    """Change enrollment paralelo — Secretaría only."""

    rol_requerido = "secretaria"
    template_name = "secretaria/matricula_cambiar_paralelo.html"

    def get(self, request, pk):
        service = GestionMatriculasService()
        matricula = service.obtener_matricula(pk)
        paralelos = service.obtener_paralelos_activos().exclude(pk=matricula.paralelo_id)
        return render(request, self.template_name, {
            "matricula": matricula,
            "paralelos": paralelos,
        })

    def post(self, request, pk):
        service = GestionMatriculasService()
        nuevo_paralelo_id = request.POST.get("nuevo_paralelo", "").strip()

        if not nuevo_paralelo_id:
            messages.error(request, "Debe seleccionar un paralelo.")
            return redirect("secretaria:matricula_cambiar_paralelo", pk=pk)

        try:
            service.cambiar_paralelo(pk, int(nuevo_paralelo_id))
            messages.success(request, "Paralelo actualizado exitosamente.")
        except (MatriculaDuplicadaError, CupoExcedidoError, EstadoMatriculaInvalidoError) as e:
            messages.error(request, str(e))

        return redirect("secretaria:matricula_list")


class MatriculaCambiarEstadoView(RolRequeridoMixin, View):
    """Change enrollment state — Secretaría only."""

    rol_requerido = "secretaria"

    def post(self, request, pk):
        service = GestionMatriculasService()
        nuevo_estado = request.POST.get("nuevo_estado", "").strip()

        try:
            service.cambiar_estado(pk, nuevo_estado, "secretaria")
            messages.success(request, "Estado de matrícula actualizado exitosamente.")
        except (EstadoMatriculaInvalidoError, CupoExcedidoError) as e:
            messages.error(request, str(e))

        return redirect("secretaria:matricula_list")
