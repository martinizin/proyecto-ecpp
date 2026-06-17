"""Unit tests for the ModeracionServicio domain layer (PR 1a, copilot-content-moderation).

Pure-Python domain service — no DB, no network. Uses fake providers injected
via the Protocol contracts (real implementations land in PR 1b).

Conventions:
- Spanish class/field names to match the copilot domain style
  (e.g. ``QueryClassifierService``, ``ConsultaAcademica``, ``SesionLlenaError``).
- Tests are grouped by TDD task (T1.1 → T1.8) so a failing group clearly
  identifies which RED phase is open.
- Each class uses lazy imports so a missing implementation at a given TDD
  step produces a clean ImportError against the test(s) for that step only,
  without breaking collection of later steps.
"""

from __future__ import annotations

from enum import Enum
from unittest import mock

import pytest


# --------------------------------------------------------------------------- #
# T1.1 — Severidad enum + ResultadoModeracion dataclass
# --------------------------------------------------------------------------- #
class TestSeveridad:
    def test_es_un_enum(self):
        from apps.copilot.domain.moderation import Severidad

        assert issubclass(Severidad, Enum)

    def test_valor_light(self):
        from apps.copilot.domain.moderation import Severidad

        assert Severidad.LIGHT.value == "light"

    def test_valor_strong(self):
        from apps.copilot.domain.moderation import Severidad

        assert Severidad.STRONG.value == "strong"

    def test_valor_clean(self):
        from apps.copilot.domain.moderation import Severidad

        # El servicio expone CLEAN para representar el caso sin matches
        assert Severidad.CLEAN.value == "clean"

    def test_solo_tres_valores_exactos(self):
        from apps.copilot.domain.moderation import Severidad

        assert {s.name for s in Severidad} == {"CLEAN", "LIGHT", "STRONG"}


class TestResultadoModeracion:
    def test_crear_con_campos_minimos(self):
        from apps.copilot.domain.moderation import ResultadoModeracion, Severidad

        r = ResultadoModeracion(
            flagged=False,
            severidad=Severidad.CLEAN,
            razon=None,
            contenido_sanitizado="hola",
        )
        assert r.flagged is False
        assert r.severidad is Severidad.CLEAN
        assert r.razon is None
        assert r.contenido_sanitizado == "hola"

    def test_es_inmutable(self):
        from apps.copilot.domain.moderation import ResultadoModeracion, Severidad

        r = ResultadoModeracion(
            flagged=True,
            severidad=Severidad.STRONG,
            razon="strong_list",
            contenido_sanitizado="***",
        )
        with pytest.raises(Exception):
            r.flagged = False  # type: ignore[misc]

    def test_strong_match_contenido_censurado(self):
        from apps.copilot.domain.moderation import ResultadoModeracion, Severidad

        r = ResultadoModeracion(
            flagged=True,
            severidad=Severidad.STRONG,
            razon="strong_list",
            contenido_sanitizado="eres un ***",
        )
        assert r.flagged is True
        assert r.severidad is Severidad.STRONG
        assert r.razon == "strong_list"

    def test_light_match_no_es_flagged(self):
        """Light match es un match a censurar (no flagged = no rechaza)."""
        from apps.copilot.domain.moderation import ResultadoModeracion, Severidad

        r = ResultadoModeracion(
            flagged=False,
            severidad=Severidad.LIGHT,
            razon=None,
            contenido_sanitizado="dame mi *** de notas",
        )
        assert r.flagged is False
        assert r.severidad is Severidad.LIGHT
        assert r.razon is None


