"""
Domain-specific exceptions for the Solicitudes bounded context.
Pure Python — NO Django imports allowed in this layer.
"""


class SolicitudError(Exception):
    """Base exception for Solicitud domain errors."""


class SolicitudYaResueltaError(SolicitudError):
    """Raised when trying to resolve an already-resolved request."""


# --- HU20: Certificados de justificación ---


class CamposObligatoriosFaltantesError(SolicitudError):
    """Raised when required certificate metadata fields are missing.

    Stakeholder rule (HU20): every ``tipo_certificado`` has its own set of
    required fields. This exception lists the field names that the caller
    failed to provide so the presentation layer can highlight them.
    """

    def __init__(self, campos: list[str]):
        self.campos = list(campos)
        super().__init__(self.campos)

    def __str__(self) -> str:
        if not self.campos:
            return "Faltan campos obligatorios."
        return f"Faltan campos obligatorios: {', '.join(self.campos)}"


class FechaCertificadoInvalidaError(SolicitudError):
    """Raised when ``fecha_certificado`` is in the future.

    Same-day and past dates are accepted; only future dates are invalid.
    """

    def __str__(self) -> str:
        return "La fecha del certificado no puede ser futura."


class MaximoArchivosExcedidoError(SolicitudError):
    """Raised when the submission contains more files than allowed.

    HU20 caps attachments at ``CertificadoValidationService.MAX_ARCHIVOS`` (5).
    """

    def __init__(self, cantidad: int):
        self.cantidad = cantidad
        super().__init__(cantidad)

    def __str__(self) -> str:
        return (
            f"Se excedió el máximo de archivos permitidos "
            f"(recibidos: {self.cantidad})."
        )


class ArchivoInvalidoError(SolicitudError):
    """Raised when a single uploaded file fails domain validation.

    ``nombre`` identifies the offending file; ``errores`` is a list of
    machine-readable error codes (e.g. ``extension_invalida``,
    ``tamanio_excedido``) for the presentation layer to localize.
    """

    def __init__(self, nombre: str, errores: list[str]):
        self.nombre = nombre
        self.errores = list(errores)
        super().__init__(nombre, self.errores)

    def __str__(self) -> str:
        errores_txt = ", ".join(self.errores) if self.errores else "sin detalle"
        return f"Archivo inválido '{self.nombre}': {errores_txt}"
