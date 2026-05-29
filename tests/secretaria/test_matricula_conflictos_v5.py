"""
Integration tests for V5 (conflictos de horario) — Matrícula (secretaría).

Cubre los 2 entry points de Matricula (design §4 filas 5-6):
  - GestionMatriculasService.crear_matricula  / MatriculaCreateView  — Task 2.7
  - GestionMatriculasService.matricular_en_lote / MatriculaLoteView   — Task 2.8 (collect-all)

Reglas R2.1 (overlap conflict), R2.2 (RETIRADA ignored), R5.1 (SUSPENDIDA ignored).
"""

from __future__ import annotations

import datetime
from datetime import time

import pytest
from django.test import Client
from django.urls import reverse

from apps.academico.domain.exceptions import ConflictoHorarioEstudianteError
from apps.academico.infrastructure.models import (
    Asignatura,
    AsignaturaLicencia,
    BloqueHorario,
    Matricula,
    Paralelo,
    Periodo,
    TipoLicencia,
)
from apps.secretaria.services import GestionMatriculasService
from apps.usuarios.infrastructure.models import Usuario


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tl(codigo: str = "C") -> TipoLicencia:
    tl, _ = TipoLicencia.objects.get_or_create(
        codigo=codigo,
        defaults={
            "nombre": f"Licencia {codigo}",
            "duracion_meses": 6,
            "num_asignaturas": 10,
            "activo": True,
        },
    )
    return tl


def _make_periodo(tl: TipoLicencia, nombre: str = "Periodo V5 Mat") -> Periodo:
    return Periodo.objects.create(
        nombre=nombre,
        tipo_licencia=tl,
        fecha_inicio=datetime.date(2026, 1, 1),
        fecha_fin=datetime.date(2026, 6, 30),
        activo=True,
    )


def _make_docente(suffix: str) -> Usuario:
    return Usuario.objects.create_user(
        username=f"docente_mat_{suffix}",
        email=f"docente_mat_{suffix}@test.com",
        password="x",
        rol="docente",
    )


def _make_estudiante(suffix: str) -> Usuario:
    return Usuario.objects.create_user(
        username=f"est_mat_{suffix}",
        email=f"est_mat_{suffix}@test.com",
        password="x",
        rol="estudiante",
        cedula=f"170{suffix[-7:].rjust(7, '0')[:7]}",
    )


def _make_secretaria(suffix: str) -> Usuario:
    return Usuario.objects.create_user(
        username=f"secret_mat_{suffix}",
        email=f"secret_mat_{suffix}@test.com",
        password="x",
        rol="secretaria",
        cedula=f"180{suffix[-7:].rjust(7, '0')[:7]}",
    )


def _make_asig(codigo: str, tl: TipoLicencia) -> Asignatura:
    a = Asignatura.objects.create(nombre=f"Asig {codigo}", codigo=codigo)
    AsignaturaLicencia.objects.create(asignatura=a, tipo_licencia=tl, horas_lectivas=20)
    return a


def _make_paralelo_con_bloque(
    *,
    docente: Usuario,
    periodo: Periodo,
    tl: TipoLicencia,
    asignatura: Asignatura,
    nombre: str,
    dia: str,
    hi: time,
    hf: time,
) -> Paralelo:
    p = Paralelo.objects.create(
        asignatura=asignatura,
        periodo=periodo,
        tipo_licencia=tl,
        docente=docente,
        nombre=nombre,
        capacidad_maxima=30,
    )
    BloqueHorario.objects.create(paralelo=p, dia_semana=dia, hora_inicio=hi, hora_fin=hf)
    return p


