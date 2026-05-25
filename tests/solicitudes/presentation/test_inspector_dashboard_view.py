"""Tests for InspectorJustificacionesDashboardView (HU21 — T4).

Capability: ``inspector-justificaciones-dashboard``.

Covers spec requirements R1..R6: paginated list, filters + search, stats
panel, urgency badge classification, access control, querystring
preservation across pagination. Includes an ``assertNumQueries`` guard
against N+1 regression.
"""

import datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.asistencia.infrastructure.models import Asistencia
from apps.solicitudes.infrastructure.models import (
    CertificadoJustificacion,
    ConfiguracionJustificacion,
    Solicitud,
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


URL = reverse("solicitudes:inspector_justificaciones_dashboard")


# -------------------------------------------------------------------- #
# Helpers
# -------------------------------------------------------------------- #


def _make_justificacion(
    *,
    estudiante=None,
    paralelo=None,
    estado=Solicitud.EstadoSolicitud.PENDIENTE,
    fecha_creacion=None,
    tipo_certificado=None,
    fecha_resolucion=None,
):
    """Create a Solicitud(tipo=JUSTIFICACION) with optional Certificado + Asistencia."""
    if estudiante is None:
        estudiante = EstudianteFactory()
        estudiante.save()
    if paralelo is None:
        periodo = PeriodoFactory(activo=True)
        paralelo = ParaleloFactory(periodo=periodo)
    asistencia = AsistenciaFactory(
        estudiante=estudiante,
        paralelo=paralelo,
        estado=Asistencia.Estado.AUSENTE,
    )
    sol = SolicitudFactory(
        tipo=Solicitud.TipoSolicitud.JUSTIFICACION,
        estudiante=estudiante,
        asistencia=asistencia,
        estado=estado,
        descripcion="Test justification",
    )
    if fecha_creacion is not None:
        # ``fecha_creacion`` is auto_now_add — bypass with explicit update.
        Solicitud.objects.filter(pk=sol.pk).update(fecha_creacion=fecha_creacion)
        sol.refresh_from_db()
    if fecha_resolucion is not None:
        Solicitud.objects.filter(pk=sol.pk).update(fecha_resolucion=fecha_resolucion)
        sol.refresh_from_db()
    if tipo_certificado is not None:
        CertificadoJustificacion.objects.create(
            solicitud=sol,
            tipo=tipo_certificado,
            fecha_certificado=datetime.date(2026, 4, 1),
        )
    return sol


# -------------------------------------------------------------------- #
# R5 — Access control
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestAccesoControl:
    def test_anonymous_redirects_to_login(self, client):
        resp = client.get(URL)
        assert resp.status_code == 302
        assert "/usuarios/login/" in resp.url

    @pytest.mark.parametrize(
        "factory_callable",
        [
            lambda: EstudianteFactory(),
            lambda: DocenteFactory(),
            lambda: UsuarioFactory(rol=Usuario.Rol.SECRETARIA),
        ],
        ids=["estudiante", "docente", "secretaria"],
    )
    def test_no_inspector_forbidden(self, client, factory_callable):
        user = factory_callable()
        user.save()
        client.force_login(user)
        resp = client.get(URL)
        assert resp.status_code == 403

    def test_inspector_ok(self, client):
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        resp = client.get(URL)
        assert resp.status_code == 200


# -------------------------------------------------------------------- #
# R1 — Pagination & ordering
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestPaginacionYOrdenamiento:
    def test_paginate_by_20_first_page(self, client):
        for _ in range(45):
            _make_justificacion()
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)

        resp = client.get(URL)
        assert resp.status_code == 200
        assert len(resp.context["solicitudes"]) == 20

    def test_paginate_by_20_page_3_has_5_rows(self, client):
        for _ in range(45):
            _make_justificacion()
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)

        resp = client.get(URL + "?page=3")
        assert resp.status_code == 200
        assert len(resp.context["solicitudes"]) == 5

    def test_ordering_fecha_creacion_desc(self, client):
        # Create 3 solicitudes spaced 1 day apart by overriding fecha_creacion.
        base = timezone.now() - datetime.timedelta(days=10)
        sols = []
        for offset in range(3):
            sol = _make_justificacion(fecha_creacion=base + datetime.timedelta(days=offset))
            sols.append(sol)
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)

        resp = client.get(URL)
        assert resp.status_code == 200
        ordered_ids = [s.pk for s in resp.context["solicitudes"]]
        # Newest first => reverse-order of insertion.
        assert ordered_ids == [sols[2].pk, sols[1].pk, sols[0].pk]


