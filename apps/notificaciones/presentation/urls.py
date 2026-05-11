"""
URL patterns for notifications API.
"""

from django.urls import path

from apps.notificaciones.presentation.views import (
    ContadorNoLeidasView,
    MarcarLeidaView,
    MarcarTodasLeidasView,
    NotificacionesListView,
)

app_name = "notificaciones"

urlpatterns = [
    path("", NotificacionesListView.as_view(), name="lista"),
    path("<int:pk>/leer/", MarcarLeidaView.as_view(), name="marcar_leida"),
    path("leer-todas/", MarcarTodasLeidasView.as_view(), name="marcar_todas_leidas"),
    path("contador/", ContadorNoLeidasView.as_view(), name="contador"),
]
