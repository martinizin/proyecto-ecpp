"""
Integration tests for ReporteANTAppService (HU26).
Hits the database — requires pytest-django and migrations applied.
"""

import datetime
from decimal import Decimal

import pytest
from django.test import Client

from apps.asistencia.infrastructure.models import Asistencia
from apps.reportes.application.reporte_ant_app_service import ReporteANTAppService
from apps.reportes.domain.exceptions import PeriodoSinEstudiantesError
from apps.reportes.domain.services import ReporteANTService
from apps.reportes.infrastructure.models import ReporteANT
from tests.factories import (
    AsistenciaFactory,
    CalificacionFactory,
    EstudianteFactory,
    EvaluacionFactory,
    MatriculaFactory,
    ParaleloFactory,
    PeriodoFactory,
    SecretariaFactory,
)

pytestmark = pytest.mark.django_db


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_periodo_con_datos(aprobado=True):
    """
    Build a Periodo with one Paralelo, one Estudiante, one Evaluacion,
    one Calificacion and attendance records.
    Returns (periodo, estudiante, matricula).
    """
    periodo = PeriodoFactory()
    paralelo = ParaleloFactory(periodo=periodo)
    estudiante = EstudianteFactory()
    matricula = MatriculaFactory(estudiante=estudiante, paralelo=paralelo)

    ev = EvaluacionFactory(paralelo=paralelo, peso=Decimal("100.00"))
    nota = Decimal("17.00") if aprobado else Decimal("12.00")
    CalificacionFactory(evaluacion=ev, estudiante=estudiante, nota=nota)

    # 9 de 10 clases asistidas → 90%
    for i in range(9):
        AsistenciaFactory(
            estudiante=estudiante,
            paralelo=paralelo,
            fecha=datetime.date(2026, 4, i + 1),
            estado=Asistencia.Estado.PRESENTE,
        )
    AsistenciaFactory(
        estudiante=estudiante,
        paralelo=paralelo,
        fecha=datetime.date(2026, 4, 10),
        estado=Asistencia.Estado.AUSENTE,
    )
    return periodo, estudiante, matricula


# ─── A. Generación básica ─────────────────────────────────────────────────────


class TestReporteANTAppServiceGenerar:

    def test_genera_reporte_y_persiste_en_db(self):
        periodo, _, _ = _make_periodo_con_datos()
        secretaria = SecretariaFactory()

        service = ReporteANTAppService(periodo=periodo, generado_por=secretaria)
        reporte = service.generar()

        assert ReporteANT.objects.filter(pk=reporte.pk).exists()

    def test_pdf_generado_no_esta_vacio(self):
        periodo, _, _ = _make_periodo_con_datos()
        secretaria = SecretariaFactory()

        reporte = ReporteANTAppService(periodo=periodo, generado_por=secretaria).generar()

        assert reporte.archivo_pdf
        contenido = reporte.archivo_pdf.read()
        assert len(contenido) > 0

    def test_pdf_inicia_con_header_pdf(self):
        periodo, _, _ = _make_periodo_con_datos()
        secretaria = SecretariaFactory()

        reporte = ReporteANTAppService(periodo=periodo, generado_por=secretaria).generar()

        contenido = reporte.archivo_pdf.read()
        assert contenido[:4] == b"%PDF"

    def test_hash_almacenado_coincide_con_contenido_real(self):
        periodo, _, _ = _make_periodo_con_datos()
        secretaria = SecretariaFactory()

        reporte = ReporteANTAppService(periodo=periodo, generado_por=secretaria).generar()

        contenido = reporte.archivo_pdf.read()
        hash_calculado = ReporteANTService.computar_hash(contenido)
        assert hash_calculado == reporte.hash_sha256

    def test_hash_tiene_64_caracteres(self):
        periodo, _, _ = _make_periodo_con_datos()
        secretaria = SecretariaFactory()

        reporte = ReporteANTAppService(periodo=periodo, generado_por=secretaria).generar()

        assert len(reporte.hash_sha256) == 64

    def test_metadatos_del_reporte_son_correctos(self):
        periodo, _, _ = _make_periodo_con_datos()
        secretaria = SecretariaFactory()

        reporte = ReporteANTAppService(
            periodo=periodo,
            generado_por=secretaria,
            notas="Test de integración",
        ).generar()

        assert reporte.periodo == periodo
        assert reporte.generado_por == secretaria
        assert reporte.notas == "Test de integración"
        assert reporte.total_estudiantes == 1
        assert reporte.numero_resolucion == "005-DIR-2022-ANT"


