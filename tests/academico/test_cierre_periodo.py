"""
Tests for the period-closing dashboard (HU28) — snapshot-based flow.

The dashboard is generated automatically when a period ends (fecha_fin
passes) or is deactivated, freezing the data as of that date. It shows
attendance rates, grade counts and averages per paralelo/asignatura, and
request summaries (justificaciones / recalificaciones).
"""

import datetime
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from apps.academico.application.services import (
    CierrePeriodoAppService,
    PeriodoAppService,
)
from apps.academico.domain.services import CierrePeriodoService
from apps.academico.domain.value_objects import ResumenSolicitudes, TasasAsistencia
from apps.academico.infrastructure.models import CierrePeriodo, Periodo
from tests.factories import (
    AsistenciaFactory,
    CalificacionFactory,
    EvaluacionFactory,
    InspectorFactory,
    MatriculaFactory,
    ParaleloFactory,
    PeriodoFactory,
    SolicitudFactory,
)

HOY = datetime.date(2026, 7, 6)


# =============================================================================
# Domain — eligibility rules (pure, no DB)
# =============================================================================


class TestElegibilidadCierre:
    def test_periodo_activo_sin_terminar_no_es_elegible(self):
        assert not CierrePeriodoService.es_elegible_cierre(
            fecha_fin=HOY + datetime.timedelta(days=10),
            fecha_actual=HOY,
            activo=True,
        )

    def test_periodo_activo_con_fecha_fin_pasada_es_elegible(self):
        assert CierrePeriodoService.es_elegible_cierre(
            fecha_fin=HOY - datetime.timedelta(days=1),
            fecha_actual=HOY,
            activo=True,
        )

    def test_periodo_desactivado_es_elegible_aunque_no_termine(self):
        assert CierrePeriodoService.es_elegible_cierre(
            fecha_fin=HOY + datetime.timedelta(days=30),
            fecha_actual=HOY,
            activo=False,
        )

    def test_el_dia_de_fecha_fin_aun_no_es_elegible(self):
        assert not CierrePeriodoService.es_elegible_cierre(
            fecha_fin=HOY, fecha_actual=HOY, activo=True
        )

    def test_motivo_fin_periodo_corta_en_fecha_fin(self):
        fecha_fin = HOY - datetime.timedelta(days=5)
        motivo, corte = CierrePeriodoService.determinar_motivo_cierre(fecha_fin, HOY, activo=True)
        assert motivo == "fin_periodo"
        assert corte == fecha_fin

    def test_motivo_desactivacion_corta_en_fecha_actual(self):
        motivo, corte = CierrePeriodoService.determinar_motivo_cierre(
            HOY + datetime.timedelta(days=20), HOY, activo=False
        )
        assert motivo == "desactivacion"
        assert corte == HOY

    def test_sin_motivo_si_periodo_activo_vigente(self):
        motivo, corte = CierrePeriodoService.determinar_motivo_cierre(
            HOY + datetime.timedelta(days=20), HOY, activo=True
        )
        assert motivo is None
        assert corte is None


# =============================================================================
# Domain — metric math (pure, no DB)
# =============================================================================


class TestCalculoMetricas:
    def test_tasas_asistencia(self):
        tasas = CierrePeriodoService.calcular_tasas_asistencia(
            presentes=6, ausentes=3, justificados=1
        )
        assert isinstance(tasas, TasasAsistencia)
        assert tasas.total == 10
        assert tasas.tasa_presentes == Decimal("60.0")
        assert tasas.tasa_ausentes == Decimal("30.0")
        assert tasas.tasa_justificados == Decimal("10.0")

    def test_tasas_asistencia_sin_registros(self):
        tasas = CierrePeriodoService.calcular_tasas_asistencia(
            presentes=0, ausentes=0, justificados=0
        )
        assert tasas.total == 0
        assert tasas.tasa_presentes == Decimal("0.0")

    def test_resumen_solicitudes(self):
        resumen = CierrePeriodoService.resumir_solicitudes(
            aprobadas=2, rechazadas=1, pendientes=3, total_estudiantes=4
        )
        assert isinstance(resumen, ResumenSolicitudes)
        assert resumen.total == 6
        assert resumen.promedio_por_estudiante == Decimal("1.50")

    def test_resumen_solicitudes_sin_estudiantes(self):
        resumen = CierrePeriodoService.resumir_solicitudes(
            aprobadas=1, rechazadas=0, pendientes=0, total_estudiantes=0
        )
        assert resumen.promedio_por_estudiante == Decimal("0.00")


