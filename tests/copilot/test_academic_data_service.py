"""Tests for AcademicDataService — real DB queries for the copilot context.

Covers all six data types: calificaciones, solicitudes, asistencia,
horario, informacion, and the dispatcher.
"""

import datetime
from decimal import Decimal

import pytest

from apps.copilot.application.services import AcademicDataService
from tests.factories import (
    AsignaturaFactory,
    AsignaturaLicenciaFactory,
    AsistenciaFactory,
    BloqueHorarioFactory,
    CalificacionFactory,
    DocenteFactory,
    EstudianteFactory,
    EvaluacionFactory,
    MatriculaFactory,
    ParaleloFactory,
    PeriodoFactory,
    RegistroCalificacionParaleloFactory,
    SolicitudFactory,
    TipoLicenciaFactory,
)

pytestmark = [pytest.mark.django_db]


# =========================================================================== #
# Dispatcher
# =========================================================================== #
class TestObtenerDatosDispatcher:
    def test_tipo_calificaciones_llama_metodo_correcto(self):
        svc = AcademicDataService()
        result = svc.obtener_datos(EstudianteFactory(), "calificaciones")
        assert result == "No hay calificaciones registradas para este usuario."

    def test_tipo_solicitudes_llama_metodo_correcto(self):
        svc = AcademicDataService()
        result = svc.obtener_datos(EstudianteFactory(), "solicitudes")
        assert result == "No hay solicitudes registradas para este usuario."

    def test_tipo_asistencia_llama_metodo_correcto(self):
        svc = AcademicDataService()
        result = svc.obtener_datos(EstudianteFactory(), "asistencia")
        assert result == "No hay registros de asistencia para este usuario."

    def test_tipo_horario_llama_metodo_correcto(self):
        svc = AcademicDataService()
        result = svc.obtener_datos(EstudianteFactory(), "horario")
        assert result == "No tienes paralelos activos este período."

    def test_tipo_informacion_retorna_datos(self):
        svc = AcademicDataService()
        est = EstudianteFactory()
        result = svc.obtener_datos(est, "informacion")
        assert "Rol: estudiante" in result
        assert est.get_full_name() in result

    def test_tipo_general_redirige_a_informacion(self):
        svc = AcademicDataService()
        est = EstudianteFactory()
        result = svc.obtener_datos(est, "general")
        assert "Rol: estudiante" in result
        assert est.get_full_name() in result

    def test_tipo_desconocido_retorna_mensaje(self):
        svc = AcademicDataService()
        result = svc.obtener_datos(EstudianteFactory(), "foo")
        assert result == "No hay datos disponibles para esta consulta."


# =========================================================================== #
# Calificaciones
# =========================================================================== #
class TestObtenerCalificaciones:
    def test_sin_calificaciones_retorna_mensaje(self):
        svc = AcademicDataService()
        result = svc._obtener_calificaciones(EstudianteFactory())
        assert "No hay calificaciones" in result

    def test_con_calificaciones_agrupadas_por_asignatura(self):
        estudiante = EstudianteFactory()
        tipo_licencia = TipoLicenciaFactory()
        periodo = PeriodoFactory(tipo_licencia=tipo_licencia, activo=True)
        asig_a = AsignaturaFactory(codigo="MAT-01", nombre="Matematicas")
        AsignaturaLicenciaFactory(asignatura=asig_a, tipo_licencia=tipo_licencia)

        paralelo = ParaleloFactory(asignatura=asig_a, periodo=periodo, tipo_licencia=tipo_licencia)
        MatriculaFactory(estudiante=estudiante, paralelo=paralelo, estado="activa")
        RegistroCalificacionParaleloFactory(paralelo=paralelo, estado="completo")
        evaluacion = EvaluacionFactory(paralelo=paralelo, tipo="parcial1", peso=Decimal("25.00"))
        CalificacionFactory(evaluacion=evaluacion, estudiante=estudiante, nota=Decimal("15.00"))

        svc = AcademicDataService()
        result = svc._obtener_calificaciones(estudiante)
        assert "MAT-01" in result
        assert "Matematicas" in result
        assert "Parcial 1" in result
        assert "15.00" in result
        assert "Promedio" in result


