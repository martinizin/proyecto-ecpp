"""Domain services for the Solicitudes bounded context (HU20).

Pure Python — NO Django imports. These services encapsulate business
rules so they can be unit-tested in isolation and reused across
application services, forms, and tasks.
"""

from __future__ import annotations

import os
from datetime import date


class CertificadoValidationService:
    """Validation rules for ``CertificadoJustificacion`` and its attachments.

    All methods are pure: they take primitive inputs and return primitives
    or lists of error codes / missing field names. They do NOT raise; the
    application service decides whether to translate a non-empty result
    into a domain exception.

    Stakeholder overrides applied here (HU20):
        * MAX_ARCHIVOS = 5   (PRD said 3)
        * NO deadline rule — there is intentionally NO
          ``validar_plazo_justificacion`` method.
    """

    MAX_ARCHIVOS: int = 5
    MAX_TAMANIO: int = 5 * 1024 * 1024  # 5 MB
    EXTENSIONES_VALIDAS: list[str] = [".pdf", ".jpg", ".jpeg", ".png"]

    CAMPOS_OBLIGATORIOS: dict[str, list[str]] = {
        "medico": [
            "institucion_emisora",
            "fecha_certificado",
            "numero_documento",
            "nombre_medico",
            "dias_reposo",
        ],
        "laboral": [
            "institucion_emisora",
            "fecha_certificado",
            "cargo",
        ],
        "calamidad": [
            "fecha_certificado",
            "descripcion_evento",
            "relacion_familiar",
        ],
    }

    # ------------------------------------------------------------------ #
    # required fields
    # ------------------------------------------------------------------ #
    @classmethod
    def validar_campos_obligatorios(cls, tipo: str, datos: dict) -> list[str]:
        """Return the list of required field names missing from ``datos``.

        A field counts as missing when:
          * it is not a key of ``datos``, OR
          * its value is ``None``, OR
          * its value is a string that is empty after ``strip()``.

        Unknown ``tipo`` returns an empty list — the form/app layer is
        responsible for rejecting invalid types via the ``TipoCertificado``
        enum; this method only enforces per-type required fields.
        """
        requeridos = cls.CAMPOS_OBLIGATORIOS.get(tipo, [])
        faltantes: list[str] = []
        for campo in requeridos:
            valor = datos.get(campo)
            if valor is None:
                faltantes.append(campo)
                continue
            if isinstance(valor, str) and not valor.strip():
                faltantes.append(campo)
        return faltantes

    # ------------------------------------------------------------------ #
    # date
    # ------------------------------------------------------------------ #
    @classmethod
    def validar_fecha_certificado(
        cls, fecha_certificado: date, fecha_referencia: date
    ) -> bool:
        """Return ``True`` iff ``fecha_certificado <= fecha_referencia``.

        ``fecha_referencia`` is typically ``date.today()`` in the server
        timezone. Same-day is accepted; future dates are rejected.
        """
        return fecha_certificado <= fecha_referencia

    # ------------------------------------------------------------------ #
    # files
    # ------------------------------------------------------------------ #
    @classmethod
    def validar_archivo(cls, nombre: str, tamanio: int) -> list[str]:
        """Return a list of error codes for the given file metadata.

        Error codes:
          * ``"extension_invalida"`` — extension not in
            :attr:`EXTENSIONES_VALIDAS` (case-insensitive) or absent.
          * ``"tamanio_excedido"`` — size strictly greater than
            :attr:`MAX_TAMANIO`.

        Empty result means the file is valid.
        """
        errores: list[str] = []
        _, ext = os.path.splitext(nombre or "")
        if ext.lower() not in cls.EXTENSIONES_VALIDAS:
            errores.append("extension_invalida")
        if tamanio > cls.MAX_TAMANIO:
            errores.append("tamanio_excedido")
        return errores
