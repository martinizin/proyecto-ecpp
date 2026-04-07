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
    AsignaturaListView,
    AsignaturaUpdateView,
    ParaleloCreateView,
    ParaleloListView,
    ParaleloUpdateView,
    PeriodoCreateView,
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
    # Asignaturas
    path("asignaturas/", AsignaturaListView.as_view(), name="asignatura_list"),
    path("asignaturas/crear/", AsignaturaCreateView.as_view(), name="asignatura_create"),
    path("asignaturas/<int:pk>/editar/", AsignaturaUpdateView.as_view(), name="asignatura_update"),
    # Paralelos
    path("paralelos/", ParaleloListView.as_view(), name="paralelo_list"),
    path("paralelos/crear/", ParaleloCreateView.as_view(), name="paralelo_create"),
    path("paralelos/<int:pk>/editar/", ParaleloUpdateView.as_view(), name="paralelo_update"),
    # Tipos de Licencia (read-only)
    path("tipos-licencia/", TipoLicenciaListView.as_view(), name="tipo_licencia_list"),
    # API
    path("api/", include(router.urls)),
]
