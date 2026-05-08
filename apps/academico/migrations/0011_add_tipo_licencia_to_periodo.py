"""
Migration: add tipo_licencia FK to Periodo, remove unique on nombre,
add unique_together (nombre, tipo_licencia).

Strategy for existing data:
1. Add tipo_licencia as nullable FK
2. Data migration: assign first TipoLicencia to existing periods
3. Make tipo_licencia non-nullable
4. Remove old unique constraint on nombre
5. Add new unique_together
"""

from django.db import migrations, models
import django.db.models.deletion


def assign_default_tipo_licencia(apps, schema_editor):
    """Assign the first active TipoLicencia to existing periods."""
    Periodo = apps.get_model("academico", "Periodo")
    TipoLicencia = apps.get_model("academico", "TipoLicencia")

    default_tipo = TipoLicencia.objects.filter(activo=True).first()
    if default_tipo:
        Periodo.objects.filter(tipo_licencia__isnull=True).update(tipo_licencia=default_tipo)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("academico", "0010_fix_tipolicencia_e_duracion"),
    ]

    operations = [
        # Step 1: Add nullable FK
        migrations.AddField(
            model_name="periodo",
            name="tipo_licencia",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="periodos",
                to="academico.tipolicencia",
            ),
        ),
        # Step 2: Assign default to existing rows
        migrations.RunPython(assign_default_tipo_licencia, noop),
        # Step 3: Make non-nullable
        migrations.AlterField(
            model_name="periodo",
            name="tipo_licencia",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="periodos",
                to="academico.tipolicencia",
            ),
        ),
        # Step 4: Remove old unique on nombre
        migrations.AlterField(
            model_name="periodo",
            name="nombre",
            field=models.CharField(max_length=100),
        ),
        # Step 5: Add unique_together
        migrations.AlterUniqueTogether(
            name="periodo",
            unique_together={("nombre", "tipo_licencia")},
        ),
    ]
