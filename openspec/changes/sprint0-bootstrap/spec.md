# Sprint 0 Bootstrap — Specifications

**Change**: sprint0-bootstrap
**Type**: New (greenfield)
**Capabilities**: project-infrastructure, django-project-config, ddd-architecture, ui-layout

> Individual spec files: `openspec/changes/sprint0-bootstrap/specs/{capability}/spec.md`

---

## 1. project-infrastructure (SP0-01)

### Req: Git Ignore Configuration
`.gitignore` MUST cover: `__pycache__/`, `*.pyc`, `.env`, `db.sqlite3`, `media/`, `staticfiles/`, `.venv/`, `venv/`, `htmlcov/`, `.coverage`, `.pytest_cache/`, `.idea/`, `.vscode/`.

### Req: README Documentation
`README.md` MUST include: Project Description, Prerequisites, Installation, Env Vars, Running Locally, Tests, CI, Structure, Contributing.

### Req: Dependency Management
`requirements.txt` MUST pin: Django 5.1.x, psycopg2-binary 2.9.x, python-dotenv 1.1.x, djangorestframework 3.16.x, flake8 7.2.x, black 25.1.x, pytest 8.3.x, pytest-django 4.10.x, coverage 7.8.x, factory-boy 3.3.x.

### Req: Tool Configuration
`pyproject.toml` MUST configure: black (line-length=99, py312), flake8 (max-line-length=99), pytest (DJANGO_SETTINGS_MODULE), coverage (fail_under=70).

### Req: CI Pipeline
`.github/workflows/ci.yml` MUST: trigger on push/PR, use ubuntu-latest + Python 3.12 + PostgreSQL 16 service, run flake8 → black --check → migrate → coverage run -m pytest → coverage report --fail-under=70.

**Scenarios**: 8 (CI green, CI fail lint, CI fail coverage, reproducible install, linting passes, formatter idempotent, ignored files, developer onboarding)

---

## 2. django-project-config (SP0-02)

### Req: Django Project Structure
`django-admin startproject config .` → `config/` package + `manage.py` at root.

### Req: Settings Split
MUST split into `config/settings/{base,development,production}.py`. base.py has shared config; development.py sets DEBUG=True; production.py sets DEBUG=False + ALLOWED_HOSTS from env.

### Req: PostgreSQL Configuration
`DATABASES['default']` MUST use env vars: DATABASE_NAME, DATABASE_USER, DATABASE_PASSWORD, DATABASE_HOST (default localhost), DATABASE_PORT (default 5432). Engine: postgresql. No silent SQLite fallback.

### Req: Environment Variable Template
`.env.example` MUST list: DJANGO_SECRET_KEY, DJANGO_DEBUG, DJANGO_SETTINGS_MODULE, DJANGO_ALLOWED_HOSTS, DATABASE_NAME/USER/PASSWORD/HOST/PORT.

### Req: WSGI/ASGI Configuration
Both MUST default to `config.settings.development` and load python-dotenv before Django setup.

### Req: Django Admin Access
Admin MUST be at `/admin/` via `config/urls.py`.

### Req: Initial Django Apps
INSTALLED_APPS MUST register: apps.usuarios, apps.academico, apps.calificaciones, apps.asistencia, apps.solicitudes, rest_framework.

**Scenarios**: 8 (server starts, dev settings, prod settings, DB connection, missing env var, env template, WSGI works, admin renders, apps check)

---

## 3. ddd-architecture (SP0-03)

### Req: DDD Layer Structure
Each app MUST have: domain/ (models.py), application/ (services.py), infrastructure/ (repositories.py), presentation/ (views.py, urls.py). App root models.py re-exports domain models.

### Req: Five Django Apps
apps/: usuarios, academico, calificaciones, asistencia, solicitudes. Each with apps.py name='apps.<name>'.

### Req: 7 Aggregate Root Models

| Model | App | Key Fields |
|-------|-----|------------|
| Usuario | usuarios | extends AbstractUser, rol (estudiante/docente/inspector) |
| Periodo | academico | nombre (unique), fecha_inicio, fecha_fin, activo |
| Asignatura | academico | nombre, codigo (unique), descripcion |
| Paralelo | academico | FK asignatura, FK periodo, FK docente (limit docente), nombre, horario |
| Evaluacion | calificaciones | FK paralelo, tipo (parcial1/parcial2_10h/parcial3/parcial4_10h/proyecto/examen), peso, fecha |
| Asistencia | asistencia | FK estudiante (limit estudiante), FK paralelo, fecha, estado (presente/ausente/justificado), unique_together |
| Solicitud | solicitudes | tipo (rectificacion/justificacion), FK estudiante, estado (pendiente/aprobada/rechazada), descripcion, fecha_creacion |

### Req: Architecture Documentation
`docs/arquitectura-ddd.md` MUST document layers, bounded contexts, aggregates with fields, and relationships.

**Scenarios**: 11 (layers exist, models discoverable, create user with role, reject no role, create periodo, create asignatura, create paralelo, create evaluacion, record attendance, reject duplicate, create solicitud, doc coverage)

---

## 4. ui-layout (SP0-04)

### Req: Base Template
`templates/base.html` MUST include: Tailwind 3.4.17 CDN, Alpine.js 3.15.9 CDN (defer), Inter font from Google Fonts, blocks for title/content/extra_js.

### Req: Tailwind Corporate Palette
Inline Tailwind config MUST extend theme: primary=#2D5016, secondary=#4A7C2F, accent=#D4B942. Usable as bg-primary, text-accent, etc.

### Req: Navbar Partial
`templates/partials/navbar.html` MUST use Alpine.js x-data for hamburger toggle. Role-based links: Estudiante (calificaciones, asistencia, solicitudes), Docente (paralelos, registrar calif, registrar asist), Inspector (gestion, reportes, solicitudes pendientes). Accepts mocked role context.

### Req: Login Page Placeholder
`templates/registration/login.html` MUST extend base.html with styled form (username/password + corporate-colored submit). MAY be non-functional.

### Req: Django Admin Branding
site_header="ECPPP - Plataforma Academica", site_title="ECPPP Admin", index_title="Panel de Administracion".

### Req: Template Directory Configuration
TEMPLATES DIRS MUST include BASE_DIR/'templates'.

**Scenarios**: 6 (base renders, corporate colors, mobile toggle, role links, login accessible, admin branding)

---

## Cross-Cutting Dependencies

```
SP0-01 → SP0-02 → SP0-03 → SP0-04
```

## Totals

| Capability | Requirements | Scenarios |
|------------|-------------|-----------|
| project-infrastructure | 5 | 8 |
| django-project-config | 7 | 9 |
| ddd-architecture | 4 (+7 models) | 12 |
| ui-layout | 6 | 6 |
| **Total** | **22** | **35** |
