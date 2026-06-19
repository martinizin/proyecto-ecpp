"""
Servicios de dominio para el bounded context de reportes (HU27b).

D2 del design: ``ReportesDisponibilidadService`` encapsula el filtrado
role-aware de ``Periodo`` y ``Paralelo`` para el hub y el endpoint
``/reportes/preview/``. Mantiene la vista delgada y la DDD layering
limpia (sin ``HttpResponse`` ni ``View``).
"""

from apps.academico.infrastructure.models import Paralelo, Periodo


class ReportesDisponibilidadService:
    """Role-aware list of ``Periodo`` and ``Paralelo`` for the export UX.

    Spec concern #2 (HU27b): keep DDD layering clean — view delegates,
    doesn't query. The service is pure read-only static methods.

    Reglas:
    - ``docente``: solo períodos/paralelos donde enseña (asignado al Paralelo).
    - ``inspector`` / ``secretaria``: todos los períodos/paralelos.
    - ``estudiante``: NO se llama al servicio; la vista rechaza con 403 antes.
    """

    @staticmethod
    def obtener_periodos_disponibles(usuario) -> list:
        """Retorna los períodos disponibles para el ``usuario`` según su rol.

        Para ``docente`` retorna los períodos donde tiene al menos un
        paralelo asignado. Para ``inspector`` / ``secretaria`` retorna
        todos los períodos ordenados por ``-fecha_inicio``.
        """
        if getattr(usuario, "rol", None) == "docente":
            return list(
                Periodo.objects.filter(paralelos__docente=usuario)
                .distinct()
                .order_by("-fecha_inicio")
            )
        # Inspector, secretaria, otros roles con permiso
        return list(Periodo.objects.all().order_by("-fecha_inicio"))

    @staticmethod
    def obtener_paralelos_disponibles(usuario, periodo) -> list:
        """Retorna los paralelos del ``periodo`` disponibles para el ``usuario`` según su rol.

        Para ``docente`` retorna solo los paralelos donde enseña en ese
        período. Para ``inspector`` / ``secretaria`` retorna todos los
        paralelos del período (con ``asignatura`` seleccionado para
        evitar N+1 en el template).
        """
        if getattr(usuario, "rol", None) == "docente":
            return list(
                Paralelo.objects.filter(periodo=periodo, docente=usuario).select_related(
                    "asignatura"
                )
            )
        return list(Paralelo.objects.filter(periodo=periodo).select_related("asignatura"))
