"""
URL configuration for ECPPP project.
"""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import TemplateView

# Admin branding
admin.site.site_header = "ECPPP - Plataforma Academica"
admin.site.site_title = "ECPPP Admin"
admin.site.index_title = "Panel de Administracion"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", TemplateView.as_view(template_name="pages/home.html"), name="home"),
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
]
