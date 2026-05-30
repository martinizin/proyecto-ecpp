"""
Tests for usuarios data + schema migrations introduced by SDD change
`qa-usuarios-registro-inmutable`.

Strategy: we test the migration **callbacks** directly (the functions passed to
`RunPython`) instead of orchestrating `MigrationExecutor`. Reasons:

- `django-test-migrations` / `pytest-django-migrations` are NOT in
  `requirements.txt`; we can't add deps without coordination.
- The callbacks are pure functions over the `apps` registry — perfect unit-test
  shape. Running them with the live `django.apps.apps` is semantically equal to
  running them through `RunPython` because both pass the same `Apps` instance
  to the callback (the historical state is irrelevant here: we only filter by
  `cedula__isnull=True` on the `Usuario` model, whose schema for `cedula` is
  unchanged in 0005 — only 0006 alters it).
- Importing migration files whose name starts with a digit requires
  `importlib.import_module` (the regular `import` statement is a syntax error).
"""

import importlib

import pytest
from django.apps import apps as django_apps

from apps.usuarios.infrastructure.models import Usuario

pytestmark = pytest.mark.django_db


# =============================================================================
# 0005_validate_no_null_cedulas — data migration that aborts on NULL cedulas
# =============================================================================


class TestMigration0005ValidateNoNullCedulas:
    """Acceptance:
    - Forward callback raises `RuntimeError` listing the offending emails when
      at least one `Usuario` row has `cedula IS NULL`.
    - Forward callback is silent when no NULL rows exist.
    - Reverse callback is a no-op (rollback must restore nullable cleanly via
      0006 reverse; this migration introduces no schema change).
    """

    MIGRATION_PATH = "apps.usuarios.migrations.0005_validate_no_null_cedulas"

    def _load(self):
        return importlib.import_module(self.MIGRATION_PATH)

    def test_forward_raises_runtime_error_listing_emails(self):
        """RED → GREEN: a single NULL row → RuntimeError mentions the email."""
        Usuario.objects.create(
            username="null_user",
            email="null@test.com",
            cedula=None,
            rol="estudiante",
            password="x",
        )
        try:
            module = self._load()
            with pytest.raises(RuntimeError, match="null@test.com"):
                module.raise_on_null_cedulas(django_apps, None)
        finally:
            Usuario.objects.filter(email="null@test.com").delete()

    def test_forward_silent_when_no_null_rows(self):
        """Triangulation: empty NULL set must NOT raise."""
        # Defensive: make sure no leftover NULL rows from other tests/fixtures.
        Usuario.objects.filter(cedula__isnull=True).delete()
        module = self._load()
        # Should complete without raising.
        module.raise_on_null_cedulas(django_apps, None)

    def test_reverse_is_noop(self):
        """Triangulation: rollback path must be safe (no-op)."""
        module = self._load()
        module.noop_reverse(django_apps, None)  # must not raise

    def test_error_lists_all_offending_emails(self):
        """Triangulation: multiple NULL rows → all emails appear in the message."""
        Usuario.objects.create(
            username="null_a", email="a@test.com", cedula=None,
            rol="estudiante", password="x",
        )
        Usuario.objects.create(
            username="null_b", email="b@test.com", cedula=None,
            rol="docente", password="x",
        )
        try:
            module = self._load()
            with pytest.raises(RuntimeError) as excinfo:
                module.raise_on_null_cedulas(django_apps, None)
            message = str(excinfo.value)
            assert "a@test.com" in message
            assert "b@test.com" in message
        finally:
            Usuario.objects.filter(email__in=["a@test.com", "b@test.com"]).delete()