# -------------------------------------------------------------------- #
# R2 — Filters & search
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestFiltros:
    def test_filtro_estado_pendiente(self, client):
        _make_justificacion(estado=Solicitud.EstadoSolicitud.PENDIENTE)
        _make_justificacion(estado=Solicitud.EstadoSolicitud.APROBADA)
        _make_justificacion(estado=Solicitud.EstadoSolicitud.RECHAZADA)
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)

        resp = client.get(URL + "?estado=pendiente")
        assert resp.status_code == 200
        for s in resp.context["solicitudes"]:
            assert s.estado == Solicitud.EstadoSolicitud.PENDIENTE

    def test_filtro_tipo_certificado_medico(self, client):
        _make_justificacion(tipo_certificado="medico")
        _make_justificacion(tipo_certificado="laboral")
        _make_justificacion()  # sin certificado
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)

        resp = client.get(URL + "?tipo_certificado=medico")
        assert resp.status_code == 200
        sols = list(resp.context["solicitudes"])
        assert len(sols) == 1
        assert sols[0].certificado.tipo == "medico"

    def test_filtro_paralelo(self, client):
        periodo = PeriodoFactory(activo=True)
        paralelo_a = ParaleloFactory(periodo=periodo)
        paralelo_b = ParaleloFactory(periodo=periodo)
        _make_justificacion(paralelo=paralelo_a)
        _make_justificacion(paralelo=paralelo_a)
        _make_justificacion(paralelo=paralelo_b)
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)

        resp = client.get(URL + f"?paralelo={paralelo_a.id}")
        assert resp.status_code == 200
        sols = list(resp.context["solicitudes"])
        assert len(sols) == 2
        for s in sols:
            assert s.asistencia.paralelo_id == paralelo_a.id

    def test_busqueda_q_por_first_name(self, client):
        e1 = EstudianteFactory(first_name="Mariana", last_name="Lopez")
        e1.save()
        e2 = EstudianteFactory(first_name="Pedro", last_name="Gomez")
        e2.save()
        _make_justificacion(estudiante=e1)
        _make_justificacion(estudiante=e2)
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)

        resp = client.get(URL + "?q=Mariana")
        assert resp.status_code == 200
        sols = list(resp.context["solicitudes"])
        assert len(sols) == 1
        assert sols[0].estudiante_id == e1.pk

    def test_busqueda_q_por_cedula(self, client):
        e1 = EstudianteFactory(cedula="1799999999")
        e1.save()
        e2 = EstudianteFactory(cedula="1788888888")
        e2.save()
        _make_justificacion(estudiante=e1)
        _make_justificacion(estudiante=e2)
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)

        resp = client.get(URL + "?q=1799999999")
        assert resp.status_code == 200
        sols = list(resp.context["solicitudes"])
        assert len(sols) == 1
        assert sols[0].estudiante_id == e1.pk

    def test_filtros_combinados_estado_y_q(self, client):
        e1 = EstudianteFactory(last_name="Zambrano")
        e1.save()
        e2 = EstudianteFactory(last_name="Zambrano")
        e2.save()
        _make_justificacion(estudiante=e1, estado=Solicitud.EstadoSolicitud.PENDIENTE)
        _make_justificacion(estudiante=e2, estado=Solicitud.EstadoSolicitud.APROBADA)
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)

        resp = client.get(URL + "?estado=pendiente&q=Zambrano")
        assert resp.status_code == 200
        sols = list(resp.context["solicitudes"])
        assert len(sols) == 1
        assert sols[0].estudiante_id == e1.pk


# -------------------------------------------------------------------- #
# R3 — Stats panel
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestStatsPanel:
    def test_stats_counters(self, client):
        # Force config defaults so vencidas math is predictable.
        ConfiguracionJustificacion.objects.filter(pk=1).delete()
        ConfiguracionJustificacion.get_singleton()

        today = timezone.localdate()
        now = timezone.now()

        # 3 pendientes recientes (no vencidas).
        for _ in range(3):
            _make_justificacion(
                estado=Solicitud.EstadoSolicitud.PENDIENTE,
                fecha_creacion=now,
            )
        # 1 aprobada hoy.
        _make_justificacion(
            estado=Solicitud.EstadoSolicitud.APROBADA,
            fecha_resolucion=now,
        )
        # 1 aprobada ayer.
        _make_justificacion(
            estado=Solicitud.EstadoSolicitud.APROBADA,
            fecha_resolucion=now - datetime.timedelta(days=1),
        )
        # 1 rechazada hoy.
        _make_justificacion(
            estado=Solicitud.EstadoSolicitud.RECHAZADA,
            fecha_resolucion=now,
        )
        # 1 pendiente vencida (created 30 days ago -> elapsed >> deadline=5).
        _make_justificacion(
            estado=Solicitud.EstadoSolicitud.PENDIENTE,
            fecha_creacion=now - datetime.timedelta(days=30),
        )

        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)

        resp = client.get(URL)
        assert resp.status_code == 200
        stats = resp.context["stats"]
        # 3 fresh pendientes + 1 vencida pendiente = 4 total pendientes.
        assert stats["pendientes"] == 4
        assert stats["aprobadas_hoy"] == 1
        assert stats["rechazadas_hoy"] == 1
        assert stats["vencidas"] == 1
        # Today-based filters should NOT count items resolved yesterday.
        assert today  # sanity touch


