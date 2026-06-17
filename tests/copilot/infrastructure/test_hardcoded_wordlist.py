"""Unit tests for HardcodedWordListProvider (PR 1b, copilot-content-moderation).

Concrete implementation of the ``ProveedorListaDura`` Protocol declared in
``apps.copilot.domain.moderation``. The provider scans text against a curated
ES/EN word list with severity tags, applies an evasion-normalization pipeline
(NFKD + leet substitution + punctuation strip + whitespace collapse), and
relaxes strong-severity matches when the input contains an allow-list phrase.

Tests are written first (strict TDD, RED → GREEN → REFACTOR) and grouped by
TDD task (T1b.1 → T1b.22). Each class uses lazy imports so a missing
implementation at a given TDD step produces a clean ``ImportError`` against
the test(s) for that step only.
"""

from __future__ import annotations

import json

# `pytest` is required for fixtures like `tmp_path` and `caplog` (used in
# TestCargaAllowlistJSON and TestNormalizacionEvasion).
import pytest  # noqa: F401


# --------------------------------------------------------------------------- #
# T1b.1 — Constructor + empty / whitespace / clean input → None
# --------------------------------------------------------------------------- #
class TestHardcodedWordListProviderBasics:
    """Constructor and the trivial 'no match' cases (T1b.1, T1b.2)."""

    def test_constructor_acepta_listas_custom(self):
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(
            lista_light=["mierda", "shit"],
            lista_strong=["puta", "fuck"],
        )
        assert provider is not None

    def test_constructor_acepta_allowlist_none(self):
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(
            lista_light=["mierda"],
            lista_strong=["puta"],
            allowlist=None,
        )
        assert provider is not None

    def test_escanear_texto_vacio_retorna_none(self):
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(lista_light=["mierda"], lista_strong=["puta"])
        assert provider.escanear("") is None

    def test_escanear_texto_solo_espacios_retorna_none(self):
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(lista_light=["mierda"], lista_strong=["puta"])
        assert provider.escanear("   \t\n  ") is None

    def test_escanear_texto_limpio_retorna_none(self):
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(lista_light=["mierda"], lista_strong=["puta"])
        assert provider.escanear("hola mundo") is None

    def test_escanear_texto_sin_palabras_censuradas_retorna_none(self):
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(
            lista_light=["mierda", "shit"],
            lista_strong=["puta", "fuck"],
        )
        assert provider.escanear("consulta academica normal") is None


