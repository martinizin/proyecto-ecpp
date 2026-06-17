"""Hardcoded ES/EN word-list provider for the copilot moderation layer.

Concrete implementation of the ``ProveedorListaDura`` Protocol declared in
``apps.copilot.domain.moderation``. The provider scans text against a curated
ES/EN word list with severity tags and applies an evasion-normalization
pipeline (NFKD + leet substitution + punctuation strip + whitespace collapse)
before pattern matching.

Allow-list precedence (REQ-006, design §3-tier decision flow): if the input
contains an allow-list phrase as a substring (case-insensitive, on the
normalized form), strong-severity matches are relaxed to clean. Light matches
are NEVER demoted — light is censored, not blocked.

The allow-list is loaded once at construction time from the JSON file pointed
to by ``COPILOT_MODERATION_ALLOWLIST_PATH``. A missing or invalid file logs a
WARNING and falls back to an empty allow-list.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Callable

from apps.copilot.domain.moderation import Severidad


logger = logging.getLogger("apps.copilot.moderation.wordlist")


class HardcodedWordListProvider:
    """Curated ES/EN word-list provider with evasion normalization.

    Matches ``ProveedorListaDura`` from ``apps.copilot.domain.moderation``:
    exposes ``escanear(texto) -> tuple[Severidad, str] | None``.

    Constructor signature:
        - ``lista_light``: tokens censored with ``***`` (no exception).
        - ``lista_strong``: tokens that raise ``ContenidoBloqueadoError`` at the
          service layer (the provider itself only reports the match).
        - ``allowlist``: phrases (substrings) that relax strong-severity
          matches. ``None`` = no allow-list relaxation.
        - ``normalizador``: optional override for the normalization pipeline.
          Tests inject custom normalizers to keep the unit boundary clean.

    The provider compiles a regex from the light list at construction time.
    Strong matches are reported as ``Severidad.STRONG`` so the domain service
    can decide whether to raise (the provider does NOT raise directly — that
    keeps the protocol pure data).
    """

    # Mapa de sustitución leet-speak (REQ-010, design §Normalization).
    # Sólo caracteres que tienen una UNICA lectura razonable en español/inglés
    # para evitar falsos positivos. La sustitución inversa ``l → 1`` está
    # omitida porque ``l`` es una letra normal y el matcher ya acepta
    # palabras reales del español.
    _LEET_MAP: dict[str, str] = {
        "1": "i",
        "3": "e",
        "4": "a",
        "0": "o",
        "5": "s",
        "7": "t",
    }
    # Puntuación típica insertada para evadir el filtro (REQ-010).
    _LEET_PUNCT: str = "._-*"

    def __init__(
        self,
        lista_light: list[str],
        lista_strong: list[str],
        allowlist: list[str] | None = None,
        normalizador: Callable[[str], str] | None = None,
    ):
        self._lista_light: tuple[str, ...] = tuple(lista_light)
        self._lista_strong: tuple[str, ...] = tuple(lista_strong)
        self._allowlist: tuple[str, ...] = tuple(allowlist) if allowlist else ()
        self._normalizador: Callable[[str], str] = (
            normalizador if normalizador is not None else self._normalizar
        )
        # Compilamos el regex de la lista light una sola vez. La lista strong
        # se recorre por tokens (no se compila) porque permite el camino de
        # ``strong token aislado = match`` que el regex global de light
        # también atrapa — pero el orden de chequeo importa para el caso
        # ``strong_wins_over_light``.
        self._regex_light: re.Pattern[str] | None = (
            self._compilar_regex_light(self._lista_light) if self._lista_light else None
        )

    # ------------------------------------------------------------------ #
    # API pública
    # ------------------------------------------------------------------ #
    def escanear(self, texto: str) -> tuple[Severidad, str] | None:
        """Devuelve ``(severidad, texto_censurado)`` si hay match, ``None`` si limpio.

        El provider NO levanta ``ContenidoBloqueadoError``; sólo reporta la
        severidad. La política de rechazo vive en
        ``apps.copilot.domain.moderation.ModeracionServicio``.
        """
        if not texto or not texto.strip():
            return None

        # 1. Normalizar (minúsculas, NFKD, leet, espacios).
        normalizado = self._normalizador(texto)

        # 2. Allow-list precedence (REQ-006): si el input contiene una frase
        #    del allow-list, los matches strong se DEMOTAN a clean. Light NUNCA
        #    se demota (siempre se censura).
        allow_list_hit = self._check_allowlist(normalizado)

        # 3. Strong matches primero (strong wins over light, REQ-002 edge case).
        for token in self._lista_strong:
            patron = self._regex_token(token)
            match = patron.search(normalizado)
            if match is not None and not allow_list_hit:
                return (Severidad.STRONG, texto)

        # 4. Light matches (censura con ***).
        if self._regex_light is not None:
            match = self._regex_light.search(normalizado)
            if match is not None:
                censurado = self._regex_light.sub("***", texto)
                return (Severidad.LIGHT, censurado)

        return None

    # ------------------------------------------------------------------ #
    # Helpers — normalización
    # ------------------------------------------------------------------ #
    @classmethod
    def _normalizar(cls, texto: str) -> str:
        """Pipeline de normalización: NFKD → strip combining → leet → colapsar
        whitespace → lower(). Idéntico al aplicado al allow-list para que
        ambos operen sobre la misma forma (REQ-010, design §Normalization)."""
        if not texto:
            return ""
        # 1. NFKD descompone caracteres con diacríticos (REQ-010):
        #    "míérda" → "mi" + combining acute + "e" + combining acute + "rda"
        decomposed = unicodedata.normalize("NFKD", texto)
        # 2. Strip combining marks (los acentos quedan solos y se eliminan):
        sin_diacriticos = "".join(c for c in decomposed if not unicodedata.combining(c))
        # 3. Sustitución leet-speak:
        leet = "".join(cls._LEET_MAP.get(c, c) for c in sin_diacriticos)
        # 4. Strip puntuación leet (".", "_", "-", "*"):
        sin_punct = "".join(c for c in leet if c not in cls._LEET_PUNCT)
        # 5. Collapse whitespace:
        colapsado = re.sub(r"\s+", " ", sin_punct)
        # 6. Lowercase:
        return colapsado.lower().strip()

    @classmethod
    def _regex_token(cls, token: str) -> re.Pattern[str]:
        """Compila un patrón con \\b word-boundaries para un token normalizado.

        Los tokens se asumen ya normalizados al cargarse (la lista curada se
        escribe en su forma canónica). Si el token tiene espacios
        (multi-palabra como ``hijo de puta``), los \\b se anclan al inicio
        y al final del primer/último caracter.
        """
        return re.compile(rf"\b{re.escape(token)}\b", re.IGNORECASE)

    @classmethod
    def _compilar_regex_light(cls, tokens: tuple[str, ...]) -> re.Pattern[str]:
        """Une todos los tokens light en un solo regex con grupos nombrados.

        La censura posterior usa ``re.sub`` que reemplaza la coincidencia
        completa (no los grupos) por ``***``."""
        if not tokens:
            # Regex que no matchea nada
            return re.compile(r"(?!)")
        escaped = "|".join(re.escape(t) for t in tokens)
        return re.compile(rf"\b(?:{escaped})\b", re.IGNORECASE)

    # ------------------------------------------------------------------ #
    # Helpers — allow-list
    # ------------------------------------------------------------------ #
    def _check_allowlist(self, normalizado: str) -> bool:
        """Devuelve True si el input normalizado contiene alguna frase del
        allow-list (case-insensitive, substring)."""
        for frase in self._allowlist:
            frase_normalizada = self._normalizador(frase)
            if frase_normalizada and frase_normalizada in normalizado:
                return True
        return False

    # ------------------------------------------------------------------ #
    # Carga de allow-list desde JSON
    # ------------------------------------------------------------------ #
    @staticmethod
    def cargar_allowlist_desde_json(path: str | Path) -> list[str]:
        """Lee el archivo JSON y devuelve la lista de frases del allow-list.

        Shape esperado: ``{"phrases": [str, ...]}``. En cualquier fallo
        (``FileNotFoundError``, ``json.JSONDecodeError``, schema incorrecto)
        emite WARNING ``copilot.moderation.allowlist.fallback`` con
        ``path`` y ``error_class`` y devuelve ``[]``.
        """
        path = Path(path)
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except FileNotFoundError as exc:
            logger.warning(
                "copilot.moderation.allowlist.fallback",
                extra={
                    "path": str(path),
                    "error_class": type(exc).__name__,
                },
            )
            return []
        except json.JSONDecodeError as exc:
            logger.warning(
                "copilot.moderation.allowlist.fallback",
                extra={
                    "path": str(path),
                    "error_class": type(exc).__name__,
                },
            )
            return []

        if not isinstance(data, dict) or "phrases" not in data:
            logger.warning(
                "copilot.moderation.allowlist.fallback",
                extra={
                    "path": str(path),
                    "error_class": "SchemaError",
                },
            )
            return []

        phrases = data["phrases"]
        if not isinstance(phrases, list) or not all(isinstance(p, str) for p in phrases):
            logger.warning(
                "copilot.moderation.allowlist.fallback",
                extra={
                    "path": str(path),
                    "error_class": "SchemaError",
                },
            )
            return []

        return list(phrases)
