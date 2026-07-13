#!/usr/bin/env sh
set -e

# Migrations must run once per deploy, not once per replica. Compose has nowhere
# else to run them, so it keeps the default. Kubernetes sets this to 0 on the
# Deployment and lets a PreSync Job own migrations instead; otherwise every pod
# would race the others through the same schema change.
if [ "${RUN_MIGRATIONS_ON_BOOT:-1}" = "1" ]; then
    echo "-> Applying database migrations..."
    python manage.py migrate --noinput
else
    echo "-> Skipping migrations (RUN_MIGRATIONS_ON_BOOT=0)."
fi

# collectstatic is only meaningful when WhiteNoise serves static (production).
# In DEBUG/development Django serves static itself, so it is opt-in via env.
if [ "${DJANGO_COLLECTSTATIC:-0}" = "1" ]; then
    echo "-> Collecting static files..."
    python manage.py collectstatic --noinput
fi

echo "-> Starting Gunicorn..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout "${GUNICORN_TIMEOUT:-60}" \
    --access-logfile - \
    --error-logfile -