# ---------------------------------------------------------------------------
# Task 2.7 — crear_matricula (service-level)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCrearMatriculaConflictoEstudiante:
    def test_crear_matricula_con_conflicto_levanta_excepcion_typed(self):
        """R2.1: estudiante con ACTIVA en P1 (mar 14-16). Crear en P2 (mar 15-17)
        en el mismo periodo debe levantar ConflictoHorarioEstudianteError."""
        tl = _make_tl()
        periodo = _make_periodo(tl)
        docente = _make_docente("crear_conf")
        estudiante = _make_estudiante("crear_conf")
        secretaria = _make_secretaria("crear_conf")
        a1 = _make_asig("MV5-A", tl)
        a2 = _make_asig("MV5-B", tl)

        p1 = _make_paralelo_con_bloque(
            docente=docente,
            periodo=periodo,
            tl=tl,
            asignatura=a1,
            nombre="A",
            dia="martes",
            hi=time(14, 0),
            hf=time(16, 0),
        )
        Matricula.objects.create(
            estudiante=estudiante,
            paralelo=p1,
            estado=Matricula.Estado.ACTIVA,
            matriculado_por=secretaria,
        )

        p2 = _make_paralelo_con_bloque(
            docente=docente,
            periodo=periodo,
            tl=tl,
            asignatura=a2,
            nombre="B",
            dia="martes",
            hi=time(15, 0),
            hf=time(17, 0),
        )

        service = GestionMatriculasService()
        with pytest.raises(ConflictoHorarioEstudianteError) as exc_info:
            service.crear_matricula(
                estudiante_id=estudiante.pk,
                paralelo_id=p2.pk,
                registrado_por_id=secretaria.pk,
            )

        assert len(exc_info.value.conflictos) == 1
        c = exc_info.value.conflictos[0]
        assert c.asignatura_codigo == "MV5-A"
        assert c.dia_semana == "martes"
        # No se creó matrícula en P2
        assert not Matricula.objects.filter(estudiante=estudiante, paralelo=p2).exists()

    def test_crear_matricula_con_retirada_no_es_conflicto_R2_2(self):
        """R2.2: matrícula RETIRADA en otro paralelo solapante NO bloquea."""
        tl = _make_tl()
        periodo = _make_periodo(tl)
        docente = _make_docente("crear_ret")
        estudiante = _make_estudiante("crear_ret")
        secretaria = _make_secretaria("crear_ret")
        a1 = _make_asig("MV5R-A", tl)
        a2 = _make_asig("MV5R-B", tl)

        p1 = _make_paralelo_con_bloque(
            docente=docente,
            periodo=periodo,
            tl=tl,
            asignatura=a1,
            nombre="A",
            dia="martes",
            hi=time(14, 0),
            hf=time(16, 0),
        )
        Matricula.objects.create(
            estudiante=estudiante,
            paralelo=p1,
            estado=Matricula.Estado.RETIRADA,
            matriculado_por=secretaria,
        )

        p2 = _make_paralelo_con_bloque(
            docente=docente,
            periodo=periodo,
            tl=tl,
            asignatura=a2,
            nombre="B",
            dia="martes",
            hi=time(15, 0),
            hf=time(17, 0),
        )

        service = GestionMatriculasService()
        m = service.crear_matricula(
            estudiante_id=estudiante.pk,
            paralelo_id=p2.pk,
            registrado_por_id=secretaria.pk,
        )
        assert m.pk is not None
        assert m.estado == Matricula.Estado.ACTIVA

    def test_crear_matricula_con_suspendida_no_es_conflicto_R5_1(self):
        """R5.1: SUSPENDIDA se trata como RETIRADA — filtro estado=ACTIVA la excluye."""
        tl = _make_tl()
        periodo = _make_periodo(tl)
        docente = _make_docente("crear_susp")
        estudiante = _make_estudiante("crear_susp")
        secretaria = _make_secretaria("crear_susp")
        a1 = _make_asig("MV5S-A", tl)
        a2 = _make_asig("MV5S-B", tl)

        p1 = _make_paralelo_con_bloque(
            docente=docente,
            periodo=periodo,
            tl=tl,
            asignatura=a1,
            nombre="A",
            dia="miercoles",
            hi=time(10, 0),
            hf=time(12, 0),
        )
        Matricula.objects.create(
            estudiante=estudiante,
            paralelo=p1,
            estado=Matricula.Estado.SUSPENDIDA,
            matriculado_por=secretaria,
        )

        p2 = _make_paralelo_con_bloque(
            docente=docente,
            periodo=periodo,
            tl=tl,
            asignatura=a2,
            nombre="B",
            dia="miercoles",
            hi=time(11, 0),
            hf=time(13, 0),
        )

        service = GestionMatriculasService()
        m = service.crear_matricula(
            estudiante_id=estudiante.pk,
            paralelo_id=p2.pk,
            registrado_por_id=secretaria.pk,
        )
        assert m.pk is not None


