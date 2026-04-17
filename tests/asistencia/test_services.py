"""Tests for RegistroAsistenciaAppService (HU08)."""

import datetime
from decimal import Decimal

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


class TestObtenerDatosAsistenciaEstudiante:
    """Tests for obtener_datos_asistencia_estudiante (HU09)."""

    def setup_method(self):
        self.service = RegistroAsistenciaAppService()

    def test_sin_matriculas(self):
        """Student with no active matriculas → empty results."""
        estudiante = EstudianteFactory()
        resultado = self.service.obtener_datos_asistencia_estudiante(estudiante.pk)

        assert resultado["asignaturas"] == []
        assert resultado["inasistencia_general"] == Decimal("0.00")
        assert resultado["riesgo_general"] == "verde"

    def test_una_asignatura_sin_registros(self):
        """Active matricula but no attendance records → 0% inasistencia."""
        estudiante = EstudianteFactory()
        MatriculaFactory(estudiante=estudiante)

        resultado = self.service.obtener_datos_asistencia_estudiante(estudiante.pk)

        assert len(resultado["asignaturas"]) == 1
        asig = resultado["asignaturas"][0]
        assert asig["sesiones_asistidas"] == 0
        assert asig["total_sesiones"] == 0
        assert asig["porcentaje_inasistencia"] == Decimal("0.00")
        assert asig["riesgo"] == "verde"
        assert resultado["inasistencia_general"] == Decimal("0.00")

    def test_una_asignatura_con_registros(self):
        """18 presente + 2 ausente out of 20 → 10% inasistencia."""
        estudiante = EstudianteFactory()
        paralelo = ParaleloFactory()
        MatriculaFactory(estudiante=estudiante, paralelo=paralelo)

        for i in range(18):
            AsistenciaFactory(
                estudiante=estudiante,
                paralelo=paralelo,
                fecha=datetime.date(2026, 4, 1) + datetime.timedelta(days=i),
                estado=Asistencia.Estado.PRESENTE,
            )
        for i in range(2):
            AsistenciaFactory(
                estudiante=estudiante,
                paralelo=paralelo,
                fecha=datetime.date(2026, 5, 1) + datetime.timedelta(days=i),
                estado=Asistencia.Estado.AUSENTE,
            )

        resultado = self.service.obtener_datos_asistencia_estudiante(estudiante.pk)

        assert len(resultado["asignaturas"]) == 1
        asig = resultado["asignaturas"][0]
        assert asig["sesiones_asistidas"] == 18
        assert asig["total_sesiones"] == 20
        assert asig["porcentaje_inasistencia"] == Decimal("10.00")

    def test_multiples_asignaturas(self):
        """Two subjects with different attendance → correct per-subject and general."""
        estudiante = EstudianteFactory()
        periodo = PeriodoFactory(activo=True)

        # Subject 1: 8/10 presente → 20% inasistencia
        p1 = ParaleloFactory(periodo=periodo)
        MatriculaFactory(estudiante=estudiante, paralelo=p1)
        for i in range(8):
            AsistenciaFactory(
                estudiante=estudiante, paralelo=p1,
                fecha=datetime.date(2026, 4, 1) + datetime.timedelta(days=i),
                estado=Asistencia.Estado.PRESENTE,
            )
        for i in range(2):
            AsistenciaFactory(
                estudiante=estudiante, paralelo=p1,
                fecha=datetime.date(2026, 5, 1) + datetime.timedelta(days=i),
                estado=Asistencia.Estado.AUSENTE,
            )

        # Subject 2: 10/10 presente → 0% inasistencia
        p2 = ParaleloFactory(periodo=periodo)
        MatriculaFactory(estudiante=estudiante, paralelo=p2)
        for i in range(10):
            AsistenciaFactory(
                estudiante=estudiante, paralelo=p2,
                fecha=datetime.date(2026, 4, 1) + datetime.timedelta(days=i),
                estado=Asistencia.Estado.PRESENTE,
            )

        resultado = self.service.obtener_datos_asistencia_estudiante(estudiante.pk)

        assert len(resultado["asignaturas"]) == 2
        datos_by_paralelo = {a["paralelo"].pk: a for a in resultado["asignaturas"]}

        assert datos_by_paralelo[p1.pk]["porcentaje_inasistencia"] == Decimal("20.00")
        assert datos_by_paralelo[p2.pk]["porcentaje_inasistencia"] == Decimal("0.00")

        # General: (8+10) asistidas of (10+10) total → 10% inasistencia
        assert resultado["inasistencia_general"] == Decimal("10.00")

    def test_ignora_matricula_retirada(self):
        """Retired matricula is excluded from results."""
        estudiante = EstudianteFactory()
        paralelo_activo = ParaleloFactory()
        paralelo_retirado = ParaleloFactory()
        MatriculaFactory(estudiante=estudiante, paralelo=paralelo_activo)
        MatriculaFactory(
            estudiante=estudiante,
            paralelo=paralelo_retirado,
            estado=Matricula.Estado.RETIRADA,
        )

        resultado = self.service.obtener_datos_asistencia_estudiante(estudiante.pk)

        assert len(resultado["asignaturas"]) == 1
        assert resultado["asignaturas"][0]["paralelo"].pk == paralelo_activo.pk

    def test_ignora_periodo_inactivo(self):
        """Matricula in inactive period is excluded."""
        estudiante = EstudianteFactory()
        periodo_inactivo = PeriodoFactory(activo=False)
        paralelo = ParaleloFactory(periodo=periodo_inactivo)
        MatriculaFactory(estudiante=estudiante, paralelo=paralelo)

        resultado = self.service.obtener_datos_asistencia_estudiante(estudiante.pk)

        assert resultado["asignaturas"] == []
        assert resultado["inasistencia_general"] == Decimal("0.00")


