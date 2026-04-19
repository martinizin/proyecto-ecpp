"""
Data migration: fix Licencia tipo E duracion_meses from 9 to 5.

Corrects seed data based on confirmed stakeholder information.
"""

from django.db import migrations


def fix_duracion_e(apps, schema_editor):
    TipoLicencia = apps.get_model("academico", "TipoLicencia")
    TipoLicencia.objects.filter(codigo="E").update(duracion_meses=5)


def reverse_fix(apps, schema_editor):
    TipoLicencia = apps.get_model("academico", "TipoLicencia")
    TipoLicencia.objects.filter(codigo="E").update(duracion_meses=9)


class Migration(migrations.Migration):

    dependencies = [
        ("academico", "0009_remove_paralelo_estudiantes_matricula"),
    ]

    operations = [
        migrations.RunPython(fix_duracion_e, reverse_fix),
    ]
