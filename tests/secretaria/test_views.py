"""Tests for Secretaría views (user and enrollment management)."""

import pytest
from django.urls import reverse

from apps.academico.infrastructure.models import Matricula
from tests.factories import (
    DocenteFactory,
    EstudianteFactory,
    MatriculaFactory,
    ParaleloFactory,
    PeriodoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db


def _saved(user):
    """Persist password hash so force_login session survives request cycle."""
    user.save()
    return user


def make_secretaria():
    user = UsuarioFactory(rol="secretaria")
    user.save()
    return user


# =============================================================================
# Usuario Views
# =============================================================================


class TestUsuarioListView:
    """Tests for UsuarioListView."""

    def setup_method(self):
        self.url = reverse("secretaria:usuario_list")

    def test_anonymous_redirect(self, client):
        """Unauthenticated user is redirected to login."""
        response = client.get(self.url)
        assert response.status_code == 302
        assert "/login/" in response.url

    def test_estudiante_forbidden(self, client):
        """Student user gets 403."""
        estudiante = _saved(EstudianteFactory())
        client.force_login(estudiante)
        response = client.get(self.url)
        assert response.status_code == 403

    def test_docente_forbidden(self, client):
        """Docente user gets 403."""
        docente = _saved(DocenteFactory())
        client.force_login(docente)
        response = client.get(self.url)
        assert response.status_code == 403

    def test_secretaria_access(self, client):
        """Secretaria can access, status 200."""
        sec = make_secretaria()
        client.force_login(sec)
        response = client.get(self.url)
        assert response.status_code == 200

    def test_search_filter(self, client):
        """GET with ?q= filters results."""
        sec = make_secretaria()
        UsuarioFactory(first_name="Buscable")
        UsuarioFactory(first_name="Otro")

        client.force_login(sec)
        response = client.get(self.url, {"q": "Buscable"})
        assert response.status_code == 200
        usuarios = response.context["usuarios"]
        assert usuarios.count() == 1


class TestUsuarioCreateView:
    """Tests for UsuarioCreateView."""

    def setup_method(self):
        self.url = reverse("secretaria:usuario_create")

    def test_get_shows_form(self, client):
        """Secretaria sees the creation form."""
        sec = make_secretaria()
        client.force_login(sec)
        response = client.get(self.url)
        assert response.status_code == 200
        assert "form" in response.context

    def test_post_creates_user(self, client):
        """Valid POST creates user and redirects to list."""
        sec = make_secretaria()
        client.force_login(sec)

        from apps.usuarios.infrastructure.models import Usuario

        response = client.post(self.url, {
            "email": "newuser@test.com",
            "first_name": "Nuevo",
            "last_name": "Usuario",
            "rol": "estudiante",
            "cedula": "0777777777",
        })
        assert response.status_code == 302
        assert Usuario.objects.filter(email="newuser@test.com").exists()

    def test_post_duplicate_email(self, client):
        """POST with existing email shows form error."""
        sec = make_secretaria()
        UsuarioFactory(email="dup@test.com", username="dup@test.com")

        client.force_login(sec)
        response = client.post(self.url, {
            "email": "dup@test.com",
            "first_name": "Test",
            "last_name": "User",
            "rol": "estudiante",
            "cedula": "0666666666",
        })
        assert response.status_code == 200
        assert "email" in response.context["form"].errors

    def test_post_duplicate_cedula(self, client):
        """POST with existing cedula shows form error."""
        sec = make_secretaria()
        UsuarioFactory(cedula="0555555555")

        client.force_login(sec)
        response = client.post(self.url, {
            "email": "unique@test.com",
            "first_name": "Test",
            "last_name": "User",
            "rol": "estudiante",
            "cedula": "0555555555",
        })
        assert response.status_code == 200
        assert "cedula" in response.context["form"].errors


class TestUsuarioEditView:
    """Tests for UsuarioEditView."""

    def test_get_shows_form(self, client):
        """Secretaria sees the edit form with editing=True."""
        sec = make_secretaria()
        target = UsuarioFactory()
        client.force_login(sec)

        url = reverse("secretaria:usuario_edit", kwargs={"pk": target.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert response.context["editing"] is True

    def test_post_updates_user(self, client):
        """Valid POST updates user fields."""
        sec = make_secretaria()
        target = UsuarioFactory(first_name="Viejo")
        client.force_login(sec)

        url = reverse("secretaria:usuario_edit", kwargs={"pk": target.pk})
        response = client.post(url, {
            "first_name": "Nuevo",
            "last_name": "Apellido",
            "rol": "docente",
            "telefono": "0991234567",
            "direccion": "Calle 123",
        })
        assert response.status_code == 302
        target.refresh_from_db()
        assert target.first_name == "Nuevo"

    def test_non_secretaria_forbidden(self, client):
        """Inspector cannot access edit view."""
        from tests.factories import InspectorFactory

        inspector = _saved(InspectorFactory())
        target = UsuarioFactory()
        client.force_login(inspector)

        url = reverse("secretaria:usuario_edit", kwargs={"pk": target.pk})
        response = client.get(url)
        assert response.status_code == 403


# =============================================================================
# Matrícula Views
# =============================================================================


class TestMatriculaListView:
    """Tests for MatriculaListView."""

    def setup_method(self):
        self.url = reverse("secretaria:matricula_list")

    def test_secretaria_access(self, client):
        """Secretaria can access, status 200."""
        sec = make_secretaria()
        client.force_login(sec)
        response = client.get(self.url)
        assert response.status_code == 200

    def test_non_secretaria_forbidden(self, client):
        """Docente gets 403."""
        docente = _saved(DocenteFactory())
        client.force_login(docente)
        response = client.get(self.url)
        assert response.status_code == 403

    def test_filter_by_estado(self, client):
        """GET with ?estado=activa filters results."""
        sec = make_secretaria()
        MatriculaFactory(estado=Matricula.Estado.ACTIVA)
        MatriculaFactory(estado="retirada")

        client.force_login(sec)
        response = client.get(self.url, {"estado": "activa"})
        assert response.status_code == 200
        assert response.context["matriculas"].count() == 1


class TestMatriculaCreateView:
    """Tests for MatriculaCreateView."""

    def setup_method(self):
        self.url = reverse("secretaria:matricula_create")

    def test_get_shows_form(self, client):
        """GET shows form with estudiantes and paralelos in context."""
        sec = make_secretaria()
        client.force_login(sec)
        response = client.get(self.url)
        assert response.status_code == 200
        assert "estudiantes" in response.context
        assert "paralelos" in response.context

    def test_post_creates_matricula(self, client):
        """Valid POST creates enrollment and redirects."""
        sec = make_secretaria()
        estudiante = EstudianteFactory()
        paralelo = ParaleloFactory()

        client.force_login(sec)
        response = client.post(self.url, {
            "estudiante": estudiante.pk,
            "paralelo": paralelo.pk,
        })
        assert response.status_code == 302
        assert Matricula.objects.filter(
            estudiante=estudiante, paralelo=paralelo
        ).exists()

    def test_post_duplicada(self, client):
        """Duplicate enrollment shows error message."""
        sec = make_secretaria()
        mat = MatriculaFactory()

        client.force_login(sec)
        response = client.post(self.url, {
            "estudiante": mat.estudiante_id,
            "paralelo": mat.paralelo_id,
        })
        assert response.status_code == 200
        # Form should have non-field errors
        assert response.context["form"].non_field_errors()

    def test_post_cupo_excedido(self, client):
        """Full paralelo shows error message."""
        sec = make_secretaria()
        paralelo = ParaleloFactory(capacidad_maxima=1)
        MatriculaFactory(paralelo=paralelo)
        nuevo_est = EstudianteFactory()

        client.force_login(sec)
        response = client.post(self.url, {
            "estudiante": nuevo_est.pk,
            "paralelo": paralelo.pk,
        })
        assert response.status_code == 200
        assert response.context["form"].non_field_errors()


class TestMatriculaCambiarEstadoView:
    """Tests for MatriculaCambiarEstadoView."""

    def test_retirar_matricula(self, client):
        """POST with nuevo_estado=retirada changes state."""
        sec = make_secretaria()
        mat = MatriculaFactory(estado=Matricula.Estado.ACTIVA)

        client.force_login(sec)
        url = reverse("secretaria:matricula_cambiar_estado", kwargs={"pk": mat.pk})
        response = client.post(url, {"nuevo_estado": "retirada"})
        assert response.status_code == 302
        mat.refresh_from_db()
        assert mat.estado == "retirada"

    def test_transicion_invalida(self, client):
        """Invalid transition shows error message."""
        sec = make_secretaria()
        mat = MatriculaFactory(estado=Matricula.Estado.ACTIVA)

        client.force_login(sec)
        url = reverse("secretaria:matricula_cambiar_estado", kwargs={"pk": mat.pk})
        response = client.post(url, {"nuevo_estado": "suspendida"})
        assert response.status_code == 302  # redirects with error message
        mat.refresh_from_db()
        assert mat.estado == "activa"  # state unchanged


class TestMatriculaCambiarParaleloView:
    """Tests for MatriculaCambiarParaleloView."""

    def test_get_shows_form(self, client):
        """GET renders the change paralelo form."""
        sec = make_secretaria()
        mat = MatriculaFactory(estado=Matricula.Estado.ACTIVA)

        client.force_login(sec)
        url = reverse("secretaria:matricula_cambiar_paralelo", kwargs={"pk": mat.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert "matricula" in response.context
        assert "paralelos" in response.context

    def test_change_paralelo_success(self, client):
        """POST with valid paralelo changes enrollment."""
        sec = make_secretaria()
        mat = MatriculaFactory(estado=Matricula.Estado.ACTIVA)
        nuevo = ParaleloFactory(periodo=mat.paralelo.periodo)

        client.force_login(sec)
        url = reverse("secretaria:matricula_cambiar_paralelo", kwargs={"pk": mat.pk})
        response = client.post(url, {"nuevo_paralelo": nuevo.pk})
        assert response.status_code == 302
        mat.refresh_from_db()
        assert mat.paralelo_id == nuevo.pk

    def test_change_to_same_paralelo_fails(self, client):
        """Cannot move to the same paralelo."""
        sec = make_secretaria()
        mat = MatriculaFactory(estado=Matricula.Estado.ACTIVA)

        client.force_login(sec)
        url = reverse("secretaria:matricula_cambiar_paralelo", kwargs={"pk": mat.pk})
        response = client.post(url, {"nuevo_paralelo": mat.paralelo.pk})
        assert response.status_code == 302
        mat.refresh_from_db()
        assert mat.paralelo_id == mat.paralelo_id  # unchanged

    def test_change_paralelo_inactive_matricula_fails(self, client):
        """Cannot change paralelo of a retired enrollment."""
        sec = make_secretaria()
        mat = MatriculaFactory(estado=Matricula.Estado.RETIRADA)
        nuevo = ParaleloFactory(periodo=mat.paralelo.periodo)
        original_paralelo_id = mat.paralelo_id

        client.force_login(sec)
        url = reverse("secretaria:matricula_cambiar_paralelo", kwargs={"pk": mat.pk})
        response = client.post(url, {"nuevo_paralelo": nuevo.pk})
        assert response.status_code == 302
        mat.refresh_from_db()
        assert mat.paralelo_id == original_paralelo_id  # unchanged

    def test_empty_paralelo_redirects_with_error(self, client):
        """POST without selecting paralelo redirects with error."""
        sec = make_secretaria()
        mat = MatriculaFactory(estado=Matricula.Estado.ACTIVA)

        client.force_login(sec)
        url = reverse("secretaria:matricula_cambiar_paralelo", kwargs={"pk": mat.pk})
        response = client.post(url, {"nuevo_paralelo": ""})
        assert response.status_code == 302

    def test_anonymous_redirect(self, client):
        """Unauthenticated user is redirected to login."""
        mat = MatriculaFactory()
        url = reverse("secretaria:matricula_cambiar_paralelo", kwargs={"pk": mat.pk})
        response = client.get(url)
        assert response.status_code == 302
        assert "/login/" in response.url


class TestMatriculaLoteView:
    """Tests for MatriculaLoteView (batch enrollment)."""

    def test_get_shows_form(self, client):
        """GET renders the batch enrollment form."""
        sec = make_secretaria()
        client.force_login(sec)
        url = reverse("secretaria:matricula_create_lote")
        response = client.get(url)
        assert response.status_code == 200
        assert "estudiantes" in response.context
        assert "periodos" in response.context

    def test_post_batch_success(self, client):
        """POST with student + paralelos creates enrollments."""
        sec = make_secretaria()
        est = _saved(EstudianteFactory())
        periodo = PeriodoFactory(activo=True)
        p1 = ParaleloFactory(periodo=periodo)
        p2 = ParaleloFactory(periodo=periodo)

        client.force_login(sec)
        url = reverse("secretaria:matricula_create_lote")
        response = client.post(url, {
            "estudiante": est.pk,
            "paralelos": [p1.pk, p2.pk],
        })
        assert response.status_code == 302
        from apps.academico.infrastructure.models import Matricula as Mat
        assert Mat.objects.filter(estudiante=est).count() == 2

    def test_post_no_estudiante_shows_error(self, client):
        """POST without student shows error."""
        sec = make_secretaria()
        client.force_login(sec)
        url = reverse("secretaria:matricula_create_lote")
        response = client.post(url, {"estudiante": "", "paralelos": []})
        assert response.status_code == 200  # re-renders form

    def test_post_no_paralelos_shows_error(self, client):
        """POST without paralelos shows error."""
        sec = make_secretaria()
        est = _saved(EstudianteFactory())
        client.force_login(sec)
        url = reverse("secretaria:matricula_create_lote")
        response = client.post(url, {"estudiante": est.pk})
        assert response.status_code == 200  # re-renders form

    def test_anonymous_redirect(self, client):
        """Unauthenticated user is redirected to login."""
        url = reverse("secretaria:matricula_create_lote")
        response = client.get(url)
        assert response.status_code == 302
        assert "/login/" in response.url


class TestParalelosPorPeriodoView:
    """Tests for ParalelosPorPeriodoView JSON endpoint."""

    def test_returns_paralelos_json(self, client):
        """GET with periodo_id returns paralelos as JSON."""
        sec = make_secretaria()
        periodo = PeriodoFactory(activo=True)
        ParaleloFactory(periodo=periodo)

        client.force_login(sec)
        url = reverse("secretaria:paralelos_por_periodo")
        response = client.get(url, {"periodo_id": periodo.pk})
        assert response.status_code == 200
        data = response.json()
        assert len(data["paralelos"]) == 1

    def test_empty_without_periodo(self, client):
        """GET without periodo_id returns empty list."""
        sec = make_secretaria()
        client.force_login(sec)
        url = reverse("secretaria:paralelos_por_periodo")
        response = client.get(url)
        assert response.status_code == 200
        assert response.json()["paralelos"] == []
