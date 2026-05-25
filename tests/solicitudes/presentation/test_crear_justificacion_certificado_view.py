"""Tests for CrearJustificacionConCertificadoView (HU20 Slice 3)."""

import datetime
from unittest import mock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.notificaciones.infrastructure.models import Notificacion
from apps.solicitudes.infrastructure.models import (
    ArchivoSolicitud,
    CertificadoJustificacion,
    Solicitud,
)
from tests.factories import (
    AsistenciaFactory,
    DocenteFactory,
    EstudianteFactory,
    InspectorFactory,
    MatriculaFactory,
    ParaleloFactory,
    PeriodoFactory,
)


# -------------------------------------------------------------------- #
# Helpers
# -------------------------------------------------------------------- #


def _pdf(name="cert.pdf", size=512):
    return SimpleUploadedFile(name, b"x" * size, content_type="application/pdf")


def _yesterday_str():
    return (datetime.date.today() - datetime.timedelta(days=1)).isoformat()


def _tomorrow_str():
    return (datetime.date.today() + datetime.timedelta(days=1)).isoformat()


@pytest.fixture
def estudiante_with_asistencia(db):
    """Owner estudiante + an Asistencia they own."""
    actor = DocenteFactory()
    actor.save()
    periodo = PeriodoFactory(activo=True)
    paralelo = ParaleloFactory(periodo=periodo)
    estudiante = EstudianteFactory()
    estudiante.save()
    MatriculaFactory(estudiante=estudiante, paralelo=paralelo, matriculado_por=actor)
    asistencia = AsistenciaFactory(estudiante=estudiante, paralelo=paralelo)
    return estudiante, asistencia


def _url(asistencia_id):
    return reverse("solicitudes:crear_justificacion_certificado", args=[asistencia_id])


def _post_data_medico():
    return {
        "tipo_certificado": "medico",
        "motivo": "Estuve enfermo, adjunto certificado.",
        "institucion_emisora": "Hospital MSP",
        "fecha_certificado": _yesterday_str(),
        "numero_documento": "MED-001",
        "nombre_medico": "Dra. Pérez",
        "dias_reposo": 3,
    }


def _post_data_laboral():
    return {
        "tipo_certificado": "laboral",
        "motivo": "Reunión laboral.",
        "institucion_emisora": "Empresa SA",
        "fecha_certificado": _yesterday_str(),
        "cargo": "Analista",
    }


def _post_data_calamidad():
    return {
        "tipo_certificado": "calamidad",
        "motivo": "Calamidad doméstica.",
        "fecha_certificado": _yesterday_str(),
        "descripcion_evento": "Fallecimiento familiar.",
        "relacion_familiar": "padre",
    }


# -------------------------------------------------------------------- #
# Access control
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestAccesoControl:
    def test_anonymous_get_redirects_to_login(self, client, estudiante_with_asistencia):
        _, asistencia = estudiante_with_asistencia
        resp = client.get(_url(asistencia.id))
        assert resp.status_code == 302
        assert "/usuarios/login/" in resp.url

    def test_anonymous_post_redirects_to_login(self, client, estudiante_with_asistencia):
        _, asistencia = estudiante_with_asistencia
        resp = client.post(_url(asistencia.id), data={})
        assert resp.status_code == 302
        assert "/usuarios/login/" in resp.url

    def test_no_estudiante_get_403(self, client, estudiante_with_asistencia):
        _, asistencia = estudiante_with_asistencia
        docente = DocenteFactory()
        docente.save()
        client.force_login(docente)
        resp = client.get(_url(asistencia.id))
        assert resp.status_code == 403

    def test_inspector_get_403(self, client, estudiante_with_asistencia):
        _, asistencia = estudiante_with_asistencia
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        resp = client.get(_url(asistencia.id))
        assert resp.status_code == 403

    def test_estudiante_no_owner_403(self, client, estudiante_with_asistencia):
        _, asistencia = estudiante_with_asistencia
        otro = EstudianteFactory()
        otro.save()
        client.force_login(otro)
        resp = client.get(_url(asistencia.id))
        assert resp.status_code == 403


# -------------------------------------------------------------------- #
# GET render
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestGet:
    def test_estudiante_owner_get_200(self, client, estudiante_with_asistencia):
        estudiante, asistencia = estudiante_with_asistencia
        client.force_login(estudiante)
        resp = client.get(_url(asistencia.id))
        assert resp.status_code == 200
        # Form is in context
        assert "form" in resp.context
        # Template renders the tipo select
        assert b"tipo_certificado" in resp.content


