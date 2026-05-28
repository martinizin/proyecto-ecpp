"""Tests for InspectorResolverJustificacionView (HU21 — T6).

Capability: ``inspector-resolucion-justificacion`` (R4, R5, R9 — POST
approve/reject from the detail view).

Covers:
  * Access control (anonymous redirect, non-inspector roles 403, GET 405).
  * Aprobar happy path: estado → APROBADA, historial +1, message success,
    idempotent on already-resolved rows.
  * Rechazar happy path: estado → RECHAZADA, comentario almacenado en
    ``respuesta``, historial +1, message success.
  * Rechazar rechaza comentario vacío o whitespace-only sin escribir nada.
  * Idempotencia: POST sobre una solicitud ya resuelta no modifica el
    estado ni crea historial.
  * Acción inválida o ausente: sin escrituras, message error.
  * Queryset filter: 404 si la solicitud no es JUSTIFICACION o no existe.
  * PRG: redirect a la URL del detalle (incluso en error).
"""

import pytest
from django.contrib.messages import get_messages
from django.urls import reverse

from apps.asistencia.infrastructure.models import Asistencia
from apps.solicitudes.infrastructure.models import Solicitud
from apps.usuarios.infrastructure.models import Usuario
from tests.factories import (
    AsistenciaFactory,
    DocenteFactory,
    EstudianteFactory,
    InspectorFactory,
    ParaleloFactory,
    PeriodoFactory,
    SolicitudFactory,
    UsuarioFactory,
)


# -------------------------------------------------------------------- #
# Helpers
# -------------------------------------------------------------------- #


def _make_justificacion(*, estado=Solicitud.EstadoSolicitud.PENDIENTE):
    """Create a ``Solicitud(tipo=JUSTIFICACION)`` with an Asistencia link."""
    estudiante = EstudianteFactory()
    estudiante.save()
    periodo = PeriodoFactory(activo=True)
    paralelo = ParaleloFactory(periodo=periodo)
    asistencia = AsistenciaFactory(
        estudiante=estudiante,
        paralelo=paralelo,
        estado=Asistencia.Estado.AUSENTE,
    )
    return SolicitudFactory(
        tipo=Solicitud.TipoSolicitud.JUSTIFICACION,
        estudiante=estudiante,
        asistencia=asistencia,
        estado=estado,
        descripcion="Justificación de prueba",
    )


def _resolver_url(pk):
    return reverse("solicitudes:inspector_justificacion_resolver", args=[pk])


def _detalle_url(pk):
    return reverse("solicitudes:inspector_justificacion_detalle", args=[pk])


