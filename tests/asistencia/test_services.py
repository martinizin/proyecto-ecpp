"""Tests for RegistroAsistenciaAppService (HU08)."""

import datetime

import pytest

from apps.academico.infrastructure.models import Matricula, Paralelo
from apps.asistencia.application.services import RegistroAsistenciaAppService
from apps.asistencia.infrastructure.models import Asistencia
from tests.factories import (
    AsistenciaFactory,
    DocenteFactory,
    EstudianteFactory,
    MatriculaFactory,
    ParaleloFactory,
    PeriodoFactory,
)

pytestmark = pytest.mark.django_db


class TestObtenerEstudiantesMatriculados:
    """Tests for obtener_estudiantes_matriculados."""

    def setup_method(self):
        self.service = RegistroAsistenciaAppService()
        self.paralelo = ParaleloFactory()

    def test_obtener_estudiantes_matriculados(self):
        """Returns only active matriculas, excludes retired."""
        m1 = MatriculaFactory(paralelo=self.paralelo)
        m2 = MatriculaFactory(paralelo=self.paralelo)
        MatriculaFactory(
            paralelo=self.paralelo, estado=Matricula.Estado.RETIRADA
        )

        result = self.service.obtener_estudiantes_matriculados(self.paralelo.pk)
        ids = [m.estudiante_id for m in result]
        assert len(result) == 2
        assert m1.estudiante_id in ids
        assert m2.estudiante_id in ids


class TestAsistenciaYaRegistrada:
    """Tests for asistencia_ya_registrada."""

    def setup_method(self):
        self.service = RegistroAsistenciaAppService()
        self.paralelo = ParaleloFactory()

    def test_asistencia_ya_registrada_true(self):
        fecha = datetime.date(2026, 5, 10)
        AsistenciaFactory(paralelo=self.paralelo, fecha=fecha)
        assert self.service.asistencia_ya_registrada(self.paralelo.pk, fecha) is True

    def test_asistencia_ya_registrada_false(self):
        fecha = datetime.date(2026, 5, 10)
        assert self.service.asistencia_ya_registrada(self.paralelo.pk, fecha) is False


class TestRegistrarAsistencia:
    """Tests for registrar_asistencia."""

    def setup_method(self):
        self.service = RegistroAsistenciaAppService()
        self.paralelo = ParaleloFactory()
        self.docente = self.paralelo.docente
        self.estudiantes = [
            MatriculaFactory(paralelo=self.paralelo).estudiante
            for _ in range(3)
        ]

    def test_registrar_asistencia_crea_registros(self):
        """Creates records for all enrolled students: 2 present, 1 absent."""
        fecha = datetime.date(2026, 5, 10)
        presentes_ids = [self.estudiantes[0].pk, self.estudiantes[1].pk]

        resultado = self.service.registrar_asistencia(
            paralelo_id=self.paralelo.pk,
            fecha=fecha,
            estudiantes_presentes_ids=presentes_ids,
            registrado_por_id=self.docente.pk,
        )

        assert resultado["registros_creados"] == 3
        assert Asistencia.objects.filter(
            paralelo=self.paralelo, fecha=fecha, estado=Asistencia.Estado.PRESENTE
        ).count() == 2
        assert Asistencia.objects.filter(
            paralelo=self.paralelo, fecha=fecha, estado=Asistencia.Estado.AUSENTE
        ).count() == 1

    def test_registrar_asistencia_retoma(self):
        """Second registration on same date replaces the first (no duplicates)."""
        fecha = datetime.date(2026, 5, 10)
        presentes_ids_v1 = [self.estudiantes[0].pk]
        presentes_ids_v2 = [self.estudiantes[1].pk, self.estudiantes[2].pk]

        self.service.registrar_asistencia(
            self.paralelo.pk, fecha, presentes_ids_v1, self.docente.pk
        )
        self.service.registrar_asistencia(
            self.paralelo.pk, fecha, presentes_ids_v2, self.docente.pk
        )

        total = Asistencia.objects.filter(paralelo=self.paralelo, fecha=fecha).count()
        assert total == 3  # still 3, not 6
        presentes = Asistencia.objects.filter(
            paralelo=self.paralelo, fecha=fecha, estado=Asistencia.Estado.PRESENTE
        ).count()
        assert presentes == 2

    def test_registrar_asistencia_detecta_alertas_rojo(self):
        """Student with >= 5% inasistencia appears in alertas."""
        # Register 20 sessions with 1 student always absent → 100% inasistencia
        estudiante_ausente = self.estudiantes[2]
        presentes_ids = [self.estudiantes[0].pk, self.estudiantes[1].pk]

        resultado = self.service.registrar_asistencia(
            paralelo_id=self.paralelo.pk,
            fecha=datetime.date(2026, 5, 10),
            estudiantes_presentes_ids=presentes_ids,
            registrado_por_id=self.docente.pk,
        )

        # The absent student has 100% inasistencia (1/1 absent) → rojo
        alertas_ids = [a["estudiante_id"] for a in resultado["alertas"]]
        assert estudiante_ausente.pk in alertas_ids


class TestObtenerHistorial:
    """Tests for obtener_historial."""

    def setup_method(self):
        self.service = RegistroAsistenciaAppService()
        self.paralelo = ParaleloFactory()

    def test_obtener_historial(self):
        """Returns dates in descending order."""
        AsistenciaFactory(paralelo=self.paralelo, fecha=datetime.date(2026, 5, 1))
        AsistenciaFactory(paralelo=self.paralelo, fecha=datetime.date(2026, 5, 3))

        historial = self.service.obtener_historial(self.paralelo.pk)
        assert len(historial) == 2
        assert historial[0]["fecha"] == datetime.date(2026, 5, 3)
        assert historial[1]["fecha"] == datetime.date(2026, 5, 1)


class TestObtenerParalelosDocente:
    """Tests for obtener_paralelos_docente."""

    def setup_method(self):
        self.service = RegistroAsistenciaAppService()

    def test_obtener_paralelos_docente(self):
        """Returns only paralelos in active periods."""
        docente = DocenteFactory()
        periodo_activo = PeriodoFactory(activo=True)
        periodo_inactivo = PeriodoFactory(activo=False)

        p1 = ParaleloFactory(docente=docente, periodo=periodo_activo)
        p2 = ParaleloFactory(docente=docente, periodo=periodo_activo)
        ParaleloFactory(docente=docente, periodo=periodo_inactivo)

        result = self.service.obtener_paralelos_docente(docente.pk)
        ids = [p.pk for p in result]
        assert len(ids) == 2
        assert p1.pk in ids
        assert p2.pk in ids


class TestObtenerTodosParalelosActivos:
    """Tests for obtener_todos_paralelos_activos."""

    def setup_method(self):
        self.service = RegistroAsistenciaAppService()

    def test_obtener_todos_paralelos_activos(self):
        """Returns only paralelos with active period."""
        periodo_activo = PeriodoFactory(activo=True)
        periodo_inactivo = PeriodoFactory(activo=False)

        p1 = ParaleloFactory(periodo=periodo_activo)
        ParaleloFactory(periodo=periodo_inactivo)

        result = self.service.obtener_todos_paralelos_activos()
        ids = [p.pk for p in result]
        assert p1.pk in ids
        # The inactive paralelo should not appear
        assert all(
            p.periodo.activo for p in result
        )
