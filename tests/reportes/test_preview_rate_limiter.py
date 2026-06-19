"""
Tests unitarios para ``ExportacionPreviewRateLimiter`` (HU27b).

Espejo de ``tests/reportes/test_rate_limiter.py`` para el limiter de
preview, que es paralelo pero con cache key prefix distinto
(``preview_rate_``) y un límite 2× mayor (20/min).

La fixture ``_clear_cache`` (autouse) en ``conftest.py`` mantiene
aislamiento entre tests.
"""

import datetime
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.utils import timezone

from apps.reportes.application.rate_limiter import ExportacionPreviewRateLimiter


pytestmark = pytest.mark.django_db


class TestExportacionPreviewRateLimiterCheck:
    """Comportamiento del método ``check`` del preview rate limiter."""

    def test_check_returns_true_on_first_call(self):
        """La primera llamada para un usuario retorna True."""
        assert ExportacionPreviewRateLimiter.check(user_id=1) is True

    def test_check_allows_20_calls(self):
        """Las primeras 20 llamadas dentro del mismo minuto retornan True."""
        for i in range(20):
            assert (
                ExportacionPreviewRateLimiter.check(user_id=1) is True
            ), f"call #{i + 1} should pass"

    def test_check_blocks_21st_call(self):
        """La 21ª llamada dentro del mismo minuto retorna False."""
        for _ in range(20):
            ExportacionPreviewRateLimiter.check(user_id=1)
        assert ExportacionPreviewRateLimiter.check(user_id=1) is False

    def test_check_per_user_isolation(self):
        """Usuarios distintos tienen contadores independientes."""
        # Usuario 1 satura su cupo
        for _ in range(20):
            ExportacionPreviewRateLimiter.check(user_id=1)
        assert ExportacionPreviewRateLimiter.check(user_id=1) is False
        # Usuario 2 sigue pasando
        assert ExportacionPreviewRateLimiter.check(user_id=2) is True

    def test_check_resets_on_new_minute(self):
        """El counter se resetea cuando el reloj cruza al siguiente minuto."""
        fixed_now = datetime.datetime(2026, 6, 18, 14, 30, 45)
        with patch("django.utils.timezone.now", return_value=fixed_now):
            for _ in range(20):
                ExportacionPreviewRateLimiter.check(user_id=1)
            assert ExportacionPreviewRateLimiter.check(user_id=1) is False  # 21 bloqueada

        # Cruzamos al siguiente minuto
        next_minute = datetime.datetime(2026, 6, 18, 14, 31, 0)
        with patch("django.utils.timezone.now", return_value=next_minute):
            assert ExportacionPreviewRateLimiter.check(user_id=1) is True

    def test_check_uses_distinct_cache_key_prefix_from_export_limiter(self):
        """El cache key prefix es ``preview_rate_`` (NO colisiona con ``export_rate_``)."""
        ExportacionPreviewRateLimiter.check(user_id=42)
        bucket = timezone.now().strftime("%Y%m%d%H%M")
        preview_key = f"preview_rate_42_{bucket}"
        # El key del preview limiter DEBE existir
        assert cache.get(preview_key) == 1
        # El key del export limiter NO debe existir (sin colisión)
        export_key = f"export_rate_42_{bucket}"
        assert cache.get(export_key) is None

    def test_max_por_minuto_is_20(self):
        """El límite es 20/min (mayor que el de export que es 10/min)."""
        assert ExportacionPreviewRateLimiter.MAX_POR_MINUTO == 20

    def test_check_returns_false_does_not_increment(self):
        """Cuando retorna False, NO incrementa el counter (cortocircuita)."""
        for _ in range(20):
            ExportacionPreviewRateLimiter.check(user_id=1)
        # La 21ª retorna False
        assert ExportacionPreviewRateLimiter.check(user_id=1) is False

        # El counter sigue en 20 (no se incrementa)
        bucket = timezone.now().strftime("%Y%m%d%H%M")
        key = f"preview_rate_1_{bucket}"
        assert cache.get(key, 0) == 20
