"""
Migration 0014: Remove old M2M and horas_lectivas, add new M2M with through.

Step 2 of 2 for the AsignaturaLicencia refactor.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("academico", "0013_asignaturalicencia"),
    ]

    operations = [
        # 1. Remove old plain M2M field
        migrations.RemoveField(
            model_name="asignatura",
            name="tipos_licencia",
        ),
        # 2. Remove horas_lectivas from Asignatura
        migrations.RemoveField(
            model_name="asignatura",
            name="horas_lectivas",
        ),
        # 3. Add new M2M with through
        migrations.AddField(
            model_name="asignatura",
            name="tipos_licencia",
            field=models.ManyToManyField(
                blank=True,
                related_name="asignaturas",
                through="academico.AsignaturaLicencia",
                to="academico.tipolicencia",
            ),
        ),
    ]
