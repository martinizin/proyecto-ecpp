"""
Shared pytest fixtures for ECPPP test suite.
"""

import datetime

import pytest
from django.test import Client

from apps.academico.infrastructure.models import Periodo
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
        cedula="0909876542",
    )


@pytest.fixture
def active_periodo(db):
    """Create an active academic period."""
    return Periodo.objects.create(
        nombre="2026-A",
        fecha_inicio=datetime.date(2026, 3, 1),
        fecha_fin=datetime.date(2026, 7, 31),
        activo=True,
    )


@pytest.fixture
def inspector_client(inspector):
    """Return a Django test Client logged in as inspector."""
    client = Client()
    client.force_login(inspector)
    return client


@pytest.fixture
def docente_client(docente):
    """Return a Django test Client logged in as docente."""
    client = Client()
    client.force_login(docente)
    return client


@pytest.fixture
def estudiante_client(estudiante):
    """Return a Django test Client logged in as estudiante."""
    client = Client()
    client.force_login(estudiante)
    return client
