"""
Rate limiter para los endpoints de exportación de reportes (HU27 / HU27b).

Limita cada usuario autenticado a un máximo de ``MAX_POR_MINUTO``
exportaciones por ventana de ``WINDOW_SEGUNDOS``. La 11ª llamada
retorna ``False`` y la vista retorna HTTP 429.

Cache backend: ``LocMemCache`` (default de Django, per-worker, in-process).
En producción con N gunicorn workers el límite efectivo es ``10 * N``
por usuario por minuto — aceptable para Sprint 5; follow-up = wire
``django-redis``.

HU27b: añade ``ExportacionPreviewRateLimiter`` (20/min) para el endpoint
``GET /reportes/preview/`` — paralelo pero con cache key prefix distinto
para mantener contadores independientes del export.
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


class ExportacionPreviewRateLimiter:
    """Rate limiter per-user para el endpoint ``/reportes/preview/`` (HU27b).

    Paralelo a ``ExportacionRateLimiter`` (10/min export) con su propio
    cache key prefix y un límite 2× mayor (20/min preview). Sub-100 ms
    por request (LIMIT 3 + COUNT), así que el doble de slots es seguro.

    Q2 del proposal (HU27b): 20/min/user. Implementado como clase
    separada para mantener contadores independientes del export.
    """

    MAX_POR_MINUTO = 20
    WINDOW_SEGUNDOS = 60
    CACHE_KEY_PREFIX = "preview_rate_"  # distinto de "export_rate_"

    @classmethod
    def check(cls, user_id: int) -> bool:
        """Retorna ``True`` si la request está permitida; ``False`` si fue rate-limited.

        Bucket key: ``preview_rate_<user_id>_<YYYYMMDDHHMM>``. El counter
        se resetea automáticamente al cambiar el minuto.
        """
        bucket = timezone.now().strftime("%Y%m%d%H%M")
        key = f"{cls.CACHE_KEY_PREFIX}{user_id}_{bucket}"
        count = cache.get(key, 0)
        if count >= cls.MAX_POR_MINUTO:
            return False
        cache.set(key, count + 1, timeout=cls.WINDOW_SEGUNDOS)
        return True
