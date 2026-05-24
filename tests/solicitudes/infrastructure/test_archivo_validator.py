"""W3 from verify report: ArchivoSolicitud.archivo must use FileExtensionValidator."""

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.solicitudes.infrastructure.models import ArchivoSolicitud


class TestArchivoSolicitudFileFieldValidator:
    def test_archivo_field_has_file_extension_validator(self):
        """Field-level defense in depth (W3): only pdf/jpg/jpeg/png allowed."""
        field = ArchivoSolicitud._meta.get_field("archivo")
        from django.core.validators import FileExtensionValidator

        ext_validators = [v for v in field.validators if isinstance(v, FileExtensionValidator)]
        assert len(ext_validators) == 1
        allowed = set(ext_validators[0].allowed_extensions)
        assert allowed == {"pdf", "jpg", "jpeg", "png"}

    def test_archivo_field_rejects_invalid_extension_at_validator_level(self):
        field = ArchivoSolicitud._meta.get_field("archivo")
        archivo = SimpleUploadedFile(
            "malicious.exe", b"x", content_type="application/octet-stream"
        )
        try:
            field.run_validators(archivo)
        except ValidationError:
            pass  # expected
        else:
            raise AssertionError("Expected ValidationError for .exe extension")

    def test_archivo_field_accepts_pdf(self):
        field = ArchivoSolicitud._meta.get_field("archivo")
        archivo = SimpleUploadedFile("doc.pdf", b"x", content_type="application/pdf")
        # Should NOT raise
        field.run_validators(archivo)
