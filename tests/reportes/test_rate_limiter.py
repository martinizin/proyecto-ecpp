"""
Tests unitarios para ``apps.reportes.application.rate_limiter``.

Estrategia TDD: RED primero. La fixture ``_clear_cache`` en conftest.py
limpia el cache antes y después de cada test (autouse), así cada test
arranca con un cache vacío y no hay interferencia entre tests.
"""

import datetime
from unittest.mock import patch

import pytest
from django.core.cache import cache, caches

from apps.reportes.application.rate_limiter import ExportacionRateLimiter


pytestmark = pytest.mark.django_db


class TestExportacionRateLimiterCheck:
    """Comportamiento del método ``check`` del rate limiter."""

    def test_check_returns_true_on_first_call(self):
        """La primera llamada para un usuario retorna True."""
        assert ExportacionRateLimiter.check(user_id=1) is True

    def test_check_allows_up_to_10_calls(self):
        """Las primeras 10 llamadas dentro del mismo minuto retornan True."""
        for i in range(10):
            assert ExportacionRateLimiter.check(user_id=1) is True, f"call #{i + 1} should pass"

    def test_check_blocks_11th_call(self):
        """La 11ª llamada dentro del mismo minuto retorna False."""
        for _ in range(10):
            ExportacionRateLimiter.check(user_id=1)
        assert ExportacionRateLimiter.check(user_id=1) is False

    def test_check_blocks_12th_13th_and_50th_within_window(self):
        """Las llamadas 12, 13, 50 (todas dentro del mismo minuto) retornan False."""
        for _ in range(10):
            ExportacionRateLimiter.check(user_id=1)
        assert ExportacionRateLimiter.check(user_id=1) is False  # 11
        assert ExportacionRateLimiter.check(user_id=1) is False  # 12
        assert ExportacionRateLimiter.check(user_id=1) is False  # 13
        # 14..50
        for _ in range(37):
            assert ExportacionRateLimiter.check(user_id=1) is False

    def test_check_per_user_isolation(self):
        """Usuarios distintos tienen contadores independientes."""
        # Usuario 1 satura su cupo
        for _ in range(10):
            ExportacionRateLimiter.check(user_id=1)
        assert ExportacionRateLimiter.check(user_id=1) is False
        # Usuario 2 sigue pasando (counter independiente)
        assert ExportacionRateLimiter.check(user_id=2) is True

    def test_check_key_includes_minute_bucket(self):
        """El counter se resetea cuando el reloj cruza al siguiente minuto."""
        fixed_now = datetime.datetime(2026, 6, 18, 14, 30, 45)
        with patch("django.utils.timezone.now", return_value=fixed_now):
            for _ in range(10):
                ExportacionRateLimiter.check(user_id=1)
            assert ExportacionRateLimiter.check(user_id=1) is False  # 11 bloqueada

        # Cruzamos al siguiente minuto
        next_minute = datetime.datetime(2026, 6, 18, 14, 31, 0)
        with patch("django.utils.timezone.now", return_value=next_minute):
            assert ExportacionRateLimiter.check(user_id=1) is True  # counter reseteado

    def test_check_uses_locmemcache_default(self):
        """El backend de cache es LocMemCache (per-worker, in-process)."""
        # ``cache`` es un ConnectionProxy; el backend real está en ``caches['default']``.
        backend = caches["default"]
        assert backend.__class__.__name__ == "LocMemCache"
        assert backend.__class__.__module__ == "django.core.cache.backends.locmem"

    def test_check_returns_false_does_not_increment(self):
        """Cuando retorna False, NO incrementa el counter (cortocircuita)."""
        for _ in range(10):
            ExportacionRateLimiter.check(user_id=1)
        # La 11ª retorna False, el counter sigue en 10
        assert ExportacionRateLimiter.check(user_id=1) is False

        # Inspeccionamos la key actual
        from django.utils import timezone

        bucket = timezone.now().strftime("%Y%m%d%H%M")
        key = f"export_rate_1_{bucket}"
        assert cache.get(key, 0) == 10
