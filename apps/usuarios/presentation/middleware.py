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

    # URL prefixes que NUNCA disparan cierre de sesión. Incluye los
    # endpoints de keep-alive (``/api/session/extend/`` y
    # ``/api/session/touch/``) — que en el proyecto viven bajo
    # ``/usuarios/api/session/...`` por el ``include()`` del root
    # URLconf, y que referenciamos por nombre en ``EXEMPT_PATH_NAMES``
    # para no acoplarnos al prefijo del namespace.
    EXEMPT_PATH_PREFIXES = frozenset(
        [
            "/admin/",
            "/static/",
            "/media/",
        ]
    )

    # URL names que tampoco disparan cierre. Se matchean por
    # ``resolve(request.path_info).url_name`` en runtime. Incluye los
    # 3 endpoints de sesión — ``session_check`` queda en la lista
    # intermedia (ver ``PRESERVE_ACTIVITY_PATH_NAMES``).
    EXEMPT_PATH_NAMES = frozenset(
        [
            "login",
            "logout",
            "password_reset",
            "password_reset_done",
            "password_reset_confirm",
            "password_reset_complete",
            "verificar_2fa",
            "session_extend",
            "session_touch",
        ]
    )

    # URL names que SÍ pasan por el chequeo de expiración pero la
    # middleware NO les actualiza ``last_activity``. Justificación: el
    # endpoint /api/session/check/ debe reportar el estado REAL de la
    # sesión al cliente (idle real, no el que la propia request acaba
    # de producir). Sin este set, T7 falla porque el view siempre ve
    # ``last_activity`` recién escrito.
    PRESERVE_ACTIVITY_PATH_NAMES = frozenset(
        [
            "session_check",
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

        exempt = self._is_exempt_path(request)

        # 2) Chequeo de expiración (salteado para paths exentos).
        if not exempt:
            last = request.session.get("last_activity")
            if last is None:
                # Primera request autenticada: inicializar el reloj
                # y seguir (R10.3). last_activity ahora = int(time.time()).
                request.session["last_activity"] = int(time.time())
                request.session.modified = True
                return self.get_response(request)
            idle = time.time() - int(last)
            if idle > timeout:
                # Sesión expirada → logout + redirect al login con
                # flag ``session=expired`` para que login.html muestre
                # el banner.
                logout(request)
                login_url = reverse("usuarios:login")
                return redirect(f"{login_url}?session=expired")

        # 3) Refrescar ``last_activity`` salvo que el path esté marcado
        # como "preserve" (típicamente /api/session/check/, cuya view
        # necesita leer el valor original para reportar el estado real).
        if not self._is_preserve_path(request):
            request.session["last_activity"] = int(time.time())
            request.session.modified = True

        return self.get_response(request)

    def _is_exempt_path(self, request) -> bool:
        """Devuelve True si la URL no debe disparar cierre de sesión."""
        path = request.path_info or ""
        if any(path.startswith(prefix) for prefix in self.EXEMPT_PATH_PREFIXES):
            return True
        try:
            match = resolve(path)
        except Exception:
            return False
        # match.url_name viene del path_info sin namespace; lo
        # cruzamos con la lista de names del namespace ``usuarios``.
        url_name = match.url_name
        if url_name and url_name in self.EXEMPT_PATH_NAMES:
            return True
        return False

    def _is_preserve_path(self, request) -> bool:
        """Devuelve True si la URL no debe actualizar ``last_activity``."""
        path = request.path_info or ""
        try:
            match = resolve(path)
        except Exception:
            return False
        url_name = match.url_name
        return bool(url_name and url_name in self.PRESERVE_ACTIVITY_PATH_NAMES)