# =========================================================================== #
# Solicitudes
# =========================================================================== #
class TestObtenerSolicitudes:
    def test_sin_solicitudes_retorna_mensaje(self):
        svc = AcademicDataService()
        result = svc._obtener_solicitudes(EstudianteFactory())
        assert "No hay solicitudes" in result

    def test_con_solicitudes_muestra_datos(self):
        estudiante = EstudianteFactory()
        SolicitudFactory(
            estudiante=estudiante,
            tipo="rectificacion",
            estado="pendiente",
            descripcion="Error en mi nota del parcial",
        )

        svc = AcademicDataService()
        result = svc._obtener_solicitudes(estudiante)
        assert "Rectificación de Calificación" in result
        assert "Pendiente" in result
        assert "Error en mi nota" in result


# =========================================================================== #
# Asistencia
# =========================================================================== #
class TestObtenerAsistencia:
    def test_sin_asistencia_retorna_mensaje(self):
        svc = AcademicDataService()
        result = svc._obtener_asistencia(EstudianteFactory())
        assert "No hay registros" in result

    def test_con_asistencia_muestra_resumen_por_asignatura(self):
        estudiante = EstudianteFactory()
        tipo_licencia = TipoLicenciaFactory()
        periodo = PeriodoFactory(tipo_licencia=tipo_licencia)
        asignatura = AsignaturaFactory(codigo="MAT-01")
        AsignaturaLicenciaFactory(asignatura=asignatura, tipo_licencia=tipo_licencia)
        paralelo = ParaleloFactory(
            asignatura=asignatura, periodo=periodo, tipo_licencia=tipo_licencia
        )

        AsistenciaFactory(
            estudiante=estudiante,
            paralelo=paralelo,
            estado="presente",
            fecha=datetime.date(2026, 4, 1),
        )
        AsistenciaFactory(
            estudiante=estudiante,
            paralelo=paralelo,
            estado="ausente",
            fecha=datetime.date(2026, 4, 2),
        )

        svc = AcademicDataService()
        result = svc._obtener_asistencia(estudiante)
        assert "MAT-01" in result
        assert "1/2 clases" in result
        assert "1 ausencia" in result


# =========================================================================== #
# Horario
# =========================================================================== #
class TestObtenerHorario:
    def test_sin_matricula_retorna_mensaje(self):
        svc = AcademicDataService()
        result = svc._obtener_horario(EstudianteFactory())
        assert "No tienes paralelos activos" in result

    def test_con_matricula_muestra_bloques_horario(self):
        estudiante = EstudianteFactory()
        tipo_licencia = TipoLicenciaFactory()
        periodo = PeriodoFactory(tipo_licencia=tipo_licencia)
        asignatura = AsignaturaFactory(codigo="MAT-01", nombre="Matematicas")
        docente = DocenteFactory(first_name="Juan", last_name="Perez")
        AsignaturaLicenciaFactory(asignatura=asignatura, tipo_licencia=tipo_licencia)
        paralelo = ParaleloFactory(
            asignatura=asignatura,
            periodo=periodo,
            tipo_licencia=tipo_licencia,
            docente=docente,
            nombre="A",
        )
        BloqueHorarioFactory(
            paralelo=paralelo,
            dia_semana="lunes",
            hora_inicio=datetime.time(8, 0),
            hora_fin=datetime.time(10, 0),
        )
        MatriculaFactory(estudiante=estudiante, paralelo=paralelo, estado="activa")

        svc = AcademicDataService()
        result = svc._obtener_horario(estudiante)
        assert "MAT-01" in result
        assert "Matematicas" in result
        assert "Lunes" in result
        assert "08:00" in result
        assert "10:00" in result


