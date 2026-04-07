"""
Forms for the Academico bounded context.
Period, subject, and parallel CRUD forms.
"""

from django import forms
from django.contrib.auth import get_user_model

from apps.academico.infrastructure.models import Asignatura, Paralelo, Periodo, TipoLicencia

Usuario = get_user_model()


class PeriodoForm(forms.ModelForm):
    """Form for creating/editing academic periods."""

    class Meta:
        model = Periodo
        fields = ["nombre", "fecha_inicio", "fecha_fin"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Periodo 2026-A"}),
            "fecha_inicio": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "fecha_fin": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get("fecha_inicio")
        fecha_fin = cleaned_data.get("fecha_fin")
        if fecha_inicio and fecha_fin and fecha_inicio >= fecha_fin:
            raise forms.ValidationError(
                "La fecha de inicio debe ser anterior a la fecha de fin."
            )
        return cleaned_data


class AsignaturaForm(forms.ModelForm):
    """Form for creating/editing subjects with license type association."""

    tipos_licencia = forms.ModelMultipleChoiceField(
        queryset=TipoLicencia.objects.filter(activo=True),
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        label="Tipos de licencia",
        error_messages={"required": "Debe seleccionar al menos un tipo de licencia."},
    )

    class Meta:
        model = Asignatura
        fields = ["nombre", "codigo", "descripcion", "horas_lectivas", "tipos_licencia"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre de la asignatura"}),
            "codigo": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: LEG-001"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Descripción opcional"}),
            "horas_lectivas": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
        }

    def clean_horas_lectivas(self):
        horas = self.cleaned_data.get("horas_lectivas")
        if horas is not None and horas <= 0:
            raise forms.ValidationError("Las horas lectivas deben ser mayores a 0.")
        return horas


class ParaleloForm(forms.ModelForm):
    """Form for creating/editing parallels with teacher assignment."""

    docente = forms.ModelChoiceField(
        queryset=Usuario.objects.filter(rol="docente", is_active=True),
        label="Docente",
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label="Seleccione un docente",
    )
    periodo = forms.ModelChoiceField(
        queryset=Periodo.objects.filter(activo=True),
        label="Período",
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label="Seleccione un período",
    )
    tipo_licencia = forms.ModelChoiceField(
        queryset=TipoLicencia.objects.filter(activo=True),
        label="Tipo de licencia",
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label="Seleccione un tipo",
    )

    class Meta:
        model = Paralelo
        fields = [
            "periodo",
            "tipo_licencia",
            "asignatura",
            "nombre",
            "docente",
            "horario",
            "capacidad_maxima",
        ]
        widgets = {
            "asignatura": forms.Select(attrs={"class": "form-select"}),
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: A, B, GR1"}),
            "horario": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Horario del paralelo"}),
            "capacidad_maxima": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
        }
