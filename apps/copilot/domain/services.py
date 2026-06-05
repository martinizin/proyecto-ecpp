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

    @classmethod
    def clasificar(cls, query: str) -> ConsultaAcademica:
        """
        Classify a free-text query and return a ConsultaAcademica value object.

        Priority order: calificaciones > asistencia > horario > general.
        Returns a ConsultaAcademica with the detected type and the original query.
        """
        query_lower = query.lower()

        if any(kw in query_lower for kw in cls.KEYWORDS_CALIFICACIONES):
            tipo = "calificaciones"
        elif any(kw in query_lower for kw in cls.KEYWORDS_ASISTENCIA):
            tipo = "asistencia"
        elif any(kw in query_lower for kw in cls.KEYWORDS_HORARIO):
            tipo = "horario"
        else:
            tipo = "general"

        return ConsultaAcademica(tipo=tipo, query_original=query)
