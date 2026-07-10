"""Tests for HU32: sub-nota views (configuración + registro en planilla)."""

from decimal import Decimal

import pytest

from apps.calificaciones.application.services import SubNotaParcialAppService
from apps.calificaciones.infrastructure.models import (
    Calificacion,
    ConfiguracionSubNotas,
    Evaluacion,
    RegistroCalificacionParalelo,
    SubNotaParcial,
)
from tests.factories import (
    DocenteFactory,
    EstudianteFactory,
    EvaluacionFactory,
    MatriculaFactory,
    ParaleloFactory,
)

pytestmark = pytest.mark.django_db


def _saved(user):
    """Persist password hash so force_login session survives request cycle."""
    user.save()
    return user


def _url_config(paralelo, evaluacion):
    return f"/calificaciones/paralelo/{paralelo.pk}/evaluaciones/{evaluacion.pk}/sub-notas/"


class TestConfigurarSubNotasView:

    def test_get_como_docente(self, client):
        docente = _saved(DocenteFactory())
        paralelo = ParaleloFactory(docente=docente)
        ev = EvaluacionFactory(paralelo=paralelo, tipo=Evaluacion.TipoEvaluacion.PARCIAL_1)
        client.force_login(docente)
        response = client.get(_url_config(paralelo, ev))
        assert response.status_code == 200
        assert b"Configurar Sub-notas" in response.content

    def test_get_otro_docente_redirige(self, client):
        docente = _saved(DocenteFactory())
        otro = _saved(DocenteFactory())
        paralelo = ParaleloFactory(docente=otro)
        ev = EvaluacionFactory(paralelo=paralelo, tipo=Evaluacion.TipoEvaluacion.PARCIAL_1)
        client.force_login(docente)
        response = client.get(_url_config(paralelo, ev))
        assert response.status_code == 302

    def test_get_no_parcial_redirige(self, client):
        docente = _saved(DocenteFactory())
        paralelo = ParaleloFactory(docente=docente)
        ev = EvaluacionFactory(paralelo=paralelo, tipo=Evaluacion.TipoEvaluacion.EXAMEN_FINAL)
        client.force_login(docente)
        response = client.get(_url_config(paralelo, ev))
        assert response.status_code == 302
        assert response.url.endswith(f"/calificaciones/paralelo/{paralelo.pk}/evaluaciones/")

    def test_post_crea_configuracion(self, client):
        docente = _saved(DocenteFactory())
        paralelo = ParaleloFactory(docente=docente)
        ev = EvaluacionFactory(paralelo=paralelo, tipo=Evaluacion.TipoEvaluacion.PARCIAL_1)
        client.force_login(docente)
        response = client.post(
            _url_config(paralelo, ev),
            {"nombre": ["Tarea 1", "Quiz", "Examen"]},
        )
        assert response.status_code == 302
        config = ConfiguracionSubNotas.objects.get(evaluacion=ev)
        assert [i.nombre for i in config.items.all()] == ["Tarea 1", "Quiz", "Examen"]

    def test_post_cantidad_invalida_no_crea(self, client):
        docente = _saved(DocenteFactory())
        paralelo = ParaleloFactory(docente=docente)
        ev = EvaluacionFactory(paralelo=paralelo, tipo=Evaluacion.TipoEvaluacion.PARCIAL_1)
        client.force_login(docente)
        response = client.post(_url_config(paralelo, ev), {"nombre": ["A", "B"]})
        assert response.status_code == 302
        assert not ConfiguracionSubNotas.objects.filter(evaluacion=ev).exists()

    def test_post_bloqueado_si_enviado(self, client):
        docente = _saved(DocenteFactory())
        paralelo = ParaleloFactory(docente=docente)
        ev = EvaluacionFactory(paralelo=paralelo, tipo=Evaluacion.TipoEvaluacion.PARCIAL_1)
        RegistroCalificacionParalelo.objects.create(
            paralelo=paralelo,
            estado=RegistroCalificacionParalelo.Estado.COMPLETO,
        )
        client.force_login(docente)
        client.post(_url_config(paralelo, ev), {"nombre": ["A", "B", "C"]})
        assert not ConfiguracionSubNotas.objects.filter(evaluacion=ev).exists()

    def test_post_crea_configuracion_con_pesos(self, client):
        docente = _saved(DocenteFactory())
        paralelo = ParaleloFactory(docente=docente)
        ev = EvaluacionFactory(paralelo=paralelo, tipo=Evaluacion.TipoEvaluacion.PARCIAL_1)
        client.force_login(docente)
        response = client.post(
            _url_config(paralelo, ev),
            {"nombre": ["Tarea 1", "Quiz", "Examen"], "peso": ["20", "30", "50"]},
        )
        assert response.status_code == 302
        config = ConfiguracionSubNotas.objects.get(evaluacion=ev)
        assert [(i.nombre, i.peso) for i in config.items.all()] == [
            ("Tarea 1", Decimal("20.00")),
            ("Quiz", Decimal("30.00")),
            ("Examen", Decimal("50.00")),
        ]

    def test_post_pesos_no_suman_cien_no_crea(self, client):
        docente = _saved(DocenteFactory())
        paralelo = ParaleloFactory(docente=docente)
        ev = EvaluacionFactory(paralelo=paralelo, tipo=Evaluacion.TipoEvaluacion.PARCIAL_1)
        client.force_login(docente)
        response = client.post(
            _url_config(paralelo, ev),
            {"nombre": ["A", "B", "C"], "peso": ["20", "30", "40"]},
        )
        assert response.status_code == 302
        assert not ConfiguracionSubNotas.objects.filter(evaluacion=ev).exists()


