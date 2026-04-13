"""
Middleware for the Usuarios bounded context.
Forces users with temporary passwords to change them before accessing any page.
"""

from django.shortcuts import redirect
from django.urls import reverse


class ForzarCambioPasswordMiddleware:
    """
    Intercepts every request from an authenticated user who has
    debe_cambiar_password=True and redirects them to the password change page.

    Exempt paths:
    - The password change page itself (to avoid infinite redirect loop)
    - Logout (so the user can leave if needed)
    - Django Admin (staff users manage their own passwords there)
    - Static/media files
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and getattr(request.user, "debe_cambiar_password", False):
            cambiar_url = reverse("usuarios:cambiar_contrasena")
            logout_url = reverse("usuarios:logout")

            # Allow these paths without redirect
            exempt_paths = (cambiar_url, logout_url, "/admin/")
            if not request.path.startswith(exempt_paths):
                return redirect(cambiar_url)

        return self.get_response(request)
