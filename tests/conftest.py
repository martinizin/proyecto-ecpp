"""
Shared pytest fixtures for ECPPP test suite.
"""

import pytest

from apps.usuarios.infrastructure.models import Usuario


@pytest.fixture
def estudiante(db):
    """Create a test student user."""
    return Usuario.objects.create_user(
        username="estudiante_test",
        password="testpass123",
        first_name="Juan",
        last_name="Perez",
        email="estudiante@test.com",
        rol=Usuario.Rol.ESTUDIANTE,
        cedula="0901234567",
    )


@pytest.fixture
def docente(db):
    """Create a test teacher user."""
    return Usuario.objects.create_user(
        username="docente_test",
        password="testpass123",
        first_name="Maria",
        last_name="Garcia",
        email="docente@test.com",
        rol=Usuario.Rol.DOCENTE,
        cedula="0907654321",
    )


@pytest.fixture
def inspector(db):
    """Create a test inspector user."""
    return Usuario.objects.create_user(
        username="inspector_test",
        password="testpass123",
        first_name="Carlos",
        last_name="Lopez",
        email="inspector@test.com",
        rol=Usuario.Rol.INSPECTOR,
        cedula="0909876543",
    )
