"""Tests for Secretaría services (user and enrollment management)."""

from unittest.mock import patch

import pytest

from apps.academico.domain.exceptions import (
    CupoExcedidoError,
    EstadoMatriculaInvalidoError,
    MatriculaDuplicadaError,
    PeriodoInactivoError,
)
from apps.academico.infrastructure.models import Matricula
from apps.secretaria.services import GestionMatriculasService, GestionUsuariosService
from tests.factories import (
    DocenteFactory,
    EstudianteFactory,
    MatriculaFactory,
    ParaleloFactory,
    PeriodoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db


# =============================================================================
# GestionUsuariosService
# =============================================================================


class TestGestionUsuariosService:
    """Tests for user management service."""

    def setup_method(self):
        self.service = GestionUsuariosService()

    @patch("apps.secretaria.services.send_credenciales_email")
    def test_crear_usuario(self, mock_email):
        """Service creates user with temp password and debe_cambiar_password=True."""
        mock_email.return_value = None

        usuario, temp_password, email_sent = self.service.crear_usuario(
            email="nuevo@test.com",
            first_name="Ana",
            last_name="Torres",
            rol="estudiante",
            cedula="0999999999",
        )

        assert usuario.pk is not None
        assert usuario.debe_cambiar_password is True
        assert usuario.username == "nuevo@test.com"
        assert usuario.check_password(temp_password)
        assert email_sent is True

    @patch("apps.secretaria.services.send_credenciales_email")
    def test_crear_usuario_email_duplicado(self, mock_email):
        """Creating user with existing email raises form-level validation."""
        UsuarioFactory(email="dup@test.com", username="dup@test.com")

        from apps.secretaria.forms import CrearUsuarioForm

        form = CrearUsuarioForm(data={
            "email": "dup@test.com",
            "first_name": "Test",
            "last_name": "User",
            "rol": "estudiante",
            "cedula": "0888888888",
        })
        assert not form.is_valid()
        assert "email" in form.errors

    def test_listar_usuarios_sin_filtros(self):
        """Returns all users when no filters applied."""
        UsuarioFactory()
        UsuarioFactory()
        UsuarioFactory()

        result = self.service.listar_usuarios()
        assert result.count() == 3

    def test_listar_usuarios_con_search(self):
        """Search by name filters correctly."""
        UsuarioFactory(first_name="Marcos")
        UsuarioFactory(first_name="Pedro")

        result = self.service.listar_usuarios(search="Marcos")
        assert result.count() == 1
        assert result.first().first_name == "Marcos"

    def test_listar_usuarios_con_rol_filter(self):
        """Filter by rol works."""
        EstudianteFactory()
        DocenteFactory()
        DocenteFactory()

        result = self.service.listar_usuarios(rol_filter="docente")
        assert result.count() == 2

    def test_editar_usuario(self):
        """Updates fields correctly."""
        user = UsuarioFactory(first_name="Viejo")
        updated = self.service.editar_usuario(user.pk, first_name="Nuevo")
        assert updated.first_name == "Nuevo"

    def test_toggle_activo(self):
        """Toggles is_active."""
        user = UsuarioFactory(is_active=True)
        toggled = self.service.toggle_activo(user.pk)
        assert toggled.is_active is False

        toggled2 = self.service.toggle_activo(user.pk)
        assert toggled2.is_active is True


# =============================================================================
# GestionMatriculasService
# =============================================================================


class TestGestionMatriculasService:
    """Tests for enrollment management service."""

    def setup_method(self):
        self.service = GestionMatriculasService()

    def test_crear_matricula(self):
        """Creates enrollment successfully."""
        estudiante = EstudianteFactory()
        paralelo = ParaleloFactory()
        secretaria = UsuarioFactory(rol="secretaria")

        matricula = self.service.crear_matricula(
            estudiante_id=estudiante.pk,
            paralelo_id=paralelo.pk,
            registrado_por_id=secretaria.pk,
        )

        assert matricula.pk is not None
        assert matricula.estado == Matricula.Estado.ACTIVA
        assert matricula.estudiante == estudiante

    def test_crear_matricula_duplicada(self):
        """Duplicate enrollment raises MatriculaDuplicadaError."""
        mat = MatriculaFactory()

        with pytest.raises(MatriculaDuplicadaError):
            self.service.crear_matricula(
                estudiante_id=mat.estudiante_id,
                paralelo_id=mat.paralelo_id,
                registrado_por_id=mat.matriculado_por_id,
            )

    def test_crear_matricula_cupo_excedido(self):
        """Full paralelo raises CupoExcedidoError."""
        paralelo = ParaleloFactory(capacidad_maxima=1)
        MatriculaFactory(paralelo=paralelo)
        nuevo_est = EstudianteFactory()
        secretaria = UsuarioFactory(rol="secretaria")

        with pytest.raises(CupoExcedidoError):
            self.service.crear_matricula(
                estudiante_id=nuevo_est.pk,
                paralelo_id=paralelo.pk,
                registrado_por_id=secretaria.pk,
            )

    def test_crear_matricula_periodo_inactivo(self):
        """Inactive period raises PeriodoInactivoError."""
        periodo_inactivo = PeriodoFactory(activo=False)
        paralelo = ParaleloFactory(periodo=periodo_inactivo)
        estudiante = EstudianteFactory()
        secretaria = UsuarioFactory(rol="secretaria")

        with pytest.raises(PeriodoInactivoError):
            self.service.crear_matricula(
                estudiante_id=estudiante.pk,
                paralelo_id=paralelo.pk,
                registrado_por_id=secretaria.pk,
            )

    def test_cambiar_estado_retirar(self):
        """Active → retired works for secretaria."""
        mat = MatriculaFactory(estado=Matricula.Estado.ACTIVA)

        result = self.service.cambiar_estado(mat.pk, "retirada", "secretaria")
        assert result.estado == "retirada"

    def test_cambiar_estado_transicion_invalida(self):
        """Invalid transition raises EstadoMatriculaInvalidoError."""
        mat = MatriculaFactory(estado=Matricula.Estado.ACTIVA)

        with pytest.raises(EstadoMatriculaInvalidoError):
            self.service.cambiar_estado(mat.pk, "suspendida", "secretaria")

    def test_listar_matriculas_con_filtros(self):
        """Search and filters work."""
        mat1 = MatriculaFactory()
        MatriculaFactory()

        # Filter by estado
        result = self.service.listar_matriculas(estado_filter="activa")
        assert result.count() == 2

        # Search by student name
        result = self.service.listar_matriculas(
            search=mat1.estudiante.first_name
        )
        assert result.count() >= 1