# ---------------------------------------------------------------------------
# Task 2.7 — MatriculaCreateView (Web layer, conflictos_horario en contexto)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMatriculaCreateViewConflictoEstudiante:
    def test_view_con_conflicto_rerenderiza_con_conflictos_horario(self):
        tl = _make_tl()
        periodo = _make_periodo(tl)
        docente = _make_docente("view_conf")
        estudiante = _make_estudiante("view_conf")
        secretaria = _make_secretaria("view_conf")
        a1 = _make_asig("MV5V-A", tl)
        a2 = _make_asig("MV5V-B", tl)

        p1 = _make_paralelo_con_bloque(
            docente=docente,
            periodo=periodo,
            tl=tl,
            asignatura=a1,
            nombre="A",
            dia="jueves",
            hi=time(8, 0),
            hf=time(10, 0),
        )
        Matricula.objects.create(
            estudiante=estudiante,
            paralelo=p1,
            estado=Matricula.Estado.ACTIVA,
            matriculado_por=secretaria,
        )
        p2 = _make_paralelo_con_bloque(
            docente=docente,
            periodo=periodo,
            tl=tl,
            asignatura=a2,
            nombre="B",
            dia="jueves",
            hi=time(9, 0),
            hf=time(11, 0),
        )

        client = Client()
        client.force_login(secretaria)
        response = client.post(
            reverse("secretaria:matricula_create"),
            data={
                "estudiante": estudiante.pk,
                "paralelo": p2.pk,
                "periodo": periodo.pk,
            },
        )

        assert response.status_code == 200
        ctx_conf = response.context.get("conflictos_horario")
        assert ctx_conf is not None
        assert len(ctx_conf) == 1
        assert ctx_conf[0].asignatura_codigo == "MV5V-A"
        # No matricula creada
        assert not Matricula.objects.filter(estudiante=estudiante, paralelo=p2).exists()


# ---------------------------------------------------------------------------
# Task 2.8 — matricular_en_lote: collect-all
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMatricularEnLoteCollectAll:
    def test_lote_con_paralelo_conflictivo_omite_y_continua(self):
        """3 paralelos: P1 (lun 08-10) creado, P2 (lun 09-11) omitido por conflicto
        con P1 recién creado en el mismo batch, P3 (lun 11-12) creado (back-to-back OK)."""
        tl = _make_tl()
        periodo = _make_periodo(tl)
        docente = _make_docente("lote_conf")
        estudiante = _make_estudiante("lote_conf")
        secretaria = _make_secretaria("lote_conf")

        a1 = _make_asig("MV5L-A", tl)
        a2 = _make_asig("MV5L-B", tl)
        a3 = _make_asig("MV5L-C", tl)

        p1 = _make_paralelo_con_bloque(
            docente=docente,
            periodo=periodo,
            tl=tl,
            asignatura=a1,
            nombre="A",
            dia="lunes",
            hi=time(8, 0),
            hf=time(10, 0),
        )
        p2 = _make_paralelo_con_bloque(
            docente=docente,
            periodo=periodo,
            tl=tl,
            asignatura=a2,
            nombre="B",
            dia="lunes",
            hi=time(9, 0),
            hf=time(11, 0),
        )
        p3 = _make_paralelo_con_bloque(
            docente=docente,
            periodo=periodo,
            tl=tl,
            asignatura=a3,
            nombre="C",
            dia="lunes",
            hi=time(11, 0),
            hf=time(12, 0),
        )

        service = GestionMatriculasService()
        creados, omitidos = service.matricular_en_lote(
            estudiante_id=estudiante.pk,
            paralelo_ids=[p1.pk, p2.pk, p3.pk],
            registrado_por_id=secretaria.pk,
        )

        # P1 + P3 creados; P2 omitido
        assert creados == 2
        assert Matricula.objects.filter(estudiante=estudiante, paralelo=p1).exists()
        assert not Matricula.objects.filter(estudiante=estudiante, paralelo=p2).exists()
        assert Matricula.objects.filter(estudiante=estudiante, paralelo=p3).exists()
        # Mensaje en omitidos para P2
        assert any("MV5L-B" in o.lower() or "MV5L-B" in o for o in omitidos)
