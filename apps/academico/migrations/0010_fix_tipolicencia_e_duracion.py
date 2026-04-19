"""
Data migration: fix all TipoLicencia data to match confirmed stakeholder specs.

- Licencia C: 6 meses, 13 asignaturas
- Licencia E: 5 meses, 17 asignaturas
- Licencia EC: 5 meses, 8 asignaturas
"""

from django.db import migrations


DATOS_CORRECTOS = {
    "C": {"nombre": "Licencia tip C", "duracion_meses": 6, "num_asignaturas": 13},
    "E": {"nombre": "Licencia tip E", "duracion_meses": 5, "num_asignaturas": 17},
    "EC": {"nombre": "Licencia tip EC", "duracion_meses": 5, "num_asignaturas": 8},
}


def fix_tipos_licencia(apps, schema_editor):
    TipoLicencia = apps.get_model("academico", "TipoLicencia")
    for codigo, datos in DATOS_CORRECTOS.items():
        TipoLicencia.objects.filter(codigo=codigo).update(**datos)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("academico", "0009_remove_paralelo_estudiantes_matricula"),
    ]

    operations = [
        migrations.RunPython(fix_tipos_licencia, noop),
    ]
