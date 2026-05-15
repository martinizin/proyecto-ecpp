"""Tests for HU16 — Validación de calificaciones por secretaría."""

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.calificaciones.application.services import (
    RegistroCalificacionAppService,
    ValidacionCalificacionAppService,
)
from apps.calificaciones.infrastructure.models import RegistroCalificacionParalelo
from tests.factories import (
    CalificacionFactory,
    DocenteFactory,
    EstudianteFactory,
    EvaluacionFactory,
    MatriculaFactory,
    ParaleloFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db


def _saved(user):
    """Persist password hash so force_login session survives request cycle."""
    user.save()
    return user


def _paralelo_completo():
    """Helper: create a paralelo with complete grades and estado=COMPLETO."""
    docente = DocenteFactory()
    paralelo = ParaleloFactory(docente=docente)
    ev = EvaluacionFactory(paralelo=paralelo, peso=Decimal("100"))
    est = EstudianteFactory()
    MatriculaFactory(paralelo=paralelo, estudiante=est)
    CalificacionFactory(evaluacion=ev, estudiante=est)
    registro = RegistroCalificacionParalelo.objects.create(
        paralelo=paralelo,
        estado=RegistroCalificacionParalelo.Estado.COMPLETO,
        fecha_envio=timezone.now(),
    )
    return paralelo, registro, docente


# ─── A. Service tests ────────────────────────────────────────────────────────


class TestValidacionCalificacionAppService:

    def setup_method(self):
        self.service = ValidacionCalificacionAppService()
        self.registro_service = RegistroCalificacionAppService()

    def test_obtener_pendientes_returns_completo_only(self):
        """Only paralelos with estado COMPLETO are returned."""
        p1, _, _ = _paralelo_completo()
        # Create one in BORRADOR — should not appear
        p2 = ParaleloFactory()
        RegistroCalificacionParalelo.objects.create(paralelo=p2, estado="borrador")

        pendientes = self.service.obtener_pendientes()
        paralelo_ids = [r.paralelo_id for r in pendientes]
        assert p1.pk in paralelo_ids
        assert p2.pk not in paralelo_ids

    def test_obtener_pendientes_empty_when_no_completo(self):
        """Returns empty queryset when no COMPLETO registros exist."""
        ParaleloFactory()  # no registro at all
        p2 = ParaleloFactory()
        RegistroCalificacionParalelo.objects.create(paralelo=p2, estado="borrador")

        pendientes = self.service.obtener_pendientes()
        assert pendientes.count() == 0

    def test_obtener_detalle_validacion_completo(self):
        """Returns planilla data for a COMPLETO registro."""
        paralelo, _, _ = _paralelo_completo()

        datos = self.service.obtener_detalle_validacion(paralelo.pk)
        assert datos is not None
        assert "registro" in datos
        assert "evaluaciones" in datos
        assert "filas" in datos
        assert datos["registro"].estado == "completo"

    def test_obtener_detalle_validacion_not_completo_returns_none(self):
        """Returns None for non-COMPLETO registro."""
        paralelo = ParaleloFactory()
        RegistroCalificacionParalelo.objects.create(paralelo=paralelo, estado="borrador")

        datos = self.service.obtener_detalle_validacion(paralelo.pk)
        assert datos is None

    def test_aprobar_sets_validado(self):
        """Aprobar sets estado=VALIDADO, fecha_validacion, validado_por."""
        paralelo, _, _ = _paralelo_completo()
        secretaria = UsuarioFactory(rol="secretaria")

        result = self.service.aprobar(paralelo.pk, secretaria)
        assert result["ok"] is True

        registro = RegistroCalificacionParalelo.objects.get(paralelo=paralelo)
        assert registro.estado == "validado"
        assert registro.fecha_validacion is not None
        assert registro.validado_por == secretaria

    def test_aprobar_fails_if_borrador(self):
        """Cannot approve from BORRADOR state."""
        paralelo = ParaleloFactory()
        RegistroCalificacionParalelo.objects.create(paralelo=paralelo, estado="borrador")
        secretaria = UsuarioFactory(rol="secretaria")

        result = self.service.aprobar(paralelo.pk, secretaria)
        assert result["ok"] is False

    def test_aprobar_fails_if_validado(self):
        """Cannot approve an already VALIDADO registro."""
        paralelo = ParaleloFactory()
        RegistroCalificacionParalelo.objects.create(paralelo=paralelo, estado="validado")
        secretaria = UsuarioFactory(rol="secretaria")

        result = self.service.aprobar(paralelo.pk, secretaria)
        assert result["ok"] is False

    def test_rechazar_sets_rechazado_with_observaciones(self):
        """Rechazar sets estado=RECHAZADO and stores observaciones."""
        paralelo, _, _ = _paralelo_completo()
        secretaria = UsuarioFactory(rol="secretaria")

        result = self.service.rechazar(paralelo.pk, secretaria, "Notas incorrectas en parcial 1")
        assert result["ok"] is True

        registro = RegistroCalificacionParalelo.objects.get(paralelo=paralelo)
        assert registro.estado == "rechazado"
        assert registro.observaciones_secretaria == "Notas incorrectas en parcial 1"

    def test_rechazar_fails_if_observaciones_empty(self):
        """Cannot reject without observaciones."""
        paralelo, _, _ = _paralelo_completo()
        secretaria = UsuarioFactory(rol="secretaria")

        result = self.service.rechazar(paralelo.pk, secretaria, "")
        assert result["ok"] is False
        assert "observaciones" in result["error"].lower()

    def test_rechazar_fails_if_not_completo(self):
        """Cannot reject from BORRADOR state."""
        paralelo = ParaleloFactory()
        RegistroCalificacionParalelo.objects.create(paralelo=paralelo, estado="borrador")
        secretaria = UsuarioFactory(rol="secretaria")

        result = self.service.rechazar(paralelo.pk, secretaria, "Observacion")
        assert result["ok"] is False

    def test_after_rechazar_docente_can_edit(self):
        """After rejection, docente can edit (puede_editar returns True)."""
        paralelo, _, _ = _paralelo_completo()
        secretaria = UsuarioFactory(rol="secretaria")

        self.service.rechazar(paralelo.pk, secretaria, "Corregir notas")
        assert self.registro_service.puede_editar(paralelo.pk) is True

    def test_after_aprobar_docente_cannot_edit(self):
        """After approval, docente cannot edit (puede_editar returns False)."""
        paralelo, _, _ = _paralelo_completo()
        secretaria = UsuarioFactory(rol="secretaria")

        self.service.aprobar(paralelo.pk, secretaria)
        assert self.registro_service.puede_editar(paralelo.pk) is False


# ─── B. View tests ───────────────────────────────────────────────────────────


class TestPendientesValidacionView:

    def test_only_secretaria_can_access(self, client):
        """Docente gets 403 or redirect when accessing pendientes."""
        docente = _saved(DocenteFactory())
        client.force_login(docente)
        response = client.get("/calificaciones/pendientes-validacion/")
        assert response.status_code in (302, 403)

    def test_shows_pending_paralelos(self, client):
        """Secretaria sees pending paralelos."""
        _paralelo_completo()
        secretaria = _saved(UsuarioFactory(rol="secretaria"))
        client.force_login(secretaria)
        response = client.get("/calificaciones/pendientes-validacion/")
        assert response.status_code == 200


class TestDetalleValidacionView:

    def test_shows_planilla_for_completo(self, client):
        """GET shows readonly planilla for COMPLETO registro."""
        paralelo, _, _ = _paralelo_completo()
        secretaria = _saved(UsuarioFactory(rol="secretaria"))
        client.force_login(secretaria)
        response = client.get(f"/calificaciones/paralelo/{paralelo.pk}/detalle-validacion/")
        assert response.status_code == 200

    def test_redirects_if_not_completo(self, client):
        """GET redirects if estado != COMPLETO."""
        paralelo = ParaleloFactory()
        RegistroCalificacionParalelo.objects.create(paralelo=paralelo, estado="borrador")
        secretaria = _saved(UsuarioFactory(rol="secretaria"))
        client.force_login(secretaria)
        response = client.get(f"/calificaciones/paralelo/{paralelo.pk}/detalle-validacion/")
        assert response.status_code == 302


class TestAprobarCalificacionesView:

    def test_approves_and_redirects(self, client):
        """POST approves and redirects with success message."""
        paralelo, _, _ = _paralelo_completo()
        secretaria = _saved(UsuarioFactory(rol="secretaria"))
        client.force_login(secretaria)
        response = client.post(f"/calificaciones/paralelo/{paralelo.pk}/aprobar/")
        assert response.status_code == 302
        registro = RegistroCalificacionParalelo.objects.get(paralelo=paralelo)
        assert registro.estado == "validado"

    def test_only_secretaria_can_approve(self, client):
        """Docente cannot approve."""
        paralelo, _, _ = _paralelo_completo()
        docente = _saved(DocenteFactory())
        client.force_login(docente)
        response = client.post(f"/calificaciones/paralelo/{paralelo.pk}/aprobar/")
        assert response.status_code in (302, 403)
        registro = RegistroCalificacionParalelo.objects.get(paralelo=paralelo)
        assert registro.estado == "completo"  # unchanged


class TestRechazarCalificacionesView:

    def test_rejects_with_observaciones(self, client):
        """POST rejects with observaciones and redirects."""
        paralelo, _, _ = _paralelo_completo()
        secretaria = _saved(UsuarioFactory(rol="secretaria"))
        client.force_login(secretaria)
        response = client.post(
            f"/calificaciones/paralelo/{paralelo.pk}/rechazar/",
            {"observaciones": "Revisar parcial 2"},
        )
        assert response.status_code == 302
        registro = RegistroCalificacionParalelo.objects.get(paralelo=paralelo)
        assert registro.estado == "rechazado"

    def test_fails_without_observaciones(self, client):
        """POST fails without observaciones."""
        paralelo, _, _ = _paralelo_completo()
        secretaria = _saved(UsuarioFactory(rol="secretaria"))
        client.force_login(secretaria)
        response = client.post(
            f"/calificaciones/paralelo/{paralelo.pk}/rechazar/",
            {"observaciones": ""},
        )
        assert response.status_code == 302
        registro = RegistroCalificacionParalelo.objects.get(paralelo=paralelo)
        assert registro.estado == "completo"  # unchanged


# ─── C. Integration flow tests ───────────────────────────────────────────────


class TestIntegrationFlows:

    def test_enviar_aprobar_no_edit(self, client):
        """Full flow: docente envía → secretaria aprueba → docente can't edit."""
        docente = _saved(DocenteFactory())
        paralelo = ParaleloFactory(docente=docente)
        ev = EvaluacionFactory(paralelo=paralelo, peso=Decimal("100"))
        est = EstudianteFactory()
        MatriculaFactory(paralelo=paralelo, estudiante=est)
        CalificacionFactory(evaluacion=ev, estudiante=est)

        # Docente sends
        client.force_login(docente)
        client.post(f"/calificaciones/paralelo/{paralelo.pk}/enviar-validacion/")
        registro = RegistroCalificacionParalelo.objects.get(paralelo=paralelo)
        assert registro.estado == "completo"

        # Secretaria approves
        secretaria = _saved(UsuarioFactory(rol="secretaria"))
        client.force_login(secretaria)
        client.post(f"/calificaciones/paralelo/{paralelo.pk}/aprobar/")
        registro.refresh_from_db()
        assert registro.estado == "validado"

        # Docente can't edit
        service = RegistroCalificacionAppService()
        assert service.puede_editar(paralelo.pk) is False

    def test_enviar_rechazar_edit_reenviar(self, client):
        """Full flow: docente envía → secretaria rechaza → docente edits → reenvía."""
        docente = _saved(DocenteFactory())
        paralelo = ParaleloFactory(docente=docente)
        ev = EvaluacionFactory(paralelo=paralelo, peso=Decimal("100"))
        est = EstudianteFactory()
        MatriculaFactory(paralelo=paralelo, estudiante=est)
        CalificacionFactory(evaluacion=ev, estudiante=est)

        # Docente sends
        client.force_login(docente)
        client.post(f"/calificaciones/paralelo/{paralelo.pk}/enviar-validacion/")

        # Secretaria rejects
        secretaria = _saved(UsuarioFactory(rol="secretaria"))
        client.force_login(secretaria)
        client.post(
            f"/calificaciones/paralelo/{paralelo.pk}/rechazar/",
            {"observaciones": "Corregir nota de parcial"},
        )
        registro = RegistroCalificacionParalelo.objects.get(paralelo=paralelo)
        assert registro.estado == "rechazado"

        # Docente can edit
        service = RegistroCalificacionAppService()
        assert service.puede_editar(paralelo.pk) is True

        # Docente re-sends
        client.force_login(docente)
        client.post(f"/calificaciones/paralelo/{paralelo.pk}/enviar-validacion/")
        registro.refresh_from_db()
        assert registro.estado == "completo"
