"""Health check endpoint for monitoring and post-deploy smoke tests."""

from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse


def health_check(request):
    """Return 200 when the database and cache are reachable, 503 otherwise.

    Unauthenticated and intentionally cheap: a ``SELECT 1`` plus a cache
    round-trip. Used by the deploy smoke test and uptime monitoring.
    """
    db_ok = True
    cache_ok = True

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        db_ok = False

    try:
        cache.set("healthcheck", "ok", 5)
        cache_ok = cache.get("healthcheck") == "ok"
    except Exception:
        cache_ok = False

    healthy = db_ok and cache_ok
    return JsonResponse(
        {"status": "ok" if healthy else "error", "db": db_ok, "cache": cache_ok},
        status=200 if healthy else 503,
    )
