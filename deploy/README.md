# Despliegue (HU30)

Stack Docker Compose en un solo servidor: **web** (Gunicorn) · **db** (PostgreSQL) ·
**redis** (caché / rate-limit de HU27) · **caddy** (reverse proxy + HTTPS
automático). Solo Caddy está expuesto públicamente; `db` y `redis` quedan en la
red interna.

Objetivo primario: Oracle Cloud Always Free ARM. Alternativa: Hetzner CX22. El
mismo Compose y la misma imagen corren en los dos.

> Para la guía completa paso a paso desde cero, ver **`DEPLOY.md`** en la raíz del
> repo. Este archivo es la referencia técnica rápida.

## Correr en local

Compose lee los secretos de un `.env` (git-ignored) en la raíz del repo — no hay
contraseñas hardcodeadas en `docker-compose.yml`. Creá un `.env` mínimo:

```sh
# .env (raíz del repo, git-ignored)
DJANGO_SECRET_KEY=dev-only-change-me
DATABASE_PASSWORD=dev-only-change-me
```

Luego:

```sh
docker compose up --build
```

Abrí `https://localhost` (Caddy sirve un certificado self-signed local; aceptá la
advertencia o usá `curl -k`). Los defaults apuntan a `config.settings.development`;
solo `DJANGO_SECRET_KEY` y `DATABASE_PASSWORD` son obligatorios.

## Variables de entorno

Definilas en un `.env` (git-ignored) en la raíz del repo. En el servidor de
producción, además seteá `DJANGO_SETTINGS_MODULE=config.settings.production`.

| Variable | Ejemplo | Notas |
|----------|---------|-------|
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` | En local, el default es `development`. |
| `DJANGO_SECRET_KEY` | `<50 chars aleatorios>` | Obligatoria. `python -c "import secrets;print(secrets.token_urlsafe(50))"`. |
| `DJANGO_ALLOWED_HOSTS` | `ecppp.edu.ec,www.ecppp.edu.ec` | Separadas por coma. |
| `DJANGO_DOMAIN` | `ecppp.edu.ec` | Dominio de Caddy; dispara Let's Encrypt. En local: `localhost`. |
| `DATABASE_NAME` | `ecppp` | Nombre de la base Postgres. |
| `DATABASE_USER` | `ecppp` | Usuario de Postgres. |
| `DATABASE_PASSWORD` | `<contraseña fuerte>` | Contraseña de Postgres. |
| `REDIS_URL` | `redis://redis:6379/0` | Usada por `CACHES` en producción. |
| `OPENAI_API_KEY` | `sk-...` | Copiloto (HU22). |
| `EMAIL_HOST` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | — | SMTP para notificaciones. |
| `GUNICORN_WORKERS` | `3` | Cantidad de workers. |
| `DJANGO_COLLECTSTATIC` | `1` | Poné `1` en producción para que WhiteNoise tenga los estáticos. |

> `DATABASE_HOST` y `DATABASE_PORT` los fija Compose a `db` / `5432` (el servicio
> interno de Postgres); no los sobreescribas en el contenedor.

## Provisionar el servidor (una sola vez)

Oracle A1 primario, Hetzner CX22 alternativa — mismos pasos.

1. Instalar Docker + plugin de Compose.
2. Clonar el repo en la ruta de deploy (ej. `/home/deploy/proyecto-ecpp`).
3. Crear el `.env` de producción (git-ignored) con `DJANGO_SETTINGS_MODULE=config.settings.production`,
   `DJANGO_COLLECTSTATIC=1`, una `DJANGO_SECRET_KEY` real, `DJANGO_ALLOWED_HOSTS`,
   `DJANGO_DOMAIN`, `DATABASE_*`, `REDIS_URL`, `OPENAI_API_KEY`, `EMAIL_*`.
4. Apuntar el DNS (`DJANGO_DOMAIN`) al servidor; Caddy emite el certificado TLS en el primer arranque.
5. Primer arranque: `docker compose --env-file .env up -d`.

## Despliegue continuo (CD)

`.github/workflows/cd.yml` corre en cada push a `develop`: construye la imagen
ARM64, la publica en GHCR (`ghcr.io/<owner>/<repo>:<sha>` y `:develop`), y luego
entra por SSH al servidor para bajar ese tag SHA y reiniciar el stack.

Secrets requeridos en el repositorio de GitHub:

| Secret | Para qué |
|--------|----------|
| `SSH_HOST` | IP/DNS del servidor. **Cambiar Oracle↔Hetzner = cambiar solo este valor.** |
| `SSH_USER` | Usuario de deploy (ej. `deploy`). |
| `SSH_KEY` | Clave privada del usuario de deploy. |
| `DEPLOY_PATH` | Ruta al repo/compose en el servidor. |

El `GITHUB_TOKEN` (incorporado) se usa para publicar y bajar de GHCR — no hace
falta otro token. Si el paquete de GHCR es privado, el usuario de deploy tiene que
poder leerlo.

### Rollback

Los deploys usan tags de imagen inmutables (`:<sha>`). Para volver atrás,
re-desplegá un SHA anterior en el servidor:

```sh
cd "$DEPLOY_PATH"
echo "ECPPP_IMAGE=ghcr.io/<owner>/<repo>:<sha-anterior>" > .env.image
docker compose --env-file .env --env-file .env.image up -d
```

## Backups (cron)

`scripts/backup_db.sh` y `scripts/backup_media.sh` escriben en `/var/backups/ecppp/`
con retención de 30 días. Instalalos en el crontab del servidor (corriendo desde la
ruta de deploy):

```cron
0 */6  * * * cd /home/deploy/proyecto-ecpp && ./scripts/backup_db.sh    >> /var/log/ecppp-backup.log 2>&1
0 */12 * * * cd /home/deploy/proyecto-ecpp && ./scripts/backup_media.sh >> /var/log/ecppp-backup.log 2>&1
```

Procedimiento de restauración: ver `scripts/restore.md` (validalo una vez durante el rollout).

## Smoke test post-deploy

```sh
BASE_URL=https://ecppp.edu.ec ./scripts/smoke_e2e.sh
```

Verifica `/health/`, la página de login (estáticos de WhiteNoise) y el redirect del
gate de autenticación. El flujo funcional completo (login → libreta → reporte ANT →
export) está en el checklist manual post-deploy (PRD §4.5.4).
