"""Tests for HU23 — Dashboard de Rendimiento Académico.

Covers:
  - RendimientoAcademicoService (pure domain, no DB)
  - DashboardRendimientoAppService (integration: DB fixtures)
  - DashboardRendimientoView (access control, filtros, bienvenida, resumen)
  - DashboardRendimientoAPIView (JSON endpoint: tendencia y métricas)
"""

import json
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.academico.domain.services import RendimientoAcademicoService
from apps.academico.infrastructure.models import Matricula
from apps.asistencia.infrastructure.models import Asistencia
from apps.calificaciones.infrastructure.models import Evaluacion
from tests.factories import (
    AsistenciaFactory,
    CalificacionFactory,
    EstudianteFactory,
    EvaluacionFactory,
    InspectorFactory,
    MatriculaFactory,
    ParaleloFactory,
    PeriodoFactory,
    SecretariaFactory,
    TipoLicenciaFactory,
    DocenteFactory,
)

URL = reverse("academico:dashboard_rendimiento")
URL_API = reverse("academico:dashboard_rendimiento_api")


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════


def _matricular(estudiante, paralelo):
    """Crea una Matricula activa para el estudiante en el paralelo."""
    m = MatriculaFactory(estudiante=estudiante, paralelo=paralelo, estado=Matricula.Estado.ACTIVA)
    return m


def _calificar(evaluacion, estudiante, nota):
    """Crea una Calificacion para el estudiante en la evaluacion."""
    return CalificacionFactory(
        evaluacion=evaluacion, estudiante=estudiante, nota=Decimal(str(nota))
    )


def _asistencia(estudiante, paralelo, estado=Asistencia.Estado.PRESENTE, fecha=None):
    kwargs = {"estudiante": estudiante, "paralelo": paralelo, "estado": estado}
    if fecha is not None:
        kwargs["fecha"] = fecha
    return AsistenciaFactory(**kwargs)


# ══════════════════════════════════════════════════════════════════════════════
# 1. RendimientoAcademicoService — servicio de dominio puro (sin DB)
# ══════════════════════════════════════════════════════════════════════════════


class TestRendimientoAcademicoServiceCalcPromedio:

    def test_lista_vacia_retorna_cero(self):
        assert RendimientoAcademicoService.calcular_promedio_paralelo([]) == Decimal("0.00")

    def test_un_elemento(self):
        assert RendimientoAcademicoService.calcular_promedio_paralelo(
            [Decimal("14.00")]
        ) == Decimal("14.00")

    def test_promedio_correcto_dos_decimales(self):
        notas = [Decimal("15.00"), Decimal("17.00"), Decimal("13.00")]
        resultado = RendimientoAcademicoService.calcular_promedio_paralelo(notas)
        assert resultado == Decimal("15.00")

    def test_redondeo_a_dos_decimales(self):
        notas = [Decimal("10.00"), Decimal("11.00"), Decimal("12.00")]
        resultado = RendimientoAcademicoService.calcular_promedio_paralelo(notas)
        assert resultado == Decimal("11.00")


class TestRendimientoAcademicoServiceTasaAprobacion:

    def test_total_cero_retorna_cero(self):
        assert RendimientoAcademicoService.calcular_tasa_aprobacion(0, 0) == Decimal("0.0")

    def test_todos_aprobados(self):
        assert RendimientoAcademicoService.calcular_tasa_aprobacion(10, 10) == Decimal("100.0")

    def test_ninguno_aprobado(self):
        assert RendimientoAcademicoService.calcular_tasa_aprobacion(0, 5) == Decimal("0.0")

    def test_mitad_aprobados(self):
        assert RendimientoAcademicoService.calcular_tasa_aprobacion(1, 2) == Decimal("50.0")

    def test_un_decimal_en_resultado(self):
        resultado = RendimientoAcademicoService.calcular_tasa_aprobacion(1, 3)
        assert resultado == Decimal("33.3")