# --------------------------------------------------------------------------- #
# T1.3 — ContenidoBloqueadoError
# --------------------------------------------------------------------------- #
class TestContenidoBloqueadoError:
    def test_levanta_con_razon(self):
        from apps.copilot.domain.exceptions import ContenidoBloqueadoError

        with pytest.raises(ContenidoBloqueadoError) as excinfo:
            raise ContenidoBloqueadoError(razon="strong_list")
        assert excinfo.value.razon == "strong_list"

    def test_mensaje_por_defecto_es_canned_refusal(self):
        """El mensaje de la excepción es SIEMPRE CANNED_REFUSAL (byte-locked)."""
        from apps.copilot.domain.exceptions import ContenidoBloqueadoError
        from apps.copilot.domain.moderation import CANNED_REFUSAL

        with pytest.raises(ContenidoBloqueadoError) as excinfo:
            raise ContenidoBloqueadoError(razon="strong_list")
        assert str(excinfo.value) == CANNED_REFUSAL

    def test_acepta_las_tres_razones_de_la_spec(self):
        from apps.copilot.domain.exceptions import ContenidoBloqueadoError

        for razon in ("strong_list", "openai_input", "openai_output"):
            err = ContenidoBloqueadoError(razon=razon)
            assert err.razon == razon
            assert isinstance(err, Exception)

    def test_razon_obligatoria(self):
        from apps.copilot.domain.exceptions import ContenidoBloqueadoError

        with pytest.raises(TypeError):
            ContenidoBloqueadoError()  # type: ignore[call-arg]

    def test_canned_refusal_byte_locked(self):
        """Pin del texto canónico (REQ-005): byte-exacto, sin comillas, sin
        espacios extra, empieza con 'n' minúscula."""
        from apps.copilot.domain.moderation import CANNED_REFUSAL

        assert (
            CANNED_REFUSAL == "no puedo responder consultas con ese tipo de palabras, "
            "intenta realizar tu consulta de manera diferente por favor"
        )


# --------------------------------------------------------------------------- #
# Fakes — used by T1.5/T1.7 (ModeracionServicio)
# --------------------------------------------------------------------------- #
class _FakeListaDura:
    """Stub del ProveedorListaDura (PR 1b). Devuelve un resultado fijo."""

    def __init__(self, resultado):
        # None → CLEAN; tuple(Severidad, texto) → match
        self._resultado = resultado
        self.calls: list[str] = []

    def escanear(self, texto: str):
        self.calls.append(texto)
        return self._resultado


class _FakeModeracionExterna:
    """Stub del ProveedorModeracionExterno (PR 1b). Configurable."""

    def __init__(self, flagged: bool = False, fail_with: Exception | None = None):
        self._flagged = flagged
        self._fail_with = fail_with
        self.calls: list[str] = []

    def clasificar(self, texto: str) -> bool:
        self.calls.append(texto)
        if self._fail_with is not None:
            raise self._fail_with
        return self._flagged


