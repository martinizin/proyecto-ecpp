"""Adapter helpers to translate domain exceptions into framework ValidationErrors."""
from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers as drf_serializers


def to_django(exc: Exception) -> DjangoValidationError:
    """Translate a domain exception to a Django form ValidationError."""
    return DjangoValidationError(str(exc))


def to_drf(exc: Exception, field: str | None = None) -> drf_serializers.ValidationError:
    """Translate a domain exception to a DRF ValidationError.

    When ``field`` is provided, errors are routed as ``{field: [msg]}``
    so they land under ``serializer.errors[field]`` (not non_field_errors).
    """
    message = str(exc)
    if field is None:
        return drf_serializers.ValidationError(message)
    return drf_serializers.ValidationError({field: [message]})
