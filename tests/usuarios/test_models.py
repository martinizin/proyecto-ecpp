"""Tests for the Usuario model."""

import pytest
from django.db import IntegrityError

from apps.usuarios.infrastructure.models import Usuario
from tests.factories import DocenteFactory, EstudianteFactory, InspectorFactory


pytestmark = pytest.mark.django_db


class TestUsuarioCreation:
    """Test creating users with each role."""

    def test_create_estudiante(self, estudiante):
        """A student user should have rol='estudiante'."""
        assert estudiante.rol == Usuario.Rol.ESTUDIANTE
        assert estudiante.username == "estudiante_test"
        assert str(estudiante) == "Juan Perez (estudiante)"

    def test_create_docente(self, docente):
        """A teacher user should have rol='docente'."""
        assert docente.rol == Usuario.Rol.DOCENTE
        assert docente.username == "docente_test"
        assert str(docente) == "Maria Garcia (docente)"

    def test_create_inspector(self, inspector):
        """An inspector user should have rol='inspector'."""
        assert inspector.rol == Usuario.Rol.INSPECTOR
        assert inspector.username == "inspector_test"
        assert str(inspector) == "Carlos Lopez (inspector)"


class TestUsuarioFactory:
    """Test factory-boy factories for Usuario."""

    def test_estudiante_factory(self):
        user = EstudianteFactory()
        assert user.pk is not None
        assert user.rol == Usuario.Rol.ESTUDIANTE
        assert user.check_password("testpass123")

    def test_docente_factory(self):
        user = DocenteFactory()
        assert user.pk is not None
        assert user.rol == Usuario.Rol.DOCENTE

    def test_inspector_factory(self):
        user = InspectorFactory()
        assert user.pk is not None
        assert user.rol == Usuario.Rol.INSPECTOR


class TestUsuarioConstraints:
    """Test model constraints and edge cases."""

    def test_cedula_unique(self, estudiante):
        """Two users cannot share the same cedula."""
        with pytest.raises(IntegrityError):
            Usuario.objects.create_user(
                username="duplicate_cedula",
                password="testpass123",
                rol=Usuario.Rol.ESTUDIANTE,
                cedula=estudiante.cedula,
            )

    def test_cedula_blank_allowed(self):
        """Cedula can be left blank."""
        user = Usuario.objects.create_user(
            username="no_cedula",
            password="testpass123",
            rol=Usuario.Rol.ESTUDIANTE,
        )
        assert user.cedula is None

    def test_telefono_blank_allowed(self):
        """Telefono can be left blank."""
        user = Usuario.objects.create_user(
            username="no_phone",
            password="testpass123",
            rol=Usuario.Rol.ESTUDIANTE,
        )
        assert user.telefono == ""

    def test_rol_choices_valid(self):
        """Only valid rol choices should be accepted at the model level."""
        choices = [c[0] for c in Usuario.Rol.choices]
        assert "estudiante" in choices
        assert "docente" in choices
        assert "inspector" in choices
        assert len(choices) == 3