class TestRendimientoAcademicoServicePorcentajeAsistencia:

    def test_sin_registros_retorna_cero(self):
        assert RendimientoAcademicoService.calcular_porcentaje_asistencia(0, 0) == Decimal("0.0")

    def test_todos_presentes(self):
        assert RendimientoAcademicoService.calcular_porcentaje_asistencia(10, 10) == Decimal(
            "100.0"
        )

    def test_ninguno_presente(self):
        assert RendimientoAcademicoService.calcular_porcentaje_asistencia(0, 10) == Decimal("0.0")

    def test_noventa_por_ciento(self):
        assert RendimientoAcademicoService.calcular_porcentaje_asistencia(9, 10) == Decimal("90.0")


class TestRendimientoAcademicoServiceClasificarEstudiante:

    def test_nota_exactamente_16_es_aprobado(self):
        assert RendimientoAcademicoService.clasificar_estudiante(Decimal("16.00")) == "aprobado"

    def test_nota_mayor_16_es_aprobado(self):
        assert RendimientoAcademicoService.clasificar_estudiante(Decimal("18.50")) == "aprobado"

    def test_nota_menor_16_es_reprobado(self):
        assert RendimientoAcademicoService.clasificar_estudiante(Decimal("15.99")) == "reprobado"

    def test_nota_cero_es_reprobado(self):
        assert RendimientoAcademicoService.clasificar_estudiante(Decimal("0.00")) == "reprobado"


class TestRendimientoAcademicoServicePromediosPonderados:

    def test_lista_vacia_retorna_vacia(self):
        resultado = RendimientoAcademicoService.calcular_promedios_por_estudiante([])
        assert resultado == []

    def test_estudiante_sin_notas_retorna_cero(self):
        resultado = RendimientoAcademicoService.calcular_promedios_por_estudiante([(1, [])])
        assert resultado == [(1, Decimal("0.00"))]

    def test_ponderacion_correcta(self):
        # nota=18, peso=25 → contribución = 18 * 25/100 = 4.50
        # nota=14, peso=75 → contribución = 14 * 75/100 = 10.50
        # total ponderado = 15.00
        resultado = RendimientoAcademicoService.calcular_promedios_por_estudiante(
            [(7, [(Decimal("18.00"), Decimal("25.00")), (Decimal("14.00"), Decimal("75.00"))])]
        )
        assert len(resultado) == 1
        est_id, promedio = resultado[0]
        assert est_id == 7
        assert promedio == Decimal("15.00")

    def test_multiples_estudiantes(self):
        datos = [
            (1, [(Decimal("20.00"), Decimal("100.00"))]),
            (2, [(Decimal("10.00"), Decimal("100.00"))]),
        ]
        resultado = dict(RendimientoAcademicoService.calcular_promedios_por_estudiante(datos))
        assert resultado[1] == Decimal("20.00")
        assert resultado[2] == Decimal("10.00")


