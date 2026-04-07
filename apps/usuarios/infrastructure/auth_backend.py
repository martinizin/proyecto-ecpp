"""
Custom authentication backend for ECPPP.
Authenticates by email + password + tipo_usuario (role).
AD1: Extends ModelBackend to preserve Django's security layer.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

Usuario = get_user_model()


class ECPPPAuthBackend(ModelBackend):
    """
    Authenticate users by email, password, and tipo_usuario (role).

    This backend overrides the default username-based authentication
    to support triple-field login: email + password + tipo_usuario.
    """

    def authenticate(self, request, email=None, password=None, tipo_usuario=None, **kwargs):
        """
        Authenticate a user by email, password, and role.

        Args:
            request: The HTTP request.
            email: User's email address.
            password: User's password.
            tipo_usuario: Expected role (estudiante, docente, inspector).

        Returns:
            Usuario instance if authentication succeeds, None otherwise.
        """
        if email is None or password is None:
            return None

        try:
            user = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            # Run the default password hasher to mitigate timing attacks
            Usuario().set_password(password)
            return None

        if not user.check_password(password):
            return None

        # Validate role if provided
        if tipo_usuario and user.rol != tipo_usuario:
            return None

        # Check if user is active (Django standard)
        if not self.user_can_authenticate(user):
            return None

        return user
