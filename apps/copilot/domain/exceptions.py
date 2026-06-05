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
