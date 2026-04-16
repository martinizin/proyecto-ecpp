"""
Permission classes and mixins for ECPPP.
AD5: DRF permissions + Django CBV mixins for role-based access control.
"""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from rest_framework.permissions import BasePermission


# =============================================================================
# Django CBV Mixins (for template views)
# =============================================================================


class RolRequeridoMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin for Django CBVs that restricts access to a specific role.
    Set `rol_requerido` on the view class.

    Usage:
        class MyView(RolRequeridoMixin, TemplateView):
            rol_requerido = 'inspector'
    """

    rol_requerido: str = ""

    def test_func(self) -> bool:
        return (
            self.request.user.is_authenticated
            and self.request.user.rol == self.rol_requerido
        )


class MultiRolRequeridoMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin for Django CBVs that restricts access to multiple roles.
    Set `roles_permitidos` as a list on the view class.

    Usage:
        class MyView(MultiRolRequeridoMixin, TemplateView):
            roles_permitidos = ['docente', 'inspector']
    """

    roles_permitidos: list = []

    def test_func(self) -> bool:
        return (
            self.request.user.is_authenticated
            and self.request.user.rol in self.roles_permitidos
        )


# =============================================================================
# DRF Permission Classes (for API views)
# =============================================================================


class IsInspector(BasePermission):
    """Allow access only to users with rol='inspector'."""

    message = "Solo el Inspector Académico puede realizar esta acción."

    def has_permission(self, request, view) -> bool:
        return (
            request.user
            and request.user.is_authenticated
            and request.user.rol == "inspector"
        )


class IsDocente(BasePermission):
    """Allow access only to users with rol='docente'."""

    message = "Solo docentes pueden realizar esta acción."

    def has_permission(self, request, view) -> bool:
        return (
            request.user
            and request.user.is_authenticated
            and request.user.rol == "docente"
        )
