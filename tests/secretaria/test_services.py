"""Tests for Secretaría services (user and enrollment management)."""

from unittest.mock import patch

import pytest

from apps.academico.domain.exceptions import (
    CupoExcedidoError,
    EstadoMatriculaInvalidoError,
    MatriculaAsignaturaDuplicadaError,
    MatriculaDuplicadaError,
    PeriodoInactivoError,
)
from apps.academico.infrastructure.models import Matricula
from apps.secretaria.services import GestionMatriculasService, GestionUsuariosService
from tests.factories import (
    AsignaturaFactory,
    CalificacionFactory,
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

        usuario, temp_password = self.service.crear_usuario(
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

    @patch("apps.secretaria.services.send_credenciales_email")
    def test_crear_usuario_email_duplicado(self, mock_email):
        """Creating user with existing email raises form-level validation."""
        UsuarioFactory(email="dup@test.com", username="dup@test.com")

        from apps.secretaria.forms import CrearUsuarioForm

        form = CrearUsuarioForm(
            data={
                "email": "dup@test.com",
                "first_name": "Test",
                "last_name": "User",
                "rol": "estudiante",
                "cedula": "0888888888",
            }
        )
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

    def test_toggle_activo(self):
        """toggle_activo flips is_active both ways."""
        user = UsuarioFactory(is_active=True)

        toggled = self.service.toggle_activo(user.pk)
        assert toggled.is_active is False

        toggled2 = self.service.toggle_activo(user.pk)
        assert toggled2.is_active is True

    @patch("apps.secretaria.services.send_credenciales_email")
    def test_crear_usuario_rollback_en_fallo_email(self, mock_email):
        """RED → GREEN: SMTP failure must roll back the user creation.

        Acceptance (R8 — qa-usuarios-registro-inmutable): if the credentials
        email cannot be sent, the user MUST NOT exist in the database. Half-
        created accounts are worse than no account at all because the
        secretaría has no way to deliver the temp password and the email is
        burned (unique constraint).

        Current behavior (before this task): the service swallows the
        exception and returns `email_sent=False`, leaving an orphan account.
        That contract was wrong — this test pins the correct one.
        """
        from apps.usuarios.infrastructure.models import Usuario

        mock_email.side_effect = Exception("SMTP unreachable")

        with pytest.raises(Exception, match="SMTP unreachable"):
            self.service.crear_usuario(
                email="ghost@test.com",
                first_name="Ghost",
                last_name="Account",
                rol="estudiante",
                cedula="0926687856",
            )

        # The Usuario row must NOT have been persisted.
        assert not Usuario.objects.filter(email="ghost@test.com").exists()


# =============================================================================
# eliminar_usuario — hard delete with FK-dependency guard
# (SDD change qa-usuarios-registro-inmutable, Phase 3)
# =============================================================================


class TestEliminarUsuario:
    """Acceptance for `GestionUsuariosService.eliminar_usuario`:

    - Happy path: user with no FK dependencies is removed from the table.
    - With dependencies: raises `UsuarioConDependenciasError` carrying a dict
      of FK counts (covered by Task 3.2, not this RED slice).
    - Wrapped in `transaction.atomic` with `select_for_update` (covered by
      Task 3.4 GREEN; this RED slice only drives the method into existence).
    """

    def setup_method(self):
        self.service = GestionUsuariosService()

    def test_eliminar_usuario_sin_dependencias_borra(self):
        """RED → GREEN: deleting a user without FK refs removes the row."""
        from apps.usuarios.infrastructure.models import Usuario

        user = UsuarioFactory()
        user_id = user.pk

        self.service.eliminar_usuario(user_id)

        assert not Usuario.objects.filter(pk=user_id).exists()

    def test_eliminar_usuario_con_matriculas_raises_y_no_borra(self):
        """RED → GREEN: user with matrículas must raise + NOT be deleted.

        Canonical FK-guard case: matrículas are the most critical dependency
        because losing them silently (CASCADE) would destroy academic history.
        """
        from apps.usuarios.domain.exceptions import UsuarioConDependenciasError
        from apps.usuarios.infrastructure.models import Usuario

        estudiante = EstudianteFactory()
        MatriculaFactory(estudiante=estudiante)
        MatriculaFactory(estudiante=estudiante)
        MatriculaFactory(estudiante=estudiante)
        user_id = estudiante.pk

        with pytest.raises(UsuarioConDependenciasError) as excinfo:
            self.service.eliminar_usuario(user_id)

        assert excinfo.value.dependencias.get("matriculas") == 3
        # Row must survive — the guard runs BEFORE delete.
        assert Usuario.objects.filter(pk=user_id).exists()

    def test_eliminar_usuario_con_calificaciones_raises(self):
        """Triangulation: a different CASCADE FK (calificaciones) also blocks."""
        from apps.usuarios.domain.exceptions import UsuarioConDependenciasError
        from apps.usuarios.infrastructure.models import Usuario

        estudiante = EstudianteFactory()
        CalificacionFactory(estudiante=estudiante)
        user_id = estudiante.pk

        with pytest.raises(UsuarioConDependenciasError) as excinfo:
            self.service.eliminar_usuario(user_id)

        assert excinfo.value.dependencias.get("calificaciones") == 1
        assert Usuario.objects.filter(pk=user_id).exists()

    def test_eliminar_usuario_reporta_todas_las_dependencias(self):
        """Triangulation: the dict must enumerate EVERY CASCADE source,
        not just the first one found. The secretaría needs the full picture
        before deciding how to proceed.
        """
        from apps.usuarios.domain.exceptions import UsuarioConDependenciasError

        estudiante = EstudianteFactory()
        MatriculaFactory(estudiante=estudiante)
        MatriculaFactory(estudiante=estudiante)
        CalificacionFactory(estudiante=estudiante)

        with pytest.raises(UsuarioConDependenciasError) as excinfo:
            self.service.eliminar_usuario(estudiante.pk)

        deps = excinfo.value.dependencias
        assert deps.get("matriculas") == 2
        assert deps.get("calificaciones") == 1

    def test_eliminar_usuario_ignora_dependencias_set_null(self):
        """Triangulation: SET_NULL relations must NOT block deletion.

        E.g. `Matricula.matriculado_por` is SET_NULL — when a secretaría
        registered enrollments and then leaves, her account must be removable
        without dragging matrículas with her. Only CASCADE relations block.
        """
        from apps.usuarios.infrastructure.models import Usuario

        secretaria = UsuarioFactory(rol="secretaria")
        # MatriculaFactory's `matriculado_por` defaults to a different user.
        # We attach our secretaria explicitly:
        MatriculaFactory(matriculado_por=secretaria)
        user_id = secretaria.pk

        self.service.eliminar_usuario(user_id)

        assert not Usuario.objects.filter(pk=user_id).exists()

    def test_eliminar_usuario_usa_select_for_update(self):
        """The SELECT that fetches the user must carry FOR UPDATE (row lock).

        We capture the raw SQL executed during `eliminar_usuario` and assert
        that at least one query contains 'FOR UPDATE'. This verifies the lock
        is actually requested from the database (PG16 — no SQLite fallback).
        """
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        user = UsuarioFactory()
        user_id = user.pk

        with CaptureQueriesContext(connection) as ctx:
            self.service.eliminar_usuario(user_id)

        sqls = [q["sql"] for q in ctx.captured_queries]
        assert any("FOR UPDATE" in sql.upper() for sql in sqls), (
            f"No SELECT FOR UPDATE found in queries:\n" + "\n".join(sqls)
        )


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
        result = self.service.listar_matriculas(search=mat1.estudiante.first_name)
        assert result.count() >= 1

    def test_cambiar_paralelo_success(self):
        """Change paralelo of an active enrollment."""
        mat = MatriculaFactory(estado=Matricula.Estado.ACTIVA)
        nuevo = ParaleloFactory(periodo=mat.paralelo.periodo)

        result = self.service.cambiar_paralelo(mat.pk, nuevo.pk)
        assert result.paralelo_id == nuevo.pk

    def test_cambiar_paralelo_inactive_raises(self):
        """Cannot change paralelo of a retired enrollment."""
        mat = MatriculaFactory(estado=Matricula.Estado.RETIRADA)
        nuevo = ParaleloFactory(periodo=mat.paralelo.periodo)

        with pytest.raises(EstadoMatriculaInvalidoError):
            self.service.cambiar_paralelo(mat.pk, nuevo.pk)

    def test_cambiar_paralelo_same_raises(self):
        """Cannot move to the same paralelo."""
        mat = MatriculaFactory(estado=Matricula.Estado.ACTIVA)

        with pytest.raises(MatriculaDuplicadaError):
            self.service.cambiar_paralelo(mat.pk, mat.paralelo.pk)

    def test_cambiar_paralelo_duplicate_raises(self):
        """Cannot move if student already enrolled in target paralelo."""
        est = EstudianteFactory()
        est.save()
        mat = MatriculaFactory(estudiante=est, estado=Matricula.Estado.ACTIVA)
        otro_paralelo = ParaleloFactory(periodo=mat.paralelo.periodo)
        # Create existing enrollment in target
        MatriculaFactory(estudiante=est, paralelo=otro_paralelo)

        with pytest.raises(MatriculaDuplicadaError):
            self.service.cambiar_paralelo(mat.pk, otro_paralelo.pk)

    def test_cambiar_paralelo_full_capacity_raises(self):
        """Cannot move if target paralelo is at max capacity."""
        mat = MatriculaFactory(estado=Matricula.Estado.ACTIVA)
        nuevo = ParaleloFactory(periodo=mat.paralelo.periodo, capacidad_maxima=1)
        # Fill the target paralelo
        MatriculaFactory(paralelo=nuevo, estado=Matricula.Estado.ACTIVA)

        with pytest.raises(CupoExcedidoError):
            self.service.cambiar_paralelo(mat.pk, nuevo.pk)

    def test_matricular_en_lote_success(self):
        """Batch enrollment creates multiple matriculas."""
        est = EstudianteFactory()
        est.save()
        periodo = PeriodoFactory(activo=True)
        p1 = ParaleloFactory(periodo=periodo)
        p2 = ParaleloFactory(periodo=periodo)

        creados, omitidos = self.service.matricular_en_lote(
            estudiante_id=est.pk,
            paralelo_ids=[p1.pk, p2.pk],
            registrado_por_id=est.pk,
        )
        assert creados == 2
        assert len(omitidos) == 0

    def test_matricular_en_lote_skips_duplicates(self):
        """Batch enrollment skips paralelos where student is already enrolled."""
        est = EstudianteFactory()
        est.save()
        periodo = PeriodoFactory(activo=True)
        p1 = ParaleloFactory(periodo=periodo)
        p2 = ParaleloFactory(periodo=periodo)
        MatriculaFactory(estudiante=est, paralelo=p1)

        creados, omitidos = self.service.matricular_en_lote(
            estudiante_id=est.pk,
            paralelo_ids=[p1.pk, p2.pk],
            registrado_por_id=est.pk,
        )
        assert creados == 1
        assert len(omitidos) == 1
        assert "ya matriculado" in omitidos[0]

    def test_matricular_en_lote_skips_full_capacity(self):
        """Batch enrollment skips paralelos at max capacity."""
        est = EstudianteFactory()
        est.save()
        periodo = PeriodoFactory(activo=True)
        p1 = ParaleloFactory(periodo=periodo, capacidad_maxima=1)
        MatriculaFactory(paralelo=p1, estado=Matricula.Estado.ACTIVA)

        creados, omitidos = self.service.matricular_en_lote(
            estudiante_id=est.pk,
            paralelo_ids=[p1.pk],
            registrado_por_id=est.pk,
        )
        assert creados == 0
        assert len(omitidos) == 1
        assert "sin cupo" in omitidos[0]

    def test_obtener_periodos_activos(self):
        """Returns only active periods."""
        PeriodoFactory(activo=True)
        PeriodoFactory(activo=False)
        result = self.service.obtener_periodos_activos()
        assert result.count() == 1

    def test_obtener_paralelos_por_periodo(self):
        """Returns paralelos for a specific period."""
        periodo = PeriodoFactory(activo=True)
        ParaleloFactory(periodo=periodo)
        ParaleloFactory()  # different period
        result = self.service.obtener_paralelos_por_periodo(periodo.pk)
        assert result.count() == 1

    def test_crear_matricula_asignatura_duplicada(self):
        """Cannot enroll in same asignatura even in different paralelo."""
        est = EstudianteFactory()
        periodo = PeriodoFactory(activo=True)
        asignatura = AsignaturaFactory()
        paralelo_a = ParaleloFactory(periodo=periodo, asignatura=asignatura, nombre="A")
        paralelo_b = ParaleloFactory(periodo=periodo, asignatura=asignatura, nombre="B")
        secretaria = UsuarioFactory(rol="secretaria")

        # Enroll in paralelo A
        self.service.crear_matricula(
            estudiante_id=est.pk,
            paralelo_id=paralelo_a.pk,
            registrado_por_id=secretaria.pk,
        )

        # Try to enroll in paralelo B (same asignatura) — should fail
        with pytest.raises(MatriculaAsignaturaDuplicadaError):
            self.service.crear_matricula(
                estudiante_id=est.pk,
                paralelo_id=paralelo_b.pk,
                registrado_por_id=secretaria.pk,
            )

    def test_crear_matricula_asignatura_retirada_permite_reinscripcion(self):
        """Student retired from asignatura CAN enroll in different paralelo."""
        est = EstudianteFactory()
        periodo = PeriodoFactory(activo=True)
        asignatura = AsignaturaFactory()
        paralelo_a = ParaleloFactory(periodo=periodo, asignatura=asignatura, nombre="A")
        paralelo_b = ParaleloFactory(periodo=periodo, asignatura=asignatura, nombre="B")
        secretaria = UsuarioFactory(rol="secretaria")

        # Enroll and then retire from paralelo A
        mat = self.service.crear_matricula(
            estudiante_id=est.pk,
            paralelo_id=paralelo_a.pk,
            registrado_por_id=secretaria.pk,
        )
        self.service.cambiar_estado(mat.pk, "retirada", "secretaria")

        # Now enroll in paralelo B — should succeed
        mat_b = self.service.crear_matricula(
            estudiante_id=est.pk,
            paralelo_id=paralelo_b.pk,
            registrado_por_id=secretaria.pk,
        )
        assert mat_b.pk is not None

    def test_matricular_en_lote_skips_asignatura_duplicada(self):
        """Batch enrollment skips paralelos where student already has same asignatura."""
        est = EstudianteFactory()
        est.save()
        periodo = PeriodoFactory(activo=True)
        asignatura = AsignaturaFactory()
        paralelo_a = ParaleloFactory(periodo=periodo, asignatura=asignatura, nombre="A")
        paralelo_b = ParaleloFactory(periodo=periodo, asignatura=asignatura, nombre="B")
        otra_asignatura = AsignaturaFactory()
        paralelo_c = ParaleloFactory(periodo=periodo, asignatura=otra_asignatura, nombre="A")
        MatriculaFactory(estudiante=est, paralelo=paralelo_a)

        creados, omitidos = self.service.matricular_en_lote(
            estudiante_id=est.pk,
            paralelo_ids=[paralelo_b.pk, paralelo_c.pk],
            registrado_por_id=est.pk,
        )
        assert creados == 1  # only paralelo_c (different asignatura)
        assert len(omitidos) == 1
        assert "ya inscrito en esta asignatura" in omitidos[0]