# =============================================================================
# Application — automatic snapshot generation
# =============================================================================


@pytest.mark.django_db
class TestGeneracionAutomaticaSnapshot:
    def test_desactivar_periodo_genera_snapshot_con_fecha_de_hoy(self):
        inspector = InspectorFactory()
        periodo = PeriodoFactory(
            activo=True,
            fecha_inicio=datetime.date.today() - datetime.timedelta(days=60),
            fecha_fin=datetime.date.today() + datetime.timedelta(days=30),
        )
        MatriculaFactory(paralelo=ParaleloFactory(periodo=periodo))

        PeriodoAppService().desactivar(periodo_id=periodo.pk, usuario_id=inspector.pk)

        snapshot = CierrePeriodo.objects.get(periodo=periodo)
        assert snapshot.motivo == "desactivacion"
        assert snapshot.fecha_corte == datetime.date.today()
        assert snapshot.datos["version"] == CierrePeriodoAppService.VERSION_DATOS
        assert snapshot.datos["total_estudiantes"] == 1

    def test_snapshot_lazy_por_fecha_fin_pasada(self):
        periodo = PeriodoFactory(
            activo=True,
            fecha_inicio=datetime.date.today() - datetime.timedelta(days=120),
            fecha_fin=datetime.date.today() - datetime.timedelta(days=3),
        )
        MatriculaFactory(paralelo=ParaleloFactory(periodo=periodo))

        snapshot = CierrePeriodoAppService().obtener_o_generar_snapshot(periodo)

        assert snapshot is not None
        assert snapshot.motivo == "fin_periodo"
        assert snapshot.fecha_corte == periodo.fecha_fin

    def test_no_genera_snapshot_para_periodo_activo_vigente(self):
        periodo = PeriodoFactory(
            activo=True,
            fecha_fin=datetime.date.today() + datetime.timedelta(days=30),
        )

        snapshot = CierrePeriodoAppService().obtener_o_generar_snapshot(periodo)

        assert snapshot is None
        assert not CierrePeriodo.objects.filter(periodo=periodo).exists()

    def test_activar_otro_periodo_genera_snapshot_del_anterior(self):
        inspector = InspectorFactory()
        anterior = PeriodoFactory(
            activo=True,
            fecha_fin=datetime.date.today() + datetime.timedelta(days=10),
        )
        nuevo = PeriodoFactory(
            activo=False,
            tipo_licencia=anterior.tipo_licencia,
            nombre="Nuevo periodo",
            fecha_inicio=datetime.date.today(),
            fecha_fin=datetime.date.today() + datetime.timedelta(days=180),
        )

        PeriodoAppService().activar(
            periodo_id=nuevo.pk,
            usuario_id=inspector.pk,
            confirmar_desactivacion=True,
        )

        assert CierrePeriodo.objects.filter(periodo=anterior).exists()
        assert not CierrePeriodo.objects.filter(periodo=nuevo).exists()

    def test_reactivar_periodo_elimina_su_snapshot(self):
        inspector = InspectorFactory()
        periodo = PeriodoFactory(
            activo=True,
            fecha_fin=datetime.date.today() + datetime.timedelta(days=30),
        )
        service = PeriodoAppService()
        service.desactivar(periodo_id=periodo.pk, usuario_id=inspector.pk)
        assert CierrePeriodo.objects.filter(periodo=periodo).exists()

        service.activar(periodo_id=periodo.pk, usuario_id=inspector.pk)

        assert not CierrePeriodo.objects.filter(periodo=periodo).exists()

    def test_extender_periodo_vencido_elimina_snapshot_fin_periodo(self):
        inspector = InspectorFactory()
        periodo = PeriodoFactory(
            activo=True,
            fecha_inicio=datetime.date.today() - datetime.timedelta(days=120),
            fecha_fin=datetime.date.today() - datetime.timedelta(days=3),
        )
        CierrePeriodoAppService().obtener_o_generar_snapshot(periodo)
        assert CierrePeriodo.objects.filter(periodo=periodo).exists()

        PeriodoAppService().actualizar(
            periodo_id=periodo.pk,
            nombre=periodo.nombre,
            fecha_inicio=periodo.fecha_inicio,
            fecha_fin=datetime.date.today() + datetime.timedelta(days=30),
            usuario_id=inspector.pk,
        )

        assert not CierrePeriodo.objects.filter(periodo=periodo).exists()

    def test_cambiar_fecha_fin_pasada_regenera_snapshot_con_nuevo_corte(self):
        inspector = InspectorFactory()
        periodo = PeriodoFactory(
            activo=True,
            fecha_inicio=datetime.date.today() - datetime.timedelta(days=120),
            fecha_fin=datetime.date.today() - datetime.timedelta(days=10),
        )
        CierrePeriodoAppService().obtener_o_generar_snapshot(periodo)

        nueva_fecha_fin = datetime.date.today() - datetime.timedelta(days=3)
        PeriodoAppService().actualizar(
            periodo_id=periodo.pk,
            nombre=periodo.nombre,
            fecha_inicio=periodo.fecha_inicio,
            fecha_fin=nueva_fecha_fin,
            usuario_id=inspector.pk,
        )

        periodo = Periodo.objects.get(pk=periodo.pk)
        snapshot = CierrePeriodoAppService().obtener_o_generar_snapshot(periodo)
        assert snapshot.fecha_corte == nueva_fecha_fin

    def test_editar_periodo_desactivado_conserva_su_snapshot(self):
        inspector = InspectorFactory()
        periodo = PeriodoFactory(
            activo=True,
            fecha_fin=datetime.date.today() + datetime.timedelta(days=30),
        )
        PeriodoAppService().desactivar(periodo_id=periodo.pk, usuario_id=inspector.pk)
        original = CierrePeriodo.objects.get(periodo=periodo)

        PeriodoAppService().actualizar(
            periodo_id=periodo.pk,
            nombre=periodo.nombre,
            fecha_inicio=periodo.fecha_inicio,
            fecha_fin=datetime.date.today() + datetime.timedelta(days=90),
            usuario_id=inspector.pk,
        )

        snapshot = CierrePeriodo.objects.get(periodo=periodo)
        assert snapshot.pk == original.pk
        assert snapshot.motivo == "desactivacion"
        assert snapshot.fecha_corte == original.fecha_corte

    def test_snapshot_version_vieja_se_regenera_preservando_corte(self):
        inspector = InspectorFactory()
        periodo = PeriodoFactory(
            activo=True,
            fecha_fin=datetime.date.today() + datetime.timedelta(days=30),
        )
        PeriodoAppService().desactivar(periodo_id=periodo.pk, usuario_id=inspector.pk)
        original = CierrePeriodo.objects.get(periodo=periodo)
        CierrePeriodo.objects.filter(pk=original.pk).update(datos={"version": 1})
        periodo = Periodo.objects.get(pk=periodo.pk)

        snapshot = CierrePeriodoAppService().obtener_o_generar_snapshot(periodo)

        assert snapshot.datos["version"] == CierrePeriodoAppService.VERSION_DATOS
        assert snapshot.motivo == "desactivacion"
        assert snapshot.fecha_corte == original.fecha_corte


