from django.urls import path

from apps.reportes.presentation.views import (
    ReporteANTDescargarView,
    ReporteANTGenerarView,
    ReporteANTListView,
    ReporteANTVerificarHashView,
)

app_name = "reportes"

urlpatterns = [
    path("ant/", ReporteANTListView.as_view(), name="ant_listado"),
    path("ant/generar/", ReporteANTGenerarView.as_view(), name="ant_generar"),
    path("ant/<int:pk>/descargar/", ReporteANTDescargarView.as_view(), name="ant_descargar"),
    path("ant/<int:pk>/verificar-hash/", ReporteANTVerificarHashView.as_view(), name="ant_verificar_hash"),
]
