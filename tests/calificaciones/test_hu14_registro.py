"""Tests for HU14 — RegistroCalificacionParalelo model, state management, and views."""

from decimal import Decimal

import pytest
from django.db import IntegrityError

from apps.calificaciones.application.services import RegistroCalificacionAppService
from apps.calificaciones.infrastructure.models import (
    Calificacion,
    RegistroCalificacionParalelo,
)
from tests.factories import (
    CalificacionFactory,
    DocenteFactory,
    EstudianteFactory,
    EvaluacionFactory,
    MatriculaFactory,
    ParaleloFactory,
)

pytestmark = pytest.mark.django_db


def _saved(user):
    """Persist password hash so force_login session survives request cycle."""
    user.save()
    return user


# ─── A. Model tests ──────────────────────────────────────────────────────────


class TestRegistroCalificacionParaleloModel:

    def test_create_registro_default_borrador(self):
        """Creating a registro defaults to BORRADOR state."""
        paralelo = ParaleloFactory()
        registro = RegistroCalificacionParalelo.objects.create(paralelo=paralelo)
        assert registro.estado == "borrador"

    def test_str_representation(self):
        """str should show paralelo and estado display."""
        paralelo = ParaleloFactory()
        registro = RegistroCalificacionParalelo.objects.create(paralelo=paralelo)
        result = str(registro)
        assert str(paralelo) in result
        assert "Borrador" in result

    def test_one_to_one_constraint(self):
        """Only one registro per paralelo."""
        paralelo = ParaleloFactory()
        RegistroCalificacionParalelo.objects.create(paralelo=paralelo)
        with pytest.raises(IntegrityError):
            RegistroCalificacionParalelo.objects.create(paralelo=paralelo)

    def test_estado_choices(self):
        """All 4 states should be available."""
        choices = [c[0] for c in RegistroCalificacionParalelo.Estado.choices]
        assert choices == ["borrador", "completo", "validado", "rechazado"]


# ─── B. Service tests ────────────────────────────────────────────────────────


