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

## Scope note (PR chain)

This is **PR 1** of the HU30 chain: container image + Compose stack, runnable
locally. Production settings hardening (Redis `CACHES`, WhiteNoise, SSL/HSTS,
structured logging) and the `/health/` endpoint land in **PR 2**; the CD workflow
and automated backups land in **PR 3**.