# ══════════════════════════════════════════════════════════════════════════════
# 2. DashboardRendimientoAppService — integración con DB
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestDashboardRendimientoAppServiceMetricas:

    def _setup_paralelo(self):
        """Crea un período + paralelo con 2 estudiantes matriculados."""
        from apps.academico.application.services import DashboardRendimientoAppService

        periodo = PeriodoFactory(activo=True)
        paralelo = ParaleloFactory(periodo=periodo)
        e1 = EstudianteFactory()
        e2 = EstudianteFactory()
        _matricular(e1, paralelo)
        _matricular(e2, paralelo)
        svc = DashboardRendimientoAppService()
        return periodo, paralelo, e1, e2, svc

    def test_paralelo_sin_notas_promedio_cero(self):
        from apps.academico.application.services import DashboardRendimientoAppService

        periodo = PeriodoFactory(activo=True)
        paralelo = ParaleloFactory(periodo=periodo)
        e = EstudianteFactory()
        _matricular(e, paralelo)
        svc = DashboardRendimientoAppService()

        metricas = svc.obtener_metricas_por_periodo(periodo.id)
        assert len(metricas) == 1
        m = metricas[0]
        assert m.promedio_general == Decimal("0.00")
        assert m.total_estudiantes == 1

    def test_aprobados_y_reprobados_contados_correctamente(self):
        periodo, paralelo, e1, e2, svc = self._setup_paralelo()
        ev = EvaluacionFactory(paralelo=paralelo, peso=Decimal("100.00"))
        _calificar(ev, e1, "18.00")  # aprobado
        _calificar(ev, e2, "12.00")  # reprobado

        metricas = svc.obtener_metricas_por_periodo(periodo.id)
        m = metricas[0]
        assert m.estudiantes_aprobados == 1
        assert m.estudiantes_reprobados == 1
        assert m.tasa_aprobacion == Decimal("50.0")
        assert m.tasa_reprobacion == Decimal("50.0")

    def test_porcentaje_asistencia_incluye_justificado(self):
        periodo, paralelo, e1, e2, svc = self._setup_paralelo()
        _asistencia(e1, paralelo, Asistencia.Estado.PRESENTE)
        _asistencia(e2, paralelo, Asistencia.Estado.JUSTIFICADO)

        metricas = svc.obtener_metricas_por_periodo(periodo.id)
        m = metricas[0]
        assert m.porcentaje_asistencia == Decimal("100.0")

    def test_asistencia_ausente_no_cuenta(self):
        periodo, paralelo, e1, e2, svc = self._setup_paralelo()
        _asistencia(e1, paralelo, Asistencia.Estado.PRESENTE)
        _asistencia(e2, paralelo, Asistencia.Estado.AUSENTE)

        metricas = svc.obtener_metricas_por_periodo(periodo.id)
        m = metricas[0]
        assert m.porcentaje_asistencia == Decimal("50.0")

    def test_filtro_por_asignatura(self):
        from apps.academico.application.services import DashboardRendimientoAppService

        periodo = PeriodoFactory(activo=True)
        p1 = ParaleloFactory(periodo=periodo)
        p2 = ParaleloFactory(periodo=periodo)
        svc = DashboardRendimientoAppService()

        metricas = svc.obtener_metricas_por_periodo(periodo.id, asignatura_id=p1.asignatura_id)
        assert all(m.paralelo_id == p1.id for m in metricas)
        assert not any(m.paralelo_id == p2.id for m in metricas)

    def test_filtro_por_paralelo_especifico(self):
        from apps.academico.application.services import DashboardRendimientoAppService

        periodo = PeriodoFactory(activo=True)
        p1 = ParaleloFactory(periodo=periodo)
        ParaleloFactory(periodo=periodo)
        svc = DashboardRendimientoAppService()

        metricas = svc.obtener_metricas_por_periodo(periodo.id, paralelo_id=p1.id)
        assert len(metricas) == 1
        assert metricas[0].paralelo_id == p1.id

    def test_periodo_sin_paralelos_retorna_lista_vacia(self):
        from apps.academico.application.services import DashboardRendimientoAppService

        periodo = PeriodoFactory(activo=True)
        svc = DashboardRendimientoAppService()
        assert svc.obtener_metricas_por_periodo(periodo.id) == []

    def test_estudiantes_en_curso_cuando_no_hay_notas(self):
        from apps.academico.application.services import DashboardRendimientoAppService

        periodo = PeriodoFactory(activo=True)
        paralelo = ParaleloFactory(periodo=periodo)
        for _ in range(3):
            e = EstudianteFactory()
            _matricular(e, paralelo)
        svc = DashboardRendimientoAppService()

        metricas = svc.obtener_metricas_por_periodo(periodo.id)
        m = metricas[0]
        assert m.total_estudiantes == 3
        assert m.estudiantes_en_curso == 3
        assert m.estudiantes_aprobados == 0
        assert m.estudiantes_reprobados == 0


