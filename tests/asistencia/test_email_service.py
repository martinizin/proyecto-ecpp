"""
Tests for attendance email notification service.
"""

from unittest.mock import patch

import pytest
from django.core import mail

from datetime import date

from apps.asistencia.infrastructure.email_service import (
    notificar_alertas_inasistencia,
    notificar_estudiantes_ausencia,
    notificar_estudiantes_riesgo_rojo,
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
        html_content = email.alternatives[0][0] if email.alternatives else ""
        assert "Juan Pérez" in email.body or "Juan Pérez" in html_content
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


@pytest.mark.django_db
class TestNotificarEstudiantesAusencia:
    """Tests for in-app absence notifications sent to students."""

    def test_creates_in_app_notification_per_student(self):
        est1 = EstudianteFactory()
        est2 = EstudianteFactory()
        paralelo = ParaleloFactory()

        notificar_estudiantes_ausencia([est1.pk, est2.pk], paralelo, date(2026, 5, 30))

        notifs = Notificacion.objects.filter(tipo="ausencia_registrada")
        assert notifs.count() == 2
        assert set(notifs.values_list("destinatario_id", flat=True)) == {est1.pk, est2.pk}
        assert notifs.first().url == "/asistencia/mi-asistencia/"
        assert "30/05/2026" in notifs.first().mensaje

    def test_does_not_send_email(self):
        est = EstudianteFactory()
        paralelo = ParaleloFactory()

        notificar_estudiantes_ausencia([est.pk], paralelo, date(2026, 5, 30))

        # By design: per-absence is in-app ONLY (no email spam)
        assert len(mail.outbox) == 0

    def test_empty_list_is_noop(self):
        paralelo = ParaleloFactory()
        notificar_estudiantes_ausencia([], paralelo, date(2026, 5, 30))
        assert Notificacion.objects.count() == 0
        assert len(mail.outbox) == 0


@pytest.mark.django_db
class TestNotificarEstudiantesRiesgoRojo:
    """Tests for red-risk email notifications to students."""

    def test_sends_email_to_each_student_in_alertas(self):
        est = EstudianteFactory(email="estudiante@test.com")
        paralelo = ParaleloFactory()

        alertas = [{"estudiante_id": est.pk, "porcentaje_inasistencia": 12.0}]
        notificar_estudiantes_riesgo_rojo(alertas, paralelo)

        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert email.to == ["estudiante@test.com"]
        assert "crítico" in email.subject.lower() or "critico" in email.subject.lower()

    def test_skips_students_without_email(self):
        est = EstudianteFactory(email="")
        paralelo = ParaleloFactory()

        alertas = [{"estudiante_id": est.pk, "porcentaje_inasistencia": 11.0}]
        notificar_estudiantes_riesgo_rojo(alertas, paralelo)
        assert len(mail.outbox) == 0

    def test_empty_alertas_is_noop(self):
        paralelo = ParaleloFactory()
        notificar_estudiantes_riesgo_rojo([], paralelo)
        assert len(mail.outbox) == 0
