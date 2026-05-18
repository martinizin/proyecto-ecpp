"""
Tests for HU19 — Flujo de aprobación de rectificaciones y justificaciones.

Covers: service layer (listados, tomar, escalar, resolver) + view layer.
"""

from decimal import Decimal

import datetime

import pytest
from django.urls import reverse

from apps.asistencia.infrastructure.models import Asistencia
from apps.calificaciones.infrastructure.models import (
    LogCalificacion,
    RegistroCalificacionParalelo,
)
from apps.notificaciones.infrastructure.models import Notificacion
from apps.solicitudes.application.services import SolicitudAppService
from apps.solicitudes.infrastructure.models import HistorialSolicitud
from tests.factories import (
    AsistenciaFactory,
    CalificacionFactory,
    DocenteFactory,
    EstudianteFactory,
    EvaluacionFactory,
    InspectorFactory,
    MatriculaFactory,
    ParaleloFactory,
    PeriodoFactory,
    RegistroCalificacionParaleloFactory,
    SolicitudFactory,
    UsuarioFactory,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _setup_recalificacion_chain(docente=None, estudiante=None):
    """Build the full chain: periodo → paralelo → matricula → evaluacion → calificacion → registro.

    Returns (estudiante, docente, calificacion, paralelo).
    """
    periodo = PeriodoFactory(activo=True)
    if docente is None:
        docente = DocenteFactory()
        docente.save()
    paralelo = ParaleloFactory(periodo=periodo, docente=docente)
    if estudiante is None:
        estudiante = EstudianteFactory()
        estudiante.save()
    MatriculaFactory(estudiante=estudiante, paralelo=paralelo)
    RegistroCalificacionParaleloFactory(
        paralelo=paralelo, estado=RegistroCalificacionParalelo.Estado.VALIDADO
    )
    evaluacion = EvaluacionFactory(paralelo=paralelo)
    calificacion = CalificacionFactory(evaluacion=evaluacion, estudiante=estudiante)
    return estudiante, docente, calificacion, paralelo


def _make_rectificacion_solicitud(
    estudiante, calificacion, estado="pendiente", requiere_secretaria=False, numero=1
):
    return SolicitudFactory(
        tipo="rectificacion",
        calificacion=calificacion,
        estudiante=estudiante,
        estado=estado,
        requiere_secretaria=requiere_secretaria,
        numero_solicitud=numero,
    )


def _make_justificacion_solicitud(estudiante, paralelo, estado="pendiente", fecha=None):
    asistencia = AsistenciaFactory(
        estudiante=estudiante,
        paralelo=paralelo,
        estado=Asistencia.Estado.AUSENTE,
        fecha=fecha or datetime.date(2026, 4, 1),
    )
    return SolicitudFactory(
        tipo="justificacion",
        asistencia=asistencia,
        estudiante=estudiante,
        estado=estado,
    )


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE TESTS — Listados
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestObtenerPendientesDocente:
    def test_obtener_pendientes_docente_1ra_solicitud(self):
        """1ra solicitud: PENDIENTE + requiere_secretaria=False → appears for docente."""
        est, doc, cal, _ = _setup_recalificacion_chain()
        sol = _make_rectificacion_solicitud(
            est, cal, estado="pendiente", requiere_secretaria=False
        )

        qs = SolicitudAppService.obtener_pendientes_docente(doc)
        assert sol in qs

    def test_obtener_pendientes_docente_2da_escalada(self):
        """2da+ solicitud: EN_REVISION + requiere_secretaria=True → appears for docente."""
        est, doc, cal, _ = _setup_recalificacion_chain()
        sol = _make_rectificacion_solicitud(
            est, cal, estado="en_revision", requiere_secretaria=True, numero=2
        )

        qs = SolicitudAppService.obtener_pendientes_docente(doc)
        assert sol in qs

    def test_obtener_pendientes_docente_excluye_otros(self):
        """Solicitudes from other docentes' paralelos are NOT returned."""
        est, doc1, cal, _ = _setup_recalificacion_chain()
        _make_rectificacion_solicitud(est, cal, estado="pendiente", requiere_secretaria=False)

        doc2 = DocenteFactory()
        doc2.save()
        qs = SolicitudAppService.obtener_pendientes_docente(doc2)
        assert qs.count() == 0


@pytest.mark.django_db
class TestObtenerPendientesSecretaria:
    def test_obtener_pendientes_secretaria(self):
        """PENDIENTE + requiere_secretaria=True rectificaciones → appears for secretaria."""
        est, _, cal, _ = _setup_recalificacion_chain()
        sol = _make_rectificacion_solicitud(
            est, cal, estado="pendiente", requiere_secretaria=True, numero=2
        )

        qs = SolicitudAppService.obtener_pendientes_secretaria()
        assert sol in qs


@pytest.mark.django_db
class TestObtenerPendientesJustificacion:
    def test_obtener_pendientes_justificacion(self):
        """PENDIENTE and EN_REVISION justificaciones are returned."""
        est, _, _, paralelo = _setup_recalificacion_chain()
        sol_pend = _make_justificacion_solicitud(est, paralelo, estado="pendiente")
        sol_rev = _make_justificacion_solicitud(
            est, paralelo, estado="en_revision", fecha=datetime.date(2026, 4, 2)
        )

        qs = SolicitudAppService.obtener_pendientes_justificacion()
        assert sol_pend in qs
        assert sol_rev in qs


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE TESTS — Tomar solicitud
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestTomarSolicitud:
    def test_tomar_solicitud_exitoso(self):
        """PENDIENTE → EN_REVISION, creates HistorialSolicitud and Notificacion for student."""
        est, doc, cal, _ = _setup_recalificacion_chain()
        sol = _make_rectificacion_solicitud(est, cal)

        result = SolicitudAppService.tomar_solicitud(sol.pk, doc)

        assert result["ok"] is True
        sol.refresh_from_db()
        assert sol.estado == "en_revision"
        assert HistorialSolicitud.objects.filter(
            solicitud=sol, estado_anterior="pendiente", estado_nuevo="en_revision"
        ).exists()
        assert Notificacion.objects.filter(
            destinatario=est, tipo=Notificacion.Tipo.CAMBIO_ESTADO_SOLICITUD
        ).exists()

    def test_tomar_solicitud_no_pendiente(self):
        """Returns error if already EN_REVISION."""
        est, doc, cal, _ = _setup_recalificacion_chain()
        sol = _make_rectificacion_solicitud(est, cal, estado="en_revision")

        result = SolicitudAppService.tomar_solicitud(sol.pk, doc)
        assert result["ok"] is False
        assert "pendientes" in result["error"].lower()

    def test_tomar_solicitud_no_encontrada(self):
        """Returns error for non-existent solicitud."""
        doc = DocenteFactory()
        doc.save()
        result = SolicitudAppService.tomar_solicitud(99999, doc)
        assert result["ok"] is False
        assert "no encontrada" in result["error"].lower()


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE TESTS — Escalar a docente
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestEscalarADocente:
    def test_escalar_a_docente_exitoso(self):
        """PENDIENTE+requiere_secretaria → EN_REVISION; HistorialSolicitud + Notificaciones."""
        est, doc, cal, _ = _setup_recalificacion_chain()
        sol = _make_rectificacion_solicitud(
            est, cal, estado="pendiente", requiere_secretaria=True, numero=2
        )
        secretaria = UsuarioFactory(rol="secretaria", username="secr_esc")
        secretaria.save()

        result = SolicitudAppService.escalar_a_docente(sol.pk, secretaria)

        assert result["ok"] is True
        sol.refresh_from_db()
        assert sol.estado == "en_revision"
        assert HistorialSolicitud.objects.filter(solicitud=sol).exists()
        # Notificacion for docente
        assert Notificacion.objects.filter(
            destinatario=doc, tipo=Notificacion.Tipo.SOLICITUD_RECALIFICACION
        ).exists()
        # Notificacion for student
        assert Notificacion.objects.filter(
            destinatario=est, tipo=Notificacion.Tipo.CAMBIO_ESTADO_SOLICITUD
        ).exists()

    def test_escalar_no_requiere_secretaria(self):
        """Returns error if requiere_secretaria=False."""
        est, _, cal, _ = _setup_recalificacion_chain()
        sol = _make_rectificacion_solicitud(est, cal, requiere_secretaria=False)
        secretaria = UsuarioFactory(rol="secretaria", username="secr_nr")
        secretaria.save()

        result = SolicitudAppService.escalar_a_docente(sol.pk, secretaria)
        assert result["ok"] is False
        assert "no requiere" in result["error"].lower()

    def test_escalar_no_pendiente(self):
        """Returns error if not PENDIENTE."""
        est, _, cal, _ = _setup_recalificacion_chain()
        sol = _make_rectificacion_solicitud(
            est, cal, estado="en_revision", requiere_secretaria=True, numero=2
        )
        secretaria = UsuarioFactory(rol="secretaria", username="secr_np")
        secretaria.save()

        result = SolicitudAppService.escalar_a_docente(sol.pk, secretaria)
        assert result["ok"] is False
        assert "pendientes" in result["error"].lower()


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE TESTS — Resolver solicitud (Recalificación)
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestResolverRecalificacion:
    def test_aprobar_recalificacion_cambia_nota(self):
        """Approving changes Calificacion.nota and creates LogCalificacion RECALIFICACION."""
        est, doc, cal, _ = _setup_recalificacion_chain()
        sol = _make_rectificacion_solicitud(est, cal, estado="en_revision")

        result = SolicitudAppService.resolver_solicitud(
            sol.pk, doc, "aprobar", comentario="Nota corregida", nueva_nota="15.00"
        )

        assert result["ok"] is True
        cal.refresh_from_db()
        assert cal.nota == Decimal("15.00")
        assert LogCalificacion.objects.filter(
            calificacion=cal, accion=LogCalificacion.TipoAccion.RECALIFICACION
        ).exists()

    def test_aprobar_recalificacion_sin_nota(self):
        """Returns error 'Debe indicar la nueva nota'."""
        est, doc, cal, _ = _setup_recalificacion_chain()
        sol = _make_rectificacion_solicitud(est, cal, estado="en_revision")

        result = SolicitudAppService.resolver_solicitud(sol.pk, doc, "aprobar")
        assert result["ok"] is False
        assert "nueva nota" in result["error"].lower()

    def test_aprobar_recalificacion_nota_invalida(self):
        """Returns error for non-numeric nota."""
        est, doc, cal, _ = _setup_recalificacion_chain()
        sol = _make_rectificacion_solicitud(est, cal, estado="en_revision")

        result = SolicitudAppService.resolver_solicitud(sol.pk, doc, "aprobar", nueva_nota="abc")
        assert result["ok"] is False
        assert "numérico" in result["error"].lower()

    def test_aprobar_recalificacion_nota_fuera_rango(self):
        """Returns error for nota > 20 or < 0."""
        est, doc, cal, _ = _setup_recalificacion_chain()
        sol = _make_rectificacion_solicitud(est, cal, estado="en_revision")

        result = SolicitudAppService.resolver_solicitud(sol.pk, doc, "aprobar", nueva_nota="25")
        assert result["ok"] is False
        assert "entre 0 y 20" in result["error"].lower()

        # Also test negative
        sol2 = _make_rectificacion_solicitud(est, cal, estado="en_revision")
        result2 = SolicitudAppService.resolver_solicitud(sol2.pk, doc, "aprobar", nueva_nota="-1")
        assert result2["ok"] is False

    def test_rechazar_recalificacion(self):
        """Estado=RECHAZADA, respuesta set, HistorialSolicitud created."""
        est, doc, cal, _ = _setup_recalificacion_chain()
        sol = _make_rectificacion_solicitud(est, cal, estado="en_revision")

        result = SolicitudAppService.resolver_solicitud(
            sol.pk, doc, "rechazar", comentario="No procede"
        )

        assert result["ok"] is True
        sol.refresh_from_db()
        assert sol.estado == "rechazada"
        assert sol.respuesta == "No procede"
        assert HistorialSolicitud.objects.filter(solicitud=sol, estado_nuevo="rechazada").exists()

    def test_rechazar_sin_comentario(self):
        """Returns error 'Debe indicar el motivo del rechazo'."""
        est, doc, cal, _ = _setup_recalificacion_chain()
        sol = _make_rectificacion_solicitud(est, cal, estado="en_revision")

        result = SolicitudAppService.resolver_solicitud(sol.pk, doc, "rechazar", comentario="")
        assert result["ok"] is False
        assert "motivo del rechazo" in result["error"].lower()


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE TESTS — Resolver solicitud (Justificación)
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestResolverJustificacion:
    def test_aprobar_justificacion_cambia_asistencia(self):
        """Asistencia.estado changes from AUSENTE to JUSTIFICADO."""
        est, _, _, paralelo = _setup_recalificacion_chain()
        asistencia = AsistenciaFactory(
            estudiante=est, paralelo=paralelo, estado=Asistencia.Estado.AUSENTE
        )
        sol = SolicitudFactory(
            tipo="justificacion", asistencia=asistencia, estudiante=est, estado="en_revision"
        )
        inspector = InspectorFactory()
        inspector.save()

        result = SolicitudAppService.resolver_solicitud(
            sol.pk, inspector, "aprobar", comentario="Justificado"
        )

        assert result["ok"] is True
        asistencia.refresh_from_db()
        assert asistencia.estado == Asistencia.Estado.JUSTIFICADO

    def test_rechazar_justificacion(self):
        """Estado=RECHAZADA, asistencia stays AUSENTE."""
        est, _, _, paralelo = _setup_recalificacion_chain()
        asistencia = AsistenciaFactory(
            estudiante=est, paralelo=paralelo, estado=Asistencia.Estado.AUSENTE
        )
        sol = SolicitudFactory(
            tipo="justificacion", asistencia=asistencia, estudiante=est, estado="en_revision"
        )
        inspector = InspectorFactory()
        inspector.save()

        result = SolicitudAppService.resolver_solicitud(
            sol.pk, inspector, "rechazar", comentario="Sin evidencia"
        )

        assert result["ok"] is True
        asistencia.refresh_from_db()
        assert asistencia.estado == Asistencia.Estado.AUSENTE


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE TESTS — Historial y Notificaciones
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestHistorialYNotificaciones:
    def test_historial_registrado_en_cada_transicion(self):
        """After tomar + resolver, 2 HistorialSolicitud entries exist."""
        est, doc, cal, _ = _setup_recalificacion_chain()
        sol = _make_rectificacion_solicitud(est, cal)

        SolicitudAppService.tomar_solicitud(sol.pk, doc)
        SolicitudAppService.resolver_solicitud(
            sol.pk, doc, "aprobar", comentario="OK", nueva_nota="10"
        )

        assert HistorialSolicitud.objects.filter(solicitud=sol).count() == 2

    def test_notificacion_estudiante_en_cambio_estado(self):
        """Notificacion created for student with tipo=CAMBIO_ESTADO_SOLICITUD."""
        est, doc, cal, _ = _setup_recalificacion_chain()
        sol = _make_rectificacion_solicitud(est, cal)

        SolicitudAppService.tomar_solicitud(sol.pk, doc)

        assert Notificacion.objects.filter(
            destinatario=est, tipo=Notificacion.Tipo.CAMBIO_ESTADO_SOLICITUD
        ).exists()


# ══════════════════════════════════════════════════════════════════════════════
# VIEW TESTS
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestPendientesDocenteView:
    def test_pendientes_docente_get_200(self, client):
        docente = DocenteFactory()
        docente.save()
        client.force_login(docente)
        resp = client.get(reverse("solicitudes:pendientes_docente"))
        assert resp.status_code == 200

    def test_pendientes_docente_get_prohibido_estudiante(self, client):
        est = EstudianteFactory()
        est.save()
        client.force_login(est)
        resp = client.get(reverse("solicitudes:pendientes_docente"))
        assert resp.status_code in (302, 403)


@pytest.mark.django_db
class TestPendientesSecretariaView:
    def test_pendientes_secretaria_get_200(self, client):
        secretaria = UsuarioFactory(rol="secretaria", username="secretaria0")
        secretaria.save()
        client.force_login(secretaria)
        resp = client.get(reverse("solicitudes:pendientes_secretaria"))
        assert resp.status_code == 200


@pytest.mark.django_db
class TestPendientesJustificacionView:
    def test_pendientes_justificacion_get_200(self, client):
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        resp = client.get(reverse("solicitudes:pendientes_justificacion"))
        assert resp.status_code == 200


@pytest.mark.django_db
class TestResolverSolicitudView:
    def _setup_with_login(self, client, rol="docente"):
        est, doc, cal, paralelo = _setup_recalificacion_chain()
        sol = _make_rectificacion_solicitud(est, cal)
        if rol == "docente":
            user = doc
        elif rol == "secretaria":
            user = UsuarioFactory(rol="secretaria", username="secr_view")
            user.save()
        elif rol == "inspector":
            user = InspectorFactory()
            user.save()
        else:
            user = doc
        client.force_login(user)
        return sol, user, est, doc, cal

    def test_resolver_solicitud_get_200(self, client):
        sol, *_ = self._setup_with_login(client, "docente")
        resp = client.get(reverse("solicitudes:resolver_solicitud", kwargs={"pk": sol.pk}))
        assert resp.status_code == 200

    def test_resolver_solicitud_post_tomar(self, client):
        sol, *_ = self._setup_with_login(client, "docente")
        resp = client.post(
            reverse("solicitudes:resolver_solicitud", kwargs={"pk": sol.pk}),
            {"accion": "tomar"},
        )
        assert resp.status_code == 302
        sol.refresh_from_db()
        assert sol.estado == "en_revision"

    def test_resolver_solicitud_post_aprobar_recalificacion(self, client):
        est, doc, cal, _ = _setup_recalificacion_chain()
        sol = _make_rectificacion_solicitud(est, cal, estado="en_revision")
        client.force_login(doc)

        resp = client.post(
            reverse("solicitudes:resolver_solicitud", kwargs={"pk": sol.pk}),
            {"accion": "aprobar", "nueva_nota": "15.00", "comentario": "Corregido"},
        )
        assert resp.status_code == 302
        cal.refresh_from_db()
        assert cal.nota == Decimal("15.00")

    def test_resolver_solicitud_post_rechazar(self, client):
        est, doc, cal, _ = _setup_recalificacion_chain()
        sol = _make_rectificacion_solicitud(est, cal, estado="en_revision")
        client.force_login(doc)

        resp = client.post(
            reverse("solicitudes:resolver_solicitud", kwargs={"pk": sol.pk}),
            {"accion": "rechazar", "comentario": "No procede"},
        )
        assert resp.status_code == 302
        sol.refresh_from_db()
        assert sol.estado == "rechazada"

    def test_resolver_solicitud_post_escalar(self, client):
        est, doc, cal, _ = _setup_recalificacion_chain()
        sol = _make_rectificacion_solicitud(
            est, cal, estado="pendiente", requiere_secretaria=True, numero=2
        )
        secretaria = UsuarioFactory(rol="secretaria", username="secr_esc_v")
        secretaria.save()
        client.force_login(secretaria)

        resp = client.post(
            reverse("solicitudes:resolver_solicitud", kwargs={"pk": sol.pk}),
            {"accion": "escalar", "comentario": "Validada"},
        )
        assert resp.status_code == 302
        sol.refresh_from_db()
        assert sol.estado == "en_revision"


@pytest.mark.django_db
class TestDashboardCards:
    def test_dashboard_docente_muestra_card_solicitudes(self, client):
        docente = DocenteFactory()
        docente.save()
        client.force_login(docente)
        resp = client.get(reverse("usuarios:dashboard"))
        content = resp.content.decode()
        assert "pendientes_docente" in content or "pendientes/" in content

    def test_dashboard_secretaria_muestra_card_solicitudes(self, client):
        secretaria = UsuarioFactory(rol="secretaria", username="secr_dash")
        secretaria.save()
        client.force_login(secretaria)
        resp = client.get(reverse("usuarios:dashboard"))
        content = resp.content.decode()
        assert "pendientes_secretaria" in content or "secretaria/" in content

    def test_dashboard_inspector_muestra_card_justificaciones(self, client):
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        resp = client.get(reverse("usuarios:dashboard"))
        content = resp.content.decode()
        assert "pendientes_justificacion" in content or "justificaciones/" in content
