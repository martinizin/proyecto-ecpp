#!/usr/bin/env sh
# Media backup for ECPPP — archives the named media volume with 30-day retention.
# Run from the deploy directory (where docker-compose.yml lives), e.g. via cron.
set -eu

BACKUP_DIR="${BACKUP_DIR:-/var/backups/ecppp/media}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
# Compose prefixes volumes with the project name (directory). Override if needed.
MEDIA_VOLUME="${MEDIA_VOLUME:-proyecto-ecpp_media}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUT="$BACKUP_DIR/media_$TIMESTAMP.tar.gz"

mkdir -p "$BACKUP_DIR"

# Archive the read-only volume via a throwaway Alpine container.
docker run --rm \
    -v "$MEDIA_VOLUME":/data:ro \
    -v "$BACKUP_DIR":/backup \
    alpine \
    tar -czf "/backup/media_$TIMESTAMP.tar.gz" -C /data .

find "$BACKUP_DIR" -type f -name '*.tar.gz' -mtime "+$RETENTION_DAYS" -delete

echo "Media backup written: $OUT"
