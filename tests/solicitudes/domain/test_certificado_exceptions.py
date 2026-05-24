"""Unit tests for HU20 certificate domain exceptions.

These exceptions are raised by ``CertificadoValidationService`` and the
``JustificacionCertificadoAppService`` to signal validation failures
during the justification-with-certificate flow.
"""

import pytest

from apps.solicitudes.domain.exceptions import (
    ArchivoInvalidoError,
    CamposObligatoriosFaltantesError,
    FechaCertificadoInvalidaError,
    MaximoArchivosExcedidoError,
    SolicitudError,
)


class TestCamposObligatoriosFaltantesError:
    def test_stores_campos_list(self):
        err = CamposObligatoriosFaltantesError(["nombre_medico", "dias_reposo"])
        assert err.campos == ["nombre_medico", "dias_reposo"]

    def test_str_lists_missing_fields(self):
        err = CamposObligatoriosFaltantesError(["cargo"])
        text = str(err)
        assert "cargo" in text

    def test_is_solicitud_error(self):
        assert isinstance(CamposObligatoriosFaltantesError([]), SolicitudError)


class TestFechaCertificadoInvalidaError:
    def test_can_be_instantiated_without_args(self):
        err = FechaCertificadoInvalidaError()
        assert isinstance(err, Exception)

    def test_str_is_meaningful(self):
        assert str(FechaCertificadoInvalidaError()).strip() != ""

    def test_is_solicitud_error(self):
        assert isinstance(FechaCertificadoInvalidaError(), SolicitudError)


class TestMaximoArchivosExcedidoError:
    def test_stores_cantidad(self):
        err = MaximoArchivosExcedidoError(7)
        assert err.cantidad == 7

    def test_str_includes_received_count(self):
        err = MaximoArchivosExcedidoError(6)
        assert "6" in str(err)

    def test_is_solicitud_error(self):
        assert isinstance(MaximoArchivosExcedidoError(1), SolicitudError)


class TestArchivoInvalidoError:
    def test_stores_nombre_and_errores(self):
        err = ArchivoInvalidoError("foo.docx", ["extension_invalida"])
        assert err.nombre == "foo.docx"
        assert err.errores == ["extension_invalida"]

    def test_str_includes_filename_and_errors(self):
        err = ArchivoInvalidoError("big.pdf", ["tamanio_excedido"])
        text = str(err)
        assert "big.pdf" in text
        assert "tamanio_excedido" in text

    def test_is_solicitud_error(self):
        assert isinstance(ArchivoInvalidoError("x", []), SolicitudError)


def test_plazo_justificacion_expirado_error_does_not_exist():
    """Stakeholder override: NO deadline rule, ever."""
    from apps.solicitudes.domain import exceptions

    assert not hasattr(exceptions, "PlazoJustificacionExpiradoError")
