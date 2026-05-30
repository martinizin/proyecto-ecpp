"""Tests for the read-only Horarios views (HorarioDocenteView, HorarioEstudianteView)."""

import datetime

import pytest
from django.urls import reverse

from apps.academico.presentation.views import _construir_grilla_horario
from tests.factories import (
    BloqueHorarioFactory,
    DocenteFactory,
    EstudianteFactory,
    InspectorFactory,
    MatriculaFactory,
    ParaleloFactory,
    PeriodoFactory,
)


@pytest.mark.django_db
class TestConstruirGrillaHorario:
    """Pure helper — no DB query, but uses BloqueHorario instances."""

    def test_grilla_vacia(self):
        ctx = _construir_grilla_horario([])
        assert ctx["vacio"] is True
        assert len(ctx["dias"]) == 6  # lunes..sabado
        assert len(ctx["rows"]) == 10  # default range 8..17

    def test_grilla_con_bloques(self):
        periodo = PeriodoFactory(activo=True)
        paralelo = ParaleloFactory(periodo=periodo)
        bloque = BloqueHorarioFactory(
            paralelo=paralelo,
            dia_semana="lunes",
            hora_inicio=datetime.time(8, 0),
            hora_fin=datetime.time(9, 30),
        )
        ctx = _construir_grilla_horario([bloque])
        assert ctx["vacio"] is False
        # Solo debe haber filas para la hora de inicio (8)
        horas = [r["hora"] for r in ctx["rows"]]
        assert "08:00" in horas

    def test_grilla_celdas_ordenadas_por_dia(self):
        periodo = PeriodoFactory(activo=True)
        paralelo_a = ParaleloFactory(periodo=periodo)
        paralelo_b = ParaleloFactory(periodo=periodo)
        b1 = BloqueHorarioFactory(
            paralelo=paralelo_a,
            dia_semana="miercoles",
            hora_inicio=datetime.time(14, 0),
            hora_fin=datetime.time(15, 0),
        )
        b2 = BloqueHorarioFactory(
            paralelo=paralelo_b,
            dia_semana="lunes",
            hora_inicio=datetime.time(14, 0),
            hora_fin=datetime.time(15, 0),
        )
        ctx = _construir_grilla_horario([b1, b2])
        # dias[0]=lunes, dias[2]=miercoles
        row_14 = next(r for r in ctx["rows"] if r["hora"] == "14:00")
        assert len(row_14["celdas"][2]) == 1
        assert len(row_14["celdas"][0]) == 1


@pytest.mark.django_db
class TestHorarioDocenteView:
    """GET /academico/mis-horarios/docente/"""

    def setup_method(self):
        self.url = reverse("academico:horario_docente")

    def test_no_authenticated_redirects(self, client):
        response = client.get(self.url)
        assert response.status_code == 302  # redirect to login

    def test_inspector_no_puede_acceder(self, client):
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        response = client.get(self.url)
        # UserPassesTestMixin: 403 for authenticated user failing test_func
        assert response.status_code == 403

    def test_estudiante_no_puede_acceder(self, client):
        estudiante = EstudianteFactory()
        estudiante.save()
        client.force_login(estudiante)
        response = client.get(self.url)
        assert response.status_code == 403

    def test_docente_ve_solo_sus_bloques(self, client):
        docente = DocenteFactory()
        docente.save()
        otro_docente = DocenteFactory()
        periodo = PeriodoFactory(activo=True)

        paralelo_propio = ParaleloFactory(docente=docente, periodo=periodo)
        paralelo_ajeno = ParaleloFactory(docente=otro_docente, periodo=periodo)

        BloqueHorarioFactory(paralelo=paralelo_propio, dia_semana="lunes")
        BloqueHorarioFactory(paralelo=paralelo_ajeno, dia_semana="martes")

        client.force_login(docente)
        response = client.get(self.url)

        assert response.status_code == 200
        assert response.context["vacio"] is False
        ctx_codigos = []
        for row in response.context["rows"]:
            for celda in row["celdas"]:
                for b in celda:
                    ctx_codigos.append(b["codigo"])
        assert paralelo_propio.asignatura.codigo in ctx_codigos
        assert paralelo_ajeno.asignatura.codigo not in ctx_codigos

    def test_docente_ignora_periodos_inactivos(self, client):
        docente = DocenteFactory()
        docente.save()
        periodo_inactivo = PeriodoFactory(activo=False)
        paralelo = ParaleloFactory(docente=docente, periodo=periodo_inactivo)
        BloqueHorarioFactory(paralelo=paralelo)

        client.force_login(docente)
        response = client.get(self.url)

        assert response.status_code == 200
        assert response.context["vacio"] is True


@pytest.mark.django_db
class TestHorarioEstudianteView:
    """GET /academico/mis-horarios/estudiante/"""

    def setup_method(self):
        self.url = reverse("academico:horario_estudiante")

    def test_docente_no_puede_acceder(self, client):
        docente = DocenteFactory()
        docente.save()
        client.force_login(docente)
        response = client.get(self.url)
        assert response.status_code == 403

    def test_estudiante_ve_solo_paralelos_matriculados_activos(self, client):
        estudiante = EstudianteFactory()
        estudiante.save()
        periodo = PeriodoFactory(activo=True)

        paralelo_matriculado = ParaleloFactory(periodo=periodo)
        paralelo_no_matriculado = ParaleloFactory(periodo=periodo)

        MatriculaFactory(estudiante=estudiante, paralelo=paralelo_matriculado, estado="activa")
        BloqueHorarioFactory(paralelo=paralelo_matriculado, dia_semana="lunes")
        BloqueHorarioFactory(paralelo=paralelo_no_matriculado, dia_semana="martes")

        client.force_login(estudiante)
        response = client.get(self.url)

        assert response.status_code == 200
        codigos = [
            b["codigo"]
            for row in response.context["rows"]
            for celda in row["celdas"]
            for b in celda
        ]
        assert paralelo_matriculado.asignatura.codigo in codigos
        assert paralelo_no_matriculado.asignatura.codigo not in codigos

    def test_estudiante_ignora_matriculas_retiradas(self, client):
        estudiante = EstudianteFactory()
        estudiante.save()
        periodo = PeriodoFactory(activo=True)
        paralelo = ParaleloFactory(periodo=periodo)
        MatriculaFactory(estudiante=estudiante, paralelo=paralelo, estado="retirada")
        BloqueHorarioFactory(paralelo=paralelo)

        client.force_login(estudiante)
        response = client.get(self.url)

        assert response.status_code == 200
        assert response.context["vacio"] is True
