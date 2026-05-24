"""Unit tests for ``CertificadoValidationService`` (HU20).

Pure-Python service — no Django imports here. Covers every branch:
- required-fields map per tipo (medico/laboral/calamidad/unknown)
- date boundary (today/past/future)
- file extension + size (boundary, oversize, missing extension, mixed case)
"""

from datetime import date, timedelta

import pytest

from apps.solicitudes.domain.services import CertificadoValidationService as S


# --------------------------------------------------------------------------- #
# validar_campos_obligatorios
# --------------------------------------------------------------------------- #
class TestValidarCamposObligatorios:
    def test_medico_complete(self):
        datos = {
            "institucion_emisora": "MSP",
            "fecha_certificado": "2026-05-01",
            "numero_documento": "MSP-001",
            "nombre_medico": "Dr. House",
            "dias_reposo": 3,
        }
        assert S.validar_campos_obligatorios("medico", datos) == []

    @pytest.mark.parametrize(
        "missing",
        [
            "institucion_emisora",
            "fecha_certificado",
            "numero_documento",
            "nombre_medico",
            "dias_reposo",
        ],
    )
    def test_medico_missing_each_field(self, missing):
        datos = {
            "institucion_emisora": "MSP",
            "fecha_certificado": "2026-05-01",
            "numero_documento": "MSP-001",
            "nombre_medico": "Dr. House",
            "dias_reposo": 3,
        }
        datos.pop(missing)
        result = S.validar_campos_obligatorios("medico", datos)
        assert result == [missing]

    def test_laboral_complete(self):
        datos = {
            "institucion_emisora": "ACME",
            "fecha_certificado": "2026-05-01",
            "cargo": "Auditor",
        }
        assert S.validar_campos_obligatorios("laboral", datos) == []

    def test_laboral_missing_cargo(self):
        datos = {"institucion_emisora": "ACME", "fecha_certificado": "2026-05-01"}
        assert S.validar_campos_obligatorios("laboral", datos) == ["cargo"]

    def test_calamidad_complete(self):
        datos = {
            "fecha_certificado": "2026-05-01",
            "descripcion_evento": "Fallecimiento de tio",
            "relacion_familiar": "tio",
        }
        assert S.validar_campos_obligatorios("calamidad", datos) == []

    def test_calamidad_missing_multiple_returns_all(self):
        datos = {"fecha_certificado": "2026-05-01"}
        result = S.validar_campos_obligatorios("calamidad", datos)
        assert set(result) == {"descripcion_evento", "relacion_familiar"}

    def test_blank_string_is_missing(self):
        datos = {
            "institucion_emisora": "   ",
            "fecha_certificado": "2026-05-01",
            "cargo": "Auditor",
        }
        assert S.validar_campos_obligatorios("laboral", datos) == ["institucion_emisora"]

    def test_none_value_is_missing(self):
        datos = {
            "institucion_emisora": "ACME",
            "fecha_certificado": None,
            "cargo": "Auditor",
        }
        assert S.validar_campos_obligatorios("laboral", datos) == ["fecha_certificado"]

    def test_unknown_tipo_returns_empty(self):
        """Unknown tipo is not in the map — validator returns no missing fields.
        The form/app layer is responsible for rejecting invalid tipo values.
        """
        assert S.validar_campos_obligatorios("otro", {}) == []


# --------------------------------------------------------------------------- #
# validar_fecha_certificado
# --------------------------------------------------------------------------- #
class TestValidarFechaCertificado:
    def test_today_is_valid(self):
        today = date(2026, 5, 24)
        assert S.validar_fecha_certificado(today, today) is True

    def test_past_is_valid(self):
        ref = date(2026, 5, 24)
        assert S.validar_fecha_certificado(ref - timedelta(days=1), ref) is True

    def test_future_is_invalid(self):
        ref = date(2026, 5, 24)
        assert S.validar_fecha_certificado(ref + timedelta(days=1), ref) is False

    def test_exact_boundary_today(self):
        ref = date(2026, 5, 24)
        assert S.validar_fecha_certificado(ref, ref) is True


# --------------------------------------------------------------------------- #
# validar_archivo
# --------------------------------------------------------------------------- #
class TestValidarArchivo:
    @pytest.mark.parametrize("nombre", ["doc.pdf", "x.jpg", "y.jpeg", "z.png"])
    def test_valid_extension_under_size(self, nombre):
        assert S.validar_archivo(nombre, 1024) == []

    def test_boundary_exact_5mb(self):
        assert S.validar_archivo("ok.pdf", S.MAX_TAMANIO) == []

    def test_oversize_one_byte_over(self):
        result = S.validar_archivo("big.pdf", S.MAX_TAMANIO + 1)
        assert "tamanio_excedido" in result

    @pytest.mark.parametrize("nombre", ["bad.docx", "evil.exe", "archive.zip"])
    def test_invalid_extension(self, nombre):
        result = S.validar_archivo(nombre, 1024)
        assert "extension_invalida" in result

    def test_no_extension(self):
        result = S.validar_archivo("README", 1024)
        assert "extension_invalida" in result

    @pytest.mark.parametrize("nombre", ["MAYUS.PDF", "Foto.JPG", "Img.JPEG", "Pic.PNG"])
    def test_mixed_case_extension_accepted(self, nombre):
        assert S.validar_archivo(nombre, 1024) == []

    def test_both_errors_reported(self):
        result = S.validar_archivo("oops.docx", S.MAX_TAMANIO + 1)
        assert "extension_invalida" in result
        assert "tamanio_excedido" in result


# --------------------------------------------------------------------------- #
# constants
# --------------------------------------------------------------------------- #
class TestConstants:
    def test_max_archivos_is_5(self):
        assert S.MAX_ARCHIVOS == 5

    def test_max_tamanio_is_5mb(self):
        assert S.MAX_TAMANIO == 5 * 1024 * 1024

    def test_extensiones_validas(self):
        assert set(S.EXTENSIONES_VALIDAS) == {".pdf", ".jpg", ".jpeg", ".png"}

    def test_campos_obligatorios_keys(self):
        assert set(S.CAMPOS_OBLIGATORIOS.keys()) == {"medico", "laboral", "calamidad"}

    def test_no_validar_plazo_method(self):
        """Stakeholder override: NO deadline rule."""
        assert not hasattr(S, "validar_plazo_justificacion")
