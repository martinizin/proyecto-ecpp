import pytest
from django.test import Client


@pytest.mark.django_db
def test_health_returns_200_when_healthy():
    response = Client().get("/health/")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db"] is True
    assert data["cache"] is True


def test_health_returns_503_when_database_down(monkeypatch):
    from apps.core import health

    class BrokenConnection:
        def cursor(self):
            raise RuntimeError("database unreachable")

    monkeypatch.setattr(health, "connection", BrokenConnection())

    response = Client().get("/health/")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "error"
    assert data["db"] is False
