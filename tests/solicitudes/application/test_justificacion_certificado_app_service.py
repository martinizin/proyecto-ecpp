"""Integration tests for JustificacionCertificadoAppService (HU20 Slice 2).

Covers happy path per tipo (medico, laboral, calamidad), every domain
exception branch with atomic rollback, and notification helper invocation.
"""

import datetime
from unittest import mock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.notificaciones.infrastructure.models import Notificacion
from apps.solicitudes.application.services import (
    JustificacionCertificadoAppService,
)
from apps.solicitudes.domain.exceptions import (
    ArchivoInvalidoError,
    CamposObligatoriosFaltantesError,
    FechaCertificadoInvalidaError,
    MaximoArchivosExcedidoError,
)
from apps.solicitudes.domain.value_objects import TipoCertificado
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
# Fixtures / helpers
# -------------------------------------------------------------------- #


def _pdf(name="cert.pdf", size=1024):
    return SimpleUploadedFile(name, b"x" * size, content_type="application/pdf")


def _datos_medico():
    return {
        "institucion_emisora": "Hospital MSP",
        "fecha_certificado": datetime.date.today() - datetime.timedelta(days=1),
        "numero_documento": "MED-001",
        "nombre_medico": "Dra. Pérez",
        "dias_reposo": 3,
    }


def _datos_laboral():
    return {
        "institucion_emisora": "Empresa XYZ S.A.",
        "fecha_certificado": datetime.date.today() - datetime.timedelta(days=2),
        "cargo": "Analista",
    }


def _datos_calamidad():
    return {
        "fecha_certificado": datetime.date.today() - datetime.timedelta(days=1),
        "descripcion_evento": "Fallecimiento de familiar directo.",
        "relacion_familiar": "padre",
    }


@pytest.fixture
def setup_estudiante_asistencia(db):
    """Build a fully-related estudiante + asistencia without leaking inspectors."""
    actor = DocenteFactory()
    actor.save()
    periodo = PeriodoFactory(activo=True)
    paralelo = ParaleloFactory(periodo=periodo)
    estudiante = EstudianteFactory()
    estudiante.save()
    MatriculaFactory(estudiante=estudiante, paralelo=paralelo, matriculado_por=actor)
    asistencia = AsistenciaFactory(estudiante=estudiante, paralelo=paralelo)
    return estudiante, asistencia


# -------------------------------------------------------------------- #
# Happy path — one test per tipo
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestHappyPath:
    def _ejecutar(self, setup, tipo, datos):
        estudiante, asistencia = setup
        archivos = [_pdf("a.pdf"), _pdf("b.jpg")]
        service = JustificacionCertificadoAppService()
        solicitud = service.crear_justificacion_con_certificado(
            asistencia=asistencia,
            estudiante=estudiante,
            tipo_certificado=tipo,
            datos_certificado=datos,
            archivos=archivos,
            motivo="Adjunto certificado correspondiente.",
        )
        return solicitud

    def test_happy_medico(self, setup_estudiante_asistencia):
        solicitud = self._ejecutar(
            setup_estudiante_asistencia, TipoCertificado.MEDICO, _datos_medico()
        )
        assert Solicitud.objects.count() == 1
        assert solicitud.tipo == Solicitud.TipoSolicitud.JUSTIFICACION
        cert = CertificadoJustificacion.objects.get(solicitud=solicitud)
        assert cert.tipo == TipoCertificado.MEDICO
        assert cert.nombre_medico == "Dra. Pérez"
        assert ArchivoSolicitud.objects.filter(solicitud=solicitud).count() == 2

    def test_happy_laboral(self, setup_estudiante_asistencia):
        solicitud = self._ejecutar(
            setup_estudiante_asistencia, TipoCertificado.LABORAL, _datos_laboral()
        )
        cert = CertificadoJustificacion.objects.get(solicitud=solicitud)
        assert cert.tipo == TipoCertificado.LABORAL
        assert cert.cargo == "Analista"
        assert ArchivoSolicitud.objects.filter(solicitud=solicitud).count() == 2

    def test_happy_calamidad(self, setup_estudiante_asistencia):
        solicitud = self._ejecutar(
            setup_estudiante_asistencia, TipoCertificado.CALAMIDAD, _datos_calamidad()
        )
        cert = CertificadoJustificacion.objects.get(solicitud=solicitud)
        assert cert.tipo == TipoCertificado.CALAMIDAD
        assert cert.relacion_familiar == "padre"


