"""Tests for HU32: SubNotaParcialAppService (application layer)."""

from decimal import Decimal

import pytest

from apps.calificaciones.application.services import SubNotaParcialAppService
from apps.calificaciones.infrastructure.models import (
    Calificacion,
    ConfiguracionSubNotas,
    Evaluacion,
    LogCalificacion,
    RegistroCalificacionParalelo,
    SubNotaParcial,
)
from tests.factories import (
    DocenteFactory,
    EvaluacionFactory,
    MatriculaFactory,
    ParaleloFactory,
    RegistroCalificacionParaleloFactory,
    SubNotaParcialFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def service():
    return SubNotaParcialAppService()


@pytest.fixture
def paralelo():
    return ParaleloFactory()


@pytest.fixture
def evaluacion(paralelo):
    return EvaluacionFactory(paralelo=paralelo, tipo=Evaluacion.TipoEvaluacion.PARCIAL_1)


@pytest.fixture
def matricula(paralelo):
    return MatriculaFactory(paralelo=paralelo)


class TestConfigurarSubNotas:
    """Tests for SubNotaParcialAppService.configurar_sub_notas."""

    def test_configura_tres_sub_notas(self, service, evaluacion):
        resultado = service.configurar_sub_notas(evaluacion.id, ["Tarea 1", "Quiz", "Examen"])
        assert resultado["ok"] is True
        items = service.obtener_configuracion(evaluacion.id)
        assert [(i.orden, i.nombre) for i in items] == [
            (1, "Tarea 1"),
            (2, "Quiz"),
            (3, "Examen"),
        ]

    def test_configura_cinco_sub_notas(self, service, evaluacion):
        nombres = ["T1", "T2", "T3", "T4", "T5"]
        resultado = service.configurar_sub_notas(evaluacion.id, nombres)
        assert resultado["ok"] is True
        assert len(service.obtener_configuracion(evaluacion.id)) == 5

    @pytest.mark.parametrize("cantidad", [1, 2, 6])
    def test_cantidad_invalida_rechazada(self, service, evaluacion, cantidad):
        nombres = [f"T{i}" for i in range(cantidad)]
        resultado = service.configurar_sub_notas(evaluacion.id, nombres)
        assert resultado["ok"] is False
        assert not ConfiguracionSubNotas.objects.filter(evaluacion=evaluacion).exists()

    def test_nombre_vacio_rechazado(self, service, evaluacion):
        resultado = service.configurar_sub_notas(evaluacion.id, ["Tarea 1", "  ", "Quiz"])
        assert resultado["ok"] is False
        assert "vacíos" in resultado["error"]

    def test_reemplaza_configuracion_previa(self, service, evaluacion):
        service.configurar_sub_notas(evaluacion.id, ["A", "B", "C"])
        resultado = service.configurar_sub_notas(evaluacion.id, ["X", "Y", "Z", "W"])
        assert resultado["ok"] is True
        items = service.obtener_configuracion(evaluacion.id)
        assert [i.nombre for i in items] == ["X", "Y", "Z", "W"]
        assert ConfiguracionSubNotas.objects.filter(evaluacion=evaluacion).count() == 1

    def test_reconfigurar_elimina_sub_notas_previas(self, service, evaluacion, matricula):
        service.configurar_sub_notas(evaluacion.id, ["A", "B", "C"])
        service.registrar_sub_notas(evaluacion.id, matricula.id, ["10", "12", "14"])
        resultado = service.configurar_sub_notas(evaluacion.id, ["X", "Y", "Z"])
        assert resultado["ok"] is True
        assert resultado["sub_notas_eliminadas"] == 3
        assert not SubNotaParcial.objects.filter(evaluacion=evaluacion).exists()

    def test_solo_parciales_admiten_sub_notas(self, service, paralelo):
        examen = EvaluacionFactory(paralelo=paralelo, tipo=Evaluacion.TipoEvaluacion.EXAMEN_FINAL)
        resultado = service.configurar_sub_notas(examen.id, ["A", "B", "C"])
        assert resultado["ok"] is False
        assert "parciales" in resultado["error"]

    def test_bloqueado_si_planilla_enviada(self, service, evaluacion):
        RegistroCalificacionParaleloFactory(
            paralelo=evaluacion.paralelo,
            estado=RegistroCalificacionParalelo.Estado.COMPLETO,
        )
        resultado = service.configurar_sub_notas(evaluacion.id, ["A", "B", "C"])
        assert resultado["ok"] is False
        assert "validación" in resultado["error"]

    def test_evaluacion_inexistente(self, service):
        resultado = service.configurar_sub_notas(99999, ["A", "B", "C"])
        assert resultado["ok"] is False

    def test_configura_con_pesos_validos(self, service, evaluacion):
        resultado = service.configurar_sub_notas(
            evaluacion.id, ["Tarea", "Quiz", "Examen"], pesos=["20", "30", "50"]
        )
        assert resultado["ok"] is True
        items = service.obtener_configuracion(evaluacion.id)
        assert [i.peso for i in items] == [
            Decimal("20.00"),
            Decimal("30.00"),
            Decimal("50.00"),
        ]

    def test_pesos_que_no_suman_cien_rechazados(self, service, evaluacion):
        resultado = service.configurar_sub_notas(
            evaluacion.id, ["A", "B", "C"], pesos=["20", "30", "40"]
        )
        assert resultado["ok"] is False
        assert "sumar" in resultado["error"]
        assert not ConfiguracionSubNotas.objects.filter(evaluacion=evaluacion).exists()

    def test_pesos_invalidos_no_numericos_rechazados(self, service, evaluacion):
        resultado = service.configurar_sub_notas(
            evaluacion.id, ["A", "B", "C"], pesos=["20", "abc", "50"]
        )
        assert resultado["ok"] is False
        assert "válidos" in resultado["error"]

    def test_cantidad_de_pesos_distinta_a_nombres_rechazada(self, service, evaluacion):
        resultado = service.configurar_sub_notas(
            evaluacion.id, ["A", "B", "C"], pesos=["50", "50"]
        )
        assert resultado["ok"] is False

    def test_sin_pesos_guarda_peso_none(self, service, evaluacion):
        resultado = service.configurar_sub_notas(evaluacion.id, ["A", "B", "C"])
        assert resultado["ok"] is True
        items = service.obtener_configuracion(evaluacion.id)
        assert all(i.peso is None for i in items)


class TestRegistrarSubNotas:
    """Tests for SubNotaParcialAppService.registrar_sub_notas."""

    def test_registra_y_consolida_promedio(self, service, evaluacion, matricula):
        service.configurar_sub_notas(evaluacion.id, ["Tarea 1", "Quiz", "Examen"])
        resultado = service.registrar_sub_notas(evaluacion.id, matricula.id, ["15", "18", "12"])
        assert resultado["ok"] is True
        assert resultado["promedio"] == Decimal("15.00")
        assert resultado["nota_final"] == Decimal("15.00")

        sub_notas = service.obtener_sub_notas(evaluacion.id, matricula.id)
        assert [(s.nombre, s.nota) for s in sub_notas] == [
            ("Tarea 1", Decimal("15.00")),
            ("Quiz", Decimal("18.00")),
            ("Examen", Decimal("12.00")),
        ]
        calificacion = Calificacion.objects.get(
            evaluacion=evaluacion, estudiante=matricula.estudiante
        )
        assert calificacion.nota == Decimal("15.00")

    def test_re_registro_reemplaza_sub_notas(self, service, evaluacion, matricula):
        service.configurar_sub_notas(evaluacion.id, ["A", "B", "C"])
        service.registrar_sub_notas(evaluacion.id, matricula.id, ["10", "10", "10"])
        resultado = service.registrar_sub_notas(evaluacion.id, matricula.id, ["20", "20", "20"])
        assert resultado["ok"] is True
        assert (
            SubNotaParcial.objects.filter(evaluacion=evaluacion, matricula=matricula).count() == 3
        )
        calificacion = Calificacion.objects.get(
            evaluacion=evaluacion, estudiante=matricula.estudiante
        )
        assert calificacion.nota == Decimal("20.00")

    def test_override_con_justificacion(self, service, evaluacion, matricula):
        service.configurar_sub_notas(evaluacion.id, ["A", "B", "C"])
        resultado = service.registrar_sub_notas(
            evaluacion.id,
            matricula.id,
            ["15", "18", "12"],
            override_str="16",
            justificacion="Participación destacada en clase.",
        )
        assert resultado["ok"] is True
        assert resultado["nota_final"] == Decimal("16")
        calificacion = Calificacion.objects.get(
            evaluacion=evaluacion, estudiante=matricula.estudiante
        )
        assert calificacion.nota == Decimal("16")
        sub_nota = SubNotaParcial.objects.filter(evaluacion=evaluacion).first()
        assert sub_nota.nota_final_parcial_override == Decimal("16")
        assert sub_nota.justificacion_override == "Participación destacada en clase."

    def test_override_sin_justificacion_rechazado(self, service, evaluacion, matricula):
        service.configurar_sub_notas(evaluacion.id, ["A", "B", "C"])
        resultado = service.registrar_sub_notas(
            evaluacion.id, matricula.id, ["15", "18", "12"], override_str="16"
        )
        assert resultado["ok"] is False
        assert "justificación" in resultado["error"].lower()
        assert not SubNotaParcial.objects.filter(evaluacion=evaluacion).exists()

    def test_override_igual_al_promedio_sin_justificacion(self, service, evaluacion, matricula):
        service.configurar_sub_notas(evaluacion.id, ["A", "B", "C"])
        resultado = service.registrar_sub_notas(
            evaluacion.id, matricula.id, ["15", "18", "12"], override_str="15.00"
        )
        assert resultado["ok"] is True
        assert resultado["nota_final"] == Decimal("15.00")

    def test_nota_fuera_de_rango_rechazada(self, service, evaluacion, matricula):
        service.configurar_sub_notas(evaluacion.id, ["A", "B", "C"])
        resultado = service.registrar_sub_notas(evaluacion.id, matricula.id, ["15", "21", "12"])
        assert resultado["ok"] is False
        assert "'B'" in resultado["error"]

    def test_cantidad_distinta_a_config_rechazada(self, service, evaluacion, matricula):
        service.configurar_sub_notas(evaluacion.id, ["A", "B", "C"])
        resultado = service.registrar_sub_notas(evaluacion.id, matricula.id, ["15", "18"])
        assert resultado["ok"] is False
        assert "esperaban 3" in resultado["error"]

    def test_sin_configuracion_rechazado(self, service, evaluacion, matricula):
        resultado = service.registrar_sub_notas(evaluacion.id, matricula.id, ["15", "18", "12"])
        assert resultado["ok"] is False
        assert "configure" in resultado["error"].lower()

    def test_bloqueado_si_planilla_enviada(self, service, evaluacion, matricula):
        service.configurar_sub_notas(evaluacion.id, ["A", "B", "C"])
        RegistroCalificacionParaleloFactory(
            paralelo=evaluacion.paralelo,
            estado=RegistroCalificacionParalelo.Estado.VALIDADO,
        )
        resultado = service.registrar_sub_notas(evaluacion.id, matricula.id, ["15", "18", "12"])
        assert resultado["ok"] is False
        assert "validación" in resultado["error"]

    def test_matricula_de_otro_paralelo_rechazada(self, service, evaluacion):
        otra_matricula = MatriculaFactory()  # paralelo distinto
        service.configurar_sub_notas(evaluacion.id, ["A", "B", "C"])
        resultado = service.registrar_sub_notas(
            evaluacion.id, otra_matricula.id, ["15", "18", "12"]
        )
        assert resultado["ok"] is False
        assert "Matrícula" in resultado["error"]

    def test_genera_log_auditoria(self, service, evaluacion, matricula):
        docente = DocenteFactory()
        service.configurar_sub_notas(evaluacion.id, ["A", "B", "C"])
        service.registrar_sub_notas(
            evaluacion.id, matricula.id, ["15", "18", "12"], usuario=docente, ip="127.0.0.1"
        )
        log = LogCalificacion.objects.filter(
            accion=LogCalificacion.TipoAccion.CREACION,
            realizado_por=docente,
        ).first()
        assert log is not None
        assert log.valor_nuevo == Decimal("15.00")
        assert "sub-notas" in log.motivo

    def test_log_de_override_incluye_justificacion(self, service, evaluacion, matricula):
        docente = DocenteFactory()
        service.configurar_sub_notas(evaluacion.id, ["A", "B", "C"])
        service.registrar_sub_notas(
            evaluacion.id,
            matricula.id,
            ["15", "18", "12"],
            usuario=docente,
            override_str="17",
            justificacion="Ajuste por proyecto adicional.",
        )
        log = LogCalificacion.objects.filter(realizado_por=docente).first()
        assert "Override manual: 17" in log.motivo
        assert "Ajuste por proyecto adicional." in log.motivo

    def test_registra_y_consolida_ponderado(self, service, evaluacion, matricula):
        service.configurar_sub_notas(
            evaluacion.id, ["Tarea", "Quiz", "Examen"], pesos=["20", "30", "50"]
        )
        resultado = service.registrar_sub_notas(evaluacion.id, matricula.id, ["15", "18", "12"])
        assert resultado["ok"] is True
        # 15*0.20 + 18*0.30 + 12*0.50 = 14.40
        assert resultado["promedio"] == Decimal("14.40")
        assert resultado["nota_final"] == Decimal("14.40")
        calificacion = Calificacion.objects.get(
            evaluacion=evaluacion, estudiante=matricula.estudiante
        )
        assert calificacion.nota == Decimal("14.40")

    def test_sub_notas_guardan_peso_de_config(self, service, evaluacion, matricula):
        service.configurar_sub_notas(evaluacion.id, ["A", "B", "C"], pesos=["25", "25", "50"])
        service.registrar_sub_notas(evaluacion.id, matricula.id, ["10", "12", "14"])
        pesos = list(
            SubNotaParcial.objects.filter(evaluacion=evaluacion, matricula=matricula)
            .order_by("orden")
            .values_list("peso", flat=True)
        )
        assert pesos == [Decimal("25.00"), Decimal("25.00"), Decimal("50.00")]

    def test_notas_incompletas_rechazadas(self, service, evaluacion, matricula):
        service.configurar_sub_notas(evaluacion.id, ["A", "B", "C"])
        resultado = service.registrar_sub_notas(evaluacion.id, matricula.id, ["15", "", "12"])
        assert resultado["ok"] is False
        assert "completar" in resultado["error"].lower()
        assert not SubNotaParcial.objects.filter(
            evaluacion=evaluacion, matricula=matricula
        ).exists()


class TestObtenerSubNotas:
    """Tests for the read helpers."""

    def test_obtener_configuracion_inexistente(self, service, evaluacion):
        assert service.obtener_configuracion(evaluacion.id) is None

    def test_obtener_sub_notas_ordenadas(self, service, evaluacion, matricula):
        SubNotaParcialFactory(evaluacion=evaluacion, matricula=matricula, orden=2, nombre="B")
        SubNotaParcialFactory(evaluacion=evaluacion, matricula=matricula, orden=1, nombre="A")
        sub_notas = service.obtener_sub_notas(evaluacion.id, matricula.id)
        assert [s.nombre for s in sub_notas] == ["A", "B"]