class TestRegistroCalificacionService:

    def setup_method(self):
        self.service = RegistroCalificacionAppService()

    def test_obtener_o_crear_registro_creates_new(self):
        """First call creates a new registro in BORRADOR."""
        paralelo = ParaleloFactory()
        registro = self.service.obtener_o_crear_registro(paralelo.pk)
        assert registro.estado == "borrador"
        assert registro.paralelo_id == paralelo.pk

    def test_obtener_o_crear_registro_returns_existing(self):
        """Second call returns the same registro."""
        paralelo = ParaleloFactory()
        r1 = self.service.obtener_o_crear_registro(paralelo.pk)
        r2 = self.service.obtener_o_crear_registro(paralelo.pk)
        assert r1.pk == r2.pk

    def test_verificar_completitud_no_evaluaciones(self):
        """Returns False if no evaluaciones configured."""
        paralelo = ParaleloFactory()
        assert self.service.verificar_completitud(paralelo.pk) is False

    def test_verificar_completitud_no_matriculas(self):
        """Returns False if no active students."""
        paralelo = ParaleloFactory()
        EvaluacionFactory(paralelo=paralelo)
        assert self.service.verificar_completitud(paralelo.pk) is False

    def test_verificar_completitud_incomplete(self):
        """Returns False if some grades are missing."""
        paralelo = ParaleloFactory()
        ev = EvaluacionFactory(paralelo=paralelo)
        est1 = EstudianteFactory()
        est2 = EstudianteFactory()
        MatriculaFactory(paralelo=paralelo, estudiante=est1)
        MatriculaFactory(paralelo=paralelo, estudiante=est2)
        # Only 1 of 2 calificaciones
        CalificacionFactory(evaluacion=ev, estudiante=est1)
        assert self.service.verificar_completitud(paralelo.pk) is False

    def test_verificar_completitud_complete(self):
        """Returns True when all students have all grades."""
        paralelo = ParaleloFactory()
        ev = EvaluacionFactory(paralelo=paralelo)
        est1 = EstudianteFactory()
        est2 = EstudianteFactory()
        MatriculaFactory(paralelo=paralelo, estudiante=est1)
        MatriculaFactory(paralelo=paralelo, estudiante=est2)
        CalificacionFactory(evaluacion=ev, estudiante=est1)
        CalificacionFactory(evaluacion=ev, estudiante=est2)
        assert self.service.verificar_completitud(paralelo.pk) is True

    def test_puede_editar_no_registro(self):
        """Returns True when no registro exists (implicit BORRADOR)."""
        paralelo = ParaleloFactory()
        assert self.service.puede_editar(paralelo.pk) is True

    def test_puede_editar_borrador(self):
        """Returns True when estado is BORRADOR."""
        paralelo = ParaleloFactory()
        RegistroCalificacionParalelo.objects.create(paralelo=paralelo)
        assert self.service.puede_editar(paralelo.pk) is True

    def test_puede_editar_rechazado(self):
        """Returns True when estado is RECHAZADO."""
        paralelo = ParaleloFactory()
        RegistroCalificacionParalelo.objects.create(
            paralelo=paralelo,
            estado=RegistroCalificacionParalelo.Estado.RECHAZADO,
        )
        assert self.service.puede_editar(paralelo.pk) is True

    def test_puede_editar_completo(self):
        """Returns False when estado is COMPLETO."""
        paralelo = ParaleloFactory()
        RegistroCalificacionParalelo.objects.create(
            paralelo=paralelo,
            estado=RegistroCalificacionParalelo.Estado.COMPLETO,
        )
        assert self.service.puede_editar(paralelo.pk) is False

    def test_puede_editar_validado(self):
        """Returns False when estado is VALIDADO."""
        paralelo = ParaleloFactory()
        RegistroCalificacionParalelo.objects.create(
            paralelo=paralelo,
            estado=RegistroCalificacionParalelo.Estado.VALIDADO,
        )
        assert self.service.puede_editar(paralelo.pk) is False

    def test_enviar_a_validacion_success(self):
        """Successfully changes state to COMPLETO when all conditions met."""
        paralelo = ParaleloFactory()
        ev = EvaluacionFactory(paralelo=paralelo, peso=Decimal("100"))
        est = EstudianteFactory()
        MatriculaFactory(paralelo=paralelo, estudiante=est)
        CalificacionFactory(evaluacion=ev, estudiante=est)

        result = self.service.enviar_a_validacion(paralelo.pk)
        assert result["ok"] is True
        registro = RegistroCalificacionParalelo.objects.get(paralelo=paralelo)
        assert registro.estado == "completo"
        assert registro.fecha_envio is not None

    def test_enviar_a_validacion_incomplete(self):
        """Fails when grades are incomplete."""
        paralelo = ParaleloFactory()
        EvaluacionFactory(paralelo=paralelo, peso=Decimal("100"))
        est = EstudianteFactory()
        MatriculaFactory(paralelo=paralelo, estudiante=est)
        # No calificacion

        result = self.service.enviar_a_validacion(paralelo.pk)
        assert result["ok"] is False
        assert "faltan" in result["error"].lower()

    def test_enviar_a_validacion_pesos_not_100(self):
        """Fails when evaluacion pesos don't sum to 100."""
        paralelo = ParaleloFactory()
        ev = EvaluacionFactory(paralelo=paralelo, peso=Decimal("50"))
        est = EstudianteFactory()
        MatriculaFactory(paralelo=paralelo, estudiante=est)
        CalificacionFactory(evaluacion=ev, estudiante=est)

        result = self.service.enviar_a_validacion(paralelo.pk)
        assert result["ok"] is False
        assert "100%" in result["error"]

    def test_enviar_a_validacion_already_completo(self):
        """Fails when already in COMPLETO state."""
        paralelo = ParaleloFactory()
        RegistroCalificacionParalelo.objects.create(
            paralelo=paralelo,
            estado=RegistroCalificacionParalelo.Estado.COMPLETO,
        )
        result = self.service.enviar_a_validacion(paralelo.pk)
        assert result["ok"] is False

    def test_enviar_a_validacion_from_rechazado(self):
        """Can re-send from RECHAZADO state."""
        paralelo = ParaleloFactory()
        RegistroCalificacionParalelo.objects.create(
            paralelo=paralelo,
            estado=RegistroCalificacionParalelo.Estado.RECHAZADO,
        )
        ev = EvaluacionFactory(paralelo=paralelo, peso=Decimal("100"))
        est = EstudianteFactory()
        MatriculaFactory(paralelo=paralelo, estudiante=est)
        CalificacionFactory(evaluacion=ev, estudiante=est)

        result = self.service.enviar_a_validacion(paralelo.pk)
        assert result["ok"] is True
        registro = RegistroCalificacionParalelo.objects.get(paralelo=paralelo)
        assert registro.estado == "completo"