# --------------------------------------------------------------------------- #
# T1b.3 + T1b.4 — Evasion normalization (NFKD + leet + whitespace collapse)
# --------------------------------------------------------------------------- #
class TestNormalizacionEvasion:
    """REQ-010: la normalización se aplica antes del matching.

    La lista curada está en su forma canónica (lowercase, sin diacríticos,
    sin leet). El input se transforma con el mismo pipeline antes de
    matchear, así las evasiones obvias se siguen detectando.
    """

    def test_match_case_insensitive_lowercase(self):
        from apps.copilot.domain.moderation import Severidad
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(lista_light=["mierda"], lista_strong=[])
        resultado = provider.escanear("Mierda")
        assert resultado is not None
        assert resultado[0] is Severidad.LIGHT

    def test_match_uppercase(self):
        from apps.copilot.domain.moderation import Severidad
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(lista_light=["mierda"], lista_strong=[])
        resultado = provider.escanear("MIERDA")
        assert resultado is not None
        assert resultado[0] is Severidad.LIGHT

    def test_diacritics_stripped(self):
        """NFKD + strip combining marks hace que 'míérda' matchee 'mierda'."""
        from apps.copilot.domain.moderation import Severidad
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(lista_light=["mierda"], lista_strong=[])
        resultado = provider.escanear("míérda")
        assert resultado is not None
        assert resultado[0] is Severidad.LIGHT

    def test_combining_marks_stripped(self):
        """Combining marks (U+0301 acute) se eliminan tras NFKD."""
        from apps.copilot.domain.moderation import Severidad
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        # "mierd\u0301a" = "mierda" + combining acute = "míerda"
        provider = HardcodedWordListProvider(lista_light=["mierda"], lista_strong=[])
        resultado = provider.escanear("mierd\u0301a")
        assert resultado is not None
        assert resultado[0] is Severidad.LIGHT

    def test_leet_1_to_i_3_to_e_4_to_a(self):
        from apps.copilot.domain.moderation import Severidad
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(lista_light=["mierda"], lista_strong=[])
        # "m13rd4" → "mierda" después de leet + collapse
        resultado = provider.escanear("m13rd4")
        assert resultado is not None
        assert resultado[0] is Severidad.LIGHT

    def test_leet_punct_stripped_fuck(self):
        from apps.copilot.domain.moderation import Severidad
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(lista_light=[], lista_strong=["fuck"])
        # "f.u.c.k" → "fuck" después de strip punct
        resultado = provider.escanear("f.u.c.k")
        assert resultado is not None
        assert resultado[0] is Severidad.STRONG

    def test_leet_punct_stripped_shit(self):
        from apps.copilot.domain.moderation import Severidad
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(lista_light=["shit"], lista_strong=[])
        resultado = provider.escanear("s_h_i_t")
        assert resultado is not None
        assert resultado[0] is Severidad.LIGHT

    def test_leet_punct_stripped_asterisk(self):
        from apps.copilot.domain.moderation import Severidad
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(lista_light=[], lista_strong=["fuck"])
        resultado = provider.escanear("f*u*c*k")
        assert resultado is not None
        assert resultado[0] is Severidad.STRONG

    def test_whitespace_collapse(self):
        from apps.copilot.domain.moderation import Severidad
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        # "f   u   c   k" → "f u c k" después de collapse
        # NO matchea "fuck" como token (whitespace entre letras)
        # pero si la lista tiene "f u c k" como token, sí matchea
        provider = HardcodedWordListProvider(lista_light=[], lista_strong=["f u c k"])
        resultado = provider.escanear("f   u   c   k")
        assert resultado is not None
        assert resultado[0] is Severidad.STRONG

    def test_punctuation_around_token_preserved(self):
        """El censor *** no agrega ni quita puntuación del contexto."""
        from apps.copilot.domain.moderation import Severidad
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(lista_light=["mierda"], lista_strong=[])
        resultado = provider.escanear("dame mi mierda.")
        assert resultado is not None
        assert resultado[0] is Severidad.LIGHT
        # El "." se preserva en la versión censurada
        assert resultado[1] == "dame mi ***."


# --------------------------------------------------------------------------- #
# T1b.5 + T1b.6 — Light severity: censurar con ***
# --------------------------------------------------------------------------- #
class TestLightCensurado:
    """REQ-001: matches light se censuran con '***' y el caller recibe el texto
    censurado. NO se levanta excepción (eso es para strong)."""

    def test_light_match_devuelve_tupla_severidad_y_censurado(self):
        from apps.copilot.domain.moderation import Severidad
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(lista_light=["mierda"], lista_strong=[])
        resultado = provider.escanear("dame mi mierda de notas")
        assert resultado is not None
        severidad, censurado = resultado
        assert severidad is Severidad.LIGHT
        assert censurado == "dame mi *** de notas"
        assert "mierda" not in censurado

    def test_multiple_light_todos_censurados(self):
        from apps.copilot.domain.moderation import Severidad
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(lista_light=["mierda", "shit"], lista_strong=[])
        resultado = provider.escanear("mierda y shit")
        assert resultado is not None
        severidad, censurado = resultado
        assert severidad is Severidad.LIGHT
        assert censurado == "*** y ***"

    def test_light_censura_preserva_contexto(self):
        """La censura no toca el resto del texto."""
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(lista_light=["mierda"], lista_strong=[])
        resultado = provider.escanear("hola mierda chau")
        assert resultado is not None
        censurado = resultado[1]
        assert censurado == "hola *** chau"

    def test_light_no_lanza_excepcion(self):
        """El provider reporta la severidad; la política de rechazo es del
        servicio de dominio. Light NO levanta ContenidoBloqueadoError."""
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(lista_light=["mierda"], lista_strong=[])
        # Si raise, falla el test
        resultado = provider.escanear("dame mi mierda")
        assert resultado is not None


