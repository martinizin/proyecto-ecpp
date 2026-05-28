"""Tests for InspectorBulkActionView (HU21 — T7).

Capability: ``inspector-resolucion-justificacion`` (R6, R7, R8, R9 — bulk
approve / reject from the dashboard).

Covers:
  * Access control (anonymous redirect, non-inspector roles 403, GET 405).
  * URL ordering: ``bulk/`` resolves before ``<int:pk>/``.
  * Aprobar bulk happy path: filas pendientes transicionan a APROBADA,
    historial +1 por fila, message con contadores.
  * Aprobar bulk con filas ya resueltas: skip silencioso, contadas en
    ``omitidas``.
  * Rechazar bulk con comentario válido: filas pendientes a RECHAZADA,
    comentario almacenado.
  * Rechazar bulk con comentario vacío / whitespace: ValueError del
    servicio → message error, ZERO escrituras (all-or-nothing).
  * Sin ``solicitud_ids``: message error, sin escrituras.
  * Acción inválida: el servicio cuenta la fila como omitida silenciosa.
  * IDs no-numéricos: ignorados sin romper.
  * ID inexistente o no-JUSTIFICACION: filtro del servicio descarta.
  * PRG: siempre redirige al dashboard.
  * Render del dashboard incluye form bulk-form y marcadores del modal
    Alpine.
"""

import pytest
from django.contrib.messages import get_messages
from django.urls import resolve, reverse

from apps.asistencia.infrastructure.models import Asistencia
from apps.solicitudes.infrastructure.models import Solicitud
from apps.solicitudes.presentation.views import (
    InspectorBulkActionView,
    InspectorJustificacionDetalleView,
)
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


def _bulk_url():
    return reverse("solicitudes:inspector_justificaciones_bulk")


def _dashboard_url():
    return reverse("solicitudes:inspector_justificaciones_dashboard")


