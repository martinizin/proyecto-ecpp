"""Tests para HU15 — Logs de auditoría de calificaciones (LogCalificacion)."""

from decimal import Decimal

import pytest

from apps.calificaciones.application.services import (
    AuditoriaCalificacionService,
    RegistroCalificacionAppService,
)
from apps.calificaciones.infrastructure.models import LogCalificacion
from tests.factories import (
    CalificacionFactory,
    DocenteFactory,
    EstudianteFactory,
    EvaluacionFactory,
    LogCalificacionFactory,
    MatriculaFactory,
)

pytestmark = pytest.mark.django_db


class TestLogCalificacionModelo:
    """Pruebas de estructura del modelo LogCalificacion."""

    def test_crear_log(self):
        log = LogCalificacionFactory()
        assert log.pk is not None
        assert log.timestamp is not None

    def test_str_contiene_accion_y_estudiante(self):
        log = LogCalificacionFactory(accion=LogCalificacion.TipoAccion.CREACION)
        assert "Creación" in str(log)
        assert log.calificacion.estudiante.get_full_name() in str(log)

    def test_log_con_valor_anterior_y_nuevo(self):
        log = LogCalificacionFactory(
            accion=LogCalificacion.TipoAccion.MODIFICACION,
            valor_anterior=Decimal("12.00"),
            valor_nuevo=Decimal("15.00"),
        )
        assert log.valor_anterior == Decimal("12.00")
        assert log.valor_nuevo == Decimal("15.00")

    def test_opciones_tipo_accion(self):
        choices = [c[0] for c in LogCalificacion.TipoAccion.choices]
        assert "creacion" in choices
        assert "modificacion" in choices
        assert "recalificacion" in choices
        assert "eliminacion" in choices

    def test_ordenamiento_descendente_por_timestamp(self):
        cal = CalificacionFactory()
        LogCalificacionFactory(calificacion=cal, valor_nuevo=Decimal("10.00"))
        LogCalificacionFactory(calificacion=cal, valor_nuevo=Decimal("12.00"))
        logs = list(LogCalificacion.objects.filter(calificacion=cal))
        assert logs[0].timestamp >= logs[1].timestamp


class TestAuditoriaCalificacionService:
    """Pruebas unitarias del servicio de auditoría."""

    def test_registrar_creacion(self):
        calificacion = CalificacionFactory(nota=Decimal("18.00"))
        docente = DocenteFactory()

        AuditoriaCalificacionService.registrar_cambio(
            calificacion=calificacion,
            accion=LogCalificacion.TipoAccion.CREACION,
            valor_anterior=None,
            valor_nuevo=Decimal("18.00"),
            usuario=docente,
            ip="192.168.1.1",
        )

        log = LogCalificacion.objects.get(calificacion=calificacion)
        assert log.accion == LogCalificacion.TipoAccion.CREACION
        assert log.valor_anterior is None
        assert log.valor_nuevo == Decimal("18.00")
        assert log.realizado_por == docente
        assert log.ip == "192.168.1.1"

    def test_registrar_modificacion(self):
        calificacion = CalificacionFactory(nota=Decimal("15.00"))
        docente = DocenteFactory()

        AuditoriaCalificacionService.registrar_cambio(
            calificacion=calificacion,
            accion=LogCalificacion.TipoAccion.MODIFICACION,
            valor_anterior=Decimal("12.00"),
            valor_nuevo=Decimal("15.00"),
            usuario=docente,
            ip="10.0.0.5",
            motivo="Corrección de error de digitación",
        )

        log = LogCalificacion.objects.get(calificacion=calificacion)
        assert log.accion == LogCalificacion.TipoAccion.MODIFICACION
        assert log.valor_anterior == Decimal("12.00")
        assert log.valor_nuevo == Decimal("15.00")
        assert log.motivo == "Corrección de error de digitación"

    def test_snapshots_de_texto_se_almacenan(self):
        calificacion = CalificacionFactory()
        docente = DocenteFactory()

        AuditoriaCalificacionService.registrar_cambio(
            calificacion=calificacion,
            accion=LogCalificacion.TipoAccion.CREACION,
            valor_anterior=None,
            valor_nuevo=calificacion.nota,
            usuario=docente,
        )

        log = LogCalificacion.objects.get(calificacion=calificacion)
        assert calificacion.estudiante.cedula in log.estudiante_info
        assert str(calificacion.evaluacion) in log.evaluacion_info

    def test_ip_opcional(self):
        calificacion = CalificacionFactory()
        docente = DocenteFactory()

        AuditoriaCalificacionService.registrar_cambio(
            calificacion=calificacion,
            accion=LogCalificacion.TipoAccion.CREACION,
            valor_anterior=None,
            valor_nuevo=calificacion.nota,
            usuario=docente,
        )

        log = LogCalificacion.objects.get(calificacion=calificacion)
        assert log.ip is None

    def test_multiples_logs_por_calificacion(self):
        calificacion = CalificacionFactory()
        docente = DocenteFactory()

        AuditoriaCalificacionService.registrar_cambio(
            calificacion=calificacion,
            accion=LogCalificacion.TipoAccion.CREACION,
            valor_anterior=None,
            valor_nuevo=Decimal("10.00"),
            usuario=docente,
        )
        AuditoriaCalificacionService.registrar_cambio(
            calificacion=calificacion,
            accion=LogCalificacion.TipoAccion.MODIFICACION,
            valor_anterior=Decimal("10.00"),
            valor_nuevo=Decimal("14.00"),
            usuario=docente,
        )

        assert LogCalificacion.objects.filter(calificacion=calificacion).count() == 2