# --------------------------------------------------------------------------- #
# T1b.7 + T1b.8 — Strong severity: reportar STRONG (provider no raise)
# --------------------------------------------------------------------------- #
class TestStrongDeteccion:
    """REQ-002: matches strong se reportan como (STRONG, texto). El provider NO
    levanta ContenidoBloqueadoError; eso lo hace el servicio de dominio."""

    def test_strong_match_devuelve_tupla_strong(self):
        from apps.copilot.domain.moderation import Severidad
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(lista_light=[], lista_strong=["puta"])
        resultado = provider.escanear("eres una puta")
        assert resultado is not None
        severidad, texto = resultado
        assert severidad is Severidad.STRONG

    def test_strong_wins_over_light(self):
        """Si un input tiene light y strong, gana strong (REQ-002 edge case)."""
        from apps.copilot.domain.moderation import Severidad
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(lista_light=["mierda"], lista_strong=["puta"])
        resultado = provider.escanear("mierda puta")
        assert resultado is not None
        severidad, _ = resultado
        assert severidad is Severidad.STRONG

    def test_strong_token_aislado_es_match(self):
        from apps.copilot.domain.moderation import Severidad
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(lista_light=[], lista_strong=["cabron"])
        resultado = provider.escanear("cabron")
        assert resultado is not None
        assert resultado[0] is Severidad.STRONG

    def test_strong_token_con_contexto_es_match(self):
        from apps.copilot.domain.moderation import Severidad
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(lista_light=[], lista_strong=["puta"])
        resultado = provider.escanear("hola puta chau")
        assert resultado is not None
        assert resultado[0] is Severidad.STRONG


# --------------------------------------------------------------------------- #
# T1b.9 + T1b.10 — Allow-list precedence (whole-phrase masks strong)
# --------------------------------------------------------------------------- #
class TestAllowListPrecedencia:
    """REQ-006: el allow-list relaja la severidad STRONG para substrings
    completos (whole-phrase). Light NUNCA se demota (siempre censura)."""

    def test_allow_list_relaja_strong_substring(self):
        """Con 'hijo de' en allow-list, 'hijo de la comunidad' NO es strong."""
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(
            lista_light=[],
            lista_strong=["puta"],
            allowlist=["hijo de"],
        )
        # "hijo de la comunidad" contiene "hijo de" (allow-list)
        # pero NO contiene "puta" (strong)
        # → clean (None)
        assert provider.escanear("hijo de la comunidad") is None

    def test_allow_list_no_relaja_light(self):
        """Light NUNCA se demota (siempre se censura)."""
        from apps.copilot.domain.moderation import Severidad
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(
            lista_light=["mierda"],
            lista_strong=[],
            allowlist=["mierda"],
        )
        # El allow-list tiene "mierda" pero light siempre se censura
        resultado = provider.escanear("dame mi mierda")
        assert resultado is not None
        assert resultado[0] is Severidad.LIGHT
        assert resultado[1] == "dame mi ***"

    def test_allow_list_mas_strong_token_aislado_aun_es_strong(self):
        """El allow-list relaja substrings; un strong token aislado sigue flagged."""
        from apps.copilot.domain.moderation import Severidad
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(
            lista_light=[],
            lista_strong=["puta"],
            allowlist=["hijo de"],
        )
        # "puta" es strong, no está en el allow-list
        resultado = provider.escanear("puta")
        assert resultado is not None
        assert resultado[0] is Severidad.STRONG

    def test_sin_allow_list_strong_se_aplica(self):
        """Sin allow-list, los strong se reportan normalmente."""
        from apps.copilot.domain.moderation import Severidad
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(
            lista_light=[],
            lista_strong=["puta"],
            allowlist=None,
        )
        resultado = provider.escanear("puta")
        assert resultado is not None
        assert resultado[0] is Severidad.STRONG

    def test_allow_list_vacio_no_relaja_nada(self):
        from apps.copilot.domain.moderation import Severidad
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(
            lista_light=[],
            lista_strong=["puta"],
            allowlist=[],
        )
        resultado = provider.escanear("puta")
        assert resultado is not None
        assert resultado[0] is Severidad.STRONG


