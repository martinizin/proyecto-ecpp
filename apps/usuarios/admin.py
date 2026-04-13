"""
Django Admin configuration for the Usuarios bounded context.
The secretariat uses this panel to create and manage users.
On creation: auto-generates a temporary password and sends credentials by email.
"""

import string

from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.utils.crypto import get_random_string

from apps.usuarios.infrastructure.email_service import send_credenciales_email
from apps.usuarios.infrastructure.models import OTPToken, RegistroAuditoria, Usuario


class UsuarioCreationForm(forms.ModelForm):
    """
    Custom creation form for Django Admin — no password fields.
    The secretariat fills in user data; password is auto-generated in save_model().
    """

    class Meta:
        model = Usuario
        fields = ("email", "first_name", "last_name", "rol", "cedula", "telefono")

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError("Ya existe un usuario con este correo electrónico.")
        return email

    def clean_cedula(self):
        cedula = self.cleaned_data.get("cedula")
        if cedula and Usuario.objects.filter(cedula=cedula).exists():
            raise forms.ValidationError("Ya existe un usuario con esta cédula.")
        return cedula


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """
    Admin configuration for the custom Usuario model.
    - On user creation: auto-generates a 12-char temporary password,
      sets debe_cambiar_password=True, and sends credentials by email.
    - On edit: standard UserAdmin behavior.
    """

    # Custom creation form — no password fields
    add_form = UsuarioCreationForm

    # List view
    list_display = ("email", "first_name", "last_name", "rol", "cedula", "is_active", "debe_cambiar_password")
    list_filter = ("rol", "is_active", "is_staff", "debe_cambiar_password")
    search_fields = ("email", "first_name", "last_name", "cedula")
    ordering = ("-date_joined",)

    # Detail view — editing existing users
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Información personal", {"fields": ("first_name", "last_name", "email")}),
        ("Datos institucionales", {"fields": ("rol", "cedula", "telefono", "direccion")}),
        (
            "Permisos",
            {
                "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
                "classes": ("collapse",),
            },
        ),
        (
            "Seguridad",
            {
                "fields": ("debe_cambiar_password", "intentos_fallidos", "bloqueado_hasta"),
                "classes": ("collapse",),
            },
        ),
        ("Fechas importantes", {"fields": ("last_login", "date_joined"), "classes": ("collapse",)}),
    )

    # Creation view — new users (secretariat workflow)
    add_fieldsets = (
        (
            "Datos de acceso",
            {
                "description": (
                    "Ingrese los datos del nuevo usuario. "
                    "Se generará una contraseña temporal automáticamente "
                    "y se enviará por correo electrónico."
                ),
                "fields": ("email", "first_name", "last_name"),
            },
        ),
        (
            "Datos institucionales",
            {
                "fields": ("rol", "cedula", "telefono"),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        """
        Override save to handle user creation by secretariat:
        - Auto-set username = email
        - Generate a 12-char temporary password
        - Set is_active=True, debe_cambiar_password=True
        - Send credentials email to the new user
        """
        if not change:
            # === NEW USER CREATION ===
            # Generate temporary password: 12 chars with letters + digits + symbols
            temp_password = get_random_string(
                length=12,
                allowed_chars=string.ascii_letters + string.digits + "!@#$%&*",
            )

            # Set username = email (project convention)
            obj.username = obj.email
            obj.is_active = True
            obj.debe_cambiar_password = True
            obj.set_password(temp_password)
            obj.save()

            # Send credentials email
            try:
                send_credenciales_email(obj, temp_password)
                messages.success(
                    request,
                    f"Usuario {obj.email} creado exitosamente. "
                    f"Se enviaron las credenciales por correo electrónico.",
                )
            except Exception:
                messages.warning(
                    request,
                    f"Usuario {obj.email} creado exitosamente, pero NO se pudo enviar "
                    f"el correo con las credenciales. Contraseña temporal: {temp_password}",
                )
        else:
            # === EDITING EXISTING USER ===
            super().save_model(request, obj, form, change)


@admin.register(OTPToken)
class OTPTokenAdmin(admin.ModelAdmin):
    """Read-only admin for OTP tokens — useful for debugging."""

    list_display = ("usuario", "codigo", "creado_en", "expira_en", "usado")
    list_filter = ("usado",)
    search_fields = ("usuario__email",)
    readonly_fields = ("usuario", "codigo", "creado_en", "expira_en", "usado")

    def has_add_permission(self, request):
        return False


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    """Read-only admin for audit logs."""

    list_display = ("timestamp", "usuario", "accion", "ip")
    list_filter = ("accion",)
    search_fields = ("usuario__email", "detalle")
    readonly_fields = ("usuario", "accion", "ip", "timestamp", "detalle")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
