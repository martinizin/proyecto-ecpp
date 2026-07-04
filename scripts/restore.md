# Procedimiento de restauración (HU30)

Ejecutar desde el directorio de deploy (donde vive `docker-compose.yml`). El stack
tiene que estar arriba (`docker compose up -d`).

## Restaurar la base de datos

```sh
# Elegí el dump a restaurar.
DUMP=/var/backups/ecppp/db/ecppp_db_YYYYMMDD_HHMMSS.sql.gz

# Restaurar dentro del contenedor db (las credenciales vienen del contenedor).
gunzip -c "$DUMP" | docker compose exec -T db sh -c \
    'PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

Para una restauración limpia, borrá y recreá la base primero (ATENCIÓN: destruye
los datos actuales):

```sh
docker compose exec -T db sh -c \
    'PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d postgres \
     -c "DROP DATABASE IF EXISTS $POSTGRES_DB;" \
     -c "CREATE DATABASE $POSTGRES_DB OWNER $POSTGRES_USER;"'
gunzip -c "$DUMP" | docker compose exec -T db sh -c \
    'PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

## Restaurar media

```sh
ARCHIVE=/var/backups/ecppp/media/media_YYYYMMDD_HHMMSS.tar.gz

docker run --rm \
    -v proyecto-ecpp_media:/data \
    -v "$(dirname "$ARCHIVE")":/backup \
    alpine \
    sh -c "cd /data && tar -xzf /backup/$(basename "$ARCHIVE")"
```

## Validación (hacerlo una vez durante el rollout)

1. Crear un backup: `./scripts/backup_db.sh` y `./scripts/backup_media.sh`.
2. Restaurar en una base scratch (o en un stack de staging) con los pasos de arriba.
3. Confirmar que la cantidad de filas / un registro conocido existen tras restaurar.
4. Confirmar que un archivo de media conocido está presente y se descarga vía `/media/`.
