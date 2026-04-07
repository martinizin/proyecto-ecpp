"""
URL configuration for ECPPP project.
"""

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
]
