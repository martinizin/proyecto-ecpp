#!/usr/bin/env sh
set -e

echo "-> Applying database migrations..."
python manage.py migrate --noinput

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