# --------------------------------------------------------------------------- #
# T1.5 — ModeracionServicio.evaluar_input
# --------------------------------------------------------------------------- #
class TestEvaluarInput:
    def test_input_limpio_pasa_sin_flag(self):
        from apps.copilot.domain.moderation import ModeracionServicio, Severidad

        lista = _FakeListaDura(resultado=None)
        api = _FakeModeracionExterna(flagged=False)
        svc = ModeracionServicio(
            proveedor_lista_dura=lista,
            proveedor_moderacion_externo=api,
            habilitado=True,
        )
        resultado = svc.evaluar_input("hola mundo")
        assert resultado.flagged is False
        assert resultado.severidad is Severidad.CLEAN
        assert resultado.razon is None
        assert resultado.contenido_sanitizado == "hola mundo"
        # La lista fue consultada y la API fue llamada una vez con el original
        assert lista.calls == ["hola mundo"]
        assert api.calls == ["hola mundo"]

    def test_input_light_censura_y_pasa(self):
        from apps.copilot.domain.moderation import ModeracionServicio, Severidad

        lista = _FakeListaDura(
            resultado=(Severidad.LIGHT, "dame mi *** de notas"),
        )
        api = _FakeModeracionExterna(flagged=False)
        svc = ModeracionServicio(
            proveedor_lista_dura=lista,
            proveedor_moderacion_externo=api,
            habilitado=True,
        )
        resultado = svc.evaluar_input("dame mi mierda de notas")
        assert resultado.flagged is False
        assert resultado.severidad is Severidad.LIGHT
        assert resultado.razon is None
        assert resultado.contenido_sanitizado == "dame mi *** de notas"
        # La API externa debe ser llamada con la versión censurada (REQ-003)
        assert api.calls == ["dame mi *** de notas"]

    def test_input_strong_lanza_excepcion(self):
        from apps.copilot.domain.exceptions import ContenidoBloqueadoError
        from apps.copilot.domain.moderation import ModeracionServicio, Severidad

        lista = _FakeListaDura(
            resultado=(Severidad.STRONG, "eres un ***"),
        )
        api = _FakeModeracionExterna(flagged=False)
        svc = ModeracionServicio(
            proveedor_lista_dura=lista,
            proveedor_moderacion_externo=api,
            habilitado=True,
        )
        with pytest.raises(ContenidoBloqueadoError) as excinfo:
            svc.evaluar_input("eres un pendejo")
        assert excinfo.value.razon == "strong_list"
        # La API externa NO debe ser llamada en strong (no hay LLM que moderar)
        assert api.calls == []

    def test_input_limpio_pero_openai_flaggea_lanza(self):
        from apps.copilot.domain.exceptions import ContenidoBloqueadoError
        from apps.copilot.domain.moderation import ModeracionServicio

        lista = _FakeListaDura(resultado=None)
        api = _FakeModeracionExterna(flagged=True)
        svc = ModeracionServicio(
            proveedor_lista_dura=lista,
            proveedor_moderacion_externo=api,
            habilitado=True,
        )
        with pytest.raises(ContenidoBloqueadoError) as excinfo:
            svc.evaluar_input("consulta borderline")
        assert excinfo.value.razon == "openai_input"
        assert excinfo.value.razon != "strong_list"

    def test_feature_flag_off_corta_circuito(self):
        from apps.copilot.domain.moderation import ModeracionServicio, Severidad

        # Aunque la lista diga strong y la API diga flagged, el flag manda
        lista = _FakeListaDura(
            resultado=(Severidad.STRONG, "***"),
        )
        api = _FakeModeracionExterna(flagged=True)
        svc = ModeracionServicio(
            proveedor_lista_dura=lista,
            proveedor_moderacion_externo=api,
            habilitado=False,
        )
        resultado = svc.evaluar_input("cualquier cosa")
        # Bypass total: ni siquiera la lista se consulta
        assert resultado.flagged is False
        assert resultado.severidad is Severidad.CLEAN
        assert resultado.razon is None
        assert resultado.contenido_sanitizado == "cualquier cosa"
        assert lista.calls == []
        assert api.calls == []

    def test_input_limpio_con_flag_off_no_llama_api(self):
        """Refuerza el bypass: ni siquiera la API se consulta con flag off."""
        from apps.copilot.domain.moderation import ModeracionServicio

        lista = _FakeListaDura(resultado=None)
        api = _FakeModeracionExterna(flagged=False)
        svc = ModeracionServicio(
            proveedor_lista_dura=lista,
            proveedor_moderacion_externo=api,
            habilitado=False,
        )
        svc.evaluar_input("consulta limpia")
        assert api.calls == []

    def test_input_falla_openai_timeout_fail_open(self):
        """REQ-009: error de OpenAI en input → fail-open (no ContenidoBloqueadoError)."""
        import openai

        from apps.copilot.domain.moderation import ModeracionServicio, Severidad

        lista = _FakeListaDura(resultado=None)
        api = _FakeModeracionExterna(
            fail_with=openai.APITimeoutError("timeout"),
        )
        svc = ModeracionServicio(
            proveedor_lista_dura=lista,
            proveedor_moderacion_externo=api,
            habilitado=True,
        )
        resultado = svc.evaluar_input("consulta")
        assert resultado.flagged is False
        assert resultado.severidad is Severidad.CLEAN
        assert resultado.razon is None
        # El texto original pasa tal cual al LLM (no se censura)
        assert resultado.contenido_sanitizado == "consulta"

    def test_input_falla_openai_bad_request_fail_open(self):
        """Variante del fail-open: BadRequestError también devuelve clean."""
        import openai

        from apps.copilot.domain.moderation import ModeracionServicio, Severidad

        lista = _FakeListaDura(resultado=None)
        api = _FakeModeracionExterna(
            fail_with=openai.BadRequestError(
                message="invalid", response=mock.MagicMock(status_code=400), body={}
            ),
        )
        svc = ModeracionServicio(
            proveedor_lista_dura=lista,
            proveedor_moderacion_externo=api,
            habilitado=True,
        )
        resultado = svc.evaluar_input("consulta")
        assert resultado.flagged is False
        assert resultado.severidad is Severidad.CLEAN


