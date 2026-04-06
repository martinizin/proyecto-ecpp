# Tasks: Sprint 0 Bootstrap

## Phase 1: Project Infrastructure (SP0-01)

- [x] 1.1 Create `.gitignore` — Python/Django patterns: `__pycache__/`, `*.pyc`, `.env`, `db.sqlite3`, `media/`, `staticfiles/`, `.venv/`, `venv/`, `htmlcov/`, `.coverage`, `.pytest_cache/`, `.idea/`, `.vscode/`
- [x] 1.2 Create `requirements.txt` — pin: Django==5.1.7, psycopg2-binary==2.9.10, python-dotenv==1.1.0, djangorestframework==3.16.0, flake8==7.2.0, black==25.1.0, pytest==8.3.5, pytest-django==4.10.0, coverage==7.8.0, factory-boy==3.3.1
- [x] 1.3 Create `pyproject.toml` + `.flake8` — black (line-length=99, py312), flake8 via .flake8 (max-line-length=99), pytest (DJANGO_SETTINGS_MODULE=config.settings.development, pythonpath=.), coverage (source=apps, fail_under=70)
- [x] 1.4 Create `.github/workflows/ci.yml` — ubuntu-latest, Python 3.12, PostgreSQL 16 service, steps: pip install → flake8 → black --check → migrate → coverage run -m pytest → coverage report --fail-under=70
- [x] 1.5 Create `README.md` — project description, prerequisites, install steps, env vars, run locally, tests, CI, structure, contributing

**Verify**: All 5 files exist at expected paths; `requirements.txt` has exactly 10 pinned deps.

## Phase 2: Django Project Setup (SP0-02)

- [x] 2.1 Create `manage.py` + `config/` package — `config/__init__.py`, load dotenv before `django.setup()`
- [x] 2.2 Create `config/settings/base.py` — `AUTH_USER_MODEL='usuarios.Usuario'`, DATABASES from env vars (postgresql only), INSTALLED_APPS with 5 apps + rest_framework, TEMPLATES DIRS=[BASE_DIR/'templates']
- [x] 2.3 Create `config/settings/development.py` — `from .base import *`, DEBUG=True
- [x] 2.4 Create `config/settings/production.py` — `from .base import *`, DEBUG=False, ALLOWED_HOSTS from env, secure cookies
- [x] 2.5 Create `config/settings/__init__.py` (empty)
- [x] 2.6 Create `config/urls.py` — admin.site at `/admin/`, home placeholder view
- [x] 2.7 Create `config/wsgi.py` + `config/asgi.py` — load dotenv, default DJANGO_SETTINGS_MODULE=config.settings.development
- [x] 2.8 Create `.env.example` — 9 vars: DJANGO_SECRET_KEY, DJANGO_DEBUG, DJANGO_SETTINGS_MODULE, DJANGO_ALLOWED_HOSTS, DATABASE_NAME/USER/PASSWORD/HOST/PORT

**Verify**: `python manage.py check --settings=config.settings.development` passes (needs DB + apps from Phase 3).

## Phase 3: DDD Architecture & Models (SP0-03)

- [x] 3.1 Create 5 app directories with DDD layers — each app: `admin.py`, `models.py` (re-exports), `domain/{__init__,entities,value_objects,repositories,exceptions}.py`, `application/{__init__,services}.py`, `infrastructure/{__init__,models,repositories}.py`, `presentation/{__init__,views,urls,forms}.py`
- [x] 3.2 Create `apps/usuarios/infrastructure/models.py` — `Usuario(AbstractUser)` with `rol` CharField choices + `cedula` + `telefono`
- [x] 3.3 Create `apps/academico/infrastructure/models.py` — `Periodo`, `Asignatura`, `Paralelo` models with all fields/FKs per design
- [x] 3.4 Create `apps/calificaciones/infrastructure/models.py` — `Evaluacion` + `Calificacion` models with FK→Paralelo, tipo 6 choices, peso DecimalField
- [x] 3.5 Create `apps/asistencia/infrastructure/models.py` — `Asistencia` model with FK→Usuario+Paralelo, unique_together
- [x] 3.6 Create `apps/solicitudes/infrastructure/models.py` — `Solicitud` model with tipo/estado choices, FK→Usuario
- [x] 3.7 Wire all `models.py` re-exports + register all models in each `admin.py`
- [ ] 3.8 Run `makemigrations` for all 5 apps → verify migration files created
- [x] 3.9 Create `docs/arquitectura-ddd.md` — layers, bounded contexts, aggregates, relationships

**Verify**: `python manage.py migrate` succeeds; `python manage.py check` clean; 7 models in admin.

## Phase 4: UI Layout (SP0-04)

- [x] 4.1 Create `templates/base.html` — Tailwind 3.4.17 CDN, Alpine.js 3.15.9 CDN defer, Inter font, corporate palette config (primary=#2D5016, secondary=#4A7C2F, accent=#D4B942), blocks: title, extra_css, content, extra_js
- [x] 4.2 Create `templates/partials/navbar.html` — Alpine.js `x-data={open:false}` hamburger toggle, role-based links for estudiante/docente/inspector
- [x] 4.3 Create `templates/registration/login.html` — extends base.html, styled form placeholder
- [x] 4.4 Create `templates/pages/home.html` — extends base.html, placeholder content
- [x] 4.5 Create `static/css/.gitkeep` + `static/js/.gitkeep`
- [x] 4.6 Configure admin branding — site_header="ECPPP - Plataforma Academica", site_title="ECPPP Admin", index_title="Panel de Administracion"
- [x] 4.7 Wire URL routes — home page view at `/`, include login URL

**Verify**: `runserver` → home page renders with Tailwind styles; navbar toggles on mobile; `/admin/` shows branding.

## Phase 5: Testing & Verification

- [x] 5.1 Create `tests/__init__.py` + `tests/conftest.py` — pytest-django config, `@pytest.fixture` for users (estudiante, docente, inspector)
- [x] 5.2 Create `tests/factories.py` — factory-boy `DjangoModelFactory` for all 7 aggregates
- [x] 5.3 Create `tests/usuarios/test_models.py` — test Usuario creation with each role, reject blank role
- [x] 5.4 Create `tests/academico/test_models.py` — test Periodo/Asignatura/Paralelo creation, unique constraints
- [x] 5.5 Create `tests/calificaciones/test_models.py` — test Evaluacion creation, tipo choices
- [x] 5.6 Create `tests/asistencia/test_models.py` — test Asistencia creation, unique_together constraint
- [x] 5.7 Create `tests/solicitudes/test_models.py` — test Solicitud creation, default estado=pendiente
- [ ] 5.8 Verify full CI pipeline — `flake8 .` + `black --check .` + `migrate` + `coverage run -m pytest` + `coverage report --fail-under=70` all pass

**Verify**: `pytest` green; `coverage report` ≥ 70%; CI workflow would pass.
