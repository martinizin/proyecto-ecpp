# Restore procedure (HU30)

Run from the deploy directory (where `docker-compose.yml` lives). The stack must
be up (`docker compose up -d`).

## Restore the database

```sh
# Pick the dump to restore.
DUMP=/var/backups/ecppp/db/ecppp_db_YYYYMMDD_HHMMSS.sql.gz

# Restore into the running db container (credentials come from the container).
gunzip -c "$DUMP" | docker compose exec -T db sh -c \
    'PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

For a clean restore, drop and recreate the database first (WARNING: destroys
current data):

```sh
docker compose exec -T db sh -c \
    'PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d postgres \
     -c "DROP DATABASE IF EXISTS $POSTGRES_DB;" \
     -c "CREATE DATABASE $POSTGRES_DB OWNER $POSTGRES_USER;"'
gunzip -c "$DUMP" | docker compose exec -T db sh -c \
    'PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

## Restore media

```sh
ARCHIVE=/var/backups/ecppp/media/media_YYYYMMDD_HHMMSS.tar.gz

docker run --rm \
    -v proyecto-ecpp_media:/data \
    -v "$(dirname "$ARCHIVE")":/backup \
    alpine \
    sh -c "cd /data && tar -xzf /backup/$(basename "$ARCHIVE")"
```

## Validation (do this once during rollout)

1. Create a backup: `./scripts/backup_db.sh` and `./scripts/backup_media.sh`.
2. Restore into a scratch database (or a staging stack) using the steps above.
3. Confirm row counts / a known record exist after restore.
4. Confirm a known media file is present and downloadable via `/media/`.