# -------------------------------------------------------------------- #
# Notification side effect
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestNotificacion:
    def test_invoca_notificar_nueva_justificacion(self, setup_estudiante_asistencia):
        estudiante, asistencia = setup_estudiante_asistencia
        service = JustificacionCertificadoAppService()
        with mock.patch(
            "apps.solicitudes.application.services.notificar_nueva_justificacion"
        ) as mock_notif:
            solicitud = service.crear_justificacion_con_certificado(
                asistencia=asistencia,
                estudiante=estudiante,
                tipo_certificado=TipoCertificado.MEDICO,
                datos_certificado=_datos_medico(),
                archivos=[_pdf()],
                motivo="ok",
            )
        mock_notif.assert_called_once()
        args, kwargs = mock_notif.call_args
        # called with the created solicitud (positional or keyword)
        called_with = args[0] if args else kwargs.get("solicitud")
        assert called_with == solicitud

    def test_crea_notificacion_para_inspector_end_to_end(self, setup_estudiante_asistencia):
        InspectorFactory().save()
        estudiante, asistencia = setup_estudiante_asistencia
        service = JustificacionCertificadoAppService()
        service.crear_justificacion_con_certificado(
            asistencia=asistencia,
            estudiante=estudiante,
            tipo_certificado=TipoCertificado.LABORAL,
            datos_certificado=_datos_laboral(),
            archivos=[_pdf()],
            motivo="ok",
        )
        assert (
            Notificacion.objects.filter(tipo=Notificacion.Tipo.SOLICITUD_JUSTIFICACION).count()
            == 1
        )


# -------------------------------------------------------------------- #
# Domain exceptions → rollback
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestRollbackPorExcepcion:
    """Each domain exception must leave the DB untouched."""

    def _assert_no_rows(self):
        assert Solicitud.objects.count() == 0
        assert CertificadoJustificacion.objects.count() == 0
        assert ArchivoSolicitud.objects.count() == 0
        assert (
            Notificacion.objects.filter(tipo=Notificacion.Tipo.SOLICITUD_JUSTIFICACION).count()
            == 0
        )

    def test_maximo_archivos_excedido(self, setup_estudiante_asistencia):
        estudiante, asistencia = setup_estudiante_asistencia
        InspectorFactory().save()
        service = JustificacionCertificadoAppService()
        with pytest.raises(MaximoArchivosExcedidoError):
            service.crear_justificacion_con_certificado(
                asistencia=asistencia,
                estudiante=estudiante,
                tipo_certificado=TipoCertificado.MEDICO,
                datos_certificado=_datos_medico(),
                archivos=[_pdf(f"a{i}.pdf") for i in range(6)],
                motivo="ok",
            )
        self._assert_no_rows()

    def test_archivo_invalido_por_extension(self, setup_estudiante_asistencia):
        estudiante, asistencia = setup_estudiante_asistencia
        InspectorFactory().save()
        service = JustificacionCertificadoAppService()
        malo = SimpleUploadedFile("virus.exe", b"x", content_type="application/octet-stream")
        with pytest.raises(ArchivoInvalidoError) as exc:
            service.crear_justificacion_con_certificado(
                asistencia=asistencia,
                estudiante=estudiante,
                tipo_certificado=TipoCertificado.MEDICO,
                datos_certificado=_datos_medico(),
                archivos=[malo],
                motivo="ok",
            )
        assert "extension_invalida" in exc.value.errores
        self._assert_no_rows()

    def test_campos_obligatorios_faltantes(self, setup_estudiante_asistencia):
        estudiante, asistencia = setup_estudiante_asistencia
        InspectorFactory().save()
        service = JustificacionCertificadoAppService()
        datos = _datos_medico()
        del datos["nombre_medico"]
        del datos["dias_reposo"]
        with pytest.raises(CamposObligatoriosFaltantesError) as exc:
            service.crear_justificacion_con_certificado(
                asistencia=asistencia,
                estudiante=estudiante,
                tipo_certificado=TipoCertificado.MEDICO,
                datos_certificado=datos,
                archivos=[_pdf()],
                motivo="ok",
            )
        assert set(exc.value.campos) == {"nombre_medico", "dias_reposo"}
        self._assert_no_rows()

    def test_fecha_certificado_futura(self, setup_estudiante_asistencia):
        estudiante, asistencia = setup_estudiante_asistencia
        InspectorFactory().save()
        service = JustificacionCertificadoAppService()
        datos = _datos_laboral()
        datos["fecha_certificado"] = datetime.date.today() + datetime.timedelta(days=1)
        with pytest.raises(FechaCertificadoInvalidaError):
            service.crear_justificacion_con_certificado(
                asistencia=asistencia,
                estudiante=estudiante,
                tipo_certificado=TipoCertificado.LABORAL,
                datos_certificado=datos,
                archivos=[_pdf()],
                motivo="ok",
            )
        self._assert_no_rows()
