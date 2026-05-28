"""Data Transfer Objects for the Solicitudes application layer.

Used by application services to return structured results without leaking
ORM details to the presentation layer.
"""

from dataclasses import dataclass, field


@dataclass
class BulkResultadoDTO:
    """Result of a bulk resolution operation by an inspector.

    Attributes:
        procesadas: count of rows that actually transitioned to a final state.
        omitidas: count of rows skipped (already resolved OR per-row failure).
        omitidas_ids: pks of the omitted rows (for traceability / UI feedback).
    """

    procesadas: int = 0
    omitidas: int = 0
    omitidas_ids: list[int] = field(default_factory=list)
