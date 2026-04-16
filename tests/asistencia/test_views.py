"""Tests for Asistencia views (HU08)."""

import datetime

import pytest
from django.urls import reverse

from apps.asistencia.infrastructure.models import Asistencia
from tests.factories import (
    AsistenciaFactory,
    DocenteFactory,
    EstudianteFactory,
    InspectorFactory,
    MatriculaFactory,
    ParaleloFactory,
)

pytestmark = pytest.mark.django_db


def _saved(user):
    """Persist password hash so force_login session survives request cycle."""
    user.save()
    return user


class TestSeleccionarParaleloView:
    """Tests for SeleccionarParaleloView."""

    def setup_method(self):
        self.url = reverse("asistencia:seleccionar_paralelo")

    def test_anonymous_redirect(self, client):
        """Unauthenticated user is redirected to login."""
        response = client.get(self.url)
        assert response.status_code == 302
        assert "/login/" in response.url

    def test_estudiante_forbidden(self, client):
        """Student user gets 403."""
        estudiante = _saved(EstudianteFactory())
        client.force_login(estudiante)
        response = client.get(self.url)
        assert response.status_code == 403

    def test_docente_sees_own_paralelos(self, client):
        """Docente sees only their paralelos."""
        docente = _saved(DocenteFactory())
        paralelo = ParaleloFactory(docente=docente)
        ParaleloFactory()  # another docente's paralelo

        client.force_login(docente)
        response = client.get(self.url)
        assert response.status_code == 200
        assert paralelo in response.context["paralelos"]
        assert len(response.context["paralelos"]) == 1

    def test_inspector_sees_all_paralelos(self, client):
        """Inspector sees all active paralelos."""
        inspector = _saved(InspectorFactory())
        p1 = ParaleloFactory()
        p2 = ParaleloFactory()

        client.force_login(inspector)
        response = client.get(self.url)
        assert response.status_code == 200
        paralelo_ids = [p.pk for p in response.context["paralelos"]]
        assert p1.pk in paralelo_ids
        assert p2.pk in paralelo_ids


class TestRegistrarAsistenciaView:
    """Tests for RegistrarAsistenciaView."""

    def setup_method(self):
        self.docente = _saved(DocenteFactory())
        self.paralelo = ParaleloFactory(docente=self.docente)
        self.matriculas = [
            MatriculaFactory(paralelo=self.paralelo) for _ in range(3)
        ]
        self.url = reverse(
            "asistencia:registrar_asistencia",
            kwargs={"paralelo_id": self.paralelo.pk},
        )

    def test_get_shows_enrolled_students(self, client):
        """GET shows the form with enrolled students."""
        client.force_login(self.docente)
        response = client.get(self.url)
        assert response.status_code == 200
        assert len(response.context["matriculas"]) == 3

    def test_docente_cannot_access_other_paralelo(self, client):
        """Docente A cannot access paralelo of docente B."""
        otro_docente = _saved(DocenteFactory())
        otro_paralelo = ParaleloFactory(docente=otro_docente)
        url = reverse(
            "asistencia:registrar_asistencia",
            kwargs={"paralelo_id": otro_paralelo.pk},
        )

        client.force_login(self.docente)
        response = client.get(url)
        assert response.status_code == 302  # redirect with error

    def test_post_registers_attendance(self, client):
        """POST with presentes list creates records and redirects."""
        client.force_login(self.docente)
        presentes = [
            str(self.matriculas[0].estudiante_id),
            str(self.matriculas[1].estudiante_id),
        ]
        response = client.post(
            self.url,
            {"fecha": "2026-05-10", "presentes": presentes},
        )
        assert response.status_code == 302
        assert Asistencia.objects.filter(
            paralelo=self.paralelo,
            fecha=datetime.date(2026, 5, 10),
        ).count() == 3

    def test_post_invalid_fecha(self, client):
        """POST with bad date redirects with error."""
        client.force_login(self.docente)
        response = client.post(self.url, {"fecha": "not-a-date"})
        assert response.status_code == 302


class TestHistorialAsistenciaView:
    """Tests for HistorialAsistenciaView."""

    def setup_method(self):
        self.docente = _saved(DocenteFactory())
        self.paralelo = ParaleloFactory(docente=self.docente)
        self.url = reverse(
            "asistencia:historial_asistencia",
            kwargs={"paralelo_id": self.paralelo.pk},
        )

    def test_historial_shows_dates(self, client):
        """GET shows attendance history grouped by date."""
        AsistenciaFactory(
            paralelo=self.paralelo, fecha=datetime.date(2026, 5, 1)
        )
        AsistenciaFactory(
            paralelo=self.paralelo, fecha=datetime.date(2026, 5, 3)
        )

        client.force_login(self.docente)
        response = client.get(self.url)
        assert response.status_code == 200
        assert len(response.context["historial"]) == 2

    def test_docente_cannot_access_other_historial(self, client):
        """Docente cannot access another docente's historial."""
        otro_docente = _saved(DocenteFactory())
        otro_paralelo = ParaleloFactory(docente=otro_docente)
        url = reverse(
            "asistencia:historial_asistencia",
            kwargs={"paralelo_id": otro_paralelo.pk},
        )

        client.force_login(self.docente)
        response = client.get(url)
        assert response.status_code == 302
