#!/usr/bin/env sh
# PostgreSQL backup for ECPPP — compressed pg_dump with 30-day retention.
# Run from the deploy directory (where docker-compose.yml lives), e.g. via cron.
# Credentials stay inside the db container (POSTGRES_* env), never in this script.
set -eu

BACKUP_DIR="${BACKUP_DIR:-/var/backups/ecppp/db}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUT="$BACKUP_DIR/ecppp_db_$TIMESTAMP.sql.gz"

mkdir -p "$BACKUP_DIR"

docker compose exec -T db sh -c \
    'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
    | gzip >"$OUT"

# Fail loudly if the dump is empty (e.g. auth or connection error).
if [ ! -s "$OUT" ]; then
    echo "ERROR: backup file is empty, removing: $OUT" >&2
    rm -f "$OUT"
    exit 1
fi

find "$BACKUP_DIR" -type f -name '*.sql.gz' -mtime "+$RETENTION_DAYS" -delete

echo "DB backup written: $OUT"
