# Proposal: Sprint 0 Bootstrap

## Intent

Bootstrap the entire Django/DDD project from an empty repository to a working development environment with CI, database, architecture scaffolding, and UI layout. Without this, Sprint 1 cannot begin — every functional HU depends on the infrastructure established here.

## Scope

### In Scope
- **SP0-01**: `.gitignore`, GitHub Actions CI (flake8, black, pytest, coverage ≥70%), `README.md`
- **SP0-02**: Django project (`config/` settings module: base/dev/prod), PostgreSQL via env vars, `.env.example`, initial migrations, Django Admin superuser
- **SP0-03**: DDD layer structure per app (`domain/`, `application/`, `infrastructure/`, `presentation/`), 5 apps (usuarios, academico, calificaciones, asistencia, solicitudes), 7 aggregate root models with key fields, `docs/arquitectura-ddd.md`
- **SP0-04**: `base.html` with Tailwind 3.4.17 CDN + Alpine.js 3.15.9 CDN, corporate palette (#2D5016, #4A7C2F, #D4B942), Inter font, role-based nav structure, Django Admin branding, responsive

### Out of Scope
- SP0-05 (backlog refinement) — Jira/documentation task, not code
- User authentication logic (Sprint 1: HU01/HU02)
- DRF API endpoints (Sprint 1+)
- Production deployment (Nginx, Gunicorn, SSL — Sprint 5)
- Figma prototype review (manual process)
- Docker/containerization (not in stack)
- Full model field definitions and business logic — only aggregate root scaffolding

## Capabilities

### New Capabilities
- `project-infrastructure`: Repository config, CI pipeline, dev environment setup
- `django-project-config`: Django settings module (base/dev/prod), PostgreSQL, env vars
- `ddd-architecture`: DDD layer structure, app scaffolding, aggregate root models
- `ui-layout`: Base templates, corporate styling, role-based navigation, admin branding

### Modified Capabilities
None — greenfield project.

## Approach

Sequential build following dependency chain: SP0-01 → SP0-02 → SP0-03 → SP0-04.

1. **SP0-01**: Create `.gitignore` (Python/Django), `requirements.txt` with pinned deps, `pyproject.toml` for tool config, `.github/workflows/ci.yml` with PostgreSQL service, `README.md`
2. **SP0-02**: `django-admin startproject config .`, split settings into `config/settings/{base,development,production}.py`, configure `DATABASES` from env vars with `python-dotenv`, create `.env.example`, run `migrate`
3. **SP0-03**: Create 5 Django apps under `apps/` with DDD subdirectories, define base models for 7 aggregates (Usuario, Periodo, Asignatura, Paralelo, Evaluacion, Asistencia, Solicitud), write `docs/arquitectura-ddd.md`
4. **SP0-04**: Create `templates/base.html` with Tailwind CDN + Alpine.js CDN + Inter font, role-based navigation (mocked — no auth yet), Django Admin customization (colors, branding)

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `.gitignore` | New | Python/Django ignore patterns |
| `.github/workflows/ci.yml` | New | CI pipeline: lint, format, test, coverage |
| `config/` | New | Django project settings (base/dev/prod), urls, wsgi, asgi |
| `apps/{usuarios,academico,calificaciones,asistencia,solicitudes}/` | New | 5 DDD-structured Django apps |
| `templates/` | New | Global templates (base.html, nav partials) |
| `static/` | New | Static assets directory structure |
| `docs/arquitectura-ddd.md` | New | DDD architecture documentation |
| `requirements.txt` | New | Pinned Python dependencies |
| `pyproject.toml` | New | Tool config (black, flake8, pytest, coverage) |
| `.env.example` | New | Environment variable template |
| `README.md` | New | Setup and contribution instructions |
| `manage.py` | New | Django management script |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| PostgreSQL not available in dev machines | Low | Document install steps in README; provide SQLite fallback for quick testing |
| CI pipeline fails on first run | Med | Test CI config locally with `act` or iterate quickly on GitHub |
| DDD over-engineering in models | Med | Keep models minimal — only aggregate identity fields and key relationships; iterate in Sprint 1+ |
| Tailwind CDN version mismatch | Low | Pin exact version 3.4.17 in CDN URL |
| Settings split breaks imports | Low | Follow Django docs pattern; test with `DJANGO_SETTINGS_MODULE` env var |

## Rollback Plan

This is a greenfield bootstrap — rollback = `git reset --hard` to the commit before this change. No existing functionality to break. Each SP0-xx item builds on the previous, so partial rollback is possible by reverting to any intermediate commit.

## Dependencies

- **SP0-01** → No dependencies (first task)
- **SP0-02** → SP0-01 (needs repo structure, requirements.txt)
- **SP0-03** → SP0-02 (needs Django project to create apps)
- **SP0-04** → SP0-02 + SP0-03 (needs Django project + app structure for templates)

External: PostgreSQL 16.x installed locally or available via service.

## Success Criteria

- [ ] `git clone` + `pip install -r requirements.txt` + `python manage.py migrate` + `python manage.py runserver` works from scratch
- [ ] GitHub Actions CI passes: flake8, black --check, pytest, coverage ≥70%
- [ ] 5 Django apps exist with DDD layer directories (`domain/`, `application/`, `infrastructure/`, `presentation/`)
- [ ] 7 aggregate root models defined and migrations generated
- [ ] `docs/arquitectura-ddd.md` documents aggregates, layers, and relationships
- [ ] `base.html` renders with corporate palette (#2D5016, #4A7C2F, #D4B942), Inter font, Tailwind CDN, Alpine.js CDN
- [ ] Role-based navigation structure visible (mocked data — no auth logic)
- [ ] Django Admin accessible at `/admin/` with project branding
- [ ] `.env.example` documents all required environment variables
- [ ] README.md has complete setup instructions
