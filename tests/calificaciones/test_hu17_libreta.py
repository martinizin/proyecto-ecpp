"""Tests for HU17 — Visualización de libreta de calificaciones (Estudiante)."""

from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from apps.calificaciones.application.services import (
    LibretaCalificacionesAppService,
    SubNotaParcialAppService,
)
from apps.calificaciones.infrastructure.models import RegistroCalificacionParalelo
from tests.factories import (
    CalificacionFactory,
    DocenteFactory,
    EstudianteFactory,
    EvaluacionFactory,
    MatriculaFactory,
    ParaleloFactory,
    PeriodoFactory,
    RegistroCalificacionParaleloFactory,
    TipoLicenciaFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db


def _saved(user):
    """Persist password hash so force_login session survives request cycle."""
    user.save()
    return user


def _setup_materia_validada(estudiante=None, nota=Decimal("18.00"), peso=Decimal("100.00")):
    """Helper: create a full materia with VALIDADO grades for a student."""
    tipo_lic = TipoLicenciaFactory()
    periodo = PeriodoFactory(tipo_licencia=tipo_lic, activo=True)
    paralelo = ParaleloFactory(periodo=periodo, tipo_licencia=tipo_lic)
    est = estudiante or EstudianteFactory()
    MatriculaFactory(paralelo=paralelo, estudiante=est)
    ev = EvaluacionFactory(paralelo=paralelo, peso=peso)
    CalificacionFactory(evaluacion=ev, estudiante=est, nota=nota)
    RegistroCalificacionParaleloFactory(
        paralelo=paralelo,
        estado=RegistroCalificacionParalelo.Estado.VALIDADO,
    )
    return paralelo, est, ev


# =============================================================================
# A. Service tests — LibretaCalificacionesAppService
# =============================================================================


class TestLibretaCalificacionesAppService:

    def test_libreta_empty_no_matriculas(self):
        """Student with no enrollments gets empty libreta."""
        est = EstudianteFactory()
        est.save()
        libreta = LibretaCalificacionesAppService.obtener_libreta(est)

        assert libreta["materias"] == []
        assert libreta["promedio_general"] is None
        assert libreta["total_materias"] == 0
        assert libreta["materias_con_promedio"] == 0

    def test_libreta_shows_materia_validada(self):
        """Student sees grades when registro is VALIDADO."""
        paralelo, est, ev = _setup_materia_validada(nota=Decimal("17.50"))
        est.save()
        libreta = LibretaCalificacionesAppService.obtener_libreta(est)

        assert len(libreta["materias"]) == 1
        materia = libreta["materias"][0]
        assert materia["notas_visibles"] is True
        assert materia["promedio"] == Decimal("17.50")
        assert materia["estado"] == "aprobado"

    def test_libreta_hides_notas_borrador(self):
        """Notes are hidden when registro is BORRADOR."""
        tipo_lic = TipoLicenciaFactory()
        periodo = PeriodoFactory(tipo_licencia=tipo_lic, activo=True)
        paralelo = ParaleloFactory(periodo=periodo, tipo_licencia=tipo_lic)
        est = EstudianteFactory()
        est.save()
        MatriculaFactory(paralelo=paralelo, estudiante=est)
        ev = EvaluacionFactory(paralelo=paralelo, peso=Decimal("100.00"))
        CalificacionFactory(evaluacion=ev, estudiante=est, nota=Decimal("15.00"))
        RegistroCalificacionParaleloFactory(
            paralelo=paralelo,
            estado=RegistroCalificacionParalelo.Estado.BORRADOR,
        )

        libreta = LibretaCalificacionesAppService.obtener_libreta(est)
        materia = libreta["materias"][0]

        assert materia["notas_visibles"] is False
        assert materia["estado"] == "pendiente"
        assert materia["promedio"] is None

    def test_libreta_shows_notas_completo(self):
        """Notes are visible when registro is COMPLETO (sent for validation)."""
        tipo_lic = TipoLicenciaFactory()
        periodo = PeriodoFactory(tipo_licencia=tipo_lic, activo=True)
        paralelo = ParaleloFactory(periodo=periodo, tipo_licencia=tipo_lic)
        est = EstudianteFactory()
        est.save()
        MatriculaFactory(paralelo=paralelo, estudiante=est)
        ev = EvaluacionFactory(paralelo=paralelo, peso=Decimal("100.00"))
        CalificacionFactory(evaluacion=ev, estudiante=est, nota=Decimal("15.00"))
        RegistroCalificacionParaleloFactory(
            paralelo=paralelo,
            estado=RegistroCalificacionParalelo.Estado.COMPLETO,
        )

        libreta = LibretaCalificacionesAppService.obtener_libreta(est)
        materia = libreta["materias"][0]

        assert materia["notas_visibles"] is True
        assert materia["promedio"] == Decimal("15.00")

    def test_libreta_estado_en_curso(self):
        """When not all evaluaciones have grades, estado is 'en_curso'."""
        tipo_lic = TipoLicenciaFactory()
        periodo = PeriodoFactory(tipo_licencia=tipo_lic, activo=True)
        paralelo = ParaleloFactory(periodo=periodo, tipo_licencia=tipo_lic)
        est = EstudianteFactory()
        est.save()
        MatriculaFactory(paralelo=paralelo, estudiante=est)
        ev1 = EvaluacionFactory(paralelo=paralelo, tipo="parcial1", peso=Decimal("50.00"))
        EvaluacionFactory(paralelo=paralelo, tipo="parcial3", peso=Decimal("50.00"))
        CalificacionFactory(evaluacion=ev1, estudiante=est, nota=Decimal("18.00"))
        RegistroCalificacionParaleloFactory(
            paralelo=paralelo,
            estado=RegistroCalificacionParalelo.Estado.VALIDADO,
        )

        libreta = LibretaCalificacionesAppService.obtener_libreta(est)
        materia = libreta["materias"][0]

        assert materia["estado"] == "en_curso"
        assert materia["promedio"] == Decimal("18.00")

    def test_libreta_estado_reprobado(self):
        """When promedio < 16, estado is 'reprobado'."""
        paralelo, est, ev = _setup_materia_validada(nota=Decimal("12.00"))
        est.save()
        libreta = LibretaCalificacionesAppService.obtener_libreta(est)

        assert libreta["materias"][0]["estado"] == "reprobado"

    def test_libreta_promedio_general(self):
        """Promedio general is arithmetic average of per-subject promedios."""
        est = EstudianteFactory()
        est.save()
        # Materia 1: nota 18
        _setup_materia_validada(estudiante=est, nota=Decimal("18.00"))
        # Materia 2: nota 14
        _setup_materia_validada(estudiante=est, nota=Decimal("14.00"))

        libreta = LibretaCalificacionesAppService.obtener_libreta(est)

        assert libreta["promedio_general"] == Decimal("16.00")
        assert libreta["total_materias"] == 2
        assert libreta["materias_con_promedio"] == 2

    def test_libreta_excludes_inactive_period(self):
        """Materias in inactive periods are excluded."""
        tipo_lic = TipoLicenciaFactory()
        periodo = PeriodoFactory(tipo_licencia=tipo_lic, activo=False)
        paralelo = ParaleloFactory(periodo=periodo, tipo_licencia=tipo_lic)
        est = EstudianteFactory()
        est.save()
        MatriculaFactory(paralelo=paralelo, estudiante=est)

        libreta = LibretaCalificacionesAppService.obtener_libreta(est)

        assert libreta["materias"] == []

    def test_libreta_excludes_retirada_matricula(self):
        """Materias with non-active enrollment are excluded."""
        tipo_lic = TipoLicenciaFactory()
        periodo = PeriodoFactory(tipo_licencia=tipo_lic, activo=True)
        paralelo = ParaleloFactory(periodo=periodo, tipo_licencia=tipo_lic)
        est = EstudianteFactory()
        est.save()
        MatriculaFactory(paralelo=paralelo, estudiante=est, estado="retirada")

        libreta = LibretaCalificacionesAppService.obtener_libreta(est)

        assert libreta["materias"] == []

    def test_libreta_no_registro_means_pendiente(self):
        """When no RegistroCalificacionParalelo exists, notas are hidden."""
        tipo_lic = TipoLicenciaFactory()
        periodo = PeriodoFactory(tipo_licencia=tipo_lic, activo=True)
        paralelo = ParaleloFactory(periodo=periodo, tipo_licencia=tipo_lic)
        est = EstudianteFactory()
        est.save()
        MatriculaFactory(paralelo=paralelo, estudiante=est)

        libreta = LibretaCalificacionesAppService.obtener_libreta(est)
        materia = libreta["materias"][0]

        assert materia["notas_visibles"] is False
        assert materia["estado"] == "pendiente"

    def test_libreta_promedio_ponderado_multiple_evaluaciones(self):
        """Promedio is correctly weighted across evaluaciones."""
        tipo_lic = TipoLicenciaFactory()
        periodo = PeriodoFactory(tipo_licencia=tipo_lic, activo=True)
        paralelo = ParaleloFactory(periodo=periodo, tipo_licencia=tipo_lic)
        est = EstudianteFactory()
        est.save()
        MatriculaFactory(paralelo=paralelo, estudiante=est)
        ev1 = EvaluacionFactory(paralelo=paralelo, tipo="parcial1", peso=Decimal("60.00"))
        ev2 = EvaluacionFactory(paralelo=paralelo, tipo="examen_final", peso=Decimal("40.00"))
        CalificacionFactory(evaluacion=ev1, estudiante=est, nota=Decimal("20.00"))
        CalificacionFactory(evaluacion=ev2, estudiante=est, nota=Decimal("10.00"))
        RegistroCalificacionParaleloFactory(
            paralelo=paralelo,
            estado=RegistroCalificacionParalelo.Estado.VALIDADO,
        )

        libreta = LibretaCalificacionesAppService.obtener_libreta(est)
        # (20*60 + 10*40) / 100 = 1600/100 = 16.00
        assert libreta["materias"][0]["promedio"] == Decimal("16.00")


# =============================================================================
# B. View tests — MiLibretaView
# =============================================================================


class TestMiLibretaView:

    def setup_method(self):
        self.client = Client()
        self.url = reverse("calificaciones:mi_libreta")

    def test_anonymous_redirects_to_login(self):
        """Anonymous user is redirected to login."""
        response = self.client.get(self.url)

        assert response.status_code == 302
        assert "/usuarios/login/" in response.url

    def test_docente_forbidden(self):
        """Docente cannot access student libreta."""
        docente = _saved(DocenteFactory())
        self.client.force_login(docente)

        response = self.client.get(self.url)

        assert response.status_code == 403

    def test_inspector_forbidden(self):
        """Inspector cannot access student libreta."""
        inspector = _saved(UsuarioFactory(rol="inspector"))
        self.client.force_login(inspector)

        response = self.client.get(self.url)

        assert response.status_code == 403

    def test_secretaria_forbidden(self):
        """Secretaria cannot access student libreta."""
        secretaria = _saved(UsuarioFactory(rol="secretaria"))
        self.client.force_login(secretaria)

        response = self.client.get(self.url)

        assert response.status_code == 403

    def test_estudiante_access_ok(self):
        """Estudiante can access libreta — returns 200."""
        est = _saved(EstudianteFactory())
        self.client.force_login(est)

        response = self.client.get(self.url)

        assert response.status_code == 200
        assert "calificaciones/mi_libreta.html" in [t.name for t in response.templates]

    def test_estudiante_sees_materia_validada(self):
        """Estudiante sees materia with validated grades."""
        est = _saved(EstudianteFactory())
        _setup_materia_validada(estudiante=est, nota=Decimal("17.00"))

        self.client.force_login(est)
        response = self.client.get(self.url)
        content = response.content.decode()

        assert response.status_code == 200
        # L10N may render 17,00 or 17.00 depending on locale
        assert "17,00" in content or "17.00" in content
        assert "Aprobado" in content

    def test_estudiante_sees_pendiente_when_borrador(self):
        """Estudiante sees 'Pendiente' when grades not validated."""
        tipo_lic = TipoLicenciaFactory()
        periodo = PeriodoFactory(tipo_licencia=tipo_lic, activo=True)
        paralelo = ParaleloFactory(periodo=periodo, tipo_licencia=tipo_lic)
        est = _saved(EstudianteFactory())
        MatriculaFactory(paralelo=paralelo, estudiante=est)
        RegistroCalificacionParaleloFactory(
            paralelo=paralelo,
            estado=RegistroCalificacionParalelo.Estado.BORRADOR,
        )

        self.client.force_login(est)
        response = self.client.get(self.url)

        assert response.status_code == 200
        assert "Pendiente de publicación" in response.content.decode()

    def test_estudiante_empty_state(self):
        """Estudiante with no enrollments sees empty state."""
        est = _saved(EstudianteFactory())
        self.client.force_login(est)

        response = self.client.get(self.url)

        assert response.status_code == 200
        assert "No tiene materias matriculadas" in response.content.decode()


# =============================================================================
# C. Sub-notas en la libreta (HU32-T5)
# =============================================================================


def _setup_materia_con_sub_notas(estudiante=None, pesos=None, override_str=None, justificacion=""):
    """Helper: materia VALIDADA cuyo parcial fue consolidado desde sub-notas."""
    tipo_lic = TipoLicenciaFactory()
    periodo = PeriodoFactory(tipo_licencia=tipo_lic, activo=True)
    paralelo = ParaleloFactory(periodo=periodo, tipo_licencia=tipo_lic)
    est = estudiante or EstudianteFactory()
    est.save()
    matricula = MatriculaFactory(paralelo=paralelo, estudiante=est)
    ev = EvaluacionFactory(paralelo=paralelo, tipo="parcial1", peso=Decimal("100.00"))
    service = SubNotaParcialAppService()
    service.configurar_sub_notas(ev.id, ["Tarea", "Quiz", "Examen"], pesos=pesos)
    service.registrar_sub_notas(
        ev.id,
        matricula.id,
        ["15", "18", "12"],
        override_str=override_str,
        justificacion=justificacion,
    )
    RegistroCalificacionParaleloFactory(
        paralelo=paralelo,
        estado=RegistroCalificacionParalelo.Estado.VALIDADO,
    )
    return paralelo, est, ev


class TestLibretaSubNotas:
    """La libreta muestra el desglose de sub-notas del parcial (HU32-T5)."""

    def test_libreta_incluye_sub_notas(self):
        paralelo, est, ev = _setup_materia_con_sub_notas(pesos=["20", "30", "50"])
        libreta = LibretaCalificacionesAppService.obtener_libreta(est)

        fila = libreta["materias"][0]["evaluaciones"][0]
        assert fila["sub_notas"] == [
            {"nombre": "Tarea", "peso": Decimal("20.00"), "nota": Decimal("15.00")},
            {"nombre": "Quiz", "peso": Decimal("30.00"), "nota": Decimal("18.00")},
            {"nombre": "Examen", "peso": Decimal("50.00"), "nota": Decimal("12.00")},
        ]
        # 15*0.20 + 18*0.30 + 12*0.50 = 14.40
        assert fila["nota"] == Decimal("14.40")
        assert fila["override"] is None

    def test_evaluacion_sin_sub_notas_lista_vacia(self):
        paralelo, est, ev = _setup_materia_validada()
        est.save()
        libreta = LibretaCalificacionesAppService.obtener_libreta(est)

        fila = libreta["materias"][0]["evaluaciones"][0]
        assert fila["sub_notas"] == []
        assert fila["override"] is None

    def test_libreta_incluye_override_y_justificacion(self):
        paralelo, est, ev = _setup_materia_con_sub_notas(
            override_str="16", justificacion="Trabajo de recuperación."
        )
        libreta = LibretaCalificacionesAppService.obtener_libreta(est)

        fila = libreta["materias"][0]["evaluaciones"][0]
        assert fila["override"] == Decimal("16.00")
        assert fila["justificacion_override"] == "Trabajo de recuperación."
        assert fila["nota"] == Decimal("16.00")

    def test_sub_notas_ocultas_si_notas_no_publicadas(self):
        tipo_lic = TipoLicenciaFactory()
        periodo = PeriodoFactory(tipo_licencia=tipo_lic, activo=True)
        paralelo = ParaleloFactory(periodo=periodo, tipo_licencia=tipo_lic)
        est = EstudianteFactory()
        est.save()
        matricula = MatriculaFactory(paralelo=paralelo, estudiante=est)
        ev = EvaluacionFactory(paralelo=paralelo, tipo="parcial1", peso=Decimal("100.00"))
        service = SubNotaParcialAppService()
        service.configurar_sub_notas(ev.id, ["Tarea", "Quiz", "Examen"])
        service.registrar_sub_notas(ev.id, matricula.id, ["15", "18", "12"])
        RegistroCalificacionParaleloFactory(
            paralelo=paralelo,
            estado=RegistroCalificacionParalelo.Estado.BORRADOR,
        )

        libreta = LibretaCalificacionesAppService.obtener_libreta(est)
        fila = libreta["materias"][0]["evaluaciones"][0]
        assert fila["sub_notas"] == []

    def test_vista_muestra_desglose_de_sub_notas(self):
        est = _saved(EstudianteFactory())
        _setup_materia_con_sub_notas(estudiante=est, pesos=["20", "30", "50"])

        client = Client()
        client.force_login(est)
        response = client.get(reverse("calificaciones:mi_libreta"))
        content = response.content.decode()

        assert response.status_code == 200
        assert "3 sub-notas" in content
        assert "Tarea" in content
        assert "Quiz" in content

    def test_vista_muestra_override(self):
        est = _saved(EstudianteFactory())
        _setup_materia_con_sub_notas(
            estudiante=est, override_str="16", justificacion="Trabajo de recuperación."
        )

        client = Client()
        client.force_login(est)
        response = client.get(reverse("calificaciones:mi_libreta"))
        content = response.content.decode()

        assert "Nota final ajustada por el docente" in content
        assert "Trabajo de recuperación." in content
