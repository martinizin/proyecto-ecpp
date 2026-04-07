"""
Forms for the Usuarios bounded context.
Registration, OTP verification, login forms.
"""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

Usuario = get_user_model()


class RegistroForm(forms.Form):
    """Registration form — creates inactive user pending OTP verification."""

    first_name = forms.CharField(
        max_length=150,
        label="Nombres",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombres"}),
    )
    last_name = forms.CharField(
        max_length=150,
        label="Apellidos",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Apellidos"}),
    )
    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "correo@ejemplo.com"}),
    )
    cedula = forms.CharField(
        max_length=10,
        required=False,
        label="Cédula",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "1234567890"}),
    )
    telefono = forms.CharField(
        max_length=15,
        required=False,
        label="Teléfono",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "0991234567"}),
    )
    rol = forms.ChoiceField(
        choices=Usuario.Rol.choices,
        label="Tipo de usuario",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Contraseña"}),
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Repetir contraseña"}),
    )

    def clean_email(self):
        email = self.cleaned_data["email"]
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return email

    def clean_cedula(self):
        cedula = self.cleaned_data.get("cedula", "")
        if cedula and Usuario.objects.filter(cedula=cedula).exists():
            raise forms.ValidationError("Esta cédula ya está registrada.")
        return cedula

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return password2

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        if password1:
            validate_password(password1)
        return cleaned_data


class VerificacionOTPForm(forms.Form):
    """OTP verification form — 6-digit code input."""

    codigo = forms.CharField(
        max_length=6,
        min_length=6,
        label="Código de verificación",
        widget=forms.TextInput(
            attrs={
                "class": "form-control text-center",
                "placeholder": "000000",
                "maxlength": "6",
                "autocomplete": "one-time-code",
                "inputmode": "numeric",
                "pattern": "[0-9]{6}",
            }
        ),
    )

    def clean_codigo(self):
        codigo = self.cleaned_data["codigo"]
        if not codigo.isdigit():
            raise forms.ValidationError("El código debe contener solo dígitos.")
        return codigo


class LoginForm(forms.Form):
    """Login form — email + password + tipo_usuario (role)."""

    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "correo@ejemplo.com"}),
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Contraseña"}),
    )
    tipo_usuario = forms.ChoiceField(
        choices=Usuario.Rol.choices,
        label="Tipo de usuario",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
