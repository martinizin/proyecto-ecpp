"""
Schema migration: flips `Usuario.cedula` from `NULL` to `NOT NULL` at the
database column level.

Behavior (per SDD `qa-usuarios-registro-inmutable` design D1 + D2):
- Forward: `AlterField` only — drops `null=True, blank=True`, keeps
  `max_length=13` (Option A, per orchestrator decision: shrinkage to 10 is a
  separate SDD change because the live DB has rows with stale lengths).
- Reverse: Django auto-generates the inverse (`null=True, blank=True`).
- Safety: depends on `0005_validate_no_null_cedulas`, which aborts the run if
  any row still has `cedula IS NULL`. Without that gate, Postgres would
  refuse the `ALTER COLUMN ... SET NOT NULL` on a column that already holds
  NULL values.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0005_validate_no_null_cedulas"),
    ]

    operations = [
        migrations.AlterField(
            model_name="usuario",
            name="cedula",
            field=models.CharField(max_length=13, unique=True),
        ),
    ]