def _msgs(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


# -------------------------------------------------------------------- #
# Access control
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestAccesoControl:
    def test_anonymous_redirects_to_login_on_post(self, client):
        sol = _make_justificacion()
        resp = client.post(
            _bulk_url(),
            {"solicitud_ids": [sol.pk], "accion": "aprobar"},
        )
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
        resp = client.post(
            _bulk_url(),
            {"solicitud_ids": [sol.pk], "accion": "aprobar"},
        )
        assert resp.status_code == 403
        sol.refresh_from_db()
        assert sol.estado == Solicitud.EstadoSolicitud.PENDIENTE

    def test_get_returns_405(self, client):
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        resp = client.get(_bulk_url())
        assert resp.status_code == 405

    def test_inspector_post_aprobar_ok_smoke(self, client):
        sol = _make_justificacion()
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        resp = client.post(
            _bulk_url(),
            {"solicitud_ids": [sol.pk], "accion": "aprobar"},
        )
        assert resp.status_code == 302
        assert resp.url == _dashboard_url()


# -------------------------------------------------------------------- #
# URL ordering
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestURLOrdering:
    def test_bulk_url_resolves_to_bulk_view(self):
        """``inspector/justificaciones/bulk/`` debe resolver a la vista bulk,
        no ser tragado por el converter ``<int:pk>``."""
        match = resolve("/solicitudes/inspector/justificaciones/bulk/")
        assert match.func.view_class is InspectorBulkActionView

    def test_int_pk_url_resolves_to_detalle(self):
        """Sanity: una URL con pk entero sigue resolviendo al detalle."""
        match = resolve("/solicitudes/inspector/justificaciones/42/")
        assert match.func.view_class is InspectorJustificacionDetalleView


# -------------------------------------------------------------------- #
# Aprobar bulk — happy path
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestAprobarBulkHappyPath:
    def _setup(self, client):
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        return inspector

    def test_bulk_aprobar_procesa_todas_pendientes(self, client):
        self._setup(client)
        sols = [_make_justificacion() for _ in range(3)]
        ids = [s.pk for s in sols]
        resp = client.post(
            _bulk_url(),
            {"solicitud_ids": ids, "accion": "aprobar"},
        )
        assert resp.status_code == 302
        for s in sols:
            s.refresh_from_db()
            assert s.estado == Solicitud.EstadoSolicitud.APROBADA
        msgs = _msgs(resp)
        assert any("Procesadas: 3" in m for m in msgs), msgs

    def test_bulk_aprobar_crea_historial_por_fila(self, client):
        self._setup(client)
        sols = [_make_justificacion() for _ in range(3)]
        ids = [s.pk for s in sols]
        client.post(
            _bulk_url(),
            {"solicitud_ids": ids, "accion": "aprobar"},
        )
        for s in sols:
            s.refresh_from_db()
            assert s.historial.count() == 1

    def test_bulk_aprobar_omite_ya_resueltas(self, client):
        self._setup(client)
        pendientes = [_make_justificacion() for _ in range(2)]
        ya_aprobada = _make_justificacion(estado=Solicitud.EstadoSolicitud.APROBADA)
        ids = [s.pk for s in pendientes] + [ya_aprobada.pk]
        resp = client.post(
            _bulk_url(),
            {"solicitud_ids": ids, "accion": "aprobar"},
        )
        assert resp.status_code == 302
        for s in pendientes:
            s.refresh_from_db()
            assert s.estado == Solicitud.EstadoSolicitud.APROBADA
        ya_aprobada.refresh_from_db()
        assert ya_aprobada.estado == Solicitud.EstadoSolicitud.APROBADA
        msgs = _msgs(resp)
        assert any("Procesadas: 2" in m for m in msgs), msgs
        assert any("Omitidas (ya resueltas): 1" in m for m in msgs), msgs


# -------------------------------------------------------------------- #
# Rechazar bulk
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestRechazarBulk:
    def _setup(self, client):
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        return inspector

    def test_bulk_rechazar_con_comentario_happy_path(self, client):
        self._setup(client)
        sols = [_make_justificacion() for _ in range(2)]
        ids = [s.pk for s in sols]
        resp = client.post(
            _bulk_url(),
            {
                "solicitud_ids": ids,
                "accion": "rechazar",
                "comentario": "Documento ilegible",
            },
        )
        assert resp.status_code == 302
        for s in sols:
            s.refresh_from_db()
            assert s.estado == Solicitud.EstadoSolicitud.RECHAZADA
            assert "ilegible" in s.respuesta.lower()
        msgs = _msgs(resp)
        assert any("Procesadas: 2" in m for m in msgs), msgs

    def test_bulk_rechazar_sin_comentario_zero_writes(self, client):
        self._setup(client)
        sols = [_make_justificacion() for _ in range(2)]
        ids = [s.pk for s in sols]
        antes_historial_total = sum(s.historial.count() for s in sols)
        resp = client.post(
            _bulk_url(),
            {"solicitud_ids": ids, "accion": "rechazar", "comentario": ""},
        )
        assert resp.status_code == 302
        # ZERO escrituras: todas siguen PENDIENTE, sin nuevo historial.
        for s in sols:
            s.refresh_from_db()
            assert s.estado == Solicitud.EstadoSolicitud.PENDIENTE
        despues_historial_total = sum(s.historial.count() for s in sols)
        assert despues_historial_total == antes_historial_total
        msgs = _msgs(resp)
        assert any("comentario" in m.lower() for m in msgs), msgs

    def test_bulk_rechazar_solo_espacios_zero_writes(self, client):
        self._setup(client)
        sols = [_make_justificacion() for _ in range(2)]
        ids = [s.pk for s in sols]
        resp = client.post(
            _bulk_url(),
            {"solicitud_ids": ids, "accion": "rechazar", "comentario": "    "},
        )
        assert resp.status_code == 302
        for s in sols:
            s.refresh_from_db()
            assert s.estado == Solicitud.EstadoSolicitud.PENDIENTE
        msgs = _msgs(resp)
        assert any("comentario" in m.lower() for m in msgs), msgs


# -------------------------------------------------------------------- #
# Validaciones
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestValidaciones:
    def _setup(self, client):
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        return inspector

    def test_bulk_sin_ids_seleccionados(self, client):
        self._setup(client)
        sol = _make_justificacion()
        resp = client.post(_bulk_url(), {"accion": "aprobar"})
        assert resp.status_code == 302
        sol.refresh_from_db()
        assert sol.estado == Solicitud.EstadoSolicitud.PENDIENTE
        msgs = _msgs(resp)
        # Mensaje obligatorio de "seleccioná al menos una".
        assert any("seleccion" in m.lower() for m in msgs), msgs

    def test_bulk_ids_vacios_explicitos(self, client):
        self._setup(client)
        sol = _make_justificacion()
        resp = client.post(_bulk_url(), {"solicitud_ids": [], "accion": "aprobar"})
        assert resp.status_code == 302
        sol.refresh_from_db()
        assert sol.estado == Solicitud.EstadoSolicitud.PENDIENTE
        msgs = _msgs(resp)
        assert any("seleccion" in m.lower() for m in msgs), msgs

    def test_bulk_accion_invalida(self, client):
        """Acción inválida: el service cuenta la fila como omitida
        silenciosa (per-row try/except en T3). Cero escrituras en estado."""
        self._setup(client)
        sol = _make_justificacion()
        antes_count = sol.historial.count()
        resp = client.post(
            _bulk_url(),
            {"solicitud_ids": [sol.pk], "accion": "otra"},
        )
        assert resp.status_code == 302
        sol.refresh_from_db()
        assert sol.estado == Solicitud.EstadoSolicitud.PENDIENTE
        assert sol.historial.count() == antes_count

    def test_bulk_ids_no_numericos_son_ignorados(self, client):
        self._setup(client)
        sol = _make_justificacion()
        resp = client.post(
            _bulk_url(),
            {
                "solicitud_ids": ["abc", str(sol.pk), "xyz"],
                "accion": "aprobar",
            },
        )
        assert resp.status_code == 302
        sol.refresh_from_db()
        # Solo el id numérico válido fue procesado.
        assert sol.estado == Solicitud.EstadoSolicitud.APROBADA

    def test_bulk_id_inexistente_ignorado_silenciosamente(self, client):
        self._setup(client)
        resp = client.post(
            _bulk_url(),
            {"solicitud_ids": [99999], "accion": "aprobar"},
        )
        assert resp.status_code == 302
        msgs = _msgs(resp)
        # filter `id__in` no matchea → procesadas=0, omitidas=0.
        assert any("Procesadas: 0" in m for m in msgs), msgs

    def test_bulk_id_no_justificacion_ignorado(self, client):
        self._setup(client)
        # Crear una solicitud RECTIFICACION (no JUSTIFICACION).
        estudiante = EstudianteFactory()
        estudiante.save()
        sol_recti = SolicitudFactory(
            tipo=Solicitud.TipoSolicitud.RECTIFICACION,
            estudiante=estudiante,
            descripcion="No es justificacion",
        )
        antes_estado = sol_recti.estado
        resp = client.post(
            _bulk_url(),
            {"solicitud_ids": [sol_recti.pk], "accion": "aprobar"},
        )
        assert resp.status_code == 302
        sol_recti.refresh_from_db()
        # El filter pin (tipo=JUSTIFICACION) descarta la fila silenciosamente.
        assert sol_recti.estado == antes_estado


# -------------------------------------------------------------------- #
# Redirect pattern (PRG)
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestRedirectPattern:
    def test_redirect_to_dashboard_after_success(self, client):
        sol = _make_justificacion()
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        resp = client.post(
            _bulk_url(),
            {"solicitud_ids": [sol.pk], "accion": "aprobar"},
        )
        assert resp.status_code == 302
        assert resp.url == _dashboard_url()

    def test_redirect_to_dashboard_after_error(self, client):
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        resp = client.post(_bulk_url(), {"accion": "aprobar"})  # sin ids
        assert resp.status_code == 302
        assert resp.url == _dashboard_url()


# -------------------------------------------------------------------- #
# Message rendering
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestMessageRendering:
    def test_success_message_incluye_procesadas_y_omitidas(self, client):
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        sols = [_make_justificacion() for _ in range(2)]
        resp = client.post(
            _bulk_url(),
            {
                "solicitud_ids": [s.pk for s in sols],
                "accion": "aprobar",
            },
        )
        msgs = _msgs(resp)
        text = " | ".join(msgs)
        assert "Procesadas:" in text
        assert "Omitidas" in text

    def test_error_message_visible_al_seguir_redirect(self, client):
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        _make_justificacion()  # crea una pendiente para que el dashboard renderice tabla
        resp = client.post(_bulk_url(), {"accion": "aprobar"}, follow=True)
        # Tras seguir el redirect, el mensaje error debe estar en el HTML.
        assert resp.status_code == 200
        html = resp.content.decode("utf-8").lower()
        assert "seleccion" in html


# -------------------------------------------------------------------- #
# Modal + form rendering en el dashboard
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestModalDashboard:
    def test_dashboard_renderiza_form_bulk_y_modal(self, client):
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        _make_justificacion()  # al menos una fila para que la tabla renderice
        resp = client.get(_dashboard_url())
        assert resp.status_code == 200
        html = resp.content.decode("utf-8")
        # form bulk-form + action a la URL bulk + csrf
        assert 'id="bulk-form"' in html
        assert 'action="' + _bulk_url() + '"' in html
        assert "csrfmiddlewaretoken" in html
        # checkboxes vinculadas al form
        assert 'name="solicitud_ids"' in html
        assert 'form="bulk-form"' in html
        # marcadores del modal Alpine
        assert "x-data" in html
        assert "x-show" in html
        # radio buttons aprobar/rechazar
        assert 'value="aprobar"' in html
        assert 'value="rechazar"' in html

    def test_dashboard_sin_pendientes_no_rompe(self, client):
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        # sin solicitudes en BD → empty state.
        resp = client.get(_dashboard_url())
        assert resp.status_code == 200
        html = resp.content.decode("utf-8")
        # el form bulk sigue presente (puede no haber filas pero el modal no rompe)
        assert 'id="bulk-form"' in html
