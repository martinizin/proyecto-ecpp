"""Unit tests for JustificacionCertificadoForm (HU20 Slice 3)."""

import datetime

from django.core.files.uploadedfile import SimpleUploadedFile

from apps.solicitudes.presentation.forms import JustificacionCertificadoForm


def _pdf(name="cert.pdf", size=1024):
    return SimpleUploadedFile(name, b"x" * size, content_type="application/pdf")


def _today():
    return datetime.date.today()


def _yesterday():
    return _today() - datetime.timedelta(days=1)


def _tomorrow():
    return _today() + datetime.timedelta(days=1)


def _bound(data=None, files=None):
    """Build a bound form with sensible defaults overridable via kwargs."""
    return JustificacionCertificadoForm(data=data or {}, files=files or {})


# -------------------------------------------------------------------- #
# tipo_certificado required + choices
# -------------------------------------------------------------------- #


class TestTipoCertificadoField:
    def test_tipo_certificado_required(self):
        form = _bound(
            data={"motivo": "x"},
            files={"archivos": [_pdf()]},
        )
        assert not form.is_valid()
        assert "tipo_certificado" in form.errors

    def test_tipo_certificado_choices_are_medico_laboral_calamidad(self):
        form = JustificacionCertificadoForm()
        choices = [c[0] for c in form.fields["tipo_certificado"].choices if c[0]]
        assert set(choices) == {"medico", "laboral", "calamidad"}

    def test_tipo_certificado_rechaza_valor_no_listado(self):
        form = _bound(
            data={
                "tipo_certificado": "otro",
                "motivo": "x",
                "fecha_certificado": _yesterday().isoformat(),
            },
            files={"archivos": [_pdf()]},
        )
        assert not form.is_valid()
        assert "tipo_certificado" in form.errors


# -------------------------------------------------------------------- #
# Motivo required
# -------------------------------------------------------------------- #


class TestMotivoField:
    def test_motivo_opcional_post_qa(self):
        """Post-QA: motivo is no longer required."""
        form = _bound(
            data={
                "tipo_certificado": "medico",
                "fecha_certificado": _yesterday().isoformat(),
                "dias_reposo": 2,
            },
            files={"archivos": [_pdf()]},
        )
        assert form.is_valid(), form.errors
        assert "motivo" not in form.errors


# -------------------------------------------------------------------- #
# QA simplification: 3 fields removed from the form (numero_documento,
# nombre_medico/medico_tratante, institucion_emisora). Motivo opcional.
# -------------------------------------------------------------------- #


class TestJustificacionFormCamposEliminados:
    """Post-QA: the form must NOT declare numero_documento, nombre_medico
    nor institucion_emisora as input fields."""

    def test_form_no_incluye_numero_documento(self):
        form = JustificacionCertificadoForm()
        assert "numero_documento" not in form.fields

    def test_form_no_incluye_medico_tratante(self):
        # The form field for "Médico tratante" is named ``nombre_medico``.
        form = JustificacionCertificadoForm()
        assert "nombre_medico" not in form.fields

    def test_form_no_incluye_institucion_emisora(self):
        form = JustificacionCertificadoForm()
        assert "institucion_emisora" not in form.fields


class TestMotivoOpcional:
    def _base_medico(self):
        return {
            "tipo_certificado": "medico",
            "fecha_certificado": _yesterday().isoformat(),
            "dias_reposo": 2,
        }

    def test_form_valido_sin_motivo(self):
        data = self._base_medico()
        # motivo key absent on purpose.
        form = _bound(data=data, files={"archivos": [_pdf()]})
        assert form.is_valid(), form.errors

    def test_form_valido_con_motivo_vacio(self):
        data = self._base_medico()
        data["motivo"] = ""
        form = _bound(data=data, files={"archivos": [_pdf()]})
        assert form.is_valid(), form.errors

    def test_form_valido_con_motivo_whitespace(self):
        data = self._base_medico()
        data["motivo"] = "   "
        form = _bound(data=data, files={"archivos": [_pdf()]})
        # required=False does not reject whitespace; the cleaned value is the
        # raw string (or stripped — Django strips by default).
        assert form.is_valid(), form.errors


# -------------------------------------------------------------------- #
# Archivos: required, max 5, size <= 5MB, valid ext
# -------------------------------------------------------------------- #


