"""
DRF ViewSets for the Academico bounded context.

Provides REST API endpoints for periods, subjects, parallels, and license types.
SessionAuthentication + IsAuthenticated by default (settings).
Write operations restricted to Inspector role.
Refs: AC-PER-06, AC-PER-07, AC-CAT-07
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.academico.infrastructure.models import (
    Asignatura,
    Paralelo,
    Periodo,
    TipoLicencia,
)
from apps.usuarios.presentation.permissions import IsInspectorOrSecretaria

from .filters import AsignaturaFilter, ParaleloFilter
from .serializers import (
    AsignaturaSerializer,
    ParaleloSerializer,
    PeriodoSerializer,
    TipoLicenciaSerializer,
)


class PeriodoViewSet(viewsets.ModelViewSet):
    """
    CRUD for academic periods.

    GET /api/periodos/ — list all (IsAuthenticated)
    GET /api/periodos/{id}/ — retrieve (IsAuthenticated)
    POST /api/periodos/ — create (IsInspectorOrSecretaria)
    PUT/PATCH /api/periodos/{id}/ — update (IsInspectorOrSecretaria)
    DELETE /api/periodos/{id}/ — delete (IsInspectorOrSecretaria)
    GET /api/periodos/activo/ — get active period (IsAuthenticated)
    """

    queryset = Periodo.objects.select_related("creado_por").all()
    serializer_class = PeriodoSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve", "activo"):
            return [IsAuthenticated()]
        return [IsInspectorOrSecretaria()]

    def perform_create(self, serializer):
        serializer.save(creado_por=self.request.user)

    @action(detail=False, methods=["get"], url_path="activo")
    def activo(self, request):
        """Return active periods. Optionally filter by ?tipo_licencia={id}."""
        qs = Periodo.objects.filter(activo=True).select_related("creado_por", "tipo_licencia")
        tipo_id = request.query_params.get("tipo_licencia")
        if tipo_id:
            qs = qs.filter(tipo_licencia_id=tipo_id)
        periodos = qs.all()
        if not periodos:
            return Response(
                {"detail": "No hay períodos activos."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(periodos, many=True)
        return Response(serializer.data)


class TipoLicenciaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only list/retrieve for license types.

    GET /api/tipos-licencia/ — list all active (IsAuthenticated)
    GET /api/tipos-licencia/{id}/ — retrieve (IsAuthenticated)
    """

    queryset = TipoLicencia.objects.filter(activo=True)
    serializer_class = TipoLicenciaSerializer
    permission_classes = [IsAuthenticated]


class AsignaturaViewSet(viewsets.ModelViewSet):
    """
    CRUD for subjects.

    GET /api/asignaturas/ — list all, filterable by ?tipo_licencia={id}
    GET /api/asignaturas/{id}/ — retrieve
    POST /api/asignaturas/ — create (IsInspectorOrSecretaria)
    PUT/PATCH /api/asignaturas/{id}/ — update (IsInspectorOrSecretaria)
    DELETE /api/asignaturas/{id}/ — delete (IsInspectorOrSecretaria)
    """

    queryset = Asignatura.objects.prefetch_related(
        "asignatura_licencias", "asignatura_licencias__tipo_licencia"
    ).all()
    serializer_class = AsignaturaSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [IsInspectorOrSecretaria()]

    def get_queryset(self):
        qs = super().get_queryset()
        return AsignaturaFilter.apply(qs, self.request.query_params)


class ParaleloViewSet(viewsets.ModelViewSet):
    """
    CRUD for class sections (parallels).

    GET /api/paralelos/ — list all, filterable by ?periodo={id}&tipo_licencia={id}
    GET /api/paralelos/{id}/ — retrieve
    POST /api/paralelos/ — create (IsInspectorOrSecretaria)
    PUT/PATCH /api/paralelos/{id}/ — update (IsInspectorOrSecretaria)
    DELETE /api/paralelos/{id}/ — delete (IsInspectorOrSecretaria)
    """

    queryset = Paralelo.objects.select_related(
        "asignatura", "periodo", "tipo_licencia", "docente"
    ).all()
    serializer_class = ParaleloSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [IsInspectorOrSecretaria()]

    def get_queryset(self):
        qs = super().get_queryset()
        return ParaleloFilter.apply(qs, self.request.query_params)