@pytest.mark.django_db
class TestDashboardRendimientoAppServiceTendencia:

    def test_tendencia_retorna_evaluaciones_ordenadas(self):
        from apps.academico.application.services import DashboardRendimientoAppService

        paralelo = ParaleloFactory()
        e = EstudianteFactory()
        _matricular(e, paralelo)
        ev1 = EvaluacionFactory(
            paralelo=paralelo,
            tipo=Evaluacion.TipoEvaluacion.PARCIAL_1,
            peso=Decimal("50.00"),
        )
        ev2 = EvaluacionFactory(
            paralelo=paralelo,
            tipo=Evaluacion.TipoEvaluacion.EXAMEN_FINAL,
            peso=Decimal("50.00"),
        )
        _calificar(ev1, e, "14.00")
        _calificar(ev2, e, "18.00")

        svc = DashboardRendimientoAppService()
        tendencia = svc.obtener_tendencia_parciales(paralelo.id)

        assert len(tendencia) == 2
        tipos = [t["tipo"] for t in tendencia]
        assert tipos.index("parcial1") < tipos.index("examen_final")

    def test_tendencia_promedio_correcto(self):
        from apps.academico.application.services import DashboardRendimientoAppService

        paralelo = ParaleloFactory()
        e1 = EstudianteFactory()
        e2 = EstudianteFactory()
        ev = EvaluacionFactory(
            paralelo=paralelo,
            tipo=Evaluacion.TipoEvaluacion.PARCIAL_1,
            peso=Decimal("100.00"),
        )
        _calificar(ev, e1, "16.00")
        _calificar(ev, e2, "14.00")

        svc = DashboardRendimientoAppService()
        tendencia = svc.obtener_tendencia_parciales(paralelo.id)

        assert len(tendencia) == 1
        assert tendencia[0]["promedio"] == 15.0

    def test_tendencia_paralelo_sin_evaluaciones_retorna_vacia(self):
        from apps.academico.application.services import DashboardRendimientoAppService

        paralelo = ParaleloFactory()
        svc = DashboardRendimientoAppService()
        assert svc.obtener_tendencia_parciales(paralelo.id) == []

    def test_tendencia_parcial5_label_y_orden(self):
        """HU34: parcial5 (antes proyecto) sale como "Parcial 5" antes del examen."""
        from apps.academico.application.services import DashboardRendimientoAppService

        paralelo = ParaleloFactory()
        e = EstudianteFactory()
        _matricular(e, paralelo)
        ev5 = EvaluacionFactory(
            paralelo=paralelo,
            tipo=Evaluacion.TipoEvaluacion.PARCIAL_5,
            peso=Decimal("50.00"),
        )
        ev_final = EvaluacionFactory(
            paralelo=paralelo,
            tipo=Evaluacion.TipoEvaluacion.EXAMEN_FINAL,
            peso=Decimal("50.00"),
        )
        _calificar(ev5, e, "12.00")
        _calificar(ev_final, e, "18.00")

        svc = DashboardRendimientoAppService()
        tendencia = svc.obtener_tendencia_parciales(paralelo.id)

        tipos = [t["tipo"] for t in tendencia]
        assert tipos.index("parcial5") < tipos.index("examen_final")
        etiquetas = [t["evaluacion"] for t in tendencia]
        assert "Parcial 5" in etiquetas
        assert "Proyecto" not in etiquetas


# ══════════════════════════════════════════════════════════════════════════════
# 3. DashboardRendimientoView — control de acceso
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestDashboardRendimientoViewAcceso:

    def test_anonimo_redirige_a_login(self, client):
        resp = client.get(URL)
        assert resp.status_code == 302
        assert "/login/" in resp.url

    @pytest.mark.parametrize("factory_cls", [EstudianteFactory, DocenteFactory])
    def test_roles_no_autorizados_retornan_403(self, client, factory_cls):
        user = factory_cls()
        user.save()
        client.force_login(user)
        resp = client.get(URL)
        assert resp.status_code == 403

    def test_inspector_puede_acceder(self, client):
        user = InspectorFactory()
        user.save()
        client.force_login(user)
        resp = client.get(URL)
        assert resp.status_code == 200

    def test_secretaria_puede_acceder(self, client):
        user = SecretariaFactory()
        user.save()
        client.force_login(user)
        resp = client.get(URL)
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# 4. DashboardRendimientoView — estado de bienvenida
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestDashboardRendimientoViewBienvenida:

    def _login_inspector(self, client):
        user = InspectorFactory()
        user.save()
        client.force_login(user)

    def test_sin_tipo_licencia_muestra_bienvenida(self, client):
        self._login_inspector(client)
        resp = client.get(URL)
        assert resp.status_code == 200
        assert resp.context["bienvenida"] is True

    def test_bienvenida_cards_incluyen_tipo_licencias_activas(self, client):
        tl = TipoLicenciaFactory(activo=True)
        self._login_inspector(client)
        resp = client.get(URL)
        ids_en_cards = [c["obj"].id for c in resp.context["bienvenida_cards"]]
        assert tl.id in ids_en_cards

    def test_tipo_licencia_invalido_redirige(self, client):
        self._login_inspector(client)
        resp = client.get(URL + "?tipo_licencia=99999")
        assert resp.status_code == 302

    def test_tipo_licencia_no_numerico_redirige(self, client):
        self._login_inspector(client)
        resp = client.get(URL + "?tipo_licencia=abc")
        assert resp.status_code == 302