# =============================================================================
# Application — metric content and freezing at fecha_corte
# =============================================================================


@pytest.mark.django_db
class TestContenidoSnapshot:
    def _escenario_completo(self):
        """Period with 1 student, 2 asistencias, 1 calificación and 2 solicitudes."""
        hoy = datetime.date.today()
        periodo = PeriodoFactory(
            activo=True,
            fecha_inicio=hoy - datetime.timedelta(days=60),
            fecha_fin=hoy + datetime.timedelta(days=30),
        )
        paralelo = ParaleloFactory(periodo=periodo)
        matricula = MatriculaFactory(paralelo=paralelo)
        estudiante = matricula.estudiante

        presente = AsistenciaFactory(
            estudiante=estudiante,
            paralelo=paralelo,
            fecha=hoy - datetime.timedelta(days=10),
            estado="presente",
        )
        AsistenciaFactory(
            estudiante=estudiante,
            paralelo=paralelo,
            fecha=hoy - datetime.timedelta(days=9),
            estado="ausente",
        )
        calificacion = CalificacionFactory(
            evaluacion=EvaluacionFactory(paralelo=paralelo),
            estudiante=estudiante,
        )
        SolicitudFactory(
            tipo="justificacion",
            estudiante=estudiante,
            asistencia=presente,
            estado="aprobada",
        )
        SolicitudFactory(
            tipo="rectificacion",
            estudiante=estudiante,
            calificacion=calificacion,
            estado="pendiente",
        )
        return periodo, paralelo

    def test_snapshot_roundtrip_con_metricas_completas(self):
        inspector = InspectorFactory()
        periodo, paralelo = self._escenario_completo()
        PeriodoAppService().desactivar(periodo_id=periodo.pk, usuario_id=inspector.pk)

        dashboard = CierrePeriodoAppService().obtener_dashboard_desde_snapshot(periodo.cierre)

        asistencias = dashboard["asistencias"]
        assert isinstance(asistencias, TasasAsistencia)
        assert asistencias.total == 2
        assert asistencias.tasa_presentes == Decimal("50.0")
        assert asistencias.tasa_ausentes == Decimal("50.0")

        calificaciones = dashboard["calificaciones"]
        assert calificaciones["total"] == 1
        assert calificaciones["por_paralelo"][0]["paralelo_id"] == paralelo.pk
        assert calificaciones["por_paralelo"][0]["asignatura_id"] == paralelo.asignatura_id
        # CalificacionFactory default nota is 8.50; averages travel as str
        assert calificaciones["por_paralelo"][0]["promedio"] == "8.50"
        assert calificaciones["promedio_general"] == "8.50"

        justificaciones = dashboard["solicitudes"]["justificaciones"]
        assert isinstance(justificaciones, ResumenSolicitudes)
        assert justificaciones.total == 1
        assert justificaciones.aprobadas == 1
        assert justificaciones.promedio_por_estudiante == Decimal("1.00")

        recalificaciones = dashboard["solicitudes"]["recalificaciones"]
        assert recalificaciones.total == 1
        assert recalificaciones.pendientes == 1

        assert dashboard["total_estudiantes"] == 1

    def test_promedio_del_curso_por_paralelo_y_global(self):
        """HU28: the dashboard reports grade AVERAGES, not just counts."""
        hoy = datetime.date.today()
        periodo = PeriodoFactory(
            activo=True,
            fecha_inicio=hoy - datetime.timedelta(days=60),
            fecha_fin=hoy + datetime.timedelta(days=30),
        )
        paralelo = ParaleloFactory(periodo=periodo)
        evaluacion = EvaluacionFactory(paralelo=paralelo)
        m1 = MatriculaFactory(paralelo=paralelo)
        m2 = MatriculaFactory(paralelo=paralelo)
        CalificacionFactory(evaluacion=evaluacion, estudiante=m1.estudiante, nota=Decimal("8.50"))
        CalificacionFactory(evaluacion=evaluacion, estudiante=m2.estudiante, nota=Decimal("11.50"))

        dashboard = CierrePeriodoAppService().obtener_dashboard_cierre(periodo.pk, hoy)

        assert dashboard["calificaciones"]["por_paralelo"][0]["promedio"] == "10.00"
        assert dashboard["calificaciones"]["promedio_general"] == "10.00"
        assert dashboard["calificaciones"]["total"] == 2

    def test_fin_periodo_congela_asistencias_en_fecha_corte(self):
        hoy = datetime.date.today()
        periodo = PeriodoFactory(
            activo=True,
            fecha_inicio=hoy - datetime.timedelta(days=120),
            fecha_fin=hoy - datetime.timedelta(days=3),
        )
        paralelo = ParaleloFactory(periodo=periodo)
        matricula = MatriculaFactory(paralelo=paralelo)
        AsistenciaFactory(
            estudiante=matricula.estudiante,
            paralelo=paralelo,
            fecha=hoy - datetime.timedelta(days=10),
            estado="presente",
        )
        # Recorded after the period ended: must NOT enter the frozen snapshot.
        AsistenciaFactory(
            estudiante=matricula.estudiante,
            paralelo=paralelo,
            fecha=hoy - datetime.timedelta(days=1),
            estado="presente",
        )

        snapshot = CierrePeriodoAppService().obtener_o_generar_snapshot(periodo)

        assert snapshot.datos["asistencias"]["total"] == 1


