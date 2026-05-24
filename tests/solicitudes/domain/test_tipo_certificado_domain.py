"""Test that TipoCertificado lives in the domain layer (W2 from verify report)."""

from apps.solicitudes.domain.value_objects import TipoCertificado
from apps.solicitudes.infrastructure.models import CertificadoJustificacion


class TestTipoCertificadoEnDominio:
    def test_tipo_certificado_es_text_choices(self):
        from django.db import models

        assert issubclass(TipoCertificado, models.TextChoices)

    def test_tipo_certificado_tiene_los_tres_valores(self):
        valores = {choice.value for choice in TipoCertificado}
        assert valores == {"medico", "laboral", "calamidad"}

    def test_model_usa_el_enum_de_dominio(self):
        """Infrastructure model must reuse the domain enum, not redefine it."""
        # Same class identity (not a separate inner TextChoices)
        assert CertificadoJustificacion.TipoCertificado is TipoCertificado
