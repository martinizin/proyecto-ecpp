"""
Forms for the Academico bounded context.
Period, subject, and parallel CRUD forms.
"""

from django import forms
from django.contrib.auth import get_user_model

from apps.academico.infrastructure.models import Asignatura, Paralelo, Periodo, TipoLicencia

Usuario = get_user_model()


class PeriodoForm(forms.ModelForm):
    """Form for creating/editing academic periods linked to a license type."""

    tipo_licencia = forms.ModelChoiceField(
        queryset=TipoLicencia.objects.filter(activo=True),
        label="Tipo de licencia",
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label="Seleccione un tipo de licencia",
    )

    class Meta:
        model = Periodo
        fields = ["nombre", "tipo_licencia", "fecha_inicio", "fecha_fin"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Periodo 2026-A"}),
            "fecha_inicio": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
            "fecha_fin": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
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
    """Form for creating/editing a single parallel with teacher assignment."""

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


class ParaleloLoteForm(forms.Form):
    """
    Batch creation form: creates multiple paralelos (one per selected asignatura)
    sharing the same periodo, tipo_licencia, nombre, docente, horario, and capacidad.

    Asignaturas are filtered by the selected tipo_licencia.
    """

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
        empty_label="Seleccione un tipo de licencia",
    )
    asignaturas = forms.ModelMultipleChoiceField(
        queryset=Asignatura.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        label="Asignaturas",
        error_messages={"required": "Debe seleccionar al menos una asignatura."},
    )
    nombre = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: A, B, GR1"}),
        label="Nombre del paralelo",
    )
    docente = forms.ModelChoiceField(
        queryset=Usuario.objects.filter(rol="docente", is_active=True),
        label="Docente",
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label="Seleccione un docente",
    )
    horario = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Horario del paralelo"}),
        label="Horario",
    )
    capacidad_maxima = forms.IntegerField(
        min_value=1,
        initial=30,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
        label="Capacidad máxima",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If tipo_licencia was submitted, filter asignaturas by it
        if self.data.get("tipo_licencia"):
            try:
                tipo_id = int(self.data["tipo_licencia"])
                self.fields["asignaturas"].queryset = Asignatura.objects.filter(
                    tipos_licencia__id=tipo_id
                ).distinct()
            except (ValueError, TypeError):
                pass

    def clean_asignaturas(self):
        asignaturas = self.cleaned_data.get("asignaturas")
        tipo_licencia = self.cleaned_data.get("tipo_licencia")
        if asignaturas and tipo_licencia:
            max_asignaturas = tipo_licencia.num_asignaturas
            if len(asignaturas) > max_asignaturas:
                raise forms.ValidationError(
                    f"La licencia {tipo_licencia.codigo} permite máximo "
                    f"{max_asignaturas} asignaturas. Seleccionó {len(asignaturas)}."
                )
        return asignaturas
