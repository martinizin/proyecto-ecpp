from dataclasses import dataclass, field


@dataclass(frozen=True)
class ConsultaAcademica:
    """Value object representing a classified academic query."""

    # Possible values: "calificaciones", "solicitudes", "asistencia",
    #                  "horario", "informacion", "general"
    tipo: str
    query_original: str
    parametros: dict = field(default_factory=dict)

    def __post_init__(self):
        tipos_validos = {
            "calificaciones",
            "solicitudes",
            "asistencia",
            "horario",
            "informacion",
            "general",
        }
        if self.tipo not in tipos_validos:
            raise ValueError(
                f"Tipo de consulta inválido: '{self.tipo}'. Válidos: {tipos_validos}"
            )