# =============================================================================
# Presentation — dashboard visibility and context
# =============================================================================


@pytest.mark.django_db
class TestCierrePeriodoDashboardView:
    url = reverse("academico:cierre_periodo_dashboard")

    def _login_inspector(self) -> Client:
        client = Client()
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        return client

    def test_sin_periodos_muestra_estado_vacio(self):
        response = self._login_inspector().get(self.url)

        assert response.status_code == 200
        assert response.context["sin_periodos"] is True

    def test_periodo_activo_vigente_muestra_aviso_de_dashboard_pendiente(self):
        """Business rule: active periods ARE listed; an ongoing one shows the
        availability date and a shortcut to the Rendimiento module."""
        periodo = PeriodoFactory(
            activo=True,
            fecha_fin=datetime.date.today() + datetime.timedelta(days=30),
        )
        response = self._login_inspector().get(self.url)

        assert response.status_code == 200
        assert periodo in response.context["periodos"]
        assert response.context["dashboard_pendiente"] is True
        assert response.context["fecha_disponible"] == periodo.fecha_fin + datetime.timedelta(
            days=1
        )
        contenido = response.content.decode("utf-8")
        assert "estará visible a partir del" in contenido
        assert reverse("academico:dashboard_rendimiento") in contenido
        # No snapshot is generated for a period that has not closed yet
        assert not CierrePeriodo.objects.filter(periodo=periodo).exists()

    def test_periodo_terminado_por_fecha_muestra_dashboard(self):
        periodo = PeriodoFactory(
            activo=True,
            fecha_inicio=datetime.date.today() - datetime.timedelta(days=120),
            fecha_fin=datetime.date.today() - datetime.timedelta(days=1),
        )
        MatriculaFactory(paralelo=ParaleloFactory(periodo=periodo))

        response = self._login_inspector().get(self.url)

        assert response.status_code == 200
        assert response.context["periodo_seleccionado"] == periodo
        assert response.context["snapshot"].motivo == "fin_periodo"
        assert isinstance(response.context["asistencias"], TasasAsistencia)
        assert set(response.context["solicitudes"]) == {"justificaciones", "recalificaciones"}
        assert response.context["calificaciones"]["total"] == 0

    def test_periodo_desactivado_muestra_dashboard(self):
        inspector = InspectorFactory()
        periodo = PeriodoFactory(
            activo=True,
            fecha_fin=datetime.date.today() + datetime.timedelta(days=30),
        )
        MatriculaFactory(paralelo=ParaleloFactory(periodo=periodo))
        PeriodoAppService().desactivar(periodo_id=periodo.pk, usuario_id=inspector.pk)

        response = self._login_inspector().get(self.url)

        assert response.status_code == 200
        assert response.context["snapshot"].motivo == "desactivacion"

    def test_periodo_inactivo_nunca_activado_no_se_lista(self):
        PeriodoFactory(
            activo=False,
            fecha_fin=datetime.date.today() + datetime.timedelta(days=30),
        )
        response = self._login_inspector().get(self.url)

        assert response.status_code == 200
        assert response.context["sin_periodos"] is True

    def test_datos_de_graficas_se_serializan_con_json_script(self):
        """Chart payloads go through json_script (HTML-escaped), never |safe."""
        periodo = PeriodoFactory(
            activo=True,
            fecha_inicio=datetime.date.today() - datetime.timedelta(days=120),
            fecha_fin=datetime.date.today() - datetime.timedelta(days=1),
        )
        MatriculaFactory(paralelo=ParaleloFactory(periodo=periodo))

        response = self._login_inspector().get(self.url)

        contenido = response.content.decode("utf-8")
        assert 'id="datos-calificaciones"' in contenido
        assert 'id="datos-asistencias"' in contenido
        assert "calificaciones_json" not in response.context

    def test_modulo_visible_en_sidebar_y_dashboard_de_inicio(self):
        """Business rule: the module appears in the sidebar AND the home
        dashboard section, even when no period has closed yet."""
        response = self._login_inspector().get(reverse("usuarios:dashboard"))

        assert response.status_code == 200
        contenido = response.content.decode("utf-8")
        assert contenido.count(self.url) >= 2  # sidebar link + dashboard card
        assert "Cierre de Período" in contenido

    def test_docente_no_puede_acceder(self):
        from tests.factories import DocenteFactory

        client = Client()
        docente = DocenteFactory()
        docente.save()
        client.force_login(docente)
        response = client.get(self.url)

        assert response.status_code in (302, 403)
