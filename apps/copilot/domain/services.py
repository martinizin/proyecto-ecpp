from apps.copilot.domain.value_objects import ConsultaAcademica


class QueryClassifierService:
    """
    Pure domain service — classifies a natural language query into an
    academic data category based on keyword matching.

    No DB access, no Django dependencies.
    """

    KEYWORDS_CALIFICACIONES = [
        "nota",
        "calificación",
        "calificaciones",
        "promedio",
        "parcial",
        "examen",
        "libreta",
        "notas",
        "puntaje",
        "rendimiento",
    ]
    KEYWORDS_SOLICITUDES = [
        "solicitud",
        "solicitudes",
        "rectificación",
        "rectificacion",
        "rectificar",
        "recalificación",
        "recalificacion",
        "recalificar",
        "reclamo",
        "reclamos",
        "apelación",
        "apelacion",
    ]
    KEYWORDS_ASISTENCIA = [
        "asistencia",
        "falta",
        "faltas",
        "ausencia",
        "ausencias",
        "justificación",
        "justificacion",
        "inasistencia",
        "presente",
        "ausente",
    ]
    KEYWORDS_HORARIO = [
        "horario",
        "clase",
        "clases",
        "hora",
        "horas",
        "día",
        "dias",
        "aula",
        "salón",
        "salon",
        "cuando",
        "schedule",
    ]
    KEYWORDS_INFORMACION = [
        "materia",
        "materias",
        "asignatura",
        "asignaturas",
        "módulo",
        "módulos",
        "modulo",
        "modulos",
        "paralelo",
        "paralelos",
        "profesor",
        "docente",
        "matrícula",
        "matricula",
        "matriculado",
        "mis cursos",
        "mis materias",
        "qué estoy cursando",
    ]

    @classmethod
    def clasificar(cls, query: str) -> ConsultaAcademica:
        """
        Classify a free-text query and return a ConsultaAcademica value object.

        Priority order: solicitudes > calificaciones > asistencia > horario > informacion > general.
        Returns a ConsultaAcademica with the detected type and the original query.
        """
        query_lower = query.lower()

        if any(kw in query_lower for kw in cls.KEYWORDS_SOLICITUDES):
            tipo = "solicitudes"
        elif any(kw in query_lower for kw in cls.KEYWORDS_CALIFICACIONES):
            tipo = "calificaciones"
        elif any(kw in query_lower for kw in cls.KEYWORDS_ASISTENCIA):
            tipo = "asistencia"
        elif any(kw in query_lower for kw in cls.KEYWORDS_HORARIO):
            tipo = "horario"
        elif any(kw in query_lower for kw in cls.KEYWORDS_INFORMACION):
            tipo = "informacion"
        else:
            tipo = "general"

        return ConsultaAcademica(tipo=tipo, query_original=query)
