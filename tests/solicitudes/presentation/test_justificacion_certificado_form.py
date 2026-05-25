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
    def test_motivo_required(self):
        form = _bound(
            data={
                "tipo_certificado": "medico",
                "fecha_certificado": _yesterday().isoformat(),
                "institucion_emisora": "Hospital MSP",
                "numero_documento": "M-1",
                "nombre_medico": "Dra X",
                "dias_reposo": 2,
            },
            files={"archivos": [_pdf()]},
        )
        assert not form.is_valid()
        assert "motivo" in form.errors


# -------------------------------------------------------------------- #
# Archivos: required, max 5, size <= 5MB, valid ext
# -------------------------------------------------------------------- #


class TestArchivosField:
    def _base_data(self):
        return {
            "tipo_certificado": "laboral",
            "motivo": "ok",
            "institucion_emisora": "Empresa SA",
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

    def test_archivos_rechaza_tamanio_mayor_a_5mb(self):
        big = SimpleUploadedFile(
            "big.pdf", b"x" * (5 * 1024 * 1024 + 1), content_type="application/pdf"
        )
        form = _bound(data=self._base_data(), files={"archivos": [big]})
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
            "institucion_emisora": "Hospital MSP",
            "fecha_certificado": _yesterday().isoformat(),
            "numero_documento": "MED-1",
            "nombre_medico": "Dra. Pérez",
            "dias_reposo": 3,
        }
        data.update(overrides)
        return data

    def test_medico_completo_valido(self):
        form = _bound(data=self._data(), files={"archivos": [_pdf()]})
        assert form.is_valid(), form.errors

    def test_medico_sin_institucion_emisora_invalido(self):
        data = self._data()
        data["institucion_emisora"] = ""
        form = _bound(data=data, files={"archivos": [_pdf()]})
        assert not form.is_valid()
        assert "institucion_emisora" in form.errors

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
            "institucion_emisora": "Empresa SA",
            "fecha_certificado": _yesterday().isoformat(),
            "cargo": "Analista",
        }
        data.update(overrides)
        return data

    def test_laboral_completo_valido(self):
        form = _bound(data=self._data(), files={"archivos": [_pdf()]})
        assert form.is_valid(), form.errors

    def test_laboral_sin_institucion_emisora_invalido(self):
        data = self._data()
        data["institucion_emisora"] = ""
        form = _bound(data=data, files={"archivos": [_pdf()]})
        assert not form.is_valid()
        assert "institucion_emisora" in form.errors

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
                "institucion_emisora": "Hospital MSP",
                "fecha_certificado": _yesterday().isoformat(),
                "numero_documento": "MED-1",
                "nombre_medico": "Dra. Pérez",
                "dias_reposo": 3,
                # noise — should NOT leak into output
                "cargo": "Analista",
                "descripcion_evento": "x",
            },
            files={"archivos": [_pdf()]},
        )
        assert form.is_valid(), form.errors
        datos = form.datos_certificado()
        assert datos["institucion_emisora"] == "Hospital MSP"
        assert datos["fecha_certificado"] == _yesterday()
        assert datos["nombre_medico"] == "Dra. Pérez"
        assert datos["dias_reposo"] == 3
        # Fields belonging to other tipos must NOT be present
        assert "cargo" not in datos
        assert "descripcion_evento" not in datos

    def test_datos_certificado_laboral(self):
        form = _bound(
            data={
                "tipo_certificado": "laboral",
                "motivo": "ok",
                "institucion_emisora": "Empresa SA",
                "fecha_certificado": _yesterday().isoformat(),
                "cargo": "Analista",
            },
            files={"archivos": [_pdf()]},
        )
        assert form.is_valid(), form.errors
        datos = form.datos_certificado()
        assert datos["cargo"] == "Analista"
        assert "nombre_medico" not in datos
