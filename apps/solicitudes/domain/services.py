"""Domain services for the Solicitudes bounded context (HU20).

Pure Python — NO Django imports. These services encapsulate business
rules so they can be unit-tested in isolation and reused across
application services, forms, and tasks.
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Literal


# ---------------------------------------------------------------------------
# Urgency helpers (HU21) — pure Python, NO Django imports
# ---------------------------------------------------------------------------
def dias_habiles_transcurridos(fecha_inicio: date, fecha_referencia: date) -> int:
    """Return the count of weekdays (Mon-Fri) strictly AFTER ``fecha_inicio``
    up to and including ``fecha_referencia``.

    Semantics (per HU21 ``solicitudes-domain-helpers`` spec):
      * Same date -> 0.
      * Monday -> Friday same week -> 4 (Tue, Wed, Thu, Fri).
      * Friday -> next Monday -> 1 (weekend skipped, only Monday counts).
      * ``fecha_referencia <= fecha_inicio`` -> 0 (future start clamped).
      * Saturday and Sunday never count regardless of position.

    Pure Python: no Django, no ORM, no settings.
    """
    if fecha_referencia <= fecha_inicio:
        return 0
    count = 0
    current = fecha_inicio + timedelta(days=1)
    while current <= fecha_referencia:
        # Monday=0 .. Friday=4, Saturday=5, Sunday=6
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return count


def clasificar_urgencia(
    fecha_creacion: date,
    deadline_dias: int,
    alerta_dias: int,
    today: date | None = None,
) -> Literal["normal", "alerta", "vencido"]:
    """Classify how urgent a pending solicitud is based on elapsed business
    days vs configured ``deadline_dias`` and ``alerta_dias``.

    Algorithm (per HU21 spec):
      * ``elapsed = dias_habiles_transcurridos(fecha_creacion, today)``
      * ``remaining = deadline_dias - elapsed``
      * ``"vencido"`` when ``remaining <= 0``
      * ``"alerta"``  when ``0 < remaining <= alerta_dias``
      * ``"normal"``  otherwise

    ``today`` defaults to ``date.today()`` when ``None``.

    Raises ``ValueError`` if ``alerta_dias >= deadline_dias``: the alert
    window must be strictly smaller than the deadline, otherwise no
    "normal" zone exists.
    """
    if alerta_dias >= deadline_dias:
        raise ValueError("alerta_dias debe ser estrictamente menor que deadline_dias")
    if today is None:
        today = date.today()
    elapsed = dias_habiles_transcurridos(fecha_creacion, today)
    remaining = deadline_dias - elapsed
    if remaining <= 0:
        return "vencido"
    if remaining <= alerta_dias:
        return "alerta"
    return "normal"


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
    def validar_fecha_certificado(cls, fecha_certificado: date, fecha_referencia: date) -> bool:
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