class TestArchivosField:
    def _base_data(self):
        return {
            "tipo_certificado": "laboral",
            "motivo": "ok",
            "fecha_certificado": _yesterday().isoformat(),
            "cargo": "Analista",
        }

    def test_archivos_requeridos_uno_o_mas(self):
        form = _bound(data=self._base_data(), files={})
        assert not form.is_valid()
        assert "archivos" in form.errors

    def test_archivos_acepta_un_archivo_valido(self):
        form = _bound(data=self._base_data(), files={"archivos": [_pdf("a.pdf")]})
        assert form.is_valid(), form.errors

    def test_archivos_acepta_hasta_5(self):
        files = [_pdf(f"a{i}.pdf") for i in range(5)]
        form = _bound(data=self._base_data(), files={"archivos": files})
        assert form.is_valid(), form.errors

    def test_archivos_rechaza_mas_de_5(self):
        files = [_pdf(f"a{i}.pdf") for i in range(6)]
        form = _bound(data=self._base_data(), files={"archivos": files})
        assert not form.is_valid()
        assert "archivos" in form.errors

    def test_archivos_rechaza_extension_invalida(self):
        bad = SimpleUploadedFile("virus.exe", b"x", content_type="application/octet-stream")
        form = _bound(data=self._base_data(), files={"archivos": [bad]})
        assert not form.is_valid()
        assert "archivos" in form.errors

    def test_archivos_rechaza_peso_total_mayor_a_5mb(self):
        # Post-QA: limite agregado de 5MB. Un solo archivo de 5MB+1 ya excede.
        big = SimpleUploadedFile(
            "big.pdf", b"x" * (5 * 1024 * 1024 + 1), content_type="application/pdf"
        )
        form = _bound(data=self._base_data(), files={"archivos": [big]})
        assert not form.is_valid()
        assert "archivos" in form.errors


# -------------------------------------------------------------------- #
# Post-QA: limite AGREGADO — <=5 archivos AND <=5MB peso total.
# NO hay limite por archivo individual.
# -------------------------------------------------------------------- #


class TestArchivosLimiteAgregado:
    def _base_data(self):
        return {
            "tipo_certificado": "laboral",
            "motivo": "ok",
            "fecha_certificado": _yesterday().isoformat(),
            "cargo": "Analista",
        }

    def test_form_acepta_un_solo_archivo_de_exactamente_5mb(self):
        """Regression del caso del usuario: 1 PDF de 5MB es valido."""
        archivo_5mb = _pdf("certificado.pdf", size=5 * 1024 * 1024)
        form = _bound(data=self._base_data(), files={"archivos": [archivo_5mb]})
        assert form.is_valid(), form.errors

    def test_form_acepta_5_archivos_de_1mb_cada_uno(self):
        files = [_pdf(f"a{i}.pdf", size=1024 * 1024) for i in range(5)]
        form = _bound(data=self._base_data(), files={"archivos": files})
        assert form.is_valid(), form.errors

    def test_form_rechaza_2_archivos_de_3mb_cada_uno(self):
        # 2 * 3MB = 6MB > 5MB total. Mensaje debe mencionar peso total.
        files = [_pdf(f"a{i}.pdf", size=3 * 1024 * 1024) for i in range(2)]
        form = _bound(data=self._base_data(), files={"archivos": files})
        assert not form.is_valid()
        assert "archivos" in form.errors
        msg = " ".join(form.errors["archivos"])
        # El mensaje debe mencionar 'total' o 'peso total' y los MB subidos (6.00).
        assert "total" in msg.lower()
        assert "6.00 MB" in msg or "6 MB" in msg or "6.00" in msg

    def test_form_rechaza_6_archivos_pequenios(self):
        files = [_pdf(f"a{i}.pdf", size=100) for i in range(6)]
        form = _bound(data=self._base_data(), files={"archivos": files})
        assert not form.is_valid()
        assert "archivos" in form.errors
        msg = " ".join(form.errors["archivos"])
        assert "5" in msg  # menciona el limite

    def test_form_mensaje_peso_total_incluye_los_mb_subidos(self):
        # 3 archivos de 2MB = 6MB total. Mensaje UX-friendly debe incluir el monto.
        files = [_pdf(f"a{i}.pdf", size=2 * 1024 * 1024) for i in range(3)]
        form = _bound(data=self._base_data(), files={"archivos": files})
        assert not form.is_valid()
        msg = " ".join(form.errors["archivos"])
        assert "6.00 MB" in msg or "6 MB" in msg

    def test_form_rechaza_extension_invalida_sin_importar_lote(self):
        # La validacion de extension sigue por archivo individual.
        bad = SimpleUploadedFile("virus.exe", b"x", content_type="application/octet-stream")
        form = _bound(data=self._base_data(), files={"archivos": [bad]})
        assert not form.is_valid()
        assert "archivos" in form.errors


