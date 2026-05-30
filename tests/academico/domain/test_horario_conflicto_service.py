"""
Pruebas unitarias para `HorarioConflictoService` (HU21 QA V5).

RED phase (Task 1.1 SDD qa-academico-conflictos-horario-v5):
- `Conflicto` DTO aún no existe en `apps.academico.domain.services`.
- `HorarioConflictoService` aún no existe.
- `ConflictoHorarioDocenteError` / `ConflictoHorarioEstudianteError` aún no existen.

Por lo tanto este archivo DEBE FALLAR en collection/import — comportamiento
esperado en RED estricta. Una vez que las tareas 1.3, 1.4, 1.5 y 1.6 implementen
las clases, los tests pasarán a fase GREEN.

Cobertura per design §7 (R1-R5) + §7 boundary cases (B1-B6) + §8 + §3.3:
- TestOverlapBoundaries: B1-B6 (matriz half-open).
- TestDetectarConflictoDocente: R1.1 a R1.4 + empty input.
- TestDetectarConflictoEstudiante: R2.1, R2.2, R5.1 + edit-excluir.
- TestConflictoExceptionsExposeConflictos: contrato §2.4 (Task 1.1).
- TestQueryBudget: `assertNumQueries(2)` para docente y estudiante (Task 1.2, design §3.3).
"""

