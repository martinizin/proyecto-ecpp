# Deployment (HU30)

Single-host Docker Compose stack: **web** (Gunicorn) · **db** (PostgreSQL) ·
**redis** (cache / HU27 rate-limit store) · **caddy** (reverse proxy + automatic
HTTPS). Only Caddy is publicly exposed; `db` and `redis` stay on the internal
network.

Primary target: Oracle Cloud Always Free ARM. Fallback: Hetzner CX22. The same
Compose file and image run on both.

## Run locally

Compose reads secrets from a git-ignored `.env` at the repo root — no passwords
are hardcoded in `docker-compose.yml`. Create a minimal local `.env`:

```sh
# .env (repo root, git-ignored)
DJANGO_SECRET_KEY=dev-only-change-me
DATABASE_PASSWORD=dev-only-change-me
```

Then:

```sh
docker compose up --build
```

Open `https://localhost` (Caddy serves a local self-signed cert; accept the
warning or use `curl -k`). Compose defaults target `config.settings.development`;
only `DJANGO_SECRET_KEY` and `DATABASE_PASSWORD` are required.

## Environment variables

Set these in a git-ignored `.env` at the repo root. On the production host, also
set `DJANGO_SETTINGS_MODULE=config.settings.production`.

| Variable | Example | Notes |
|----------|---------|-------|
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` | Local default is `development`. |
| `DJANGO_SECRET_KEY` | `<50-char random>` | Required. `python -c "import secrets;print(secrets.token_urlsafe(50))"`. |
| `DJANGO_ALLOWED_HOSTS` | `ecppp.edu.ec,www.ecppp.edu.ec` | Comma-separated. |
| `DJANGO_DOMAIN` | `ecppp.edu.ec` | Caddy site address; drives Let's Encrypt. Local: `localhost`. |
| `DATABASE_NAME` | `ecppp` | Postgres database name. |
| `DATABASE_USER` | `ecppp` | Postgres user. |
| `DATABASE_PASSWORD` | `<strong password>` | Postgres password. |
| `REDIS_URL` | `redis://redis:6379/0` | Wired into `CACHES` in PR2. |
| `OPENAI_API_KEY` | `sk-...` | Copilot (HU22). |
| `EMAIL_HOST` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | — | SMTP for notifications. |
| `GUNICORN_WORKERS` | `3` | Worker count. |
| `DJANGO_COLLECTSTATIC` | `1` | Set to `1` in production so WhiteNoise has static files. |

> `DATABASE_HOST` and `DATABASE_PORT` are fixed to `db` / `5432` by Compose
> (the internal Postgres service); do not override them in the container.

## Provision the host (one-time)

Oracle A1 primary, Hetzner CX22 fallback — same steps.

1. Install Docker + Compose plugin.
2. Clone the repo to the deploy path (e.g. `/home/deploy/proyecto-ecpp`).
3. Create the production `.env` (git-ignored) with `DJANGO_SETTINGS_MODULE=config.settings.production`,
   `DJANGO_COLLECTSTATIC=1`, a real `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`,
   `DJANGO_DOMAIN`, `DATABASE_*`, `REDIS_URL`, `OPENAI_API_KEY`, `EMAIL_*`.
4. Point DNS (`DJANGO_DOMAIN`) at the host; Caddy issues the TLS cert on first boot.
5. First boot: `docker compose --env-file .env up -d`.

## Continuous deployment

`.github/workflows/cd.yml` runs on every push to `develop`: it builds the ARM64
image, pushes it to GHCR (`ghcr.io/<owner>/<repo>:<sha>` and `:develop`), then
SSHes to the host to pull that SHA tag and restart the stack.

Required GitHub repository secrets:

| Secret | Purpose |
|--------|---------|
| `SSH_HOST` | Host IP/DNS. **Switch Oracle↔Hetzner by changing this one value.** |
| `SSH_USER` | Deploy user (e.g. `deploy`). |
| `SSH_KEY` | Private key for the deploy user. |
| `DEPLOY_PATH` | Path to the repo/compose on the host. |

`GITHUB_TOKEN` (built-in) is used to push to and pull from GHCR — no extra token
needed. If the GHCR package is private, the deploy user must be able to read it.

### Rollback

Deploys use immutable `:<sha>` image tags. To roll back, re-deploy a previous
SHA on the host:

```sh
cd "$DEPLOY_PATH"
echo "ECPPP_IMAGE=ghcr.io/<owner>/<repo>:<previous-sha>" > .env.image
docker compose --env-file .env --env-file .env.image up -d
```

## Backups (cron)

`scripts/backup_db.sh` and `scripts/backup_media.sh` write to `/var/backups/ecppp/`
with 30-day retention. Install on the host crontab (run from the deploy path):

```cron
0 */6  * * * cd /home/deploy/proyecto-ecpp && ./scripts/backup_db.sh    >> /var/log/ecppp-backup.log 2>&1
0 */12 * * * cd /home/deploy/proyecto-ecpp && ./scripts/backup_media.sh >> /var/log/ecppp-backup.log 2>&1
```

Restore procedure: see `scripts/restore.md` (validate it once during rollout).

## Post-deploy smoke test

```sh
BASE_URL=https://ecppp.edu.ec ./scripts/smoke_e2e.sh
```

Checks `/health/`, the login page (WhiteNoise static), and the auth redirect gate.
The full functional flow (login → libreta → ANT report → export) is in the manual
post-deploy checklist (PRD §4.5.4).
