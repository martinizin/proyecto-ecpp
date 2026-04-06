# django-project-config Specification (SP0-02)

## Purpose

Django project creation with split settings, PostgreSQL configuration via environment variables, and development environment setup.

## Requirements

### Requirement: Django Project Structure

The project MUST be created with `django-admin startproject config .` producing `config/` as the project package and `manage.py` at the repository root.

#### Scenario: Project starts successfully

- GIVEN the Django project is created and dependencies installed
- WHEN running `python manage.py runserver`
- THEN the development server starts on `http://localhost:8000` without errors

### Requirement: Settings Split

Settings MUST be split into `config/settings/base.py`, `config/settings/development.py`, and `config/settings/production.py`. The original `config/settings.py` MUST NOT exist.

`base.py` MUST contain all shared configuration: INSTALLED_APPS, MIDDLEWARE, TEMPLATES, AUTH_PASSWORD_VALIDATORS, STATIC_URL, DEFAULT_AUTO_FIELD, ROOT_URLCONF, WSGI_APPLICATION.

`development.py` MUST import from base, set `DEBUG=True`, and use `ALLOWED_HOSTS=['localhost', '127.0.0.1']`.

`production.py` MUST import from base, set `DEBUG=False`, and read `ALLOWED_HOSTS` from env var.

`config/settings/__init__.py` MUST be empty (no auto-imports).

#### Scenario: Development settings active by default

- GIVEN `DJANGO_SETTINGS_MODULE=config.settings.development` in `.env`
- WHEN running `python manage.py runserver`
- THEN DEBUG is True and localhost is allowed

#### Scenario: Production settings disable debug

- GIVEN `DJANGO_SETTINGS_MODULE=config.settings.production` in `.env`
- WHEN the application loads settings
- THEN DEBUG is False

### Requirement: PostgreSQL Configuration

`base.py` MUST configure `DATABASES['default']` using environment variables loaded via `python-dotenv`: `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST` (default: `localhost`), `DATABASE_PORT` (default: `5432`). Engine MUST be `django.db.backends.postgresql`.

#### Scenario: Database connection via env vars

- GIVEN valid PostgreSQL credentials in `.env`
- WHEN running `python manage.py migrate`
- THEN Django connects to PostgreSQL and applies all migrations without errors

#### Scenario: Missing database env var

- GIVEN `DATABASE_NAME` is not set in the environment
- WHEN running `python manage.py migrate`
- THEN Django raises a configuration error (no silent fallback to SQLite)

### Requirement: Environment Variable Template

The repository MUST include `.env.example` with ALL required variables and placeholder values (no real secrets).

Required variables: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_SETTINGS_MODULE`, `DJANGO_ALLOWED_HOSTS`, `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT`.

#### Scenario: Developer configures environment

- GIVEN a developer copies `.env.example` to `.env`
- WHEN they fill in their local PostgreSQL credentials and run the project
- THEN the project starts and connects to the database

### Requirement: WSGI and ASGI Configuration

`config/wsgi.py` and `config/asgi.py` MUST exist and set `DJANGO_SETTINGS_MODULE` defaulting to `config.settings.development`. Both MUST load `python-dotenv` before Django setup.

#### Scenario: WSGI entry point works

- GIVEN the project is properly configured
- WHEN a WSGI server (e.g., Gunicorn) loads `config.wsgi:application`
- THEN the application serves requests

### Requirement: Django Admin Access

Django Admin MUST be accessible at `/admin/`. The `config/urls.py` MUST include `admin.site.urls` at the `admin/` path.

#### Scenario: Admin login page renders

- GIVEN the project is running
- WHEN navigating to `http://localhost:8000/admin/`
- THEN the Django Admin login page renders

### Requirement: Initial Django Apps

`config/settings/base.py` MUST register 5 project apps in INSTALLED_APPS: `apps.usuarios`, `apps.academico`, `apps.calificaciones`, `apps.asistencia`, `apps.solicitudes`. Third-party app `rest_framework` MUST also be registered.

#### Scenario: All apps recognized

- GIVEN all 5 apps are created under `apps/`
- WHEN running `python manage.py check`
- THEN Django reports no issues with app configuration

## Files Affected

| File | Action |
|------|--------|
| `config/__init__.py` | Create |
| `config/settings/__init__.py` | Create |
| `config/settings/base.py` | Create |
| `config/settings/development.py` | Create |
| `config/settings/production.py` | Create |
| `config/urls.py` | Create |
| `config/wsgi.py` | Create |
| `config/asgi.py` | Create |
| `manage.py` | Create |
| `.env.example` | Create |

## Dependencies

- **project-infrastructure** (SP0-01): requires `requirements.txt` and `pyproject.toml` to exist.