from datetime import time

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.academico.domain.exceptions import (
    ConflictoHorarioDocenteError,
    ConflictoHorarioEstudianteError,
)
from apps.academico.domain.services import Conflicto, HorarioConflictoService
from apps.academico.infrastructure.models import Matricula
from tests.factories import (
    AsignaturaFactory,
    BloqueHorarioFactory,
    DocenteFactory,
    EstudianteFactory,
    MatriculaFactory,
    ParaleloFactory,
    PeriodoFactory,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bloque_tuple(dia: str, hi: tuple[int, int], hf: tuple[int, int]):
    """Build a (dia, hora_inicio, hora_fin) tuple as expected by the service."""
    return (dia, time(*hi), time(*hf))


# ---------------------------------------------------------------------------
# B1-B6: Overlap matrix (boundary cases per design §7)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestOverlapBoundaries:
    """Matriz half-open: `hi1 < hf2 AND hi2 < hf1` (design §2.3)."""

    def test_b1_identical_blocks_produces_conflict(self):
        """B1: bloques idénticos (mismo día, mismo rango) → conflicto."""
        periodo = PeriodoFactory()
        docente = DocenteFactory()
        paralelo_existente = ParaleloFactory(docente=docente, periodo=periodo)
        BloqueHorarioFactory(
            paralelo=paralelo_existente,
            dia_semana="lunes",
            hora_inicio=time(8, 0),
            hora_fin=time(10, 0),
        )
        service = HorarioConflictoService()

        propuestos = [_bloque_tuple("lunes", (8, 0), (10, 0))]
        conflictos = service.detectar_conflicto_docente(
            docente_id=docente.pk,
            periodo_id=periodo.pk,
            bloques_propuestos=propuestos,
        )

        assert len(conflictos) == 1
        assert conflictos[0].paralelo_id == paralelo_existente.pk
        assert conflictos[0].dia_semana == "lunes"
        assert conflictos[0].hora_inicio == time(8, 0)
        assert conflictos[0].hora_fin == time(10, 0)

    def test_b2_contained_inside_big_block_produces_conflict(self):
        """B2: bloque pequeño dentro de grande (09:00-09:30 dentro 08:00-10:00) → conflicto."""
        periodo = PeriodoFactory()
        docente = DocenteFactory()
        paralelo = ParaleloFactory(docente=docente, periodo=periodo)
        BloqueHorarioFactory(
            paralelo=paralelo,
            dia_semana="lunes",
            hora_inicio=time(8, 0),
            hora_fin=time(10, 0),
        )
        service = HorarioConflictoService()

        propuestos = [_bloque_tuple("lunes", (9, 0), (9, 30))]
        conflictos = service.detectar_conflicto_docente(
            docente_id=docente.pk,
            periodo_id=periodo.pk,
            bloques_propuestos=propuestos,
        )

        assert len(conflictos) == 1

    def test_b3_container_big_around_small_produces_conflict(self):
        """B3: bloque grande contiene al existente (07:00-11:00 abarca 08:00-10:00) → conflicto."""
        periodo = PeriodoFactory()
        docente = DocenteFactory()
        paralelo = ParaleloFactory(docente=docente, periodo=periodo)
        BloqueHorarioFactory(
            paralelo=paralelo,
            dia_semana="lunes",
            hora_inicio=time(8, 0),
            hora_fin=time(10, 0),
        )
        service = HorarioConflictoService()

        propuestos = [_bloque_tuple("lunes", (7, 0), (11, 0))]
        conflictos = service.detectar_conflicto_docente(
            docente_id=docente.pk,
            periodo_id=periodo.pk,
            bloques_propuestos=propuestos,
        )

        assert len(conflictos) == 1

    def test_b4_partial_overlap_left_produces_conflict(self):
        """B4: solapamiento parcial por izquierda (07:00-09:00 vs 08:00-10:00) → conflicto."""
        periodo = PeriodoFactory()
        docente = DocenteFactory()
        paralelo = ParaleloFactory(docente=docente, periodo=periodo)
        BloqueHorarioFactory(
            paralelo=paralelo,
            dia_semana="lunes",
            hora_inicio=time(8, 0),
            hora_fin=time(10, 0),
        )
        service = HorarioConflictoService()

        propuestos = [_bloque_tuple("lunes", (7, 0), (9, 0))]
        conflictos = service.detectar_conflicto_docente(
            docente_id=docente.pk,
            periodo_id=periodo.pk,
            bloques_propuestos=propuestos,
        )

        assert len(conflictos) == 1

    def test_b5_partial_overlap_right_produces_conflict(self):
        """B5: solapamiento parcial por derecha (09:00-11:00 vs 08:00-10:00) → conflicto."""
        periodo = PeriodoFactory()
        docente = DocenteFactory()
        paralelo = ParaleloFactory(docente=docente, periodo=periodo)
        BloqueHorarioFactory(
            paralelo=paralelo,
            dia_semana="lunes",
            hora_inicio=time(8, 0),
            hora_fin=time(10, 0),
        )
        service = HorarioConflictoService()

        propuestos = [_bloque_tuple("lunes", (9, 0), (11, 0))]
        conflictos = service.detectar_conflicto_docente(
            docente_id=docente.pk,
            periodo_id=periodo.pk,
            bloques_propuestos=propuestos,
        )

        assert len(conflictos) == 1

    def test_b6_back_to_back_no_conflict_half_open(self):
        """B6: back-to-back (10:00 fin vs 10:00 inicio) → NO conflicto (half-open `<`)."""
        periodo = PeriodoFactory()
        docente = DocenteFactory()
        paralelo = ParaleloFactory(docente=docente, periodo=periodo)
        BloqueHorarioFactory(
            paralelo=paralelo,
            dia_semana="lunes",
            hora_inicio=time(8, 0),
            hora_fin=time(10, 0),
        )
        service = HorarioConflictoService()

        propuestos = [_bloque_tuple("lunes", (10, 0), (12, 0))]
        conflictos = service.detectar_conflicto_docente(
            docente_id=docente.pk,
            periodo_id=periodo.pk,
            bloques_propuestos=propuestos,
        )

        assert conflictos == []

    def test_different_day_same_time_no_conflict(self):
        """Edge: día distinto, misma hora → NO conflicto (`d1 == d2` falso)."""
        periodo = PeriodoFactory()
        docente = DocenteFactory()
        paralelo = ParaleloFactory(docente=docente, periodo=periodo)
        BloqueHorarioFactory(
            paralelo=paralelo,
            dia_semana="lunes",
            hora_inicio=time(8, 0),
            hora_fin=time(10, 0),
        )
        service = HorarioConflictoService()

        propuestos = [_bloque_tuple("martes", (8, 0), (10, 0))]
        conflictos = service.detectar_conflicto_docente(
            docente_id=docente.pk,
            periodo_id=periodo.pk,
            bloques_propuestos=propuestos,
        )

        assert conflictos == []


# ---------------------------------------------------------------------------
# R1.x: Docente non-overlap (design §7 R1)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDetectarConflictoDocente:
    """R1.1-R1.4 + empty input + DTO shape."""

    def test_r1_1_docente_in_two_paralelos_overlap_produces_conflict(self):
        """R1.1: D1 en P1 lunes 08-10; crear P2 con D1 lunes 09-11 → conflicto."""
        periodo = PeriodoFactory()
        docente = DocenteFactory()
        asignatura_existente = AsignaturaFactory(codigo="MAT-101", nombre="Matemáticas")
        paralelo_existente = ParaleloFactory(
            docente=docente,
            periodo=periodo,
            asignatura=asignatura_existente,
            nombre="A",
        )
        BloqueHorarioFactory(
            paralelo=paralelo_existente,
            dia_semana="lunes",
            hora_inicio=time(8, 0),
            hora_fin=time(10, 0),
        )
        service = HorarioConflictoService()

        propuestos = [_bloque_tuple("lunes", (9, 0), (11, 0))]
        conflictos = service.detectar_conflicto_docente(
            docente_id=docente.pk,
            periodo_id=periodo.pk,
            bloques_propuestos=propuestos,
        )

        assert len(conflictos) == 1
        conflicto = conflictos[0]
        # DTO debe exponer los 8 campos descritos en design §2.1.
        assert isinstance(conflicto, Conflicto)
        assert conflicto.paralelo_id == paralelo_existente.pk
        assert conflicto.paralelo_nombre == "A"
        assert conflicto.asignatura_codigo == "MAT-101"
        assert conflicto.asignatura_nombre == "Matemáticas"
        assert conflicto.dia_semana == "lunes"
        assert conflicto.dia_semana_label == "Lunes"
        assert conflicto.hora_inicio == time(8, 0)
        assert conflicto.hora_fin == time(10, 0)

    def test_r1_2_docente_back_to_back_no_conflict(self):
        """R1.2: D1 en P1 lunes 08-10; crear P2 con D1 lunes 10-12 → NO conflicto."""
        periodo = PeriodoFactory()
        docente = DocenteFactory()
        paralelo = ParaleloFactory(docente=docente, periodo=periodo)
        BloqueHorarioFactory(
            paralelo=paralelo,
            dia_semana="lunes",
            hora_inicio=time(8, 0),
            hora_fin=time(10, 0),
        )
        service = HorarioConflictoService()

        propuestos = [_bloque_tuple("lunes", (10, 0), (12, 0))]
        conflictos = service.detectar_conflicto_docente(
            docente_id=docente.pk,
            periodo_id=periodo.pk,
            bloques_propuestos=propuestos,
        )

        assert conflictos == []

    def test_r1_3_self_conflict_on_edit_with_paralelo_id_excluir(self):
        """R1.3: editar P1 (mismo paralelo) → NO self-conflict cuando paralelo_id_excluir=P1.pk."""
        periodo = PeriodoFactory()
        docente = DocenteFactory()
        paralelo = ParaleloFactory(docente=docente, periodo=periodo)
        BloqueHorarioFactory(
            paralelo=paralelo,
            dia_semana="lunes",
            hora_inicio=time(8, 0),
            hora_fin=time(10, 0),
        )
        service = HorarioConflictoService()

        # Cambiar el rango del mismo paralelo: solapa consigo mismo, pero se excluye.
        propuestos = [_bloque_tuple("lunes", (9, 0), (11, 0))]
        conflictos = service.detectar_conflicto_docente(
            docente_id=docente.pk,
            periodo_id=periodo.pk,
            bloques_propuestos=propuestos,
            paralelo_id_excluir=paralelo.pk,
        )

        assert conflictos == []

    def test_r1_4_different_periodo_no_conflict(self):
        """R1.4: D1 en P1 periodo A; crear P2 con D1 periodo B → NO conflicto."""
        periodo_a = PeriodoFactory()
        periodo_b = PeriodoFactory()
        docente = DocenteFactory()
        paralelo_a = ParaleloFactory(docente=docente, periodo=periodo_a)
        BloqueHorarioFactory(
            paralelo=paralelo_a,
            dia_semana="lunes",
            hora_inicio=time(8, 0),
            hora_fin=time(10, 0),
        )
        service = HorarioConflictoService()

        propuestos = [_bloque_tuple("lunes", (9, 0), (11, 0))]
        conflictos = service.detectar_conflicto_docente(
            docente_id=docente.pk,
            periodo_id=periodo_b.pk,
            bloques_propuestos=propuestos,
        )

        assert conflictos == []

    def test_empty_bloques_propuestos_returns_empty_list(self):
        """B6/edge: bloques_propuestos vacío → no se hace nada, retorna []."""
        periodo = PeriodoFactory()
        docente = DocenteFactory()
        paralelo = ParaleloFactory(docente=docente, periodo=periodo)
        BloqueHorarioFactory(
            paralelo=paralelo,
            dia_semana="lunes",
            hora_inicio=time(8, 0),
            hora_fin=time(10, 0),
        )
        service = HorarioConflictoService()

        conflictos = service.detectar_conflicto_docente(
            docente_id=docente.pk,
            periodo_id=periodo.pk,
            bloques_propuestos=[],
        )

        assert conflictos == []


# ---------------------------------------------------------------------------
# R2.x + R5.x: Estudiante non-overlap by ACTIVA matrícula
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDetectarConflictoEstudiante:
    """R2.1, R2.2, R5.1 + edit-excluir."""

    def test_r2_1_estudiante_activa_overlap_produces_conflict(self):
        """R2.1: E1 ACTIVA en P1 mar 14-16; matricular en P2 mar 15-17 → conflicto."""
        periodo = PeriodoFactory()
        estudiante = EstudianteFactory()
        asignatura = AsignaturaFactory(codigo="HIS-101", nombre="Historia")
        paralelo_existente = ParaleloFactory(
            periodo=periodo,
            asignatura=asignatura,
            nombre="A",
        )
        BloqueHorarioFactory(
            paralelo=paralelo_existente,
            dia_semana="martes",
            hora_inicio=time(14, 0),
            hora_fin=time(16, 0),
        )
        MatriculaFactory(
            estudiante=estudiante,
            paralelo=paralelo_existente,
            estado=Matricula.Estado.ACTIVA,
        )
        service = HorarioConflictoService()

        propuestos = [_bloque_tuple("martes", (15, 0), (17, 0))]
        conflictos = service.detectar_conflicto_estudiante(
            estudiante_id=estudiante.pk,
            periodo_id=periodo.pk,
            bloques_propuestos=propuestos,
        )

        assert len(conflictos) == 1
        assert conflictos[0].paralelo_id == paralelo_existente.pk
        assert conflictos[0].asignatura_codigo == "HIS-101"
        assert conflictos[0].dia_semana_label == "Martes"

    def test_r2_2_estudiante_retirada_overlap_no_conflict(self):
        """R2.2: E1 RETIRADA en P1 → matrícula RETIRADA se IGNORA, no hay conflicto."""
        periodo = PeriodoFactory()
        estudiante = EstudianteFactory()
        paralelo_existente = ParaleloFactory(periodo=periodo)
        BloqueHorarioFactory(
            paralelo=paralelo_existente,
            dia_semana="martes",
            hora_inicio=time(14, 0),
            hora_fin=time(16, 0),
        )
        MatriculaFactory(
            estudiante=estudiante,
            paralelo=paralelo_existente,
            estado=Matricula.Estado.RETIRADA,
        )
        service = HorarioConflictoService()

        propuestos = [_bloque_tuple("martes", (15, 0), (17, 0))]
        conflictos = service.detectar_conflicto_estudiante(
            estudiante_id=estudiante.pk,
            periodo_id=periodo.pk,
            bloques_propuestos=propuestos,
        )

        assert conflictos == []

    def test_r5_1_estudiante_suspendida_overlap_no_conflict(self):
        """R5.1: matrícula SUSPENDIDA se trata igual que RETIRADA: filtrada por queryset."""
        periodo = PeriodoFactory()
        estudiante = EstudianteFactory()
        paralelo_existente = ParaleloFactory(periodo=periodo)
        BloqueHorarioFactory(
            paralelo=paralelo_existente,
            dia_semana="martes",
            hora_inicio=time(14, 0),
            hora_fin=time(16, 0),
        )
        MatriculaFactory(
            estudiante=estudiante,
            paralelo=paralelo_existente,
            estado=Matricula.Estado.SUSPENDIDA,
        )
        service = HorarioConflictoService()

        propuestos = [_bloque_tuple("martes", (15, 0), (17, 0))]
        conflictos = service.detectar_conflicto_estudiante(
            estudiante_id=estudiante.pk,
            periodo_id=periodo.pk,
            bloques_propuestos=propuestos,
        )

        assert conflictos == []

    def test_edit_mode_matricula_id_excluir_no_self_conflict(self):
        """Edit estudiante: matricula_id_excluir → no self-conflict en la misma matrícula."""
        periodo = PeriodoFactory()
        estudiante = EstudianteFactory()
        paralelo = ParaleloFactory(periodo=periodo)
        BloqueHorarioFactory(
            paralelo=paralelo,
            dia_semana="martes",
            hora_inicio=time(14, 0),
            hora_fin=time(16, 0),
        )
        matricula = MatriculaFactory(
            estudiante=estudiante,
            paralelo=paralelo,
            estado=Matricula.Estado.ACTIVA,
        )
        service = HorarioConflictoService()

        # Mismo rango: solaparía consigo mismo si no se excluye la matrícula.
        propuestos = [_bloque_tuple("martes", (14, 0), (16, 0))]
        conflictos = service.detectar_conflicto_estudiante(
            estudiante_id=estudiante.pk,
            periodo_id=periodo.pk,
            bloques_propuestos=propuestos,
            matricula_id_excluir=matricula.pk,
        )

        assert conflictos == []


# ---------------------------------------------------------------------------
# Exception typing contract (design §2.4)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestConflictoExceptionsExposeConflictos:
    """`ConflictoHorarioDocenteError` / `ConflictoHorarioEstudianteError` deben
    aceptar `conflictos: list[Conflicto]` y exponer `.conflictos` (contrato §2.4
    consumido por exception_mapping en Phase 2 y por las vistas en el render).
    """

    def test_docente_error_carries_conflictos_list(self):
        c = Conflicto(
            paralelo_id=1,
            paralelo_nombre="A",
            asignatura_codigo="MAT-101",
            asignatura_nombre="Matemáticas",
            dia_semana="lunes",
            dia_semana_label="Lunes",
            hora_inicio=time(8, 0),
            hora_fin=time(10, 0),
        )
        exc = ConflictoHorarioDocenteError([c])

        assert hasattr(exc, "conflictos")
        assert exc.conflictos == [c]
        # Mensaje humano construido per design §2.4 ("docente").
        assert "docente" in str(exc).lower()

    def test_estudiante_error_carries_conflictos_list(self):
        c = Conflicto(
            paralelo_id=2,
            paralelo_nombre="B",
            asignatura_codigo="FIS-201",
            asignatura_nombre="Física",
            dia_semana="martes",
            dia_semana_label="Martes",
            hora_inicio=time(14, 0),
            hora_fin=time(16, 0),
        )
        exc = ConflictoHorarioEstudianteError([c])

        assert hasattr(exc, "conflictos")
        assert exc.conflictos == [c]
        assert "estudiante" in str(exc).lower()


# ---------------------------------------------------------------------------
# Query budget (design §3.3) — N+1 prevention via select_related
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestQueryBudget:
    """Both `detectar_conflicto_*` MUST execute ≤ 2 queries per call (design §3.3).

    Budget rationale (design §3.1, §3.2):
    - 1 query for `BloqueHorario.filter(...).select_related("paralelo__asignatura")`
      (select_related folds the joins, no extra round-trips for asignatura/paralelo).
    - +1 budget slack for transactional savepoints / pytest-django wrappers.

    Usa `CaptureQueriesContext` para validar el techo (`≤ 2`), no el conteo exacto:
    cualquier implementación que ejecute MENOS queries (p.ej. 1 sola consulta con
    JOIN via select_related) cumple el contrato. Lo que NO se acepta es excederlo.
    """

    def test_detectar_conflicto_docente_under_query_budget(self):
        """1 docente, 3 paralelos, 5 bloques each, 1 periodo → ≤ 2 queries (design §3.1)."""
        periodo = PeriodoFactory()
        docente = DocenteFactory()
        # 3 paralelos, cada uno con 5 bloques en distintos días → fixture realista.
        dias = ["lunes", "martes", "miercoles", "jueves", "viernes"]
        for _ in range(3):
            paralelo = ParaleloFactory(docente=docente, periodo=periodo)
            for dia in dias:
                BloqueHorarioFactory(
                    paralelo=paralelo,
                    dia_semana=dia,
                    hora_inicio=time(8, 0),
                    hora_fin=time(10, 0),
                )
        service = HorarioConflictoService()

        # Bloque propuesto que NO solapa (no importa el resultado, importa el budget).
        propuestos = [_bloque_tuple("sabado", (8, 0), (10, 0))]

        with CaptureQueriesContext(connection) as ctx:
            service.detectar_conflicto_docente(
                docente_id=docente.pk,
                periodo_id=periodo.pk,
                bloques_propuestos=propuestos,
            )
        assert len(ctx) <= 2, f"Query budget exceeded: {len(ctx)} queries (expected ≤ 2)"

    def test_detectar_conflicto_estudiante_under_query_budget(self):
        """1 estudiante ACTIVA en 3 paralelos con bloques → ≤ 2 queries (design §3.2)."""
        periodo = PeriodoFactory()
        estudiante = EstudianteFactory()
        dias = ["lunes", "martes", "miercoles", "jueves", "viernes"]
        for _ in range(3):
            paralelo = ParaleloFactory(periodo=periodo)
            for dia in dias:
                BloqueHorarioFactory(
                    paralelo=paralelo,
                    dia_semana=dia,
                    hora_inicio=time(8, 0),
                    hora_fin=time(10, 0),
                )
            MatriculaFactory(
                estudiante=estudiante,
                paralelo=paralelo,
                estado=Matricula.Estado.ACTIVA,
            )
        service = HorarioConflictoService()

        propuestos = [_bloque_tuple("sabado", (8, 0), (10, 0))]

        with CaptureQueriesContext(connection) as ctx:
            service.detectar_conflicto_estudiante(
                estudiante_id=estudiante.pk,
                periodo_id=periodo.pk,
                bloques_propuestos=propuestos,
            )
        assert len(ctx) <= 2, f"Query budget exceeded: {len(ctx)} queries (expected ≤ 2)"
