"""
Manual queryset filters for the Academico API.

Implements filtering without django-filter dependency.
Each filter class receives query_params and applies filters to a queryset.
Ref: AC-CAT-05
"""

from apps.academico.infrastructure.models import Asignatura, Paralelo


class AsignaturaFilter:
    """
    Filters Asignatura queryset by query parameters.

    Supported params:
        - tipo_licencia: int — filter by M2M tipos_licencia ID.
    """

    @staticmethod
    def apply(queryset, query_params):
        tipo_licencia = query_params.get("tipo_licencia")
        if tipo_licencia:
            queryset = queryset.filter(tipos_licencia__id=tipo_licencia).distinct()
        return queryset


class ParaleloFilter:
    """
    Filters Paralelo queryset by query parameters.

    Supported params:
        - periodo: int — filter by FK periodo ID.
        - tipo_licencia: int — filter by FK tipo_licencia ID.
    """

    @staticmethod
    def apply(queryset, query_params):
        periodo = query_params.get("periodo")
        if periodo:
            queryset = queryset.filter(periodo_id=periodo)

        tipo_licencia = query_params.get("tipo_licencia")
        if tipo_licencia:
            queryset = queryset.filter(tipo_licencia_id=tipo_licencia)

        return queryset