# -------------------------------------------------------------------- #
# POST happy paths
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestPostHappy:
    def test_post_valido_medico_crea_solicitud_certificado_archivos(
        self, client, estudiante_with_asistencia
    ):
        estudiante, asistencia = estudiante_with_asistencia
        InspectorFactory().save()  # so the notification has a recipient
        client.force_login(estudiante)

        data = _post_data_medico()
        data["archivos"] = [_pdf("a.pdf"), _pdf("b.jpg")]
        resp = client.post(_url(asistencia.id), data=data)

        assert resp.status_code == 302
        assert Solicitud.objects.filter(estudiante=estudiante).count() == 1
        solicitud = Solicitud.objects.get(estudiante=estudiante)
        assert solicitud.tipo == Solicitud.TipoSolicitud.JUSTIFICACION
        cert = CertificadoJustificacion.objects.get(solicitud=solicitud)
        assert cert.tipo == "medico"
        assert cert.nombre_medico == "Dra. Pérez"
        assert ArchivoSolicitud.objects.filter(solicitud=solicitud).count() == 2
        # Notification side-effect
        assert (
            Notificacion.objects.filter(tipo=Notificacion.Tipo.SOLICITUD_JUSTIFICACION).count()
            == 1
        )

    def test_post_valido_laboral(self, client, estudiante_with_asistencia):
        estudiante, asistencia = estudiante_with_asistencia
        InspectorFactory().save()
        client.force_login(estudiante)

        data = _post_data_laboral()
        data["archivos"] = [_pdf("a.pdf")]
        resp = client.post(_url(asistencia.id), data=data)

        assert resp.status_code == 302
        cert = CertificadoJustificacion.objects.get()
        assert cert.tipo == "laboral"
        assert cert.cargo == "Analista"

    def test_post_valido_calamidad(self, client, estudiante_with_asistencia):
        estudiante, asistencia = estudiante_with_asistencia
        InspectorFactory().save()
        client.force_login(estudiante)

        data = _post_data_calamidad()
        data["archivos"] = [_pdf("a.pdf")]
        resp = client.post(_url(asistencia.id), data=data)

        assert resp.status_code == 302
        cert = CertificadoJustificacion.objects.get()
        assert cert.tipo == "calamidad"
        assert cert.descripcion_evento == "Fallecimiento familiar."


# -------------------------------------------------------------------- #
# POST invalid → form re-rendered with errors / messages
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestPostInvalido:
    def test_post_sin_archivos_re_renderiza_con_error(self, client, estudiante_with_asistencia):
        estudiante, asistencia = estudiante_with_asistencia
        client.force_login(estudiante)
        data = _post_data_medico()
        # no archivos
        resp = client.post(_url(asistencia.id), data=data)
        assert resp.status_code == 200
        assert Solicitud.objects.count() == 0
        assert "archivos" in resp.context["form"].errors

    def test_post_fecha_futura_re_renderiza_con_mensaje_error(
        self, client, estudiante_with_asistencia
    ):
        """Backend domain validation: FechaCertificadoInvalidaError → 200 with error message."""
        estudiante, asistencia = estudiante_with_asistencia
        client.force_login(estudiante)

        data = _post_data_laboral()
        data["fecha_certificado"] = _tomorrow_str()
        data["archivos"] = [_pdf("a.pdf")]
        resp = client.post(_url(asistencia.id), data=data)

        assert resp.status_code == 200
        assert Solicitud.objects.count() == 0
        # Error surfaced via messages framework
        msgs = [m.message for m in resp.context["messages"]]
        assert any("fecha" in m.lower() for m in msgs)

    def test_post_campos_obligatorios_faltantes_re_renderiza(
        self, client, estudiante_with_asistencia
    ):
        estudiante, asistencia = estudiante_with_asistencia
        client.force_login(estudiante)
        data = _post_data_medico()
        data["nombre_medico"] = ""
        data["archivos"] = [_pdf("a.pdf")]
        resp = client.post(_url(asistencia.id), data=data)
        assert resp.status_code == 200
        assert Solicitud.objects.count() == 0
        assert "nombre_medico" in resp.context["form"].errors

    def test_post_maximo_archivos_excedido_via_form(self, client, estudiante_with_asistencia):
        """Form-level enforcement of MAX_ARCHIVOS=5."""
        estudiante, asistencia = estudiante_with_asistencia
        client.force_login(estudiante)
        data = _post_data_laboral()
        data["archivos"] = [_pdf(f"a{i}.pdf") for i in range(6)]
        resp = client.post(_url(asistencia.id), data=data)
        assert resp.status_code == 200
        assert Solicitud.objects.count() == 0
        assert "archivos" in resp.context["form"].errors

    def test_post_app_service_exception_se_renderiza_mensaje(
        self, client, estudiante_with_asistencia
    ):
        """If AppService raises a domain exception, view maps to messages.error."""
        from apps.solicitudes.domain.exceptions import ArchivoInvalidoError

        estudiante, asistencia = estudiante_with_asistencia
        client.force_login(estudiante)
        data = _post_data_laboral()
        data["archivos"] = [_pdf("a.pdf")]
        with mock.patch(
            "apps.solicitudes.presentation.views."
            "JustificacionCertificadoAppService.crear_justificacion_con_certificado",
            side_effect=ArchivoInvalidoError("a.pdf", ["extension_invalida"]),
        ):
            resp = client.post(_url(asistencia.id), data=data)
        assert resp.status_code == 200
        assert Solicitud.objects.count() == 0
        msgs = [m.message for m in resp.context["messages"]]
        assert any("a.pdf" in m for m in msgs)
