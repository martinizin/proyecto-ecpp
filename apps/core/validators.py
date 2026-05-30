import re

from django.core.exceptions import ValidationError
from django.utils.html import strip_tags


# === Name validator ===
def validate_nombre(value):
    """Only letters, accented chars (áéíóúñüÁÉÍÓÚÑÜ), spaces, hyphens. Min 2 chars."""
    value = value.strip()
    if len(value) < 2:
        raise ValidationError("Este campo debe tener al menos 2 caracteres.")
    if not re.match(r"^[a-zA-ZáéíóúñüÁÉÍÓÚÑÜ\s\-]+$", value):
        raise ValidationError("Este campo solo debe contener letras, espacios y guiones.")
    return value


# === Ecuadorian cédula validator ===
def validate_cedula_ecuatoriana(value):
    """Validates Ecuadorian cédula: exactly 10 digits + modulo 10 algorithm."""
    value = value.strip()
    if not value:
        return value  # Allow empty if field is not required

    if not re.match(r"^\d{10}$", value):
        raise ValidationError("La cédula debe contener exactamente 10 dígitos numéricos.")

    # Province code validation (01-24 or 30)
    provincia = int(value[:2])
    if provincia < 1 or (provincia > 24 and provincia != 30):
        raise ValidationError("La cédula tiene un código de provincia inválido.")

    # Third digit must be 0-5 for natural persons
    tercer_digito = int(value[2])
    if tercer_digito > 5:
        raise ValidationError("La cédula tiene un formato inválido.")

    # Modulo 10 algorithm
    coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    suma = 0
    for i in range(9):
        producto = int(value[i]) * coeficientes[i]
        if producto >= 10:
            producto -= 9
        suma += producto

    verificador = (10 - (suma % 10)) % 10
    if verificador != int(value[9]):
        raise ValidationError("La cédula ingresada no es válida (dígito verificador incorrecto).")

    return value


# === Phone validator ===
def validate_telefono(value):
    """
    Validates phone numbers: exactly 10 digits, no letters or special characters.
    Empty value is allowed when the field is not required.
    """
    value = value.strip()
    if not value:
        return value
    if not re.match(r"^\d{10}$", value):
        raise ValidationError(
            "El teléfono debe contener exactamente 10 dígitos numéricos."
        )
    return value


# === Code validator (for asignatura codes etc.) ===
def validate_codigo(value):
    """Alphanumeric + hyphens only, uppercase enforced."""
    value = value.strip().upper()
    if not re.match(r"^[A-Z0-9\-]+$", value):
        raise ValidationError("El código solo debe contener letras, números y guiones.")
    if len(value) < 2:
        raise ValidationError("El código debe tener al menos 2 caracteres.")
    return value


# === Text sanitizer (XSS protection) ===
def sanitize_text(value):
    """Strip HTML tags from text input."""
    if not value:
        return value
    cleaned = strip_tags(value)
    if cleaned != value:
        return cleaned
    return value
