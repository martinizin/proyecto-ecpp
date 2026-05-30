"""
Pruebas unitarias para el helper de traducción de excepciones de dominio
hacia los ValidationError de Django y DRF (HU21 QA V1-V4).
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers as drf_serializers

from apps.academico.domain.exceptions import AcademicoError
from apps.academico.presentation.exception_mapping import to_django, to_drf


class TestToDjango:
    def test_to_django_returns_django_validation_error_with_message(self):
        exc = AcademicoError("Mensaje de dominio")

        result = to_django(exc)

        assert isinstance(result, DjangoValidationError)
        # Django ValidationError exposes .messages with the rendered strings.
        assert "Mensaje de dominio" in result.messages


class TestToDrf:
    def test_to_drf_without_field_returns_drf_validation_error_with_message(self):
        exc = AcademicoError("Error sin campo")

        result = to_drf(exc)

        assert isinstance(result, drf_serializers.ValidationError)
        # When no field is provided, the message lives in detail as a list.
        rendered = str(result.detail)
        assert "Error sin campo" in rendered

    def test_to_drf_with_field_returns_dict_payload(self):
        exc = AcademicoError("Error con campo")

        result = to_drf(exc, field="capacidad_maxima")

        assert isinstance(result, drf_serializers.ValidationError)
        detail = result.detail
        # Field-routed errors must land under the field key, not non_field_errors.
        assert "capacidad_maxima" in detail
        rendered = str(detail["capacidad_maxima"])
        assert "Error con campo" in rendered
