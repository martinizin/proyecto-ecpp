"""Value objects for the Solicitudes bounded context.

This module exposes enums and small immutable types shared across the
domain, application, and infrastructure layers.

Django's :class:`~django.db.models.TextChoices` is imported here purely as
a typed enum helper — no ORM behavior leaks into the domain. Using it
guarantees the same enum class can be referenced directly by
``CharField(choices=...)`` without an indirection.
"""

from django.db import models


class TipoCertificado(models.TextChoices):
    """Discriminator for ``CertificadoJustificacion``.

    Lives in the domain layer so application services, forms, and the
    validation service can reference ``TipoCertificado.MEDICO`` without
    importing from ``infrastructure``.
    """

    MEDICO = "medico", "Certificado Médico"
    LABORAL = "laboral", "Certificado Laboral"
    CALAMIDAD = "calamidad", "Calamidad Doméstica"