# --------------------------------------------------------------------------- #
# T1.7 — ModeracionServicio.sanitizar
# --------------------------------------------------------------------------- #
class TestSanitizar:
    def test_sanitizar_input_limpio_retorna_original(self):
        from apps.copilot.domain.moderation import (
            ModeracionServicio,
            ResultadoModeracion,
            Severidad,
        )

        lista = _FakeListaDura(resultado=None)
        api = _FakeModeracionExterna(flagged=False)
        svc = ModeracionServicio(
            proveedor_lista_dura=lista,
            proveedor_moderacion_externo=api,
            habilitado=True,
        )
        resultado = ResultadoModeracion(
            flagged=False,
            severidad=Severidad.CLEAN,
            razon=None,
            contenido_sanitizado="hola mundo",
        )
        texto = svc.sanitizar("hola mundo", resultado)
        assert texto == "hola mundo"

    def test_sanitizar_light_retorna_censurado(self):
        from apps.copilot.domain.moderation import (
            ModeracionServicio,
            ResultadoModeracion,
            Severidad,
        )

        lista = _FakeListaDura(resultado=None)
        api = _FakeModeracionExterna(flagged=False)
        svc = ModeracionServicio(
            proveedor_lista_dura=lista,
            proveedor_moderacion_externo=api,
            habilitado=True,
        )
        resultado = ResultadoModeracion(
            flagged=False,
            severidad=Severidad.LIGHT,
            razon=None,
            contenido_sanitizado="mierda y mierda".replace("mierda", "***"),
        )
        texto = svc.sanitizar("mierda y mierda", resultado)
        assert texto == "*** y ***"

    def test_sanitizar_light_usa_contenido_sanitizado_no_original(self):
        """Aunque el caller pase el texto original, sanitizar devuelve la
        versión censurada (no el original) cuando severidad=LIGHT."""
        from apps.copilot.domain.moderation import (
            ModeracionServicio,
            ResultadoModeracion,
            Severidad,
        )

        svc = ModeracionServicio(
            proveedor_lista_dura=_FakeListaDura(resultado=None),
            proveedor_moderacion_externo=_FakeModeracionExterna(flagged=False),
            habilitado=True,
        )
        resultado = ResultadoModeracion(
            flagged=False,
            severidad=Severidad.LIGHT,
            razon=None,
            contenido_sanitizado="dame mi *** de notas",
        )
        # El caller pasa el texto original con "mierda"
        texto = svc.sanitizar("dame mi mierda de notas", resultado)
        # Pero sanitizar debe devolver la versión censurada
        assert texto == "dame mi *** de notas"
        assert "mierda" not in texto

    def test_sanitizar_strong_lanza_excepcion(self):
        from apps.copilot.domain.exceptions import ContenidoBloqueadoError
        from apps.copilot.domain.moderation import (
            ModeracionServicio,
            ResultadoModeracion,
            Severidad,
        )

        svc = ModeracionServicio(
            proveedor_lista_dura=_FakeListaDura(resultado=None),
            proveedor_moderacion_externo=_FakeModeracionExterna(flagged=False),
            habilitado=True,
        )
        resultado = ResultadoModeracion(
            flagged=True,
            severidad=Severidad.STRONG,
            razon="strong_list",
            contenido_sanitizado="eres un ***",
        )
        with pytest.raises(ContenidoBloqueadoError) as excinfo:
            svc.sanitizar("eres un pendejo", resultado)
        assert excinfo.value.razon == "strong_list"

    def test_sanitizar_openai_input_flagged_lanza_excepcion(self):
        from apps.copilot.domain.exceptions import ContenidoBloqueadoError
        from apps.copilot.domain.moderation import (
            ModeracionServicio,
            ResultadoModeracion,
            Severidad,
        )

        svc = ModeracionServicio(
            proveedor_lista_dura=_FakeListaDura(resultado=None),
            proveedor_moderacion_externo=_FakeModeracionExterna(flagged=False),
            habilitado=True,
        )
        resultado = ResultadoModeracion(
            flagged=True,
            severidad=Severidad.CLEAN,  # la lista no marcó, pero OpenAI sí
            razon="openai_input",
            contenido_sanitizado="consulta borderline",
        )
        with pytest.raises(ContenidoBloqueadoError) as excinfo:
            svc.sanitizar("consulta borderline", resultado)
        assert excinfo.value.razon == "openai_input"

    def test_sanitizar_round_trip_con_evaluar_input_limpio(self):
        """Workflow end-to-end del dominio: evaluar_input → sanitizar."""
        from apps.copilot.domain.moderation import ModeracionServicio

        svc = ModeracionServicio(
            proveedor_lista_dura=_FakeListaDura(resultado=None),
            proveedor_moderacion_externo=_FakeModeracionExterna(flagged=False),
            habilitado=True,
        )
        original = "dame mis notas"
        resultado = svc.evaluar_input(original)
        assert svc.sanitizar(original, resultado) == original

    def test_sanitizar_round_trip_con_evaluar_input_light(self):
        """Workflow end-to-end con censura: el sanitizado final coincide con
        la versión censurada, no con la original."""
        from apps.copilot.domain.moderation import ModeracionServicio, Severidad

        svc = ModeracionServicio(
            proveedor_lista_dura=_FakeListaDura(
                resultado=(Severidad.LIGHT, "dame mi *** de notas"),
            ),
            proveedor_moderacion_externo=_FakeModeracionExterna(flagged=False),
            habilitado=True,
        )
        original = "dame mi mierda de notas"
        resultado = svc.evaluar_input(original)
        assert resultado.severidad is Severidad.LIGHT
        assert svc.sanitizar(original, resultado) == "dame mi *** de notas"


