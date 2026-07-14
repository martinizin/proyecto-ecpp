class RateLimitExcedidoError(Exception):
    """Raised when a user exceeds the allowed message rate (30/hour)."""

    def __init__(self, limite: int = 30):
        self.limite = limite
        super().__init__(f"Rate limit excedido: máximo {limite} mensajes por hora.")


class SesionLlenaError(Exception):
    """Raised when a conversation session reaches the maximum message count (50)."""

    def __init__(self, maximo: int = 50):
        self.maximo = maximo
        super().__init__(f"Sesión llena: máximo {maximo} mensajes por conversación.")


class SesionExpiradaError(Exception):
    """Raised when a conversation session has expired due to inactivity (24h)."""

    def __init__(self):
        super().__init__("La sesión del copilot ha expirado por inactividad.")


class MensajeVacioError(Exception):
    """Raised when a message has no content."""

    def __init__(self):
        super().__init__("El mensaje no puede estar vacío.")


class MensajeDemaisiadoLargoError(Exception):
    """Raised when a message exceeds the maximum allowed length."""

    def __init__(self, maximo: int = 1000):
        self.maximo = maximo
        super().__init__(f"El mensaje supera el límite de {maximo} caracteres.")


class ContenidoBloqueadoError(Exception):
    """Raised when content is rejected by the moderation pipeline.

    Attributes:
        razon: Identifier of the rejection policy. One of:
            - ``"strong_list"``: hardcoded word list flagged the input as strong.
            - ``"openai_input"``: OpenAI Moderation API flagged the user input.
            - ``"openai_output"``: OpenAI Moderation API flagged the LLM reply.

        contenido_censurado: user text with the offending words masked with
            ``***``. The conversation shows and persists this version — never
            the raw wording. Empty when the rejection carries no user text
            (e.g. ``openai_output``).
        respuesta: role-aware refusal shown to the user. The application layer
            fills it in (the domain does not know the caller's role); it falls
            back to ``CANNED_REFUSAL``.

    The exception message is ALWAYS the byte-locked canned refusal text
    (``CANNED_REFUSAL`` from ``apps.copilot.domain.moderation``). The message
    is read at construction time via a lazy import to avoid a circular
    dependency with the domain module.
    """

    def __init__(self, razon: str, contenido_censurado: str = "", respuesta: str = ""):
        from apps.copilot.domain.moderation import CANNED_REFUSAL

        self.razon = razon
        self.contenido_censurado = contenido_censurado
        self.respuesta = respuesta or CANNED_REFUSAL
        super().__init__(CANNED_REFUSAL)
