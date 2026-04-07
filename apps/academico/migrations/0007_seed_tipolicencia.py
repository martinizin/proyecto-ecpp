"""
Data migration: seed 3 TipoLicencia rows (C, E, EC).
Ref: AC-CAT-01, NFR-CAT-03, AD4.

Note: duracion_meses for EC = 0 (placeholder pending stakeholder confirmation).
"""

from django.db import migrations


def seed_tipos_licencia(apps, schema_editor):
    TipoLicencia = apps.get_model("academico", "TipoLicencia")

    tipos = [
        {
            "nombre": "Conducción",
            "codigo": "C",
            "duracion_meses": 6,
            "num_asignaturas": 8,
            "activo": True,
        },
        {
            "nombre": "Educación",
            "codigo": "E",
            "duracion_meses": 12,
            "num_asignaturas": 15,
            "activo": True,
        },
        {
            "nombre": "Educación Convalidada",
            "codigo": "EC",
            "duracion_meses": 0,  # TODO: confirmar con stakeholders
            "num_asignaturas": 10,
            "activo": True,
        },
    ]

    for tipo in tipos:
        TipoLicencia.objects.get_or_create(
            codigo=tipo["codigo"],
            defaults=tipo,
        )


def reverse_seed(apps, schema_editor):
    TipoLicencia = apps.get_model("academico", "TipoLicencia")
    TipoLicencia.objects.filter(codigo__in=["C", "E", "EC"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("academico", "0006_tipolicencia_asignatura_horas_lectivas_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_tipos_licencia, reverse_seed),
    ]
