"""
Views for the Secretaría bounded context.
CRUD views for user management.
All operations restricted to Secretaría role via RolRequeridoMixin.
"""

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View

from apps.usuarios.infrastructure.models import Usuario
from apps.usuarios.presentation.permissions import RolRequeridoMixin

from apps.academico.domain.exceptions import (
    CupoExcedidoError,
    EstadoMatriculaInvalidoError,
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

        return render(request, self.template_name, {
            "matriculas": matriculas,
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
            "paralelos": service.obtener_paralelos_activos(),
        })

    def post(self, request):
        service = GestionMatriculasService()
        form = CrearMatriculaForm(request.POST)

        if not form.is_valid():
            return render(request, self.template_name, {
                "form": form,
                "estudiantes": service.obtener_estudiantes_disponibles(),
                "paralelos": service.obtener_paralelos_activos(),
            })

        try:
            service.crear_matricula(
                estudiante_id=form.cleaned_data["estudiante"],
                paralelo_id=form.cleaned_data["paralelo"],
                registrado_por_id=request.user.pk,
            )
            messages.success(request, "Matrícula registrada exitosamente.")
            return redirect("secretaria:matricula_list")
        except (CupoExcedidoError, MatriculaDuplicadaError, PeriodoInactivoError) as e:
            form.add_error(None, str(e))
            return render(request, self.template_name, {
                "form": form,
                "estudiantes": service.obtener_estudiantes_disponibles(),
                "paralelos": service.obtener_paralelos_activos(),
            })


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