# ══════════════════════════════════════════════════════════════════════════════
# 5. DashboardRendimientoView — modo dashboard con filtros
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestDashboardRendimientoViewFiltros:

    def _setup(self):
        tl = TipoLicenciaFactory(activo=True)
        periodo = PeriodoFactory(activo=True, tipo_licencia=tl)
        paralelo = ParaleloFactory(periodo=periodo, tipo_licencia=tl)
        user = InspectorFactory()
        user.save()
        return tl, periodo, paralelo, user

    def test_con_tipo_licencia_no_es_bienvenida(self, client):
        tl, periodo, paralelo, user = self._setup()
        client.force_login(user)
        resp = client.get(URL + f"?tipo_licencia={tl.id}")
        assert resp.status_code == 200
        assert resp.context["bienvenida"] is False

    def test_dentro_de_una_licencia_no_hay_tabs_de_tipo_licencia(self, client):
        """Issue 13a: ya adentro de una licencia, el selector de tipo de
        licencia es redundante; solo quedan los demás filtros. Para cambiar
        de licencia se vuelve por el breadcrumb."""
        tl, periodo, paralelo, user = self._setup()
        otra = TipoLicenciaFactory(activo=True)  # una segunda licencia
        client.force_login(user)

        resp = client.get(URL + f"?tipo_licencia={tl.id}")
        contenido = resp.content.decode("utf-8")

        # El breadcrumb de regreso al selector sí sigue presente.
        assert "Dashboard de Rendimiento" in contenido
        # Pero no hay tabs que enlacen a la otra licencia dentro del dashboard.
        assert f"?tipo_licencia={otra.pk}" not in contenido

    def test_tipo_licencia_seleccionado_en_contexto(self, client):
        tl, periodo, paralelo, user = self._setup()
        client.force_login(user)
        resp = client.get(URL + f"?tipo_licencia={tl.id}&periodo={periodo.id}")
        assert resp.context["tipo_licencia_seleccionado"].id == tl.id

    def test_metricas_presentes_con_periodo(self, client):
        tl, periodo, paralelo, user = self._setup()
        client.force_login(user)
        resp = client.get(URL + f"?tipo_licencia={tl.id}&periodo={periodo.id}")
        assert "metricas" in resp.context

    def test_filtro_paralelo_pasa_a_servicio(self, client):
        tl, periodo, paralelo, user = self._setup()
        client.force_login(user)
        resp = client.get(
            URL + f"?tipo_licencia={tl.id}&periodo={periodo.id}&paralelo={paralelo.id}"
        )
        assert resp.status_code == 200
        metricas = resp.context["metricas"]
        if metricas:
            assert all(m.paralelo_id == paralelo.id for m in metricas)

    def test_filtro_inasistencia_invalido_ignorado(self, client):
        tl, periodo, paralelo, user = self._setup()
        client.force_login(user)
        resp = client.get(URL + f"?tipo_licencia={tl.id}&periodo={periodo.id}&inasistencia=999")
        assert resp.status_code == 200
        assert resp.context["inasistencia_seleccionada"] == ""

    def test_paralelo_de_otro_periodo_ignorado(self, client):
        tl, periodo, paralelo, user = self._setup()
        otro_periodo = PeriodoFactory(activo=False, tipo_licencia=tl)
        paralelo_ajeno = ParaleloFactory(periodo=otro_periodo, tipo_licencia=tl)
        client.force_login(user)
        resp = client.get(
            URL + f"?tipo_licencia={tl.id}&periodo={periodo.id}&paralelo={paralelo_ajeno.id}"
        )
        assert resp.status_code == 200
        assert resp.context["paralelo_seleccionado"] is None

    def test_resumen_global_correcto(self, client):
        tl, periodo, paralelo, user = self._setup()
        e1 = EstudianteFactory()
        e2 = EstudianteFactory()
        _matricular(e1, paralelo)
        _matricular(e2, paralelo)
        ev = EvaluacionFactory(paralelo=paralelo, peso=Decimal("100.00"))
        _calificar(ev, e1, "18.00")
        _calificar(ev, e2, "12.00")
        client.force_login(user)

        resp = client.get(URL + f"?tipo_licencia={tl.id}&periodo={periodo.id}")
        resumen = resp.context["resumen"]
        assert resumen["total_aprobados"] == 1
        assert resumen["total_reprobados"] == 1

    def test_filtro_umbral_inasistencia_filtra_metricas(self, client):
        import datetime

        tl, periodo, paralelo, user = self._setup()
        # 1 de 10 presentes → 10% asistencia → inasistencia = 90%
        e = EstudianteFactory()
        _matricular(e, paralelo)
        base = datetime.date(2026, 4, 1)
        for i in range(10):
            estado = Asistencia.Estado.PRESENTE if i == 0 else Asistencia.Estado.AUSENTE
            _asistencia(e, paralelo, estado, fecha=base + datetime.timedelta(days=i))
        client.force_login(user)

        # umbral 20%: el paralelo tiene 90% inasistencia → supera el umbral → aparece
        resp_con = client.get(URL + f"?tipo_licencia={tl.id}&periodo={periodo.id}&inasistencia=20")
        assert resp_con.status_code == 200
        assert len(resp_con.context["metricas"]) == 1

        # umbral 95 no es opción válida → se limpia → no filtra → el paralelo sigue apareciendo
        resp_sin = client.get(URL + f"?tipo_licencia={tl.id}&periodo={periodo.id}&inasistencia=95")
        assert resp_sin.status_code == 200
        assert resp_sin.context["inasistencia_seleccionada"] == ""