# ─── C. View tests ───────────────────────────────────────────────────────────


class TestRegistrarCalificacionesView:

    def test_get_planilla_as_docente(self, client):
        """Docente can access their paralelo planilla."""
        docente = _saved(DocenteFactory())
        paralelo = ParaleloFactory(docente=docente)
        client.force_login(docente)
        response = client.get(
            f"/calificaciones/paralelo/{paralelo.pk}/registrar/"
        )
        assert response.status_code == 200

    def test_get_planilla_wrong_docente(self, client):
        """Docente cannot access another docente's paralelo."""
        docente = _saved(DocenteFactory())
        other_docente = _saved(DocenteFactory())
        paralelo = ParaleloFactory(docente=other_docente)
        client.force_login(docente)
        response = client.get(
            f"/calificaciones/paralelo/{paralelo.pk}/registrar/"
        )
        assert response.status_code == 302

    def test_post_saves_calificacion(self, client):
        """POST saves a new calificacion."""
        docente = _saved(DocenteFactory())
        paralelo = ParaleloFactory(docente=docente)
        ev = EvaluacionFactory(paralelo=paralelo)
        estudiante = EstudianteFactory()
        MatriculaFactory(paralelo=paralelo, estudiante=estudiante)
        client.force_login(docente)
        response = client.post(
            f"/calificaciones/paralelo/{paralelo.pk}/registrar/",
            {f"nota_{estudiante.pk}_{ev.pk}": "15.50"},
        )
        assert response.status_code == 302
        assert Calificacion.objects.filter(
            evaluacion=ev, estudiante=estudiante
        ).exists()

    def test_post_blocked_when_completo(self, client):
        """POST is blocked when estado is COMPLETO."""
        docente = _saved(DocenteFactory())
        paralelo = ParaleloFactory(docente=docente)
        RegistroCalificacionParalelo.objects.create(
            paralelo=paralelo,
            estado=RegistroCalificacionParalelo.Estado.COMPLETO,
        )
        client.force_login(docente)
        response = client.post(
            f"/calificaciones/paralelo/{paralelo.pk}/registrar/",
            {"nota_1_1": "15"},
        )
        assert response.status_code == 302


class TestEnviarValidacionView:

    def test_enviar_success(self, client):
        """POST enviar-validacion changes state to COMPLETO."""
        docente = _saved(DocenteFactory())
        paralelo = ParaleloFactory(docente=docente)
        ev = EvaluacionFactory(paralelo=paralelo, peso=Decimal("100"))
        estudiante = EstudianteFactory()
        MatriculaFactory(paralelo=paralelo, estudiante=estudiante)
        CalificacionFactory(evaluacion=ev, estudiante=estudiante)
        client.force_login(docente)
        response = client.post(
            f"/calificaciones/paralelo/{paralelo.pk}/enviar-validacion/"
        )
        assert response.status_code == 302
        registro = RegistroCalificacionParalelo.objects.get(paralelo=paralelo)
        assert registro.estado == "completo"

    def test_enviar_incomplete_fails(self, client):
        """POST enviar fails when grades incomplete."""
        docente = _saved(DocenteFactory())
        paralelo = ParaleloFactory(docente=docente)
        EvaluacionFactory(paralelo=paralelo, peso=Decimal("100"))
        estudiante = EstudianteFactory()
        MatriculaFactory(paralelo=paralelo, estudiante=estudiante)
        # No calificacion
        client.force_login(docente)
        response = client.post(
            f"/calificaciones/paralelo/{paralelo.pk}/enviar-validacion/"
        )
        assert response.status_code == 302
        assert not RegistroCalificacionParalelo.objects.filter(
            paralelo=paralelo, estado="completo"
        ).exists()

    def test_enviar_wrong_docente(self, client):
        """Other docente cannot send."""
        docente = _saved(DocenteFactory())
        other = _saved(DocenteFactory())
        paralelo = ParaleloFactory(docente=other)
        client.force_login(docente)
        response = client.post(
            f"/calificaciones/paralelo/{paralelo.pk}/enviar-validacion/"
        )
        assert response.status_code == 302
