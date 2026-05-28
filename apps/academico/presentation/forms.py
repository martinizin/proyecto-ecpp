"""
Forms for the Academico bounded context.
Period, subject, and parallel CRUD forms.
"""

import datetime

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model

from apps.academico.domain.exceptions import AcademicoError
from apps.academico.domain.services import ParaleloService, PeriodoService
from apps.academico.infrastructure.models import Asignatura, Paralelo, Periodo, TipoLicencia
from apps.academico.presentation.exception_mapping import to_django
from apps.core.validators import sanitize_text, validate_codigo

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
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej: Periodo 2026-A",
                }
            ),
            "fecha_inicio": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "fecha_fin": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get("nombre", "")
        if nombre and len(nombre.strip()) < 3:
            raise forms.ValidationError("El nombre debe tener al menos 3 caracteres.")
        return nombre.strip()

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get("fecha_inicio")
        fecha_fin = cleaned_data.get("fecha_fin")
        if fecha_inicio and fecha_fin and fecha_inicio >= fecha_fin:
            raise forms.ValidationError("La fecha de inicio debe ser anterior a la fecha de fin.")
        min_date = datetime.date(2020, 1, 1)
        max_date = datetime.date(2040, 12, 31)
        for field_name, fecha in [("fecha_inicio", fecha_inicio), ("fecha_fin", fecha_fin)]:
            if fecha and (fecha < min_date or fecha > max_date):
                self.add_error(
                    field_name,
                    f"La fecha debe estar entre {min_date} y {max_date}.",
                )
        if fecha_inicio and fecha_fin and fecha_inicio < fecha_fin:
            try:
                PeriodoService().validar_duracion(
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                    minimo=settings.PERIODO_DURACION_MIN_MESES,
                    maximo=settings.PERIODO_DURACION_MAX_MESES,
                )
            except AcademicoError as e:
                self.add_error("fecha_fin", to_django(e))
        return cleaned_data


class AsignaturaForm(forms.ModelForm):
    """Form for creating/editing subjects (base fields only).

    License types and per-license hours are handled separately in the view
    via dynamic POST fields (tipo_licencia_{id} / horas_{id}).
    """

    class Meta:
        model = Asignatura
        fields = ["nombre", "codigo", "descripcion"]
        widgets = {
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nombre de la asignatura",
                }
            ),
            "codigo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej: LEG-001",
                }
            ),
            "descripcion": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Descripción opcional",
                }
            ),
        }

    def clean_codigo(self):
        value = self.cleaned_data.get("codigo", "")
        return validate_codigo(value)

    def clean_descripcion(self):
        value = self.cleaned_data.get("descripcion", "")
        return sanitize_text(value)


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
            "capacidad_maxima",
        ]
        widgets = {
            "asignatura": forms.Select(attrs={"class": "form-select"}),
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej: A, B, GR1",
                }
            ),
            "capacidad_maxima": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
        }

    def clean_capacidad_maxima(self):
        value = self.cleaned_data.get("capacidad_maxima")
        if value is None:
            return value
        try:
            ParaleloService().validar_capacidad(
                capacidad=value,
                maximo=settings.PARALELO_CAPACIDAD_MAXIMA,
            )
        except AcademicoError as e:
            raise to_django(e)
        return value


class ParaleloAsignaturaEditForm(forms.ModelForm):
    """Lightweight form to edit only docente of an existing paralelo."""

    docente = forms.ModelChoiceField(
        queryset=Usuario.objects.filter(rol="docente", is_active=True),
        label="Docente",
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label="Seleccione un docente",
    )

    class Meta:
        model = Paralelo
        fields = ["docente"]


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
    capacidad_maxima = forms.IntegerField(
        min_value=1,
        max_value=settings.PARALELO_CAPACIDAD_MAXIMA,
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
                    asignatura_licencias__tipo_licencia_id=tipo_id
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
