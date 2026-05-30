"""
Data migration: validates that no `Usuario` row has `cedula IS NULL` before
the schema migration (0006) flips the column to NOT NULL.

Behavior (per SDD `qa-usuarios-registro-inmutable` design D1 + D2):
- Forward: scan `Usuario` for `cedula__isnull=True`. If any row exists, raise
  `RuntimeError` listing the offending emails. We do NOT backfill placeholders
  — the secretaría must fix each row deliberately.
- Reverse: no-op (this migration introduces no schema change; rollback is safe).
"""

from django.db import migrations


def raise_on_null_cedulas(apps, schema_editor):
    """Abort the migration loudly if any user still has a NULL cédula."""
    Usuario = apps.get_model("usuarios", "Usuario")
    null_emails = list(
        Usuario.objects.filter(cedula__isnull=True)
        .order_by("email")
        .values_list("email", flat=True)
    )
    if null_emails:
        raise RuntimeError(
            "No se puede aplicar la migración 0006 (cedula NOT NULL): hay "
            f"{len(null_emails)} usuario(s) sin cédula. Asigne una cédula "
            "válida desde la administración antes de reintentar. "
            f"Usuarios afectados: {', '.join(null_emails)}"
        )


def noop_reverse(apps, schema_editor):
    """Rollback path is a no-op — this migration alters no schema."""
    return None


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0004_add_rol_secretaria"),
    ]

    operations = [
        migrations.RunPython(raise_on_null_cedulas, reverse_code=noop_reverse),
    ]
