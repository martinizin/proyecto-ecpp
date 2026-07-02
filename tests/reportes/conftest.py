"""
Shared pytest fixtures for the reportes bounded context (HU27).

The ``_clear_cache`` fixture is autouse: every test in this folder starts
with a fresh Django cache so rate-limiter tests are isolated. Cache
backend is the default ``LocMemCache`` (no ``CACHES`` override).
"""

import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_cache():
    """Reset Django cache before and after every test in this folder."""
    cache.clear()
    yield
    cache.clear()