class TestObtenerDatosSupervision:
    """Tests for obtener_datos_supervision (HU11)."""

    def setup_method(self):
        self.service = RegistroAsistenciaAppService()

    def test_sin_estudiantes(self):
        """No active matriculas → empty estudiantes, tipos_licencia exists."""
        # Create a TipoLicencia so it appears in the dropdown
        from tests.factories import TipoLicenciaFactory
        TipoLicenciaFactory()

        resultado = self.service.obtener_datos_supervision()

        assert resultado["estudiantes"] == []
        assert resultado["tipos_licencia"].count() >= 1
        assert resultado["tipo_licencia_seleccionado"] is None

    def test_un_estudiante_sin_registros(self):
        """1 student with active matricula, no attendance → 0.00% inasistencia, riesgo verde."""
        estudiante = EstudianteFactory()
        MatriculaFactory(estudiante=estudiante)

        resultado = self.service.obtener_datos_supervision()

        assert len(resultado["estudiantes"]) == 1
        est = resultado["estudiantes"][0]
        assert est["estudiante"] == estudiante
        assert est["inasistencia_general"] == Decimal("0.00")
        assert est["riesgo"] == "verde"

    def test_un_estudiante_con_ausencias(self):
        """1 student with some absences → correct percentage and riesgo."""
        estudiante = EstudianteFactory()
        paralelo = ParaleloFactory()
        MatriculaFactory(estudiante=estudiante, paralelo=paralelo)

        # 8 present + 2 absent = 10 sessions → 20% inasistencia
        for i in range(8):
            AsistenciaFactory(
                estudiante=estudiante,
                paralelo=paralelo,
                fecha=datetime.date(2026, 4, 1) + datetime.timedelta(days=i),
                estado=Asistencia.Estado.PRESENTE,
            )
        for i in range(2):
            AsistenciaFactory(
                estudiante=estudiante,
                paralelo=paralelo,
                fecha=datetime.date(2026, 5, 1) + datetime.timedelta(days=i),
                estado=Asistencia.Estado.AUSENTE,
            )

        resultado = self.service.obtener_datos_supervision()

        assert len(resultado["estudiantes"]) == 1
        est = resultado["estudiantes"][0]
        assert est["inasistencia_general"] == Decimal("20.00")
        assert est["riesgo"] == "rojo"

    def test_multiples_estudiantes_ordenados(self):
        """2 students with different inasistencia → sorted desc (highest first)."""
        periodo = PeriodoFactory(activo=True)
        paralelo = ParaleloFactory(periodo=periodo)

        est_alto = EstudianteFactory()
        MatriculaFactory(estudiante=est_alto, paralelo=paralelo)
        # 100% absent (1 session)
        AsistenciaFactory(
            estudiante=est_alto,
            paralelo=paralelo,
            fecha=datetime.date(2026, 4, 1),
            estado=Asistencia.Estado.AUSENTE,
        )

        est_bajo = EstudianteFactory()
        MatriculaFactory(estudiante=est_bajo, paralelo=paralelo)
        # 100% present (1 session)
        AsistenciaFactory(
            estudiante=est_bajo,
            paralelo=paralelo,
            fecha=datetime.date(2026, 4, 1),
            estado=Asistencia.Estado.PRESENTE,
        )

        resultado = self.service.obtener_datos_supervision()

        assert len(resultado["estudiantes"]) == 2
        assert resultado["estudiantes"][0]["estudiante"] == est_alto
        assert resultado["estudiantes"][1]["estudiante"] == est_bajo

    def test_filtro_tipo_licencia(self):
        """2 students in different tipo_licencia paralelos, filter → only matching."""
        from tests.factories import TipoLicenciaFactory
        periodo = PeriodoFactory(activo=True)

        tl_a = TipoLicenciaFactory(nombre="Tipo A", codigo="TA")
        tl_b = TipoLicenciaFactory(nombre="Tipo B", codigo="TB")

        paralelo_a = ParaleloFactory(periodo=periodo, tipo_licencia=tl_a)
        paralelo_b = ParaleloFactory(periodo=periodo, tipo_licencia=tl_b)

        est_a = EstudianteFactory()
        MatriculaFactory(estudiante=est_a, paralelo=paralelo_a)

        est_b = EstudianteFactory()
        MatriculaFactory(estudiante=est_b, paralelo=paralelo_b)

        resultado = self.service.obtener_datos_supervision(tipo_licencia_id=tl_a.pk)

        assert len(resultado["estudiantes"]) == 1
        assert resultado["estudiantes"][0]["estudiante"] == est_a

    def test_ignora_matricula_retirada(self):
        """Retired matricula is not included."""
        estudiante = EstudianteFactory()
        paralelo = ParaleloFactory()
        MatriculaFactory(
            estudiante=estudiante,
            paralelo=paralelo,
            estado=Matricula.Estado.RETIRADA,
        )

        resultado = self.service.obtener_datos_supervision()

        assert resultado["estudiantes"] == []

    def test_tipo_licencia_seleccionado_en_resultado(self):
        """Passing tipo_licencia_id returns it in result dict."""
        from tests.factories import TipoLicenciaFactory
        tl = TipoLicenciaFactory()

        resultado = self.service.obtener_datos_supervision(tipo_licencia_id=tl.pk)

        assert resultado["tipo_licencia_seleccionado"] == tl.pk
