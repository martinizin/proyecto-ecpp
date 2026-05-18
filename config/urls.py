"""
URL configuration for ECPPP project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

# Admin branding
admin.site.site_header = "ECPPP - Plataforma Academica"
admin.site.site_title = "ECPPP Admin"
admin.site.index_title = "Panel de Administracion"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", TemplateView.as_view(template_name="pages/home.html"), name="home"),
    path("usuarios/", include("apps.usuarios.presentation.urls")),
    path("academico/", include("apps.academico.presentation.urls")),
    path("asistencia/", include("apps.asistencia.presentation.urls")),
    path("secretaria/", include("apps.secretaria.urls")),
    path("notificaciones/", include("apps.notificaciones.presentation.urls")),
    path("calificaciones/", include("apps.calificaciones.presentation.urls")),
    path("solicitudes/", include("apps.solicitudes.presentation.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
