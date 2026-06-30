"""
Middleware for the Usuarios bounded context.
Forces users with temporary passwords to change them before accessing any page.
Auto-logs out idle sessions (HU31) after SESSION_TIMEOUT_SECONDS of inactivity.
"""

import time

from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import resolve, reverse


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


class SessionTimeoutMiddleware:
    """
    HU31 — Cierra la sesión de un usuario autenticado tras
    ``SESSION_TIMEOUT_SECONDS`` (default 1200s = 20 min) de inactividad.

    El reloj corre contra ``request.session["last_activity"]`` (epoch int
    Unix, UTC). Cada request autenticado y no exento refresca el
    timestamp. Al expirar se ejecuta ``auth.logout(request)`` y se
    redirige a ``usuarios:login?session=expired``.

    Colocación en ``MIDDLEWARE``: DESPUÉS de
    ``ForzarCambioPasswordMiddleware`` (un usuario con
    ``debe_cambiar_password=True`` debe llegar a cambiar la contraseña,
    no ser deslogueado primero) y ANTES de ``MessageMiddleware`` (para
    que el mensaje de la página de login sobreviva al render).

    ``SESSION_TIMEOUT_SECONDS=0`` en ``.env`` actúa como kill-switch:
    la middleware se vuelve no-op.
    """

    # URL prefixes que NUNCA disparan cierre de sesión (los endpoints
    # /api/session/* deben estar disponibles incluso con sesión vencida
    # para que el cliente pueda renovar la sesión).
    EXEMPT_PATH_PREFIXES = frozenset(
        [
            "/api/session/",
            "/admin/",
            "/static/",
            "/media/",
        ]
    )

    # URL names que tampoco disparan cierre (se resuelven en runtime
    # contra ``resolve(request.path_info).url_name``).
    EXEMPT_PATH_NAMES = frozenset(
        [
            "login",
            "logout",
            "password_reset",
            "password_reset_done",
            "password_reset_confirm",
            "password_reset_complete",
            "verificar_2fa",
        ]
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1) Anónimo → no-op total (sin leer sesión, sin redirigir,
        # sin escribir last_activity). Cubre R2.5 y S7.
        if not request.user.is_authenticated:
            return self.get_response(request)

        # Kill-switch operativo: ``SESSION_TIMEOUT_SECONDS=0`` desactiva
        # la feature sin necesidad de tocar el código. Usado por el
        # rollback plan de proposal.md.
        timeout = getattr(settings, "SESSION_TIMEOUT_SECONDS", 1200)
        if timeout <= 0:
            return self.get_response(request)

        # 2) Path exento → refrescar last_activity y dejar pasar. Esto
        # es lo que permite que POST /api/session/extend/ renueve la
        # sesión justo antes del timeout (R3.3, S8).
        if self._is_exempt_path(request):
            request.session["last_activity"] = int(time.time())
            request.session.modified = True
            return self.get_response(request)

        # 3) Sesión expirada → logout + redirect al login con flag
        # ``session=expired`` para que login.html muestre el banner.
        last = request.session.get("last_activity")
        if last is None:
            # Primera request autenticada: inicializar el reloj (R10.3).
            request.session["last_activity"] = int(time.time())
            request.session.modified = True
            return self.get_response(request)

        idle = time.time() - int(last)
        if idle > timeout:
            logout(request)
            login_url = reverse("usuarios:login")
            return redirect(f"{login_url}?session=expired")

        # 4) Sesión activa → refrescar el timestamp y continuar.
        # El ``modified = True`` defensivo es necesario porque el
        # proyecto usa ``SESSION_SAVE_EVERY_REQUEST=False`` (R2.6).
        request.session["last_activity"] = int(time.time())
        request.session.modified = True
        return self.get_response(request)

    def _is_exempt_path(self, request) -> bool:
        """Devuelve True si la URL actual está en la lista de exentas."""
        path = request.path_info or ""
        if any(path.startswith(prefix) for prefix in self.EXEMPT_PATH_PREFIXES):
            return True
        try:
            match = resolve(path)
        except Exception:
            return False
        # match.url_name viene del path_info sin namespace; lo
        # cruzamos con la lista de names del namespace ``usuarios``
        # resolviendo cada nombre.
        url_name = match.url_name
        if url_name and url_name in self.EXEMPT_PATH_NAMES:
            return True
        return False
