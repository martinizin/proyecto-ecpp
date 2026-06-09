"""Unit tests for HU22 QueryClassifierService.

Pure-Python domain service — no Django, no DB. Anchors the keyword-based
intent detection that the copilot relies on to fetch the right academic
data context.
"""

import pytest

from apps.copilot.domain.services import QueryClassifierService
from apps.copilot.domain.value_objects import ConsultaAcademica


# --------------------------------------------------------------------------- #
# Clasificar — calificaciones
# --------------------------------------------------------------------------- #
class TestClasificarCalificaciones:
    @pytest.mark.parametrize(
        "query",
        [
            "¿Cuál es mi nota del parcial?",
            "Muéstrame mis calificaciones",
            "Necesito ver mi promedio",
            "Cómo me fue en el examen final",
            "dame la libreta del periodo",
            "Cuál es mi puntaje",
        ],
    )
    def test_keywords_calificaciones(self, query):
        resultado = QueryClassifierService.clasificar(query)
        assert resultado.tipo == "calificaciones"
        assert resultado.query_original == query


# --------------------------------------------------------------------------- #
# Clasificar — solicitudes (rectificaciones + justificaciones)
# --------------------------------------------------------------------------- #
class TestClasificarSolicitudes:
    @pytest.mark.parametrize(
        "query",
        [
            "¿Cómo va mi solicitud de rectificación?",
            "Quiero hacer una rectificación de mi nota",
            "Estado de mi reclamo de calificación",
            "Necesito rectificar mi calificación del parcial",
            "Hice una solicitud de recalificación",
            "Apelación de mi nota del examen final",
        ],
    )
    def test_keywords_solicitudes(self, query):
        resultado = QueryClassifierService.clasificar(query)
        assert resultado.tipo == "solicitudes"
        assert resultado.query_original == query


# --------------------------------------------------------------------------- #
# Clasificar — asistencia
# --------------------------------------------------------------------------- #
class TestClasificarAsistencia:
    @pytest.mark.parametrize(
        "query",
        [
            "¿Cuántas faltas tengo?",
            "Necesito una justificación por una inasistencia",
            "Cuál es mi porcentaje de asistencia",
            "Hoy no pude ir, estuvo ausente",
            "estuve presente en la clase de ayer",
        ],
    )
    def test_keywords_asistencia(self, query):
        resultado = QueryClassifierService.clasificar(query)
        assert resultado.tipo == "asistencia"


# --------------------------------------------------------------------------- #
# Clasificar — horario
# --------------------------------------------------------------------------- #
class TestClasificarHorario:
    @pytest.mark.parametrize(
        "query",
        [
            "¿A qué hora es la clase de matemáticas?",
            "Cuál es mi horario del lunes",
            "En qué salón es la clase",
            "Cuando tengo clase con el profesor X",
        ],
    )
    def test_keywords_horario(self, query):
        resultado = QueryClassifierService.clasificar(query)
        assert resultado.tipo == "horario"


# --------------------------------------------------------------------------- #
# Clasificar — informacion (datos generales del usuario)
# --------------------------------------------------------------------------- #
class TestClasificarInformacion:
    @pytest.mark.parametrize(
        "query",
        [
            "¿Qué materias estoy cursando?",
            "Quiero ver mis asignaturas",
            "En qué paralelo estoy",
            "Quién es mi profesor de matemáticas",
            "Cuáles son mis módulos este período",
            "Qué módulos tengo este ciclo",
            "Quiero ver mi matrícula",
            "Qué materias tengo este periodo",
        ],
    )
    def test_keywords_informacion(self, query):
        resultado = QueryClassifierService.clasificar(query)
        assert resultado.tipo == "informacion"


# --------------------------------------------------------------------------- #
# Clasificar — general (fallback)
# --------------------------------------------------------------------------- #
class TestClasificarGeneral:
    @pytest.mark.parametrize(
        "query",
        [
            "Hola, ¿cómo estás?",
            "Gracias por la ayuda",
            "Quién fue Abraham Lincoln",
            "",
        ],
    )
    def test_fallback_a_general(self, query):
        resultado = QueryClassifierService.clasificar(query)
        assert resultado.tipo == "general"


# --------------------------------------------------------------------------- #
# Clasificar — prioridad cuando se mezclan keywords
# --------------------------------------------------------------------------- #
class TestClasificarPrioridad:
    def test_calificaciones_tiene_prioridad_sobre_asistencia(self):
        # "nota" gana sobre "falta"
        query = "¿Cuántas notas perdí por faltas?"
        resultado = QueryClassifierService.clasificar(query)
        assert resultado.tipo == "calificaciones"

    def test_calificaciones_tiene_prioridad_sobre_horario(self):
        # "examen" gana sobre "horario"
        query = "A qué hora es el examen de matemáticas"
        resultado = QueryClassifierService.clasificar(query)
        assert resultado.tipo == "calificaciones"

    def test_asistencia_tiene_prioridad_sobre_horario(self):
        # "inasistencia" gana sobre "clase"
        query = "Mi inasistencia afectó la clase de ayer"
        resultado = QueryClassifierService.clasificar(query)
        assert resultado.tipo == "asistencia"

    def test_solicitudes_tiene_prioridad_sobre_asistencia(self):
        # "rectificación" gana sobre "falta"
        query = "Rectificación de falta en asistencia"
        resultado = QueryClassifierService.clasificar(query)
        assert resultado.tipo == "solicitudes"

    def test_solicitudes_tiene_prioridad_sobre_calificaciones(self):
        # "reclamo" gana sobre "nota"
        query = "Reclamo de mi nota del parcial"
        resultado = QueryClassifierService.clasificar(query)
        assert resultado.tipo == "solicitudes"

    def test_horario_tiene_prioridad_sobre_informacion(self):
        # "horario" gana sobre "materias"
        query = "Qué materias tengo y cuál es mi horario"
        resultado = QueryClassifierService.clasificar(query)
        assert resultado.tipo == "horario"

    def test_informacion_cuando_no_hay_otro_match(self):
        # "materias" sin horario/notas/faltas → informacion
        query = "Qué materias me asignaron este periodo"
        resultado = QueryClassifierService.clasificar(query)
        assert resultado.tipo == "informacion"


# --------------------------------------------------------------------------- #
# Clasificar — case insensitive
# --------------------------------------------------------------------------- #
class TestClasificarCaseInsensitive:
    def test_mayusculas(self):
        resultado = QueryClassifierService.clasificar("¿CUÁL ES MI NOTA?")
        assert resultado.tipo == "calificaciones"

    def test_minusculas(self):
        resultado = QueryClassifierService.clasificar("cuál es mi nota")
        assert resultado.tipo == "calificaciones"

    def test_mezcla(self):
        resultado = QueryClassifierService.clasificar("CuÁl Es Mi NoTa")
        assert resultado.tipo == "calificaciones"


# --------------------------------------------------------------------------- #
# Retorno — value object ConsultaAcademica
# --------------------------------------------------------------------------- #
class TestClasificarRetorno:
    def test_retorna_consulta_academica(self):
        resultado = QueryClassifierService.clasificar("mi promedio")
        assert isinstance(resultado, ConsultaAcademica)

    def test_preserva_query_original(self):
        original = "  ¿Cuál es mi nota?  "
        resultado = QueryClassifierService.clasificar(original)
        # preserva la query tal cual, sin strip
        assert resultado.query_original == original

    def test_parametros_default_vacio(self):
        resultado = QueryClassifierService.clasificar("algo")
        assert resultado.parametros == {}
