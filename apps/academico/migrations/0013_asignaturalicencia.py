"""
Migration 0013: Create AsignaturaLicencia through model and migrate data.

Step 1 of 2 for the AsignaturaLicencia refactor.
"""

from django.db import migrations, models
import django.db.models.deletion


def migrate_data_forward(apps, schema_editor):
    """Copy existing M2M + horas_lectivas into AsignaturaLicencia rows."""
    Asignatura = apps.get_model("academico", "Asignatura")
    AsignaturaLicencia = apps.get_model("academico", "AsignaturaLicencia")

    for asig in Asignatura.objects.all():
        for tl in asig.tipos_licencia.all():
            AsignaturaLicencia.objects.get_or_create(
                asignatura=asig,
                tipo_licencia=tl,
                defaults={"horas_lectivas": asig.horas_lectivas},
            )


class Migration(migrations.Migration):

    dependencies = [
        ("academico", "0012_remove_paralelo_horario_bloquehorario"),
    ]

    operations = [
        # 1. Create the through model
        migrations.CreateModel(
            name="AsignaturaLicencia",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("horas_lectivas", models.PositiveIntegerField(default=40)),
                (
                    "asignatura",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="asignatura_licencias",
                        to="academico.asignatura",
                    ),
                ),
                (
                    "tipo_licencia",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="asignatura_licencias",
                        to="academico.tipolicencia",
                    ),
                ),
            ],
            options={
                "verbose_name": "Asignatura por Licencia",
                "verbose_name_plural": "Asignaturas por Licencia",
                "ordering": ["tipo_licencia__codigo"],
                "unique_together": {("asignatura", "tipo_licencia")},
            },
        ),
        # 2. Migrate data from old M2M + horas_lectivas
        migrations.RunPython(migrate_data_forward, migrations.RunPython.noop),
    ]