# ══════════════════════════════════════════════════════════════════════════════
# 6. DashboardRendimientoAPIView — endpoint JSON
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestDashboardRendimientoAPIViewAcceso:

    def test_anonimo_redirige(self, client):
        resp = client.get(URL_API + "?periodo=1")
        assert resp.status_code == 302

    @pytest.mark.parametrize("factory_cls", [EstudianteFactory, DocenteFactory])
    def test_roles_no_autorizados_retornan_403(self, client, factory_cls):
        user = factory_cls()
        user.save()
        client.force_login(user)
        resp = client.get(URL_API + "?periodo=1")
        assert resp.status_code == 403

    def test_inspector_puede_acceder(self, client):
        user = InspectorFactory()
        user.save()
        client.force_login(user)
        periodo = PeriodoFactory(activo=True)
        resp = client.get(URL_API + f"?periodo={periodo.id}")
        assert resp.status_code == 200

    def test_secretaria_puede_acceder(self, client):
        user = SecretariaFactory()
        user.save()
        client.force_login(user)
        periodo = PeriodoFactory(activo=True)
        resp = client.get(URL_API + f"?periodo={periodo.id}")
        assert resp.status_code == 200


@pytest.mark.django_db
class TestDashboardRendimientoAPIViewMetricas:

    def _inspector_client(self, client):
        user = InspectorFactory()
        user.save()
        client.force_login(user)

    def test_sin_periodo_retorna_400(self, client):
        self._inspector_client(client)
        resp = client.get(URL_API)
        assert resp.status_code == 400
        data = json.loads(resp.content)
        assert "error" in data

    def test_periodo_valido_retorna_estructura_correcta(self, client):
        self._inspector_client(client)
        periodo = PeriodoFactory(activo=True)
        ParaleloFactory(periodo=periodo)
        resp = client.get(URL_API + f"?periodo={periodo.id}")
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert "labels" in data
        assert "promedios" in data
        assert "asistencia" in data
        assert "aprobacion" in data
        assert "reprobacion" in data

    def test_labels_y_promedios_tienen_misma_longitud(self, client):
        self._inspector_client(client)
        periodo = PeriodoFactory(activo=True)
        for _ in range(3):
            ParaleloFactory(periodo=periodo)
        resp = client.get(URL_API + f"?periodo={periodo.id}")
        data = json.loads(resp.content)
        assert len(data["labels"]) == len(data["promedios"]) == 3

    def test_periodo_sin_paralelos_retorna_listas_vacias(self, client):
        self._inspector_client(client)
        periodo = PeriodoFactory(activo=True)
        resp = client.get(URL_API + f"?periodo={periodo.id}")
        data = json.loads(resp.content)
        assert data["labels"] == []
        assert data["promedios"] == []

    def test_filtro_inasistencia_en_api(self, client):
        """Con umbral inasistencia=20, cursos con asistencia perfecta no aparecen."""
        import datetime

        self._inspector_client(client)
        periodo = PeriodoFactory(activo=True)
        paralelo = ParaleloFactory(periodo=periodo)
        e = EstudianteFactory()
        _matricular(e, paralelo)
        # 10 de 10 presentes → inasistencia 0% → no supera umbral 20%
        base = datetime.date(2026, 4, 1)
        for i in range(10):
            _asistencia(
                e,
                paralelo,
                Asistencia.Estado.PRESENTE,
                fecha=base + datetime.timedelta(days=i),
            )

        resp = client.get(URL_API + f"?periodo={periodo.id}&inasistencia=20")
        data = json.loads(resp.content)
        assert data["labels"] == []


