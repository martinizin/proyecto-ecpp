"""
Forms for the Solicitudes bounded context.

HU20 — JustificacionCertificadoForm: categorized certificate justification
with multi-file uploads and per-tipo conditional validation.
"""

from django import forms

from apps.solicitudes.domain.services import CertificadoValidationService
from apps.solicitudes.domain.value_objects import TipoCertificado


# --------------------------------------------------------------------------- #
# Multi-file field (Django 5.x — there is no built-in MultipleFileField)
# --------------------------------------------------------------------------- #


class _MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """FileField that accepts a list of files.

    ``clean()`` returns a Python ``list[UploadedFile]`` so the view can
    forward it directly to the application service.
    """

    widget = _MultipleFileInput

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", _MultipleFileInput(attrs={"multiple": True}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single = super().clean
        if isinstance(data, (list, tuple)):
            return [single(d, initial) for d in data]
        if data in (None, "", forms.fields.Field.empty_values):
            return []
        return [single(data, initial)]


# --------------------------------------------------------------------------- #
# JustificacionCertificadoForm
# --------------------------------------------------------------------------- #

# Fields per tipo — single source of truth: domain CertificadoValidationService.
# We re-use the SAME map so form-level required validation and AppService-level
# validation stay in sync.
_CAMPOS_POR_TIPO = CertificadoValidationService.CAMPOS_OBLIGATORIOS

# Union of all per-tipo fields (used for cleaning + datos_certificado())
_TODOS_LOS_CAMPOS_CERT = sorted({c for campos in _CAMPOS_POR_TIPO.values() for c in campos})


class JustificacionCertificadoForm(forms.Form):
    """Form for HU20 absence justification with categorized certificate.

    Fields are declared in three groups:

    1. Always-required: ``tipo_certificado``, ``archivos``.
    2. Optional metadata: ``motivo`` is a free-text field accepted blank.
    3. Per-tipo metadata: every per-tipo field is declared as ``required=False``
       at the field level — the conditional ``clean()`` enforces the
       per-tipo required set defined in
       :attr:`CertificadoValidationService.CAMPOS_OBLIGATORIOS`.

    The :meth:`datos_certificado` helper returns ONLY the fields that belong
    to the selected tipo, ready to pass to the application service.
    """

    tipo_certificado = forms.ChoiceField(
        choices=[("", "Seleccione...")] + list(TipoCertificado.choices),
        required=True,
    )
    motivo = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Opcional"}),
        required=False,
        max_length=2000,
    )
    archivos = MultipleFileField(required=True)

    # ── medico
    fecha_certificado = forms.DateField(required=False)
    dias_reposo = forms.IntegerField(min_value=1, required=False)
    # ── laboral
    cargo = forms.CharField(max_length=200, required=False)
    # ── calamidad
    descripcion_evento = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)
    relacion_familiar = forms.CharField(max_length=100, required=False)

    # ------------------------------------------------------------------ #
    # archivos validation (count / total size / extension)
    # ------------------------------------------------------------------ #
    def clean_archivos(self):
        archivos = self.cleaned_data.get("archivos") or []
        if not archivos:
            raise forms.ValidationError("Debe adjuntar al menos un archivo.")

        # 1) per-file: extension only (peso ya NO se valida por archivo).
        for f in archivos:
            errores = CertificadoValidationService.validar_archivo(f.name, f.size)
            if "extension_invalida" in errores:
                raise forms.ValidationError(
                    f"Archivo {f.name}: extensión no permitida. Solo PDF, JPG, JPEG o PNG."
                )

        # 2) batch: max files AND max total size (post-QA aggregated rule).
        lote = [(f.name, f.size) for f in archivos]
        errores_lote = CertificadoValidationService.validar_archivos(lote)
        if "max_archivos_excedido" in errores_lote:
            raise forms.ValidationError(
                f"Máximo {CertificadoValidationService.MAX_ARCHIVOS} archivos permitidos "
                f"(seleccionaste {len(archivos)})."
            )
        if "tamanio_total_excedido" in errores_lote:
            total_bytes = sum(f.size for f in archivos)
            total_mb = total_bytes / (1024 * 1024)
            max_mb = CertificadoValidationService.MAX_TAMANIO_TOTAL / (1024 * 1024)
            raise forms.ValidationError(
                f"El peso total de los archivos ({total_mb:.2f} MB) supera el "
                f"límite de {max_mb:.0f} MB. Quitá algunos archivos."
            )
        return archivos

    # ------------------------------------------------------------------ #
    # per-tipo required fields
    # ------------------------------------------------------------------ #
    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get("tipo_certificado")
        if not tipo or tipo not in _CAMPOS_POR_TIPO:
            return cleaned

        requeridos = _CAMPOS_POR_TIPO[tipo]
        for campo in requeridos:
            valor = cleaned.get(campo)
            falta = valor is None or (isinstance(valor, str) and not valor.strip())
            if falta:
                self.add_error(campo, "Este campo es obligatorio para el tipo seleccionado.")
        return cleaned

    # ------------------------------------------------------------------ #
    # datos_certificado: payload for JustificacionCertificadoAppService
    # ------------------------------------------------------------------ #
    def datos_certificado(self) -> dict:
        """Return only the fields that belong to the selected ``tipo_certificado``.

        Must only be called on a clean (validated) form. The returned dict is
        the exact payload expected by
        :meth:`JustificacionCertificadoAppService.crear_justificacion_con_certificado`.
        """
        tipo = self.cleaned_data.get("tipo_certificado")
        requeridos = _CAMPOS_POR_TIPO.get(tipo, [])
        return {campo: self.cleaned_data.get(campo) for campo in requeridos}
