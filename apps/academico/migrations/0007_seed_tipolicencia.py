"""
Data migration: seed 3 TipoLicencia rows (C, E, EC).
Ref: AC-CAT-01, NFR-CAT-03, AD4.
"""

from django.db import migrations


def seed_tipos_licencia(apps, schema_editor):
    TipoLicencia = apps.get_model("academico", "TipoLicencia")

    tipos = [
        {
            "nombre": "Licencia tipo C",
            "codigo": "C",
            "duracion_meses": 6,
            "num_asignaturas": 13,
            "activo": True,
        },
        {
            "nombre": "Licencia tipo E",
            "codigo": "E",
            "duracion_meses": 5,
            "num_asignaturas": 17,
            "activo": True,
        },
        {
            "nombre": "Licencia tipo EC",
            "codigo": "EC",
            "duracion_meses": 5,  # Convalidada: sin duración propia definida por stakeholders
            "num_asignaturas": 8,
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
