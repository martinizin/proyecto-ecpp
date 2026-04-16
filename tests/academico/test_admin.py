"""
Tests for MatriculaAdmin — validates save_model logic:
cupo, active period, duplicate enrollment, state transitions, matriculado_por.
"""

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory

from apps.academico.admin import MatriculaAdmin
from apps.academico.domain.exceptions import (
    CupoExcedidoError,
    EstadoMatriculaInvalidoError,
    MatriculaDuplicadaError,
)
from apps.academico.infrastructure.models import Matricula
from tests.factories import (
    EstudianteFactory,
    InspectorFactory,
    MatriculaFactory,
    ParaleloFactory,
    PeriodoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db


class TestMatriculaAdminSaveModel:
    """Tests for MatriculaAdmin.save_model validations."""

    def setup_method(self):
        self.site = AdminSite()
        self.admin = MatriculaAdmin(Matricula, self.site)
        self.factory = RequestFactory()

    def _make_request(self, user):
        request = self.factory.post("/admin/academico/matricula/add/")
        request.user = user
        setattr(request, "session", "session")
        setattr(request, "_messages", FallbackStorage(request))
        return request

    def test_create_matricula_sets_matriculado_por(self):
        """save_model should auto-set matriculado_por to request.user."""
        superuser = UsuarioFactory(
            is_staff=True, is_superuser=True, rol="inspector"
        )
        periodo = PeriodoFactory(activo=True)
        paralelo = ParaleloFactory(periodo=periodo)
        estudiante = EstudianteFactory()

        obj = Matricula(estudiante=estudiante, paralelo=paralelo)
        request = self._make_request(superuser)

        self.admin.save_model(request, obj, form=None, change=False)

        assert obj.pk is not None
        assert obj.matriculado_por == superuser

    def test_create_matricula_periodo_inactivo_raises(self):
        """Cannot enroll in a paralelo of an inactive period."""
        from apps.academico.domain.exceptions import PeriodoInactivoError

        superuser = UsuarioFactory(
            is_staff=True, is_superuser=True, rol="inspector"
        )
        periodo = PeriodoFactory(activo=False)
        paralelo = ParaleloFactory(periodo=periodo)
        estudiante = EstudianteFactory()

        obj = Matricula(estudiante=estudiante, paralelo=paralelo)
        request = self._make_request(superuser)

        with pytest.raises(PeriodoInactivoError):
            self.admin.save_model(request, obj, form=None, change=False)

    def test_create_matricula_duplicada_raises(self):
        """Cannot enroll the same student twice in the same paralelo."""
        superuser = UsuarioFactory(
            is_staff=True, is_superuser=True, rol="inspector"
        )
        periodo = PeriodoFactory(activo=True)
        paralelo = ParaleloFactory(periodo=periodo)
        estudiante = EstudianteFactory()

        # First enrollment
        MatriculaFactory(estudiante=estudiante, paralelo=paralelo)

        # Second enrollment attempt
        obj = Matricula(estudiante=estudiante, paralelo=paralelo)
        request = self._make_request(superuser)

        with pytest.raises(MatriculaDuplicadaError):
            self.admin.save_model(request, obj, form=None, change=False)

    def test_create_matricula_cupo_excedido_raises(self):
        """Cannot enroll if paralelo is at capacity."""
        superuser = UsuarioFactory(
            is_staff=True, is_superuser=True, rol="inspector"
        )
        periodo = PeriodoFactory(activo=True)
        paralelo = ParaleloFactory(periodo=periodo, capacidad_maxima=2)

        # Fill up capacity
        MatriculaFactory(paralelo=paralelo)
        MatriculaFactory(paralelo=paralelo)

        # One more should fail
        estudiante = EstudianteFactory()
        obj = Matricula(estudiante=estudiante, paralelo=paralelo)
        request = self._make_request(superuser)

        with pytest.raises(CupoExcedidoError):
            self.admin.save_model(request, obj, form=None, change=False)

    def test_superuser_transition_activa_to_retirada(self):
        """Superuser (secretaria) can change activa -> retirada."""
        superuser = UsuarioFactory(
            is_staff=True, is_superuser=True, rol="inspector"
        )
        periodo = PeriodoFactory(activo=True)
        paralelo = ParaleloFactory(periodo=periodo)
        matricula = MatriculaFactory(
            paralelo=paralelo, estado=Matricula.Estado.ACTIVA
        )

        matricula.estado = Matricula.Estado.RETIRADA
        request = self._make_request(superuser)

        self.admin.save_model(request, matricula, form=None, change=True)
        matricula.refresh_from_db()
        assert matricula.estado == Matricula.Estado.RETIRADA

    def test_inspector_transition_activa_to_suspendida(self):
        """Inspector can change activa -> suspendida."""
        inspector = InspectorFactory(is_staff=True)
        periodo = PeriodoFactory(activo=True)
        paralelo = ParaleloFactory(periodo=periodo)
        matricula = MatriculaFactory(
            paralelo=paralelo, estado=Matricula.Estado.ACTIVA
        )

        matricula.estado = Matricula.Estado.SUSPENDIDA
        request = self._make_request(inspector)

        self.admin.save_model(request, matricula, form=None, change=True)
        matricula.refresh_from_db()
        assert matricula.estado == Matricula.Estado.SUSPENDIDA

    def test_inspector_cannot_retirar(self):
        """Inspector cannot change activa -> retirada."""
        inspector = InspectorFactory(is_staff=True)
        periodo = PeriodoFactory(activo=True)
        paralelo = ParaleloFactory(periodo=periodo)
        matricula = MatriculaFactory(
            paralelo=paralelo, estado=Matricula.Estado.ACTIVA
        )

        matricula.estado = Matricula.Estado.RETIRADA
        request = self._make_request(inspector)

        with pytest.raises(EstadoMatriculaInvalidoError):
            self.admin.save_model(request, matricula, form=None, change=True)

    def test_reactivar_checks_cupo(self):
        """Reactivating a matricula should check capacity."""
        superuser = UsuarioFactory(
            is_staff=True, is_superuser=True, rol="inspector"
        )
        periodo = PeriodoFactory(activo=True)
        paralelo = ParaleloFactory(periodo=periodo, capacidad_maxima=1)

        # One active enrollment fills capacity
        MatriculaFactory(paralelo=paralelo, estado=Matricula.Estado.ACTIVA)

        # A retired enrollment trying to reactivate
        matricula = MatriculaFactory(
            paralelo=paralelo, estado=Matricula.Estado.RETIRADA
        )
        matricula.estado = Matricula.Estado.ACTIVA
        request = self._make_request(superuser)

        with pytest.raises(CupoExcedidoError):
            self.admin.save_model(request, matricula, form=None, change=True)
