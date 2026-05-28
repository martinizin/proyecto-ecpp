"""Adapter helpers to translate domain exceptions into framework ValidationErrors.

`to_django` stays pure (string-only). `to_drf` enriches the payload with a
serialized `conflictos` list when the domain exception exposes one (HU21 V5,
see design §6.2 de qa-academico-conflictos-horario-v5).
"""

from __future__ import annotations

from dataclasses import asdict

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers as drf_serializers


def _serialize_conflictos(exc: Exception) -> list[dict] | None:
    """Serializa `exc.conflictos` (lista de `Conflicto`) a JSON-safe dicts.

    Convierte `time` -> isoformat ("HH:MM:SS") porque `dataclasses.asdict`
    no normaliza tipos no-JSON. Devuelve `None` si la excepción no expone
    `.conflictos` (la mayoría de excepciones de dominio V1-V4).
    """
    conflictos = getattr(exc, "conflictos", None)
    if conflictos is None:
        return None
    out: list[dict] = []
    for c in conflictos:
        d = asdict(c)
        d["hora_inicio"] = c.hora_inicio.isoformat()
        d["hora_fin"] = c.hora_fin.isoformat()
        out.append(d)
    return out


def to_django(exc: Exception) -> DjangoValidationError:
    """Translate a domain exception to a Django form ValidationError.

    Permanece puro: solo el mensaje viaja en el ValidationError. Los
    `conflictos` estructurados se leen directamente desde `exc.conflictos`
    en la vista y se inyectan al contexto del render (design §5.2 + §6.2).
    """
    return DjangoValidationError(str(exc))


def to_drf(exc: Exception, field: str | None = None) -> drf_serializers.ValidationError:
    """Translate a domain exception to a DRF ValidationError.

    Payload shape:
    - sin `field`: ``{"detail": str(exc)[, "conflictos": [...]]}``
    - con `field`: ``{field: {"detail": str(exc)[, "conflictos": [...]]}}``

    La clave ``conflictos`` se agrega solo cuando `exc.conflictos` existe.
    """
    message = str(exc)
    conflictos = _serialize_conflictos(exc)
    if conflictos is None:
        # Sin conflictos preservamos el contrato V1-V4 (DRF coerce a ErrorDetail).
        payload: dict = {"detail": message}
        if field is None:
            return drf_serializers.ValidationError(payload)
        return drf_serializers.ValidationError({field: payload})

    # Con conflictos: necesitamos preservar tipos nativos (ints, strings de
    # isoformat) dentro de la lista para que los clientes JSON consuman el
    # payload sin reparsear ErrorDetail. DRF envuelve recursivamente todos
    # los valores en `ValidationError(...)`, así que construimos un
    # ValidationError "vacío" y luego asignamos `.detail` directamente.
    payload = {"detail": message, "conflictos": conflictos}
    if field is not None:
        payload = {field: payload}
    err = drf_serializers.ValidationError(message)
    err.detail = payload
    return err