class TestObtenerHorarioDocente:
    """Issue 5: un docente llega a su horario por ``paralelos_asignados``.

    Filtrar por ``estudiante`` (como hacía la implementación original) devuelve
    siempre vacío para un docente, y el copilot respondía "no tienes paralelos
    activos" aunque tuviera paralelos asignados.
    """

    def _paralelo_del_docente(self, docente, *, activo=True, con_bloque=True):
        tipo_licencia = TipoLicenciaFactory()
        periodo = PeriodoFactory(tipo_licencia=tipo_licencia, activo=activo)
        asignatura = AsignaturaFactory(codigo="LEG-01", nombre="Legislacion")
        AsignaturaLicenciaFactory(asignatura=asignatura, tipo_licencia=tipo_licencia)
        paralelo = ParaleloFactory(
            asignatura=asignatura,
            periodo=periodo,
            tipo_licencia=tipo_licencia,
            docente=docente,
            nombre="NRC 5557",
        )
        if con_bloque:
            BloqueHorarioFactory(
                paralelo=paralelo,
                dia_semana="martes",
                hora_inicio=datetime.time(14, 0),
                hora_fin=datetime.time(16, 0),
            )
        return paralelo

    def test_docente_con_paralelos_ve_su_horario(self):
        docente = DocenteFactory()
        self._paralelo_del_docente(docente)

        result = AcademicDataService()._obtener_horario(docente)

        assert "LEG-01" in result
        assert "Legislacion" in result
        assert "NRC 5557" in result
        assert "Martes" in result
        assert "14:00" in result
        assert "16:00" in result
        assert "No tienes paralelos" not in result

    def test_docente_sin_paralelos_recibe_mensaje_claro(self):
        result = AcademicDataService()._obtener_horario(DocenteFactory())
        assert "No tienes paralelos asignados en el período activo." in result

    def test_docente_solo_ve_el_periodo_activo(self):
        docente = DocenteFactory()
        self._paralelo_del_docente(docente, activo=False)

        result = AcademicDataService()._obtener_horario(docente)

        assert "LEG-01" not in result
        assert "No tienes paralelos asignados en el período activo." in result

    def test_docente_sin_bloques_lo_indica(self):
        docente = DocenteFactory()
        self._paralelo_del_docente(docente, con_bloque=False)

        result = AcademicDataService()._obtener_horario(docente)

        assert "LEG-01" in result
        assert "Sin bloques de horario asignados." in result

    def test_dispatcher_horario_usa_la_rama_docente(self):
        docente = DocenteFactory()
        self._paralelo_del_docente(docente)

        result = AcademicDataService().obtener_datos(docente, "horario")

        assert "LEG-01" in result


# =========================================================================== #
# Informacion
# =========================================================================== #
class TestObtenerInformacion:
    def test_estudiante_sin_matricula(self):
        svc = AcademicDataService()
        result = svc._obtener_informacion(EstudianteFactory())
        assert "Sin matrícula activa" in result

    def test_estudiante_con_matricula_muestra_datos(self):
        estudiante = EstudianteFactory()
        tipo_licencia = TipoLicenciaFactory(codigo="Z-E", nombre="Test Licencia")
        periodo = PeriodoFactory(tipo_licencia=tipo_licencia, nombre="2026-A")
        asignatura = AsignaturaFactory(codigo="MAT-01", nombre="Matematicas")
        docente = DocenteFactory(first_name="Juan", last_name="Perez")
        AsignaturaLicenciaFactory(asignatura=asignatura, tipo_licencia=tipo_licencia)
        paralelo = ParaleloFactory(
            asignatura=asignatura,
            periodo=periodo,
            tipo_licencia=tipo_licencia,
            docente=docente,
            nombre="A",
        )
        MatriculaFactory(estudiante=estudiante, paralelo=paralelo, estado="activa")

        svc = AcademicDataService()
        result = svc._obtener_informacion(estudiante)
        assert "MAT-01" in result
        assert "Matematicas" in result
        assert "Paralelo: A" in result
        assert "2026-A" in result
        assert "(Z-E)" in result

    def test_docente_muestra_paralelos_asignados(self):
        docente = DocenteFactory()
        paralelo = ParaleloFactory(docente=docente)
        MatriculaFactory(paralelo=paralelo)  # need at least one to keep paralelo alive

        svc = AcademicDataService()
        result = svc._obtener_informacion(docente)
        assert "Paralelos asignados" in result
