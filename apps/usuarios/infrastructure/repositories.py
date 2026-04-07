"""
Concrete repository implementations for the Usuarios bounded context.
Django ORM implementations of the abstract repositories defined in domain/.
"""

from datetime import datetime
from typing import List, Optional

from django.utils import timezone

from apps.usuarios.domain.entities import (
    OTPTokenEntity,
    RegistroAuditoriaEntity,
    Rol,
    UsuarioEntity,
)
from apps.usuarios.domain.repositories import (
    AuditoriaRepository,
    OTPTokenRepository,
    UsuarioRepository,
)

from .models import OTPToken, RegistroAuditoria, Usuario


class DjangoUsuarioRepository(UsuarioRepository):
    """Django ORM implementation of UsuarioRepository."""

    def _to_entity(self, user: Usuario) -> UsuarioEntity:
        return UsuarioEntity(
            username=user.username,
            email=user.email,
            rol=Rol(user.rol),
            first_name=user.first_name,
            last_name=user.last_name,
            cedula=user.cedula,
            telefono=user.telefono,
            direccion=user.direccion,
            is_active=user.is_active,
        )

    def get_by_id(self, user_id: int) -> Optional[UsuarioEntity]:
        try:
            user = Usuario.objects.get(pk=user_id)
            return self._to_entity(user)
        except Usuario.DoesNotExist:
            return None

    def get_by_username(self, username: str) -> Optional[UsuarioEntity]:
        try:
            user = Usuario.objects.get(username=username)
            return self._to_entity(user)
        except Usuario.DoesNotExist:
            return None

    def get_by_email(self, email: str) -> Optional[UsuarioEntity]:
        try:
            user = Usuario.objects.get(email=email)
            return self._to_entity(user)
        except Usuario.DoesNotExist:
            return None

    def email_exists(self, email: str) -> bool:
        return Usuario.objects.filter(email=email).exists()

    def cedula_exists(self, cedula: str) -> bool:
        return Usuario.objects.filter(cedula=cedula).exists()


class DjangoOTPTokenRepository(OTPTokenRepository):
    """Django ORM implementation of OTPTokenRepository."""

    def _to_entity(self, token: OTPToken) -> OTPTokenEntity:
        return OTPTokenEntity(
            usuario_id=token.usuario_id,
            codigo=token.codigo,
            creado_en=token.creado_en,
            expira_en=token.expira_en,
            usado=token.usado,
        )

    def create(self, token: OTPTokenEntity) -> OTPTokenEntity:
        obj = OTPToken.objects.create(
            usuario_id=token.usuario_id,
            codigo=token.codigo,
            expira_en=token.expira_en,
        )
        return self._to_entity(obj)

    def get_valid_token(
        self, usuario_id: int, codigo: str
    ) -> Optional[OTPTokenEntity]:
        try:
            token = OTPToken.objects.get(
                usuario_id=usuario_id,
                codigo=codigo,
                usado=False,
            )
            return self._to_entity(token)
        except OTPToken.DoesNotExist:
            return None

    def mark_as_used(self, usuario_id: int, codigo: str) -> None:
        OTPToken.objects.filter(
            usuario_id=usuario_id,
            codigo=codigo,
            usado=False,
        ).update(usado=True)

    def invalidate_previous(self, usuario_id: int) -> None:
        OTPToken.objects.filter(
            usuario_id=usuario_id,
            usado=False,
        ).update(usado=True)


class DjangoAuditoriaRepository(AuditoriaRepository):
    """Django ORM implementation of AuditoriaRepository."""

    def _to_entity(self, record: RegistroAuditoria) -> RegistroAuditoriaEntity:
        return RegistroAuditoriaEntity(
            accion=record.accion,
            usuario_id=record.usuario_id,
            ip=record.ip,
            timestamp=record.timestamp,
            detalle=record.detalle,
        )

    def registrar(self, entry: RegistroAuditoriaEntity) -> None:
        RegistroAuditoria.objects.create(
            usuario_id=entry.usuario_id,
            accion=entry.accion,
            ip=entry.ip,
            detalle=entry.detalle,
        )

    def listar_por_usuario(
        self, usuario_id: int, limit: int = 50
    ) -> List[RegistroAuditoriaEntity]:
        records = RegistroAuditoria.objects.filter(
            usuario_id=usuario_id
        ).order_by("-timestamp")[:limit]
        return [self._to_entity(r) for r in records]