# --------------------------------------------------------------------------- #
# T1b.11 + T1b.12 — Carga de allow-list desde JSON
# --------------------------------------------------------------------------- #
class TestCargaAllowlistJSON:
    """REQ-006: el allow-list se carga desde el JSON configurado."""

    def test_archivo_valido_carga_phrases(self, tmp_path):
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        allowlist_file = tmp_path / "allowlist.json"
        allowlist_file.write_text(
            json.dumps({"phrases": ["hijo de", "a partir de"]}),
            encoding="utf-8",
        )
        result = HardcodedWordListProvider.cargar_allowlist_desde_json(allowlist_file)
        assert result == ["hijo de", "a partir de"]

    def test_archivo_inexistente_retorna_lista_vacia(self, tmp_path, caplog):
        import logging

        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        missing = tmp_path / "no_existe.json"
        with caplog.at_level(logging.WARNING, logger="apps.copilot.moderation.wordlist"):
            result = HardcodedWordListProvider.cargar_allowlist_desde_json(missing)
        assert result == []
        # Verifica que se loggeó el WARNING
        assert any("allowlist.fallback" in record.message for record in caplog.records)

    def test_json_invalido_retorna_lista_vacia(self, tmp_path, caplog):
        import logging

        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        bad = tmp_path / "bad.json"
        bad.write_text("{ no es json valido", encoding="utf-8")
        with caplog.at_level(logging.WARNING, logger="apps.copilot.moderation.wordlist"):
            result = HardcodedWordListProvider.cargar_allowlist_desde_json(bad)
        assert result == []
        assert any("allowlist.fallback" in record.message for record in caplog.records)

    def test_schema_incorrecto_sin_clave_phrases_retorna_vacia(self, tmp_path, caplog):
        import logging

        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        bad = tmp_path / "wrong_schema.json"
        bad.write_text(json.dumps({"otra_clave": ["x", "y"]}), encoding="utf-8")
        with caplog.at_level(logging.WARNING, logger="apps.copilot.moderation.wordlist"):
            result = HardcodedWordListProvider.cargar_allowlist_desde_json(bad)
        assert result == []

    def test_phrases_no_es_lista_retorna_vacia(self, tmp_path, caplog):
        import logging

        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        bad = tmp_path / "phrases_not_list.json"
        bad.write_text(json.dumps({"phrases": "no soy lista"}), encoding="utf-8")
        with caplog.at_level(logging.WARNING, logger="apps.copilot.moderation.wordlist"):
            result = HardcodedWordListProvider.cargar_allowlist_desde_json(bad)
        assert result == []

    def test_phrases_con_no_strings_retorna_vacia(self, tmp_path, caplog):
        import logging

        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        bad = tmp_path / "phrases_mixed.json"
        bad.write_text(json.dumps({"phrases": ["ok", 123, "ok2"]}), encoding="utf-8")
        with caplog.at_level(logging.WARNING, logger="apps.copilot.moderation.wordlist"):
            result = HardcodedWordListProvider.cargar_allowlist_desde_json(bad)
        assert result == []

    def test_allowlist_cargado_desde_json_relaja_strong(self, tmp_path):
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        allowlist_file = tmp_path / "allowlist.json"
        allowlist_file.write_text(
            json.dumps({"phrases": ["hijo de"]}),
            encoding="utf-8",
        )
        phrases = HardcodedWordListProvider.cargar_allowlist_desde_json(allowlist_file)
        provider = HardcodedWordListProvider(
            lista_light=[],
            lista_strong=["puta"],
            allowlist=phrases,
        )
        # "hijo de la comunidad" contiene "hijo de" → strong relajado → clean
        assert provider.escanear("hijo de la comunidad") is None
        # Pero "puta" aislada sigue siendo strong
        from apps.copilot.domain.moderation import Severidad

        resultado = provider.escanear("puta")
        assert resultado is not None
        assert resultado[0] is Severidad.STRONG


# --------------------------------------------------------------------------- #
# Edge cases adicionales (no en T1b.X estricto pero pin de comportamiento)
# --------------------------------------------------------------------------- #
class TestEdgeCases:
    """Casos límite adicionales que no rompen la spec pero pin de comportamiento."""

    def test_word_boundary_bibliomierda_no_matchea(self):
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(lista_light=["mierda"], lista_strong=[])
        # "bibliomierda" NO debe matchear "mierda" por \\b word boundaries
        assert provider.escanear("bibliomierda") is None

    def test_greek_omicron_oot(self):
        """Homoglyph detection (Greek ο) es OOS — el OpenAI Moderation es la red de seguridad."""
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(lista_light=["mierda"], lista_strong=[])
        # Greek omicron "ο" no se translitera a "o" en el pipeline
        # (sólo strip combining, no transliteración cross-script)
        assert provider.escanear("ο") is None

    def test_listas_vacias_retorna_none(self):
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(lista_light=[], lista_strong=[])
        assert provider.escanear("mierda puta cabron") is None

    def test_normalizacion_case_insensitive_en_allowlist(self):
        """El allow-list matchea case-insensitive (REQ-006)."""
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(
            lista_light=[],
            lista_strong=["puta"],
            allowlist=["Hijo De"],  # mixed case en allow-list
        )
        # El allow-list está en mixed case, el input en lowercase
        # "hijo de la comunidad" contiene "hijo de" (normalizado)
        assert provider.escanear("hijo de la comunidad") is None


