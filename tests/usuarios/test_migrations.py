"""
Tests for usuarios data + schema migrations introduced by SDD change
`qa-usuarios-registro-inmutable`.

Strategy: we test the migration **callbacks** directly (the functions passed to
`RunPython`) instead of orchestrating `MigrationExecutor`. Reasons:

- `django-test-migrations` / `pytest-django-migrations` are NOT in
  `requirements.txt`; we can't add deps without coordination.
- The callbacks are pure functions over an `apps` registry. In production
  Django passes the *historical* `apps` (built from the migration graph), not
  the live `django.apps.apps`. We mirror that: the 0005 tests stub `apps` with
  a tiny fake that returns synthetic email rows. This keeps the tests pure,
  fast, and decoupled from the current DB schema — which is critical because
  once 0006 lands, the live `Usuario` table rejects `cedula=NULL` at the column
  level, so we cannot create NULL rows in the test DB anymore.
- Importing migration files whose name starts with a digit requires
  `importlib.import_module` (the regular `import` statement is a syntax error).
"""

import importlib
from unittest.mock import MagicMock

import pytest
from django.db import IntegrityError, transaction

from apps.usuarios.infrastructure.models import Usuario

pytestmark = pytest.mark.django_db


def _fake_apps_with_null_emails(emails):
    """Build a stand-in for the historical `apps` registry whose
    `get_model("usuarios", "Usuario").objects.filter(cedula__isnull=True)
    .order_by("email").values_list("email", flat=True)` chain yields `emails`.
    """
    fake_apps = MagicMock(name="HistoricalApps")
    fake_model = MagicMock(name="HistoricalUsuario")
    (
        fake_model.objects.filter.return_value
        .order_by.return_value
        .values_list.return_value
    ) = list(emails)
    fake_apps.get_model.return_value = fake_model
    return fake_apps, fake_model


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
        fake_apps, fake_model = _fake_apps_with_null_emails(["null@test.com"])
        module = self._load()
        with pytest.raises(RuntimeError, match="null@test.com"):
            module.raise_on_null_cedulas(fake_apps, None)
        # The callback must query the historical model, not the live one.
        fake_apps.get_model.assert_called_once_with("usuarios", "Usuario")
        fake_model.objects.filter.assert_called_once_with(cedula__isnull=True)

    def test_forward_silent_when_no_null_rows(self):
        """Triangulation: empty NULL set must NOT raise."""
        fake_apps, _ = _fake_apps_with_null_emails([])
        module = self._load()
        # Should complete without raising.
        module.raise_on_null_cedulas(fake_apps, None)

    def test_reverse_is_noop(self):
        """Triangulation: rollback path must be safe (no-op)."""
        module = self._load()
        module.noop_reverse(None, None)  # must not raise

    def test_error_lists_all_offending_emails(self):
        """Triangulation: multiple NULL rows → all emails appear in the message."""
        fake_apps, _ = _fake_apps_with_null_emails(["a@test.com", "b@test.com"])
        module = self._load()
        with pytest.raises(RuntimeError) as excinfo:
            module.raise_on_null_cedulas(fake_apps, None)
        message = str(excinfo.value)
        assert "a@test.com" in message
        assert "b@test.com" in message
        assert "2 usuario(s)" in message


# =============================================================================
# 0006_cedula_not_null — schema migration that enforces NOT NULL at column level
# =============================================================================


class TestMigration0006CedulaNotNull:
    """Acceptance:
    - After migration 0006 is applied, the `cedula` column rejects NULL at the
      database layer (`IntegrityError`), regardless of model-level validation.
    - The `Usuario._meta` field declares `null=False, blank=False` so the
      Django state matches the database state (no `makemigrations` drift).
    - `max_length` is preserved at 13 (per orchestrator Option A — no schema
      shrinkage; domain `value_objects.Cedula` enforces the 10-digit rule).

    Strategy: we do NOT call `MigrationExecutor` here. The pytest-django test DB
    is built by applying ALL migrations from scratch (including 0006), so the
    schema under test is already the post-migration schema. We assert the
    constraint with a direct `Usuario.objects.create(cedula=None)` — Django's
    `.save()` issues a raw INSERT without pre-validating `null=False` (that
    check only fires in `full_clean()`), so the rejection comes from Postgres.
    """

    def test_cedula_column_rejects_null_at_db_level(self):
        """RED → GREEN: inserting NULL cedula must raise IntegrityError."""
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Usuario.objects.create(
                    username="not_null_violation",
                    email="not_null@test.com",
                    cedula=None,
                    rol="estudiante",
                    password="x",
                )

    def test_model_field_declares_not_null(self):
        """Triangulation: Django model state must match DB state (no drift)."""
        field = Usuario._meta.get_field("cedula")
        assert field.null is False, "cedula must declare null=False"
        assert field.blank is False, "cedula must declare blank=False"

    def test_max_length_preserved_at_13(self):
        """Triangulation: 0006 must NOT shrink max_length (Option A).

        Domain `value_objects.Cedula` enforces exactly 10 digits; the schema
        keeps 13 to avoid breaking existing rows with stale data (>10 chars).
        Any shrinkage belongs to a separate SDD change.
        """
        field = Usuario._meta.get_field("cedula")
        assert field.max_length == 13