class TestRegistrarSubNotasEnPlanilla:

    def _setup_planilla(self):
        docente = _saved(DocenteFactory())
        paralelo = ParaleloFactory(docente=docente)
        ev = EvaluacionFactory(paralelo=paralelo, tipo=Evaluacion.TipoEvaluacion.PARCIAL_1)
        estudiante = EstudianteFactory()
        matricula = MatriculaFactory(paralelo=paralelo, estudiante=estudiante)
        SubNotaParcialAppService().configurar_sub_notas(ev.id, ["Tarea 1", "Quiz", "Examen"])
        return docente, paralelo, ev, matricula

    def test_get_planilla_muestra_sub_notas(self, client):
        docente, paralelo, ev, matricula = self._setup_planilla()
        client.force_login(docente)
        response = client.get(f"/calificaciones/paralelo/{paralelo.pk}/registrar/")
        assert response.status_code == 200
        assert f"subnota_{matricula.pk}_{ev.pk}_1".encode() in response.content
        assert f"override_{matricula.pk}_{ev.pk}".encode() in response.content

    def test_post_consolida_calificacion(self, client):
        docente, paralelo, ev, matricula = self._setup_planilla()
        client.force_login(docente)
        response = client.post(
            f"/calificaciones/paralelo/{paralelo.pk}/registrar/",
            {
                f"subnota_{matricula.pk}_{ev.pk}_1": "15",
                f"subnota_{matricula.pk}_{ev.pk}_2": "18",
                f"subnota_{matricula.pk}_{ev.pk}_3": "12",
            },
        )
        assert response.status_code == 302
        assert SubNotaParcial.objects.filter(evaluacion=ev, matricula=matricula).count() == 3
        cal = Calificacion.objects.get(evaluacion=ev, estudiante=matricula.estudiante)
        assert cal.nota == Decimal("15.00")

    def test_post_override_con_justificacion(self, client):
        docente, paralelo, ev, matricula = self._setup_planilla()
        client.force_login(docente)
        client.post(
            f"/calificaciones/paralelo/{paralelo.pk}/registrar/",
            {
                f"subnota_{matricula.pk}_{ev.pk}_1": "15",
                f"subnota_{matricula.pk}_{ev.pk}_2": "18",
                f"subnota_{matricula.pk}_{ev.pk}_3": "12",
                f"override_{matricula.pk}_{ev.pk}": "16",
                f"just_{matricula.pk}_{ev.pk}": "Participación destacada.",
            },
        )
        cal = Calificacion.objects.get(evaluacion=ev, estudiante=matricula.estudiante)
        assert cal.nota == Decimal("16")

    def test_post_override_sin_justificacion_no_guarda(self, client):
        docente, paralelo, ev, matricula = self._setup_planilla()
        client.force_login(docente)
        client.post(
            f"/calificaciones/paralelo/{paralelo.pk}/registrar/",
            {
                f"subnota_{matricula.pk}_{ev.pk}_1": "15",
                f"subnota_{matricula.pk}_{ev.pk}_2": "18",
                f"subnota_{matricula.pk}_{ev.pk}_3": "12",
                f"override_{matricula.pk}_{ev.pk}": "16",
            },
        )
        assert not SubNotaParcial.objects.filter(evaluacion=ev).exists()
        assert not Calificacion.objects.filter(evaluacion=ev).exists()

    def test_post_grupo_vacio_se_ignora(self, client):
        docente, paralelo, ev, matricula = self._setup_planilla()
        client.force_login(docente)
        response = client.post(
            f"/calificaciones/paralelo/{paralelo.pk}/registrar/",
            {
                f"subnota_{matricula.pk}_{ev.pk}_1": "",
                f"subnota_{matricula.pk}_{ev.pk}_2": "",
                f"subnota_{matricula.pk}_{ev.pk}_3": "",
                f"override_{matricula.pk}_{ev.pk}": "",
                f"just_{matricula.pk}_{ev.pk}": "",
            },
        )
        assert response.status_code == 302
        assert not SubNotaParcial.objects.filter(evaluacion=ev).exists()

    def test_post_bloqueado_si_enviado(self, client):
        docente, paralelo, ev, matricula = self._setup_planilla()
        RegistroCalificacionParalelo.objects.create(
            paralelo=paralelo,
            estado=RegistroCalificacionParalelo.Estado.COMPLETO,
        )
        client.force_login(docente)
        client.post(
            f"/calificaciones/paralelo/{paralelo.pk}/registrar/",
            {
                f"subnota_{matricula.pk}_{ev.pk}_1": "15",
                f"subnota_{matricula.pk}_{ev.pk}_2": "18",
                f"subnota_{matricula.pk}_{ev.pk}_3": "12",
            },
        )
        assert not SubNotaParcial.objects.filter(evaluacion=ev).exists()

    def test_post_consolida_ponderado_con_pesos(self, client):
        docente = _saved(DocenteFactory())
        paralelo = ParaleloFactory(docente=docente)
        ev = EvaluacionFactory(paralelo=paralelo, tipo=Evaluacion.TipoEvaluacion.PARCIAL_1)
        estudiante = EstudianteFactory()
        matricula = MatriculaFactory(paralelo=paralelo, estudiante=estudiante)
        SubNotaParcialAppService().configurar_sub_notas(
            ev.id, ["Tarea", "Quiz", "Examen"], pesos=["20", "30", "50"]
        )
        client.force_login(docente)
        response = client.post(
            f"/calificaciones/paralelo/{paralelo.pk}/registrar/",
            {
                f"subnota_{matricula.pk}_{ev.pk}_1": "15",
                f"subnota_{matricula.pk}_{ev.pk}_2": "18",
                f"subnota_{matricula.pk}_{ev.pk}_3": "12",
            },
        )
        assert response.status_code == 302
        cal = Calificacion.objects.get(evaluacion=ev, estudiante=matricula.estudiante)
        assert cal.nota == Decimal("14.40")