# --------------------------------------------------------------------------- #
# Production data wiring — verifica la integración con los archivos default
# --------------------------------------------------------------------------- #
class TestProduccionDataWiring:
    """Verifica que los archivos de datos de PR 1b existen y son usables."""

    def test_palabras_censuradas_listas_no_vacias(self):
        from apps.copilot.data.palabras_censuradas import (
            DEFAULT_PROFANITY_LIGHT,
            DEFAULT_PROFANITY_STRONG,
            DEFAULT_ALLOWLIST,
        )

        assert len(DEFAULT_PROFANITY_LIGHT) >= 6
        assert len(DEFAULT_PROFANITY_STRONG) >= 4
        assert len(DEFAULT_ALLOWLIST) >= 2
        # Todas las entradas son strings
        for entry in DEFAULT_PROFANITY_LIGHT:
            assert isinstance(entry, str)
        for entry in DEFAULT_PROFANITY_STRONG:
            assert isinstance(entry, str)
        for entry in DEFAULT_ALLOWLIST:
            assert isinstance(entry, str)

    def test_palabras_censuradas_cubre_es_y_en(self):
        """El curated default cubre ES y EN, light y strong."""
        from apps.copilot.data.palabras_censuradas import (
            DEFAULT_PROFANITY_LIGHT,
            DEFAULT_PROFANITY_STRONG,
        )

        # ES light: "mierda", "carajo"
        assert "mierda" in DEFAULT_PROFANITY_LIGHT
        assert "carajo" in DEFAULT_PROFANITY_LIGHT
        # EN light: "shit", "damn"
        assert "shit" in DEFAULT_PROFANITY_LIGHT
        assert "damn" in DEFAULT_PROFANITY_LIGHT
        # ES strong: "puta", "pendejo"
        assert "puta" in DEFAULT_PROFANITY_STRONG
        assert "pendejo" in DEFAULT_PROFANITY_STRONG
        # EN strong: "fuck", "bitch"
        assert "fuck" in DEFAULT_PROFANITY_STRONG
        assert "bitch" in DEFAULT_PROFANITY_STRONG

    def test_allowlist_es_json_existe_y_es_valido(self):
        """El JSON de allow-list existe y se carga sin error."""
        from django.conf import settings

        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        # El setting apunta al archivo real de PR 1b
        allowlist = HardcodedWordListProvider.cargar_allowlist_desde_json(
            settings.COPILOT_MODERATION_ALLOWLIST_PATH
        )
        assert isinstance(allowlist, list)
        assert len(allowlist) >= 2
        # Contiene al menos "hijo de" (frase académica clave)
        assert "hijo de" in allowlist

    def test_provider_con_datos_de_produccion_funciona(self):
        """El provider construido con los datos de producción detecta tokens."""
        from apps.copilot.data.palabras_censuradas import (
            DEFAULT_PROFANITY_LIGHT,
            DEFAULT_PROFANITY_STRONG,
            DEFAULT_ALLOWLIST,
        )
        from apps.copilot.domain.moderation import Severidad
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )

        provider = HardcodedWordListProvider(
            lista_light=list(DEFAULT_PROFANITY_LIGHT),
            lista_strong=list(DEFAULT_PROFANITY_STRONG),
            allowlist=list(DEFAULT_ALLOWLIST),
        )
        # Light match: "mierda" está en light
        resultado = provider.escanear("dame mi mierda")
        assert resultado is not None
        assert resultado[0] is Severidad.LIGHT
        # Strong match: "puta" está en strong
        resultado2 = provider.escanear("eres una puta")
        assert resultado2 is not None
        assert resultado2[0] is Severidad.STRONG
        # Allow-list: "hijo de" en allowlist → strong relajado para "hijo de la familia"
        assert provider.escanear("hijo de la familia") is None
        # Clean: "dame mis notas" no matchea nada
        assert provider.escanear("dame mis notas") is None
