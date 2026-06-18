"""
Rate limiter para los endpoints de exportación de reportes (HU27).

Limita cada usuario autenticado a un máximo de ``MAX_POR_MINUTO``
exportaciones por ventana de ``WINDOW_SEGUNDOS``. La 11ª llamada
retorna ``False`` y la vista retorna HTTP 429.

Cache backend: ``LocMemCache`` (default de Django, per-worker, in-process).
En producción con N gunicorn workers el límite efectivo es ``10 * N``
por usuario por minuto — aceptable para Sprint 5; follow-up = wire
``django-redis``.
"""

from django.core.cache import cache
from django.utils import timezone


class ExportacionRateLimiter:
    """Rate limiter per-user usando ``cache.get``/``cache.set``."""

    MAX_POR_MINUTO = 10
    WINDOW_SEGUNDOS = 60

    @classmethod
    def check(cls, user_id: int) -> bool:
        """Retorna ``True`` si la request está permitida; ``False`` si fue rate-limited.

        Bucket key: ``export_rate_<user_id>_<YYYYMMDDHHMM>``. El counter se
        resetea automáticamente al cambiar el minuto (la key cambia).
        """
        bucket = timezone.now().strftime("%Y%m%d%H%M")
        key = f"export_rate_{user_id}_{bucket}"
        count = cache.get(key, 0)
        if count >= cls.MAX_POR_MINUTO:
            return False
        cache.set(key, count + 1, timeout=cls.WINDOW_SEGUNDOS)
        return True