# ─── B. Totales y estados ─────────────────────────────────────────────────────


class TestReporteANTTotales:

    def test_estudiante_aprobado_cuenta_en_total_aprobados(self):
        periodo, _, _ = _make_periodo_con_datos(aprobado=True)
        secretaria = SecretariaFactory()

        reporte = ReporteANTAppService(periodo=periodo, generado_por=secretaria).generar()

        assert reporte.total_aprobados == 1
        assert reporte.total_reprobados == 0
        assert reporte.total_desertores == 0

    def test_estudiante_reprobado_cuenta_en_total_reprobados(self):
        periodo, _, _ = _make_periodo_con_datos(aprobado=False)
        secretaria = SecretariaFactory()

        reporte = ReporteANTAppService(periodo=periodo, generado_por=secretaria).generar()

        assert reporte.total_reprobados == 1
        assert reporte.total_aprobados == 0

    def test_estudiante_sin_calificaciones_es_en_curso(self):
        periodo = PeriodoFactory()
        paralelo = ParaleloFactory(periodo=periodo)
        estudiante = EstudianteFactory()
        MatriculaFactory(estudiante=estudiante, paralelo=paralelo)
        # Sin calificaciones ni evaluaciones
        secretaria = SecretariaFactory()

        reporte = ReporteANTAppService(periodo=periodo, generado_por=secretaria).generar()

        assert reporte.total_en_curso == 1

    def test_estudiante_sin_asistencia_presente_es_desertor(self):
        periodo = PeriodoFactory()
        paralelo = ParaleloFactory(periodo=periodo)
        estudiante = EstudianteFactory()
        MatriculaFactory(estudiante=estudiante, paralelo=paralelo)

        ev = EvaluacionFactory(paralelo=paralelo, peso=Decimal("100.00"))
        CalificacionFactory(evaluacion=ev, estudiante=estudiante, nota=Decimal("18.00"))

        # Solo ausencias (total > 0, asistidas == 0)
        for i in range(5):
            AsistenciaFactory(
                estudiante=estudiante,
                paralelo=paralelo,
                fecha=datetime.date(2026, 4, i + 1),
                estado=Asistencia.Estado.AUSENTE,
            )

        secretaria = SecretariaFactory()
        reporte = ReporteANTAppService(periodo=periodo, generado_por=secretaria).generar()

        assert reporte.total_desertores == 1

    def test_multiples_estudiantes_totales_correctos(self):
        periodo = PeriodoFactory()
        paralelo = ParaleloFactory(periodo=periodo)
        ev = EvaluacionFactory(paralelo=paralelo, peso=Decimal("100.00"))

        for i in range(3):
            est = EstudianteFactory()
            MatriculaFactory(estudiante=est, paralelo=paralelo)
            nota = Decimal("17.00") if i < 2 else Decimal("12.00")
            CalificacionFactory(evaluacion=ev, estudiante=est, nota=nota)
            AsistenciaFactory(
                estudiante=est,
                paralelo=paralelo,
                fecha=datetime.date(2026, 4, 1),
                estado=Asistencia.Estado.PRESENTE,
            )

        secretaria = SecretariaFactory()
        reporte = ReporteANTAppService(periodo=periodo, generado_por=secretaria).generar()

        assert reporte.total_estudiantes == 3
        assert reporte.total_aprobados == 2
        assert reporte.total_reprobados == 1


# ─── C. Errores y casos borde ─────────────────────────────────────────────────


