from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.usuarios.infrastructure.models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """Admin configuration for the custom Usuario model."""

    list_display = ("username", "email", "first_name", "last_name", "rol", "is_active")
    list_filter = ("rol", "is_active", "is_staff")
    search_fields = ("username", "email", "first_name", "last_name", "cedula")
    fieldsets = UserAdmin.fieldsets + (
        ("Informacion Adicional", {"fields": ("rol", "cedula", "telefono")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Informacion Adicional", {"fields": ("rol", "cedula", "telefono")}),
    )
