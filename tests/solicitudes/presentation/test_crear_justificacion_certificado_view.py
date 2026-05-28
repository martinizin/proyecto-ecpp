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
        "fecha_certificado": _yesterday_str(),
        "dias_reposo": 3,
    }


def _post_data_laboral():
    return {
        "tipo_certificado": "laboral",
        "motivo": "Reunión laboral.",
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
        assert cert.dias_reposo == 3
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
        data["dias_reposo"] = ""
        data["archivos"] = [_pdf("a.pdf")]
        resp = client.post(_url(asistencia.id), data=data)
        assert resp.status_code == 200
        assert Solicitud.objects.count() == 0
        assert "dias_reposo" in resp.context["form"].errors

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


# -------------------------------------------------------------------- #
# QA simplification: template must not render the removed inputs and the
# motivo label/textarea must no longer be marked as required.
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestTemplateFormCamposEliminados:
    """End-to-end render check: the GET response of the create-justificacion
    page must not contain inputs for the 3 removed fields, and ``motivo``
    must no longer be marked as required in the template."""

    def test_template_no_renderiza_input_numero_documento(
        self, client, estudiante_with_asistencia
    ):
        estudiante, asistencia = estudiante_with_asistencia
        client.force_login(estudiante)
        resp = client.get(_url(asistencia.id))
        assert resp.status_code == 200
        assert b'name="numero_documento"' not in resp.content

    def test_template_no_renderiza_input_medico_tratante(self, client, estudiante_with_asistencia):
        # The form field is ``nombre_medico`` (label was "Médico tratante").
        estudiante, asistencia = estudiante_with_asistencia
        client.force_login(estudiante)
        resp = client.get(_url(asistencia.id))
        assert resp.status_code == 200
        assert b'name="nombre_medico"' not in resp.content

    def test_template_no_renderiza_input_institucion_emisora(
        self, client, estudiante_with_asistencia
    ):
        estudiante, asistencia = estudiante_with_asistencia
        client.force_login(estudiante)
        resp = client.get(_url(asistencia.id))
        assert resp.status_code == 200
        assert b'name="institucion_emisora"' not in resp.content

    def test_template_motivo_textarea_no_marca_required(self, client, estudiante_with_asistencia):
        """The textarea for motivo must NOT carry the HTML ``required`` attr."""
        import re

        estudiante, asistencia = estudiante_with_asistencia
        client.force_login(estudiante)
        resp = client.get(_url(asistencia.id))
        assert resp.status_code == 200
        # Find the opening tag of <textarea ... name="motivo" ...> and assert it
        # does not contain the ``required`` attribute.
        match = re.search(rb"<textarea[^>]*\bname=\"motivo\"[^>]*>", resp.content)
        assert match is not None, "motivo textarea must still be rendered"
        assert b"required" not in match.group(0)


# -------------------------------------------------------------------- #
# Regression: bug visible en QA. Con <div x-show> Alpine ocultaba
# visualmente los bloques per-tipo pero los inputs seguian VIVOS en el
# render tree del navegador y se posteaban duplicados (3 inputs
# name="fecha_certificado", uno por bloque). Django tomaba el ultimo
# valor (vacio del bloque calamidad) y rebotaba con "campo obligatorio"
# aun con la fecha llena en pantalla.
#
# El fix migra los 3 bloques per-tipo a <template x-if>. Los hijos de
# <template> viven en template.content (DocumentFragment inerte): el
# HTML los contiene pero el browser NO los postea hasta que Alpine
# los clona al evaluar la condicion en runtime. Por eso este test NO
# puede asertar "el input no esta en el HTML" — esta, pero inerte.
# Asertamos en cambio la PRESENCIA del marker estructural correcto.
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestPostNoPisaCamposPorInputsDuplicados:
    """Anti-regression del bug x-show vs x-if (bloques per-tipo)."""

    def test_bloque_medico_usa_template_x_if_no_div_x_show(
        self, client, estudiante_with_asistencia
    ):
        estudiante, asistencia = estudiante_with_asistencia
        client.force_login(estudiante)
        resp = client.get(_url(asistencia.id))
        assert resp.status_code == 200
        # Marker post-fix: bloque medico envuelto en <template x-if>
        assert b"<template x-if=\"tipo === 'medico'\">" in resp.content, (
            "El bloque MEDICO debe estar envuelto en <template x-if> para que "
            "sus inputs no se posteen cuando el tipo activo es otro."
        )
        # Anti-regression: el wrapper de fields (data-testid='fields-medico')
        # NO debe usar x-show (eso es el bug viejo).
        assert (
            b'x-show="tipo === \'medico\'" class="space-y-4" data-testid="fields-medico"'
            not in resp.content
        ), (
            "El wrapper de fields-medico no debe usar x-show: deja los inputs "
            "en el render tree y se postean duplicados con los otros bloques."
        )

    def test_bloque_laboral_usa_template_x_if_no_div_x_show(
        self, client, estudiante_with_asistencia
    ):
        estudiante, asistencia = estudiante_with_asistencia
        client.force_login(estudiante)
        resp = client.get(_url(asistencia.id))
        assert resp.status_code == 200
        assert b"<template x-if=\"tipo === 'laboral'\">" in resp.content
        assert (
            b'x-show="tipo === \'laboral\'" class="space-y-4" data-testid="fields-laboral"'
            not in resp.content
        )

    def test_bloque_calamidad_usa_template_x_if_no_div_x_show(
        self, client, estudiante_with_asistencia
    ):
        estudiante, asistencia = estudiante_with_asistencia
        client.force_login(estudiante)
        resp = client.get(_url(asistencia.id))
        assert resp.status_code == 200
        assert b"<template x-if=\"tipo === 'calamidad'\">" in resp.content
        assert (
            b'x-show="tipo === \'calamidad\'" class="space-y-4" data-testid="fields-calamidad"'
            not in resp.content
        )

    def test_inputs_per_tipo_estan_dentro_de_template_x_if(
        self, client, estudiante_with_asistencia
    ):
        """Sanidad estructural: el input fecha_certificado debe aparecer
        SOLO dentro de bloques <template x-if=...>...</template>. Si
        aparece fuera (suelto en el DOM), el bug volveria a manifestarse."""
        import re

        estudiante, asistencia = estudiante_with_asistencia
        client.force_login(estudiante)
        resp = client.get(_url(asistencia.id))
        assert resp.status_code == 200

        html = resp.content.decode("utf-8")
        # Strip todo el contenido entre <template ...> y </template>
        sin_templates = re.sub(r"<template\b[^>]*>.*?</template>", "", html, flags=re.DOTALL)
        # Despues del strip, NO debe quedar ningun input/textarea per-tipo
        # suelto. Si quedara, el bloque escapo al <template x-if>.
        assert 'name="fecha_certificado"' not in sin_templates, (
            "name='fecha_certificado' aparece FUERA de <template x-if>: el bug "
            "x-show / input-duplicado volvio a la vida."
        )
        assert 'name="dias_reposo"' not in sin_templates
        assert 'name="cargo"' not in sin_templates
        assert 'name="relacion_familiar"' not in sin_templates
        assert 'name="descripcion_evento"' not in sin_templates

    def test_post_medico_solo_con_sus_campos_es_valido(self, client, estudiante_with_asistencia):
        """Contrato HTTP post-fix: solo los campos del bloque visible se postean."""
        estudiante, asistencia = estudiante_with_asistencia
        InspectorFactory().save()
        client.force_login(estudiante)
        resp = client.post(
            _url(asistencia.id),
            data={
                "tipo_certificado": "medico",
                "fecha_certificado": _yesterday_str(),
                "dias_reposo": 2,
                "archivos": [_pdf("a.pdf")],
            },
        )
        assert resp.status_code in (200, 302)
        if resp.status_code == 200:
            assert b"Este campo es obligatorio" not in resp.content

    def test_post_laboral_solo_con_sus_campos_es_valido(self, client, estudiante_with_asistencia):
        estudiante, asistencia = estudiante_with_asistencia
        InspectorFactory().save()
        client.force_login(estudiante)
        resp = client.post(
            _url(asistencia.id),
            data={
                "tipo_certificado": "laboral",
                "fecha_certificado": _yesterday_str(),
                "cargo": "Analista",
                "archivos": [_pdf("a.pdf")],
            },
        )
        assert resp.status_code in (200, 302)
        if resp.status_code == 200:
            assert b"Este campo es obligatorio" not in resp.content

    def test_post_calamidad_solo_con_sus_campos_es_valido(
        self, client, estudiante_with_asistencia
    ):
        estudiante, asistencia = estudiante_with_asistencia
        InspectorFactory().save()
        client.force_login(estudiante)
        resp = client.post(
            _url(asistencia.id),
            data={
                "tipo_certificado": "calamidad",
                "fecha_certificado": _yesterday_str(),
                "descripcion_evento": "Fallecimiento familiar.",
                "relacion_familiar": "padre",
                "archivos": [_pdf("a.pdf")],
            },
        )
        assert resp.status_code in (200, 302)
        if resp.status_code == 200:
            assert b"Este campo es obligatorio" not in resp.content