# -------------------------------------------------------------------- #
# Conditional clean() per tipo
# -------------------------------------------------------------------- #


class TestCleanPorTipoMedico:
    def _data(self, **overrides):
        data = {
            "tipo_certificado": "medico",
            "motivo": "ok",
            "fecha_certificado": _yesterday().isoformat(),
            "dias_reposo": 3,
        }
        data.update(overrides)
        return data

    def test_medico_completo_valido(self):
        form = _bound(data=self._data(), files={"archivos": [_pdf()]})
        assert form.is_valid(), form.errors

    def test_medico_sin_dias_reposo_invalido(self):
        data = self._data()
        data["dias_reposo"] = ""
        form = _bound(data=data, files={"archivos": [_pdf()]})
        assert not form.is_valid()
        assert "dias_reposo" in form.errors

    def test_medico_sin_fecha_certificado_invalido(self):
        data = self._data()
        data["fecha_certificado"] = ""
        form = _bound(data=data, files={"archivos": [_pdf()]})
        assert not form.is_valid()
        assert "fecha_certificado" in form.errors


class TestCleanPorTipoLaboral:
    def _data(self, **overrides):
        data = {
            "tipo_certificado": "laboral",
            "motivo": "ok",
            "fecha_certificado": _yesterday().isoformat(),
            "cargo": "Analista",
        }
        data.update(overrides)
        return data

    def test_laboral_completo_valido(self):
        form = _bound(data=self._data(), files={"archivos": [_pdf()]})
        assert form.is_valid(), form.errors

    def test_laboral_sin_cargo_invalido(self):
        data = self._data()
        data["cargo"] = ""
        form = _bound(data=data, files={"archivos": [_pdf()]})
        assert not form.is_valid()
        assert "cargo" in form.errors

    def test_laboral_sin_fecha_certificado_invalido(self):
        data = self._data()
        data["fecha_certificado"] = ""
        form = _bound(data=data, files={"archivos": [_pdf()]})
        assert not form.is_valid()
        assert "fecha_certificado" in form.errors


class TestCleanPorTipoCalamidad:
    def _data(self, **overrides):
        data = {
            "tipo_certificado": "calamidad",
            "motivo": "ok",
            "descripcion_evento": "Fallecimiento familiar.",
            "fecha_certificado": _yesterday().isoformat(),
            "relacion_familiar": "padre",
        }
        data.update(overrides)
        return data

    def test_calamidad_completo_valido(self):
        form = _bound(data=self._data(), files={"archivos": [_pdf()]})
        assert form.is_valid(), form.errors

    def test_calamidad_sin_descripcion_evento_invalido(self):
        data = self._data()
        data["descripcion_evento"] = ""
        form = _bound(data=data, files={"archivos": [_pdf()]})
        assert not form.is_valid()
        assert "descripcion_evento" in form.errors


# -------------------------------------------------------------------- #
# datos_certificado() helper for AppService consumption
# -------------------------------------------------------------------- #


class TestDatosCertificadoHelper:
    def test_datos_certificado_medico_devuelve_solo_campos_del_tipo(self):
        form = _bound(
            data={
                "tipo_certificado": "medico",
                "motivo": "ok",
                "fecha_certificado": _yesterday().isoformat(),
                "dias_reposo": 3,
                # noise — should NOT leak into output
                "cargo": "Analista",
                "descripcion_evento": "x",
            },
            files={"archivos": [_pdf()]},
        )
        assert form.is_valid(), form.errors
        datos = form.datos_certificado()
        assert datos["fecha_certificado"] == _yesterday()
        assert datos["dias_reposo"] == 3
        # Fields belonging to other tipos must NOT be present
        assert "cargo" not in datos
        assert "descripcion_evento" not in datos
        # Post-QA removed fields must NOT appear in the medico payload
        assert "institucion_emisora" not in datos
        assert "nombre_medico" not in datos
        assert "numero_documento" not in datos

    def test_datos_certificado_laboral(self):
        form = _bound(
            data={
                "tipo_certificado": "laboral",
                "motivo": "ok",
                "fecha_certificado": _yesterday().isoformat(),
                "cargo": "Analista",
            },
            files={"archivos": [_pdf()]},
        )
        assert form.is_valid(), form.errors
        datos = form.datos_certificado()
        assert datos["cargo"] == "Analista"
        assert "nombre_medico" not in datos
        assert "institucion_emisora" not in datos
