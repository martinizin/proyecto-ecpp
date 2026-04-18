"""Forms for the Secretaría module."""

from django import forms

from apps.usuarios.infrastructure.models import Usuario


class CrearUsuarioForm(forms.Form):
    """Form for creating a new user."""

    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "correo@ejemplo.com"}
        ),
    )
    first_name = forms.CharField(
        max_length=150,
        label="Nombres",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Nombres"}
        ),
    )
    last_name = forms.CharField(
        max_length=150,
        label="Apellidos",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Apellidos"}
        ),
    )
    rol = forms.ChoiceField(
        choices=Usuario.Rol.choices,
        label="Tipo de usuario",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    cedula = forms.CharField(
        max_length=13,
        label="Cédula",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "1234567890"}
        ),
    )
    telefono = forms.CharField(
        max_length=15,
        required=False,
        label="Teléfono",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "0991234567"}
        ),
    )

    def clean_email(self):
        email = self.cleaned_data["email"]
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError(
                "Ya existe un usuario con este correo electrónico."
            )
        return email

    def clean_cedula(self):
        cedula = self.cleaned_data["cedula"]
        if cedula and Usuario.objects.filter(cedula=cedula).exists():
            raise forms.ValidationError("Ya existe un usuario con esta cédula.")
        return cedula


class EditarUsuarioForm(forms.Form):
    """Form for editing an existing user."""

    first_name = forms.CharField(
        max_length=150,
        label="Nombres",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        max_length=150,
        label="Apellidos",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    rol = forms.ChoiceField(
        choices=Usuario.Rol.choices,
        label="Tipo de usuario",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    telefono = forms.CharField(
        max_length=15,
        required=False,
        label="Teléfono",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    direccion = forms.CharField(
        required=False,
        label="Dirección",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )


class CrearMatriculaForm(forms.Form):
    """Form for creating a new enrollment."""

    estudiante = forms.IntegerField(
        widget=forms.Select(attrs={"class": "form-select"})
    )
    paralelo = forms.IntegerField(
        widget=forms.Select(attrs={"class": "form-select"})
    )
