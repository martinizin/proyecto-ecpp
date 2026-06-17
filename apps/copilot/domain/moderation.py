"""Dominio de moderación de contenido del copilot ECPP (HU22 + copilot-content-moderation).

Capa pura: sin I/O, sin llamadas a OpenAI, sin acceso a disco. Las dependencias
externas (lista dura de palabras, cliente de OpenAI Moderation) se inyectan
como ``Protocol`` en el constructor de ``ModeracionServicio``. Las
implementaciones concretas viven en ``apps.copilot.infrastructure`` (PR 1b).

Reglas cubiertas (spec REQ-001 → REQ-009):
- 3-tier policy: clean / light (censura) / strong (rechazo).
- Lista dura ES/EN con normalización NFKD + leet (PR 1b).
- OpenAI Moderation API como fallback de entrada y como moderación de salida.
- Texto de rechazo byte-locked (``CANNED_REFUSAL``).
- Fail-open en entrada / skip en salida ante error de OpenAI.
- Feature flag (``habilitado``) que corta el pipeline completo.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

import openai

from apps.copilot.domain.exceptions import ContenidoBloqueadoError


# Logger del dominio de moderación. Los handlers se configuran en el
# ``LOGGING`` de Django (ver ``config/settings/base.py``).
logger = logging.getLogger("apps.copilot.moderation")


# Texto de rechazo byte-locked (REQ-005). Único punto de la verdad para el
# mensaje devuelto al usuario ante cualquier rechazo de moderación. NO
# reformatear, NO traducir, NO envolver con comillas/espacios. La apertura
# es "no" (n minúscula) sin acento.
CANNED_REFUSAL: str = (
    "no puedo responder consultas con ese tipo de palabras, "
    "intenta realizar tu consulta de manera diferente por favor"
)


class Severidad(Enum):
    """Severidad del match contra la lista dura de palabras.

    - ``CLEAN``: el proveedor no encontró matches (no se censuró nada).
    - ``LIGHT``: se encontró un match de severidad baja — se censuró con ``***``.
    - ``STRONG``: se encontró un match de severidad alta — se rechaza el input.
    """

    CLEAN = "clean"
    LIGHT = "light"
    STRONG = "strong"


@dataclass(frozen=True)
class ResultadoModeracion:
    """Resultado de una evaluación de moderación (entrada o salida).

    Atributos:
        flagged: ``True`` cuando el contenido fue rechazado (razón != None).
            Light NO cuenta como flagged porque es censura con paso a LLM.
        severidad: severidad del match contra la lista dura (CLEAN si nada).
        razon: identificador de la política que disparó el rechazo. Uno de:
            ``"strong_list"``, ``"openai_input"``, ``"openai_output"``. ``None``
            si el contenido pasó (limpio o censurado-light).
        contenido_sanitizado: texto que el llamador debe enviar al LLM / al
            cliente. Para clean es el original; para light es la versión
            censurada; para strong es la versión censurada (pero la política
            rechaza antes de llegar al LLM).
    """

    flagged: bool
    severidad: Severidad
    razon: str | None
    contenido_sanitizado: str


# --------------------------------------------------------------------------- #
# Protocolos — contratos inyectables (las implementaciones viven en PR 1b)
# --------------------------------------------------------------------------- #
class ProveedorListaDura(Protocol):
    """Contrato del proveedor de la lista curada ES/EN (PR 1b)."""

    def escanear(self, texto: str) -> tuple[Severidad, str] | None:
        """Devuelve ``(severidad, texto_censurado)`` si hay match, ``None`` si limpio."""
        ...


class ProveedorModeracionExterno(Protocol):
    """Contrato del cliente de OpenAI Moderation API (PR 1b)."""

    def clasificar(self, texto: str) -> bool:
        """Devuelve ``True`` si el texto fue flagged por la API."""
        ...


# --------------------------------------------------------------------------- #
# Servicio principal
# --------------------------------------------------------------------------- #
class ModeracionServicio:
    """Servicio de dominio puro para moderación de contenido del copilot.

    Recibe las dependencias (lista dura + cliente OpenAI) por constructor
    siguiendo el patrón usado por ``CopilotAppService`` y el ``AcademicDataServiceProtocol``.
    NO hace I/O ni llamadas a la red — los proveedores son ``Protocol`` que se
    implementan en la capa de infraestructura (PR 1b).

    El pipeline de entrada ejecuta, en orden:
        1. Short-circuit si ``habilitado`` es False.
        2. ``escanear(texto)`` del proveedor de lista dura.
            - ``None`` → continuar al paso 3.
            - ``(LIGHT, censurado)`` → devolver resultado con severidad LIGHT
              y el texto censurado para que la API externa vea la versión censurada.
            - ``(STRONG, censurado)`` → ``ContenidoBloqueadoError("strong_list")``.
        3. ``clasificar(texto)`` del proveedor externo (OpenAI Moderation).
            - ``True`` → ``ContenidoBloqueadoError("openai_input")``.
            - ``False`` → resultado CLEAN.
        4. Si la API lanza ``openai.APIError`` → fail-OPEN: resultado CLEAN
           con el texto que se estaba moderando, log ERROR.
    """

    def __init__(
        self,
        proveedor_lista_dura: ProveedorListaDura,
        proveedor_moderacion_externo: ProveedorModeracionExterno,
        habilitado: bool = True,
    ):
        self._proveedor_lista = proveedor_lista_dura
        self._proveedor_externo = proveedor_moderacion_externo
        self._habilitado = habilitado

    def evaluar_input(self, texto: str, *, request_id: str = "") -> ResultadoModeracion:
        """Evalúa el input del usuario. Devuelve ``ResultadoModeracion`` o levanta
        ``ContenidoBloqueadoError`` para rechazos (Tier 3a / 3b)."""
        # 1. Feature-flag short-circuit (REQ-007): bypass total.
        if not self._habilitado:
            return ResultadoModeracion(
                flagged=False,
                severidad=Severidad.CLEAN,
                razon=None,
                contenido_sanitizado=texto,
            )

        # 2. Lista dura (síncrona, <1 ms; provee PR 1b).
        match = self._proveedor_lista.escanear(texto)
        if match is not None:
            severidad, texto_censurado = match
            if severidad is Severidad.STRONG:
                # Tier 3a: rechazo inmediato, no se llama a OpenAI.
                raise ContenidoBloqueadoError(razon="strong_list")
            if severidad is Severidad.LIGHT:
                # Tier 2: censura y pasa; la API ve el texto censurado
                # (REQ-003, edge case: la lista corre sobre censurado).
                try:
                    flagged = self._proveedor_externo.clasificar(texto_censurado)
                except openai.APIError as exc:
                    # Fail-open: si la API externa falla en la llamada post-censura,
                    # igualmente pasamos al LLM con la versión censurada.
                    logger.error(
                        "copilot.moderation.api.error",
                        extra={
                            "fase": "input",
                            "error_class": type(exc).__name__,
                            "request_id": request_id,
                        },
                    )
                    return ResultadoModeracion(
                        flagged=False,
                        severidad=Severidad.LIGHT,
                        razon=None,
                        contenido_sanitizado=texto_censurado,
                    )
                if flagged:
                    raise ContenidoBloqueadoError(razon="openai_input")
                return ResultadoModeracion(
                    flagged=False,
                    severidad=Severidad.LIGHT,
                    razon=None,
                    contenido_sanitizado=texto_censurado,
                )

        # 3. La lista no marcó nada — fallback semántico con OpenAI.
        try:
            flagged = self._proveedor_externo.clasificar(texto)
        except openai.APIError as exc:
            # REQ-009: fail-OPEN en input.
            logger.error(
                "copilot.moderation.api.error",
                extra={
                    "fase": "input",
                    "error_class": type(exc).__name__,
                    "request_id": request_id,
                },
            )
            return ResultadoModeracion(
                flagged=False,
                severidad=Severidad.CLEAN,
                razon=None,
                contenido_sanitizado=texto,
            )

        if flagged:
            raise ContenidoBloqueadoError(razon="openai_input")

        return ResultadoModeracion(
            flagged=False,
            severidad=Severidad.CLEAN,
            razon=None,
            contenido_sanitizado=texto,
        )

    def sanitizar(self, texto: str, resultado: ResultadoModeracion) -> str:
        """Devuelve el texto que se debe enviar al LLM / persistir / mostrar.

        Comportamiento por nivel:
            - ``resultado.flagged is True`` (cualquier razón): levanta
              ``ContenidoBloqueadoError(razon=resultado.razon)``.
            - ``resultado.severidad is Severidad.LIGHT``: devuelve
              ``resultado.contenido_sanitizado`` (versión censurada).
            - ``Severidad.CLEAN``: devuelve ``texto`` (original).

        Esta función no hace I/O — sólo lee los campos del resultado ya
        calculado por ``evaluar_input`` / ``evaluar_output``.
        """
        if resultado.flagged:
            assert resultado.razon is not None  # invariant: flagged ⇒ razon
            raise ContenidoBloqueadoError(razon=resultado.razon)
        if resultado.severidad is Severidad.LIGHT:
            return resultado.contenido_sanitizado
        return texto
