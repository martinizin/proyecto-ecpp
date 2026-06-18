"""
URL configuration for ECPPP project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

# Admin branding
admin.site.site_header = "ECPPP - Plataforma Academica"
admin.site.site_title = "ECPPP Admin"
admin.site.index_title = "Panel de Administracion"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(pattern_name="usuarios:login", permanent=False), name="home"),
    path("usuarios/", include("apps.usuarios.presentation.urls")),
    path("academico/", include("apps.academico.presentation.urls")),
    path("asistencia/", include("apps.asistencia.presentation.urls")),
    path("secretaria/", include("apps.secretaria.urls")),
    path("notificaciones/", include("apps.notificaciones.presentation.urls")),
    path("calificaciones/", include("apps.calificaciones.presentation.urls")),
    path("solicitudes/", include("apps.solicitudes.presentation.urls")),
    path("copilot/", include("apps.copilot.presentation.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
