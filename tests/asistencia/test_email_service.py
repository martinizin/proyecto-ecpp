"""
Tests for attendance email notification service.
"""

from unittest.mock import patch

import pytest
from django.core import mail

from apps.asistencia.infrastructure.email_service import (
    notificar_alertas_inasistencia,
    send_alerta_inasistencia,
)
from apps.notificaciones.infrastructure.models import Notificacion
from tests.factories import EstudianteFactory, InspectorFactory, ParaleloFactory


@pytest.mark.django_db
class TestSendAlertaInasistencia:
    """Tests for the low-level send_alerta_inasistencia function."""

    def test_sends_email_with_correct_subject_and_body(self):
        send_alerta_inasistencia(
            inspector_email="inspector@test.com",
            estudiante_nombre="Juan Pérez",
            porcentaje=7.5,
            asignatura_nombre="Matemáticas",
            paralelo_nombre="A",
        )

        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert email.subject == "ECPP — Alerta de inasistencia"
        # HTML email: body is the plain-text fallback, check alternatives for HTML
        assert "Juan Pérez" in email.body or "Juan Pérez" in (email.alternatives[0][0] if email.alternatives else "")
        assert email.to == ["inspector@test.com"]


@pytest.mark.django_db
class TestNotificarAlertasInasistencia:
    """Tests for the high-level notificar_alertas_inasistencia function."""

    def test_sends_emails_to_all_inspectors(self):
        inspector1 = InspectorFactory()
        inspector2 = InspectorFactory()
        estudiante = EstudianteFactory()
        paralelo = ParaleloFactory()

        alertas = [
            {
                "estudiante_id": estudiante.pk,
                "porcentaje_inasistencia": 8.0,
                "paralelo": paralelo.nombre,
            }
        ]

        notificar_alertas_inasistencia(alertas, paralelo)

        # 1 alerta × 2 inspectors = 2 emails
        assert len(mail.outbox) == 2
        recipients = {mail.outbox[0].to[0], mail.outbox[1].to[0]}
        assert inspector1.email in recipients
        assert inspector2.email in recipients

    def test_no_inspectors_does_not_crash(self):
        estudiante = EstudianteFactory()
        paralelo = ParaleloFactory()

        alertas = [
            {
                "estudiante_id": estudiante.pk,
                "porcentaje_inasistencia": 6.0,
                "paralelo": paralelo.nombre,
            }
        ]

        # Should not raise
        notificar_alertas_inasistencia(alertas, paralelo)
        assert len(mail.outbox) == 0

    def test_email_failure_does_not_raise(self):
        InspectorFactory()
        estudiante = EstudianteFactory()
        paralelo = ParaleloFactory()

        alertas = [
            {
                "estudiante_id": estudiante.pk,
                "porcentaje_inasistencia": 10.0,
                "paralelo": paralelo.nombre,
            }
        ]

        with patch(
            "apps.asistencia.infrastructure.email_service.send_alerta_inasistencia",
            side_effect=Exception("SMTP down"),
        ):
            # Must not raise — try/except catches it
            notificar_alertas_inasistencia(alertas, paralelo)

    def test_empty_alertas_sends_no_emails(self):
        InspectorFactory()
        paralelo = ParaleloFactory()

        notificar_alertas_inasistencia([], paralelo)
        assert len(mail.outbox) == 0

    def test_creates_in_app_notifications_for_inspectors(self):
        inspector1 = InspectorFactory()
        inspector2 = InspectorFactory()
        estudiante = EstudianteFactory()
        paralelo = ParaleloFactory()

        alertas = [
            {
                "estudiante_id": estudiante.pk,
                "porcentaje_inasistencia": 8.0,
                "paralelo": paralelo.nombre,
            }
        ]

        notificar_alertas_inasistencia(alertas, paralelo)

        notifs = Notificacion.objects.filter(tipo="alerta_inasistencia")
        assert notifs.count() == 2
        destinatarios = set(notifs.values_list("destinatario_id", flat=True))
        assert destinatarios == {inspector1.pk, inspector2.pk}
        assert notifs.first().url == "/asistencia/supervision/"