class TestReporteANTErrores:

    def test_periodo_sin_estudiantes_lanza_excepcion(self):
        periodo = PeriodoFactory()
        secretaria = SecretariaFactory()

        with pytest.raises(PeriodoSinEstudiantesError):
            ReporteANTAppService(periodo=periodo, generado_por=secretaria).generar()

    def test_regenerar_crea_nuevo_registro_no_sobreescribe(self):
        periodo, _, _ = _make_periodo_con_datos()
        secretaria = SecretariaFactory()

        ReporteANTAppService(periodo=periodo, generado_por=secretaria).generar()
        ReporteANTAppService(periodo=periodo, generado_por=secretaria).generar()

        assert ReporteANT.objects.filter(periodo=periodo).count() == 2


# ─── D. Vistas HTTP ───────────────────────────────────────────────────────────


class TestReporteANTVistas:

    def test_listado_accesible_para_secretaria(self, secretaria):
        client = Client()
        client.force_login(secretaria)

        resp = client.get("/reportes/ant/")

        assert resp.status_code == 200

    def test_listado_deniega_estudiante(self, estudiante):
        client = Client()
        client.force_login(estudiante)

        resp = client.get("/reportes/ant/")

        assert resp.status_code in (302, 403)

    def test_listado_deniega_docente(self, docente):
        client = Client()
        client.force_login(docente)

        resp = client.get("/reportes/ant/")

        assert resp.status_code in (302, 403)

    def test_listado_deniega_anonimo(self):
        client = Client()

        resp = client.get("/reportes/ant/")

        assert resp.status_code == 302
        assert "/login/" in resp["Location"] or "/usuarios/login/" in resp["Location"]

    def test_generar_post_crea_reporte_y_redirige(self, secretaria):
        periodo, _, _ = _make_periodo_con_datos()
        client = Client()
        client.force_login(secretaria)

        resp = client.post("/reportes/ant/generar/", {"periodo_id": periodo.pk})

        assert resp.status_code == 302
        assert ReporteANT.objects.filter(periodo=periodo).count() == 1

    def test_generar_post_sin_periodo_redirige_con_error(self, secretaria):
        client = Client()
        client.force_login(secretaria)

        resp = client.post("/reportes/ant/generar/", {})

        assert resp.status_code == 302

    def test_generar_post_periodo_sin_estudiantes_redirige_con_error(self, secretaria):
        periodo = PeriodoFactory()
        client = Client()
        client.force_login(secretaria)

        resp = client.post("/reportes/ant/generar/", {"periodo_id": periodo.pk})

        assert resp.status_code == 302
        assert ReporteANT.objects.count() == 0

    def test_descargar_pdf_retorna_archivo(self, secretaria):
        periodo, _, _ = _make_periodo_con_datos()
        client = Client()
        client.force_login(secretaria)
        reporte = ReporteANTAppService(periodo=periodo, generado_por=secretaria).generar()

        resp = client.get(f"/reportes/ant/{reporte.pk}/descargar/")

        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/pdf"

    def test_verificar_hash_retorna_json_valido(self, secretaria):
        periodo, _, _ = _make_periodo_con_datos()
        client = Client()
        client.force_login(secretaria)
        reporte = ReporteANTAppService(periodo=periodo, generado_por=secretaria).generar()

        resp = client.get(f"/reportes/ant/{reporte.pk}/verificar-hash/")

        assert resp.status_code == 200
        data = resp.json()
        assert data["integridad_valida"] is True
        assert "hash_almacenado" in data
        assert "hash_actual" in data

    def test_verificar_hash_json_informa_hash_sha256(self, secretaria):
        periodo, _, _ = _make_periodo_con_datos()
        client = Client()
        client.force_login(secretaria)
        reporte = ReporteANTAppService(periodo=periodo, generado_por=secretaria).generar()

        resp = client.get(f"/reportes/ant/{reporte.pk}/verificar-hash/")
        data = resp.json()

        assert data["hash_almacenado"] == reporte.hash_sha256

    def test_generar_get_renderiza_formulario(self, secretaria):
        client = Client()
        client.force_login(secretaria)

        resp = client.get("/reportes/ant/generar/")

        assert resp.status_code == 200
        assert b"periodo_id" in resp.content or b"Generar" in resp.content