class TestAuditoriaIntegracion:
    """Pruebas de integración: guardar_calificaciones genera logs automáticamente."""

    def test_crear_calificacion_genera_log_creacion(self):
        ev = EvaluacionFactory(peso=Decimal("100"))
        matricula = MatriculaFactory(paralelo=ev.paralelo)
        docente = ev.paralelo.docente

        RegistroCalificacionAppService().guardar_calificaciones(
            paralelo_id=ev.paralelo_id,
            notas_data={(matricula.estudiante_id, ev.id): "16"},
            usuario=docente,
            ip="127.0.0.1",
        )

        assert LogCalificacion.objects.filter(
            accion=LogCalificacion.TipoAccion.CREACION,
            valor_anterior=None,
            valor_nuevo=Decimal("16"),
        ).exists()

    def test_modificar_calificacion_genera_log_modificacion(self):
        cal = CalificacionFactory(nota=Decimal("10.00"))
        docente = cal.evaluacion.paralelo.docente
        MatriculaFactory(paralelo=cal.evaluacion.paralelo, estudiante=cal.estudiante)

        RegistroCalificacionAppService().guardar_calificaciones(
            paralelo_id=cal.evaluacion.paralelo_id,
            notas_data={(cal.estudiante_id, cal.evaluacion_id): "18"},
            usuario=docente,
            ip="127.0.0.1",
        )

        log = LogCalificacion.objects.get(calificacion=cal)
        assert log.accion == LogCalificacion.TipoAccion.MODIFICACION
        assert log.valor_anterior == Decimal("10.00")
        assert log.valor_nuevo == Decimal("18.00")

    def test_nota_sin_cambio_no_genera_log(self):
        cal = CalificacionFactory(nota=Decimal("15.00"))
        docente = cal.evaluacion.paralelo.docente
        MatriculaFactory(paralelo=cal.evaluacion.paralelo, estudiante=cal.estudiante)

        RegistroCalificacionAppService().guardar_calificaciones(
            paralelo_id=cal.evaluacion.paralelo_id,
            notas_data={(cal.estudiante_id, cal.evaluacion_id): "15"},
            usuario=docente,
        )

        assert LogCalificacion.objects.filter(calificacion=cal).count() == 0

    def test_nota_invalida_no_genera_log(self):
        ev = EvaluacionFactory(peso=Decimal("100"))
        matricula = MatriculaFactory(paralelo=ev.paralelo)

        RegistroCalificacionAppService().guardar_calificaciones(
            paralelo_id=ev.paralelo_id,
            notas_data={(matricula.estudiante_id, ev.id): "25"},
            usuario=ev.paralelo.docente,
        )

        assert LogCalificacion.objects.count() == 0
