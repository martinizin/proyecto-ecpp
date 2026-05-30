"""
Integration tests for V5 — ParaleloSerializer (DRF) gate behind `initial_data`.

Task 2.9 + locked decision 2:
  - Si `bloques` está en `self.initial_data` → parsear, llamar al servicio,
    levantar via `to_drf(e, field='bloques')` cuando hay conflicto.
  - Si `bloques` NO está → silent skip (no validation).
  - No agrega un nuevo writable field (compatibilidad con clientes V1-V4).

Shape payload esperado en conflicto:
  serializer.errors == {'bloques': {'detail': '...', 'conflictos': [...]}}
"""

from __future__ import annotations

import datetime
from datetime import time

import pytest

from apps.academico.infrastructure.models import (
    Asignatura,
    AsignaturaLicencia,
    BloqueHorario,
    Paralelo,
    Periodo,
    TipoLicencia,
)
from apps.usuarios.infrastructure.models import Usuario


def _make_tl():
    tl, _ = TipoLicencia.objects.get_or_create(
        codigo="C",
        defaults={
            "nombre": "Licencia C",
            "duracion_meses": 6,
            "num_asignaturas": 10,
            "activo": True,
        },
    )
    return tl


def _make_periodo(tl):
    return Periodo.objects.create(
        nombre="Periodo V5 DRF",
        tipo_licencia=tl,
        fecha_inicio=datetime.date(2026, 1, 1),
        fecha_fin=datetime.date(2026, 6, 30),
        activo=True,
    )


def _make_docente(suffix: str):
    return Usuario.objects.create_user(
        username=f"docente_drf_{suffix}",
        email=f"docente_drf_{suffix}@test.com",
        password="x",
        rol="docente",
    )


def _make_asignatura(codigo: str, tl):
    a = Asignatura.objects.create(nombre=f"Asig {codigo}", codigo=codigo)
    AsignaturaLicencia.objects.create(asignatura=a, tipo_licencia=tl, horas_lectivas=20)
    return a


@pytest.mark.django_db
class TestParaleloSerializerBloquesGate:
    """Gate: validate corre solo cuando bloques está presente en initial_data."""

    def test_serializer_sin_bloques_no_corre_check_y_es_valido(self):
        """Sin `bloques` en data → silent skip; serializer valida normalmente."""
        from apps.academico.presentation.serializers import ParaleloSerializer

        tl = _make_tl()
        periodo = _make_periodo(tl)
        docente = _make_docente("nobloques")
        asig_pre = _make_asignatura("V5D-PRE", tl)
        asig_nueva = _make_asignatura("V5D-NEW", tl)

        # Estado previo: docente ocupado lunes 08-10 (NO debería disparar nada).
        pre = Paralelo.objects.create(
            asignatura=asig_pre,
            periodo=periodo,
            tipo_licencia=tl,
            docente=docente,
            nombre="A",
            capacidad_maxima=30,
        )
        BloqueHorario.objects.create(
            paralelo=pre,
            dia_semana="lunes",
            hora_inicio=time(8, 0),
            hora_fin=time(10, 0),
        )

        serializer = ParaleloSerializer(
            data={
                "periodo": periodo.pk,
                "tipo_licencia": tl.pk,
                "asignatura": asig_nueva.pk,
                "nombre": "B",
                "docente": docente.pk,
                "capacidad_maxima": 30,
            }
        )
        assert serializer.is_valid() is True, serializer.errors

    def test_serializer_con_bloques_conflictivos_devuelve_payload_estructurado(self):
        """Con `bloques` y conflicto: errors['bloques'] = {detail, conflictos}."""
        from apps.academico.presentation.serializers import ParaleloSerializer

        tl = _make_tl()
        periodo = _make_periodo(tl)
        docente = _make_docente("conf")
        asig_pre = _make_asignatura("V5D-EX", tl)
        asig_nueva = _make_asignatura("V5D-NEW2", tl)

        pre = Paralelo.objects.create(
            asignatura=asig_pre,
            periodo=periodo,
            tipo_licencia=tl,
            docente=docente,
            nombre="A",
            capacidad_maxima=30,
        )
        BloqueHorario.objects.create(
            paralelo=pre,
            dia_semana="lunes",
            hora_inicio=time(8, 0),
            hora_fin=time(10, 0),
        )

        serializer = ParaleloSerializer(
            data={
                "periodo": periodo.pk,
                "tipo_licencia": tl.pk,
                "asignatura": asig_nueva.pk,
                "nombre": "B",
                "docente": docente.pk,
                "capacidad_maxima": 30,
                "bloques": [
                    {"dia": "lunes", "inicio": "09:00", "fin": "11:00"},
                ],
            }
        )
        assert serializer.is_valid() is False
        errors = serializer.errors
        assert "bloques" in errors
        node = errors["bloques"]
        # to_drf emite {field: {"detail": str, "conflictos": [...]}}
        assert "detail" in node
        assert "conflictos" in node
        assert isinstance(node["conflictos"], list) and len(node["conflictos"]) == 1
        c = node["conflictos"][0]
        assert c["asignatura_codigo"] == "V5D-EX"
        assert c["dia_semana"] == "lunes"
        assert c["hora_inicio"] == "08:00:00"
        assert c["hora_fin"] == "10:00:00"