# -------------------------------------------------------------------- #
# R4 — Urgency badge precomputed per row
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestUrgenciaPorFila:
    def test_urgencia_normal_alerta_vencido(self, client):
        ConfiguracionJustificacion.objects.filter(pk=1).delete()
        ConfiguracionJustificacion.get_singleton()  # deadline=5, alerta=2

        now = timezone.now()
        # Fresh -> normal (0 business days elapsed).
        sol_normal = _make_justificacion(
            estado=Solicitud.EstadoSolicitud.PENDIENTE,
            fecha_creacion=now,
        )
        # 30 days ago -> vencido.
        sol_vencido = _make_justificacion(
            estado=Solicitud.EstadoSolicitud.PENDIENTE,
            fecha_creacion=now - datetime.timedelta(days=30),
        )

        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)

        resp = client.get(URL)
        assert resp.status_code == 200
        urgencias = {s.pk: s.urgencia for s in resp.context["solicitudes"]}
        assert urgencias[sol_normal.pk] == "normal"
        assert urgencias[sol_vencido.pk] == "vencido"

    def test_urgencia_clases_css_en_html(self, client):
        ConfiguracionJustificacion.objects.filter(pk=1).delete()
        ConfiguracionJustificacion.get_singleton()
        now = timezone.now()
        _make_justificacion(fecha_creacion=now)
        _make_justificacion(fecha_creacion=now - datetime.timedelta(days=30))

        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)

        resp = client.get(URL)
        assert resp.status_code == 200
        # Urgency badge partial uses Tailwind tokens with verde/amarillo/rojo
        # as semantic class fragments so tests can pin the visual mapping.
        body = resp.content
        assert b"badge-verde" in body or b"bg-green" in body
        assert b"badge-rojo" in body or b"bg-red" in body


# -------------------------------------------------------------------- #
# R6 — Querystring preserved across pagination
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestQuerystringPaginacion:
    def test_querystring_preservado_en_pagina_2(self, client):
        for _ in range(25):
            _make_justificacion(estado=Solicitud.EstadoSolicitud.PENDIENTE)
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)

        resp = client.get(URL + "?estado=pendiente")
        assert resp.status_code == 200
        # Pagination links must keep the filter.
        assert b"estado=pendiente" in resp.content


# -------------------------------------------------------------------- #
# Empty state
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestEstadoVacio:
    def test_sin_justificaciones(self, client):
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        resp = client.get(URL)
        assert resp.status_code == 200
        assert b"No hay justificaciones" in resp.content


# -------------------------------------------------------------------- #
# N+1 guard
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestNumQueries:
    def test_dashboard_query_budget(self, client, django_assert_max_num_queries):
        """Upper bound: 11 queries on the steady-state hot path. Breakdown:

        - 2 auth middleware (session + user)
        - 1 paginator count (page size)
        - 1 ConfiguracionJustificacion SELECT (singleton, no insert)
        - 1 main list (select_related joins inline — estudiante,
          asistencia/paralelo/asignatura, certificado, resuelto_por)
        - 1 prefetch archivos
        - 1 SELECT only(fecha_creacion) for vencidas Python loop
        - 3 stats COUNT (pendientes / aprobadas_hoy / rechazadas_hoy)
        - 1 paralelos distinct dropdown

        Total: 11. We pre-create the singleton so the one-time bootstrap
        (SAVEPOINT + INSERT + RELEASE) does not pollute the budget.
        Design recommended cap was ~8 but did not account for the
        ``paralelos`` dropdown query or the ``vencidas`` Python-side
        classifier loop; 11 is the honest steady-state ceiling.
        """
        # Pre-create the singleton so the get_or_create on the first
        # request does NOT add SAVEPOINT/INSERT/RELEASE (one-off cost
        # in production, never re-paid).
        ConfiguracionJustificacion.get_singleton()

        for _ in range(20):
            _make_justificacion()
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)

        with django_assert_max_num_queries(11):
            resp = client.get(URL)
            assert resp.status_code == 200