# --------------------------------------------------------------------------- #
# T1.9 — Settings (smoke test)
# --------------------------------------------------------------------------- #
class TestSettingsModeracion:
    """Smoke test: los settings COPILOT_MODERATION_* se exponen en Django."""

    def test_setting_moderation_enabled_esta_presente(self):
        from django.conf import settings

        assert hasattr(settings, "COPILOT_MODERATION_ENABLED")
        assert isinstance(settings.COPILOT_MODERATION_ENABLED, bool)

    def test_setting_allowlist_path_esta_presente(self):
        from pathlib import Path

        from django.conf import settings

        assert hasattr(settings, "COPILOT_MODERATION_ALLOWLIST_PATH")
        assert isinstance(settings.COPILOT_MODERATION_ALLOWLIST_PATH, Path)
        # El path por default vive bajo apps/copilot/data/
        assert "apps" in settings.COPILOT_MODERATION_ALLOWLIST_PATH.parts

    def test_setting_input_fail_mode_esta_presente(self):
        from django.conf import settings

        assert hasattr(settings, "COPILOT_MODERATION_INPUT_FAIL_MODE")
        # Default bloqueado por la spec a "OPEN" (REQ-009)
        assert settings.COPILOT_MODERATION_INPUT_FAIL_MODE == "OPEN"

    def test_setting_output_fail_mode_esta_presente(self):
        from django.conf import settings

        assert hasattr(settings, "COPILOT_MODERATION_OUTPUT_FAIL_MODE")
        # Default bloqueado por la spec a "SKIP" (REQ-009)
        assert settings.COPILOT_MODERATION_OUTPUT_FAIL_MODE == "SKIP"
