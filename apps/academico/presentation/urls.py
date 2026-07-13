"""
URL patterns for the Academico bounded context.

Web views: CRUD for periods, subjects, parallels, license types (Inspector only).
API: DRF ViewSets via DefaultRouter.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api_views import (
    AsignaturaViewSet,
    ParaleloViewSet,
    PeriodoViewSet,
    TipoLicenciaViewSet,
)
from .views import (
    AsignaturaCreateView,
    AsignaturaDeleteView,
    AsignaturaListView,
    AsignaturaUpdateView,
    AsignaturasPorTipoLicenciaView,
    CierrePeriodoDashboardView,
    DashboardRendimientoAPIView,
    DashboardRendimientoView,
    HorarioDocenteView,
    HorarioEstudianteView,
    ParaleloCreateLoteView,
    ParaleloCreateView,
    ParaleloDeleteView,
    ParaleloGrupoEditView,
    ParaleloHorarioUpdateView,
    ParaleloListView,
    ParaleloUpdateView,
    PeriodoCreateView,
    PeriodoDesactivarView,
    PeriodoListView,
    PeriodoUpdateView,
    TipoLicenciaListView,
)

app_name = "academico"

# DRF Router
router = DefaultRouter()
router.register("periodos", PeriodoViewSet, basename="api-periodo")
router.register("tipos-licencia", TipoLicenciaViewSet, basename="api-tipo-licencia")
router.register("asignaturas", AsignaturaViewSet, basename="api-asignatura")
router.register("paralelos", ParaleloViewSet, basename="api-paralelo")

urlpatterns = [
    # Períodos
    path("periodos/", PeriodoListView.as_view(), name="periodo_list"),
    path("periodos/crear/", PeriodoCreateView.as_view(), name="periodo_create"),
    path("periodos/<int:pk>/editar/", PeriodoUpdateView.as_view(), name="periodo_update"),
    path(
        "periodos/<int:pk>/desactivar/",
        PeriodoDesactivarView.as_view(),
        name="periodo_desactivar",
    ),
    # Asignaturas
    path("asignaturas/", AsignaturaListView.as_view(), name="asignatura_list"),
    path("asignaturas/crear/", AsignaturaCreateView.as_view(), name="asignatura_create"),
    path("asignaturas/<int:pk>/editar/", AsignaturaUpdateView.as_view(), name="asignatura_update"),
    path(
        "asignaturas/<int:pk>/eliminar/",
        AsignaturaDeleteView.as_view(),
        name="asignatura_delete",
    ),
    # Paralelos
    path("paralelos/", ParaleloListView.as_view(), name="paralelo_list"),
    path("paralelos/crear/", ParaleloCreateView.as_view(), name="paralelo_create"),
    path("paralelos/crear-lote/", ParaleloCreateLoteView.as_view(), name="paralelo_create_lote"),
    path("paralelos/<int:pk>/editar/", ParaleloUpdateView.as_view(), name="paralelo_update"),
    path("paralelos/<int:pk>/eliminar/", ParaleloDeleteView.as_view(), name="paralelo_delete"),
    path(
        "paralelos/<int:pk>/horario/",
        ParaleloHorarioUpdateView.as_view(),
        name="paralelo_horario_update",
    ),
    path(
        "paralelos/grupo/<int:periodo_id>/<int:tipo_licencia_id>/" "<str:nombre>/editar/",
        ParaleloGrupoEditView.as_view(),
        name="paralelo_grupo_edit",
    ),
    # Utilidades (JSON endpoints)
    path(
        "asignaturas-por-tipo/",
        AsignaturasPorTipoLicenciaView.as_view(),
        name="asignaturas_por_tipo",
    ),
    # Tipos de Licencia (read-only)
    path("tipos-licencia/", TipoLicenciaListView.as_view(), name="tipo_licencia_list"),
    # Horarios (vista provisional, solo lectura)
    path("mis-horarios/docente/", HorarioDocenteView.as_view(), name="horario_docente"),
    path("mis-horarios/estudiante/", HorarioEstudianteView.as_view(), name="horario_estudiante"),
    # Dashboard de rendimiento (HU23)
    path(
        "dashboard-rendimiento/",
        DashboardRendimientoView.as_view(),
        name="dashboard_rendimiento",
    ),
    path(
        "dashboard-rendimiento/api/",
        DashboardRendimientoAPIView.as_view(),
        name="dashboard_rendimiento_api",
    ),
    # Dashboard de cierre de período (HU28)
    path(
        "cierre-periodo/",
        CierrePeriodoDashboardView.as_view(),
        name="cierre_periodo_dashboard",
    ),
    # API
    path("api/", include(router.urls)),
]