def _msgs(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


# -------------------------------------------------------------------- #
# Access control
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestAccesoControl:
    def test_anonymous_post_redirects_to_login(self, client):
        sol = _make_justificacion()
        resp = client.post(_resolver_url(sol.pk), {"accion": "aprobar"})
        assert resp.status_code == 302
        assert "/usuarios/login/" in resp.url
        sol.refresh_from_db()
        assert sol.estado == Solicitud.EstadoSolicitud.PENDIENTE

    @pytest.mark.parametrize(
        "factory_callable",
        [
            lambda: EstudianteFactory(),
            lambda: DocenteFactory(),
            lambda: UsuarioFactory(rol=Usuario.Rol.SECRETARIA),
        ],
        ids=["estudiante", "docente", "secretaria"],
    )
    def test_no_inspector_forbidden_post(self, client, factory_callable):
        sol = _make_justificacion()
        user = factory_callable()
        user.save()
        client.force_login(user)
        resp = client.post(_resolver_url(sol.pk), {"accion": "aprobar"})
        assert resp.status_code == 403
        sol.refresh_from_db()
        assert sol.estado == Solicitud.EstadoSolicitud.PENDIENTE

    def test_get_returns_405(self, client):
        sol = _make_justificacion()
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        resp = client.get(_resolver_url(sol.pk))
        assert resp.status_code == 405

    def test_inspector_post_aprobar_redirects_to_detalle(self, client):
        sol = _make_justificacion()
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        resp = client.post(_resolver_url(sol.pk), {"accion": "aprobar", "comentario": "OK"})
        assert resp.status_code == 302
        assert resp.url == _detalle_url(sol.pk)


# -------------------------------------------------------------------- #
# Aprobar
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestAprobar:
    def _setup(self, client):
        sol = _make_justificacion()
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        return sol, inspector

    def test_aprobar_transiciona_a_APROBADA(self, client):
        sol, inspector = self._setup(client)
        resp = client.post(_resolver_url(sol.pk), {"accion": "aprobar", "comentario": "OK"})
        assert resp.status_code == 302
        sol.refresh_from_db()
        assert sol.estado == Solicitud.EstadoSolicitud.APROBADA
        assert sol.fecha_resolucion is not None
        assert sol.resuelto_por_id == inspector.pk

    def test_aprobar_crea_historial(self, client):
        sol, _ = self._setup(client)
        antes = sol.historial.count()
        client.post(_resolver_url(sol.pk), {"accion": "aprobar", "comentario": "OK"})
        sol.refresh_from_db()
        assert sol.historial.count() == antes + 1

    def test_aprobar_genera_message_success(self, client):
        sol, _ = self._setup(client)
        resp = client.post(_resolver_url(sol.pk), {"accion": "aprobar", "comentario": "OK"})
        msgs = _msgs(resp)
        assert any("aprobada" in m.lower() for m in msgs), msgs

    def test_aprobar_idempotente_sobre_aprobada(self, client):
        sol = _make_justificacion(estado=Solicitud.EstadoSolicitud.APROBADA)
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        antes_count = sol.historial.count()
        resp = client.post(_resolver_url(sol.pk), {"accion": "aprobar", "comentario": "OK"})
        assert resp.status_code == 302
        sol.refresh_from_db()
        assert sol.estado == Solicitud.EstadoSolicitud.APROBADA
        assert sol.historial.count() == antes_count  # sin nuevo historial


# -------------------------------------------------------------------- #
# Rechazar
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestRechazar:
    def _setup(self, client):
        sol = _make_justificacion()
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        return sol, inspector

    def test_rechazar_con_comentario_transiciona_a_RECHAZADA(self, client):
        sol, inspector = self._setup(client)
        resp = client.post(
            _resolver_url(sol.pk),
            {"accion": "rechazar", "comentario": "Documento ilegible"},
        )
        assert resp.status_code == 302
        sol.refresh_from_db()
        assert sol.estado == Solicitud.EstadoSolicitud.RECHAZADA
        assert "ilegible" in sol.respuesta.lower()
        assert sol.resuelto_por_id == inspector.pk

    def test_rechazar_crea_historial(self, client):
        sol, _ = self._setup(client)
        antes = sol.historial.count()
        client.post(
            _resolver_url(sol.pk),
            {"accion": "rechazar", "comentario": "Motivo claro"},
        )
        sol.refresh_from_db()
        assert sol.historial.count() == antes + 1

    def test_rechazar_genera_message_success(self, client):
        sol, _ = self._setup(client)
        resp = client.post(
            _resolver_url(sol.pk),
            {"accion": "rechazar", "comentario": "Motivo"},
        )
        msgs = _msgs(resp)
        assert any("rechazada" in m.lower() for m in msgs), msgs

    def test_rechazar_sin_comentario_no_modifica_estado(self, client):
        sol, _ = self._setup(client)
        antes_count = sol.historial.count()
        resp = client.post(_resolver_url(sol.pk), {"accion": "rechazar", "comentario": ""})
        assert resp.status_code == 302
        sol.refresh_from_db()
        assert sol.estado == Solicitud.EstadoSolicitud.PENDIENTE
        assert sol.historial.count() == antes_count
        msgs = _msgs(resp)
        assert any("comentario" in m.lower() for m in msgs), msgs

    def test_rechazar_solo_espacios_no_modifica_estado(self, client):
        sol, _ = self._setup(client)
        antes_count = sol.historial.count()
        resp = client.post(
            _resolver_url(sol.pk),
            {"accion": "rechazar", "comentario": "   "},
        )
        assert resp.status_code == 302
        sol.refresh_from_db()
        assert sol.estado == Solicitud.EstadoSolicitud.PENDIENTE
        assert sol.historial.count() == antes_count

    def test_rechazar_idempotente_sobre_aprobada(self, client):
        sol = _make_justificacion(estado=Solicitud.EstadoSolicitud.APROBADA)
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        antes_count = sol.historial.count()
        resp = client.post(
            _resolver_url(sol.pk),
            {"accion": "rechazar", "comentario": "tarde"},
        )
        assert resp.status_code == 302
        sol.refresh_from_db()
        # Sigue APROBADA, sin nuevas escrituras.
        assert sol.estado == Solicitud.EstadoSolicitud.APROBADA
        assert sol.historial.count() == antes_count


# -------------------------------------------------------------------- #
# Acción inválida
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestAccionInvalida:
    def test_accion_invalida_no_modifica_estado(self, client):
        sol = _make_justificacion()
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        antes_count = sol.historial.count()
        resp = client.post(
            _resolver_url(sol.pk),
            {"accion": "otra_cosa", "comentario": "x"},
        )
        assert resp.status_code == 302
        sol.refresh_from_db()
        assert sol.estado == Solicitud.EstadoSolicitud.PENDIENTE
        assert sol.historial.count() == antes_count
        msgs = _msgs(resp)
        assert any("inválida" in m.lower() or "invalida" in m.lower() for m in msgs), msgs

    def test_accion_vacia_no_modifica_estado(self, client):
        sol = _make_justificacion()
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        antes_count = sol.historial.count()
        resp = client.post(_resolver_url(sol.pk), {"comentario": "x"})
        assert resp.status_code == 302
        sol.refresh_from_db()
        assert sol.estado == Solicitud.EstadoSolicitud.PENDIENTE
        assert sol.historial.count() == antes_count


# -------------------------------------------------------------------- #
# Queryset filtering — only JUSTIFICACION
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestQuerysetFiltering:
    def test_no_justificacion_returns_404(self, client):
        estudiante = EstudianteFactory()
        estudiante.save()
        sol = SolicitudFactory(
            tipo=Solicitud.TipoSolicitud.RECTIFICACION,
            estudiante=estudiante,
            descripcion="No-justificacion",
        )
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        resp = client.post(_resolver_url(sol.pk), {"accion": "aprobar"})
        assert resp.status_code == 404

    def test_solicitud_inexistente_404(self, client):
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        resp = client.post(_resolver_url(99999), {"accion": "aprobar"})
        assert resp.status_code == 404


# -------------------------------------------------------------------- #
# PRG — siempre redirige al detalle
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestRedirectPattern:
    def test_redirect_to_detalle_after_success(self, client):
        sol = _make_justificacion()
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        resp = client.post(_resolver_url(sol.pk), {"accion": "aprobar", "comentario": "OK"})
        assert resp.status_code == 302
        assert resp.url == _detalle_url(sol.pk)

    def test_redirect_to_detalle_after_error(self, client):
        sol = _make_justificacion()
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        # rechazar sin comentario → error path, pero igual redirige a detalle.
        resp = client.post(_resolver_url(sol.pk), {"accion": "rechazar", "comentario": ""})
        assert resp.status_code == 302
        assert resp.url == _detalle_url(sol.pk)
