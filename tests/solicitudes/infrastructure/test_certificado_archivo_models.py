"""Smoke tests for HU20 infrastructure models.

These tests intentionally stay lightweight: they prove the schema is wired
correctly (FKs, OneToOne, CheckConstraint, __str__). Business validation
lives in the domain layer and is covered there.
"""

import pytest
from django.db import IntegrityError, transaction

from apps.solicitudes.infrastructure.models import (
    ArchivoSolicitud,
    CertificadoJustificacion,
    Solicitud,
)
from tests.factories import SolicitudFactory


pytestmark = pytest.mark.django_db


def _make_solicitud_justificacion():
    return SolicitudFactory(tipo=Solicitud.TipoSolicitud.JUSTIFICACION)


class TestCertificadoJustificacion:
    def test_can_be_created_with_solicitud(self):
        solicitud = _make_solicitud_justificacion()
        cert = CertificadoJustificacion.objects.create(
            solicitud=solicitud,
            tipo=CertificadoJustificacion.TipoCertificado.MEDICO,
            institucion_emisora="MSP",
            fecha_certificado="2026-05-20",
            numero_documento="MSP-123",
            nombre_medico="Dr. House",
            dias_reposo=3,
        )
        assert cert.pk is not None
        assert cert.solicitud_id == solicitud.id
        assert solicitud.certificado == cert  # related_name

    def test_one_to_one_uniqueness(self):
        solicitud = _make_solicitud_justificacion()
        CertificadoJustificacion.objects.create(
            solicitud=solicitud,
            tipo=CertificadoJustificacion.TipoCertificado.LABORAL,
            fecha_certificado="2026-05-20",
            institucion_emisora="ACME",
            cargo="Auditor",
        )
        with pytest.raises(IntegrityError), transaction.atomic():
            CertificadoJustificacion.objects.create(
                solicitud=solicitud,
                tipo=CertificadoJustificacion.TipoCertificado.LABORAL,
                fecha_certificado="2026-05-20",
                institucion_emisora="ACME-2",
                cargo="Otro",
            )

    def test_str(self):
        solicitud = _make_solicitud_justificacion()
        cert = CertificadoJustificacion.objects.create(
            solicitud=solicitud,
            tipo=CertificadoJustificacion.TipoCertificado.CALAMIDAD,
            fecha_certificado="2026-05-20",
            descripcion_evento="Fallecimiento",
            relacion_familiar="tio",
        )
        text = str(cert)
        assert "Calamidad" in text or "calamidad" in text.lower()

    def test_tipo_choices(self):
        choices = {c[0] for c in CertificadoJustificacion.TipoCertificado.choices}
        assert choices == {"medico", "laboral", "calamidad"}


class TestArchivoSolicitud:
    def test_can_be_created(self):
        solicitud = _make_solicitud_justificacion()
        archivo = ArchivoSolicitud.objects.create(
            solicitud=solicitud,
            archivo="solicitudes/2026/05/x.pdf",
            nombre_original="x.pdf",
            tipo_mime="application/pdf",
            tamanio_bytes=1024,
        )
        assert archivo.pk is not None
        assert archivo in solicitud.archivos.all()

    def test_str_is_nombre_original(self):
        solicitud = _make_solicitud_justificacion()
        archivo = ArchivoSolicitud.objects.create(
            solicitud=solicitud,
            archivo="solicitudes/2026/05/foto.jpg",
            nombre_original="foto.jpg",
            tipo_mime="image/jpeg",
            tamanio_bytes=2048,
        )
        assert str(archivo) == "foto.jpg"

    def test_check_constraint_blocks_oversize(self):
        solicitud = _make_solicitud_justificacion()
        with pytest.raises(IntegrityError), transaction.atomic():
            ArchivoSolicitud.objects.create(
                solicitud=solicitud,
                archivo="solicitudes/2026/05/big.pdf",
                nombre_original="big.pdf",
                tipo_mime="application/pdf",
                tamanio_bytes=5 * 1024 * 1024 + 1,
            )

    def test_check_constraint_allows_exact_5mb(self):
        solicitud = _make_solicitud_justificacion()
        archivo = ArchivoSolicitud.objects.create(
            solicitud=solicitud,
            archivo="solicitudes/2026/05/edge.pdf",
            nombre_original="edge.pdf",
            tipo_mime="application/pdf",
            tamanio_bytes=5 * 1024 * 1024,
        )
        assert archivo.pk is not None

    def test_multiple_archivos_per_solicitud(self):
        solicitud = _make_solicitud_justificacion()
        for i in range(3):
            ArchivoSolicitud.objects.create(
                solicitud=solicitud,
                archivo=f"solicitudes/2026/05/a{i}.pdf",
                nombre_original=f"a{i}.pdf",
                tipo_mime="application/pdf",
                tamanio_bytes=100,
            )
        assert solicitud.archivos.count() == 3