@pytest.mark.django_db
class TestDashboardRendimientoAPIViewTendencia:

    def _inspector_client(self, client):
        user = InspectorFactory()
        user.save()
        client.force_login(user)

    def test_con_paralelo_retorna_tendencia(self, client):
        self._inspector_client(client)
        paralelo = ParaleloFactory()
        e = EstudianteFactory()
        ev = EvaluacionFactory(
            paralelo=paralelo,
            tipo=Evaluacion.TipoEvaluacion.PARCIAL_1,
            peso=Decimal("100.00"),
        )
        _calificar(ev, e, "15.00")

        resp = client.get(URL_API + f"?paralelo={paralelo.id}")
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert "tendencia" in data
        assert len(data["tendencia"]) == 1
        assert data["tendencia"][0]["tipo"] == "parcial1"
        assert data["tendencia"][0]["promedio"] == 15.0

    def test_tendencia_respeta_orden_parciales(self, client):
        self._inspector_client(client)
        paralelo = ParaleloFactory()
        ev_final = EvaluacionFactory(
            paralelo=paralelo,
            tipo=Evaluacion.TipoEvaluacion.EXAMEN_FINAL,
            peso=Decimal("50.00"),
        )
        ev_p1 = EvaluacionFactory(
            paralelo=paralelo,
            tipo=Evaluacion.TipoEvaluacion.PARCIAL_1,
            peso=Decimal("50.00"),
        )
        e = EstudianteFactory()
        _calificar(ev_p1, e, "14.00")
        _calificar(ev_final, e, "18.00")

        resp = client.get(URL_API + f"?paralelo={paralelo.id}")
        data = json.loads(resp.content)
        tipos = [t["tipo"] for t in data["tendencia"]]
        assert tipos.index("parcial1") < tipos.index("examen_final")

    def test_evaluacion_sin_calificaciones_promedio_none(self, client):
        self._inspector_client(client)
        paralelo = ParaleloFactory()
        EvaluacionFactory(
            paralelo=paralelo,
            tipo=Evaluacion.TipoEvaluacion.PARCIAL_1,
            peso=Decimal("100.00"),
        )

        resp = client.get(URL_API + f"?paralelo={paralelo.id}")
        data = json.loads(resp.content)
        assert data["tendencia"][0]["promedio"] is None

    def test_paralelo_sin_evaluaciones_tendencia_vacia(self, client):
        self._inspector_client(client)
        paralelo = ParaleloFactory()

        resp = client.get(URL_API + f"?paralelo={paralelo.id}")
        data = json.loads(resp.content)
        assert data["tendencia"] == []
