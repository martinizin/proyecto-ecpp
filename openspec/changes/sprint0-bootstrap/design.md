# Design: Sprint 0 Bootstrap

## Technical Approach

Bootstrap a greenfield Django 5.1.x/DDD monolith with 5 bounded-context apps, 7 aggregate models, split settings, GitHub Actions CI, and a Tailwind+Alpine CDN-based template layer. Follows the sequential chain SP0-01→02→03→04 from the proposal. All models live in `infrastructure/` (Django ORM); `domain/` stays pure Python.

## Architecture Decisions

| # | Decision | Choice | Alternatives Rejected | Rationale |
|---|----------|--------|-----------------------|-----------|
| AD-1 | CSS/JS delivery | Tailwind 3.4.17 + Alpine.js 3.15.9 via CDN `<script>` tags | npm build pipeline, PostCSS CLI | 2-dev team, no frontend build tooling needed; CDN avoids node dependency; pin exact versions in URL for reproducibility. Trade-off: no tree-shaking (acceptable — prototyping stage). |
| AD-2 | Settings architecture | `config/settings/{base,development,production}.py` module | Single `settings.py` with if/else, django-environ | Module pattern is Django-recommended; each env file inherits `base.py` cleanly; `python-dotenv` loads `.env` before Django setup in `manage.py`/`wsgi.py`/`asgi.py`. |
| AD-3 | Domain layer purity | `domain/` = pure Python only (no Django imports) | Domain entities as Django models directly | DDD principle: domain logic must be testable without Django. `domain/entities.py` defines plain classes/dataclasses; `infrastructure/django_models.py` defines the ORM models. App-root `models.py` re-exports from infrastructure for Django's model discovery. |
| AD-4 | User model | Extend `AbstractUser` with `rol` CharField choices | Custom user from `AbstractBaseUser`, separate Profile model | `AbstractUser` provides full auth machinery (password hashing, permissions) out of the box. Adding `rol` as a field is simpler than a separate Profile table for 3 roles. Must be set BEFORE first migration (`AUTH_USER_MODEL`). |
| AD-5 | App placement | `apps/` directory with AppConfig `name='apps.<app>'` | Apps at project root, namespace packages | Keeps root clean; all 5 bounded contexts under one directory; standard Django pattern with explicit AppConfig. |
| AD-6 | Database | PostgreSQL 16 only — no SQLite fallback | SQLite for dev, PostgreSQL for prod | Spec explicitly says "No silent SQLite fallback." Avoids behavior divergence between dev/CI/prod. |

## Directory Structure

```
proyecto-ecpp/
├── .github/workflows/ci.yml
├── .env.example
├── .gitignore
├── manage.py
├── pyproject.toml
├── requirements.txt
├── README.md
├── config/
│   ├── __init__.py
│   ├── urls.py
│   ├── wsgi.py
│   ├── asgi.py
│   └── settings/
│       ├── __init__.py
│       ├── base.py
│       ├── development.py
│       └── production.py
├── apps/
│   ├── __init__.py
│   ├── usuarios/           # Aggregate: Usuario
│   │   ├── __init__.py
│   │   ├── apps.py         # name='apps.usuarios'
│   │   ├── admin.py
│   │   ├── models.py       # re-exports from infrastructure
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   └── entities.py     # pure Python Usuario entity
│   │   ├── application/
│   │   │   ├── __init__.py
│   │   │   └── services.py
│   │   ├── infrastructure/
│   │   │   ├── __init__.py
│   │   │   ├── django_models.py  # Django ORM model
│   │   │   └── repositories.py
│   │   └── presentation/
│   │       ├── __init__.py
│   │       ├── views.py
│   │       ├── urls.py
│   │       └── forms.py
│   ├── academico/          # Aggregates: Periodo, Asignatura, Paralelo
│   │   └── (same DDD layer structure)
│   ├── calificaciones/     # Aggregate: Evaluacion
│   │   └── (same DDD layer structure)
│   ├── asistencia/         # Aggregate: Asistencia
│   │   └── (same DDD layer structure)
│   └── solicitudes/        # Aggregate: Solicitud
│       └── (same DDD layer structure)
├── templates/
│   ├── base.html
│   ├── partials/
│   │   └── navbar.html
│   └── registration/
│       └── login.html
├── static/
│   ├── css/
│   └── js/
├── docs/
│   ├── PRDSprint0ECPPP.md
│   └── arquitectura-ddd.md
└── tests/
    ├── __init__.py
    ├── conftest.py           # pytest-django config, shared fixtures
    ├── factories.py          # factory-boy factories for all aggregates
    ├── usuarios/
    │   └── test_models.py
    ├── academico/
    │   └── test_models.py
    ├── calificaciones/
    │   └── test_models.py
    ├── asistencia/
    │   └── test_models.py
    └── solicitudes/
        └── test_models.py
```

## Data Model Design

```
┌──────────────┐
│   Usuario    │  AUTH_USER_MODEL = 'usuarios.Usuario'
│  (AbstractUser)
│  + rol       │──────────────────────────────────┐
└──────┬───────┘                                  │
       │ FK (docente, limit_choices_to=docente)   │ FK (estudiante)
       ▼                                          ▼
┌──────────────┐  FK   ┌──────────────┐   ┌──────────────┐
│  Paralelo    │◄──────│  Evaluacion  │   │  Asistencia  │
│  + nombre    │       │  + tipo      │   │  + fecha     │
│  + horario   │       │  + peso      │   │  + estado    │
└──┬───┬───────┘       │  + fecha     │   │  unique:     │
   │   │               └──────────────┘   │  (est,par,f) │
   │   │ FK                               └──────────────┘
   │   ▼                                         ▲ FK
   │ ┌──────────────┐                    ┌──────────────┐
   │ │  Periodo     │                    │  Solicitud   │
   │ │  + nombre ᵘ  │                    │  + tipo      │
   │ │  + activo    │                    │  + estado    │
   │ └──────────────┘                    │  + desc      │
   │ FK                                  └──────────────┘
   ▼
┌──────────────┐
│ Asignatura   │
│ + codigo ᵘ   │
│ + nombre     │
└──────────────┘
  ᵘ = unique
```

### Model Fields (all in `infrastructure/django_models.py`)

**Usuario** (apps.usuarios) — extends `AbstractUser`:
- `rol`: CharField(max_length=20, choices=[estudiante, docente, inspector])

**Periodo** (apps.academico):
- `nombre`: CharField(max_length=100, unique=True)
- `fecha_inicio`: DateField
- `fecha_fin`: DateField
- `activo`: BooleanField(default=False)

**Asignatura** (apps.academico):
- `nombre`: CharField(max_length=200)
- `codigo`: CharField(max_length=20, unique=True)
- `descripcion`: TextField(blank=True)

**Paralelo** (apps.academico):
- `asignatura`: FK → Asignatura (CASCADE)
- `periodo`: FK → Periodo (CASCADE)
- `docente`: FK → Usuario (CASCADE, limit_choices_to={'rol': 'docente'})
- `nombre`: CharField(max_length=10) — e.g. "A", "B"
- `horario`: CharField(max_length=100, blank=True)

**Evaluacion** (apps.calificaciones):
- `paralelo`: FK → Paralelo (CASCADE)
- `tipo`: CharField(max_length=20, choices=[parcial1, parcial2_10h, parcial3, parcial4_10h, proyecto, examen])
- `peso`: DecimalField(max_digits=5, decimal_places=2)
- `fecha`: DateField

**Asistencia** (apps.asistencia):
- `estudiante`: FK → Usuario (CASCADE, limit_choices_to={'rol': 'estudiante'})
- `paralelo`: FK → Paralelo (CASCADE)
- `fecha`: DateField
- `estado`: CharField(max_length=20, choices=[presente, ausente, justificado])
- `class Meta: unique_together = [('estudiante', 'paralelo', 'fecha')]`

**Solicitud** (apps.solicitudes):
- `tipo`: CharField(max_length=20, choices=[rectificacion, justificacion])
- `estudiante`: FK → Usuario (CASCADE, limit_choices_to={'rol': 'estudiante'})
- `estado`: CharField(max_length=20, choices=[pendiente, aprobada, rechazada], default='pendiente')
- `descripcion`: TextField
- `fecha_creacion`: DateTimeField(auto_now_add=True)

## Settings Architecture

```python
# config/settings/base.py — shared
import os
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']
INSTALLED_APPS = [
    'django.contrib.admin', ...,
    'rest_framework',
    'apps.usuarios', 'apps.academico', 'apps.calificaciones',
    'apps.asistencia', 'apps.solicitudes',
]
AUTH_USER_MODEL = 'usuarios.Usuario'
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DATABASE_NAME'],
        'USER': os.environ['DATABASE_USER'],
        'PASSWORD': os.environ['DATABASE_PASSWORD'],
        'HOST': os.environ.get('DATABASE_HOST', 'localhost'),
        'PORT': os.environ.get('DATABASE_PORT', '5432'),
    }
}
TEMPLATES = [{ 'DIRS': [BASE_DIR / 'templates'], ... }]

# config/settings/development.py
from .base import *
DEBUG = True

# config/settings/production.py
from .base import *
DEBUG = False
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
```

## CI Pipeline Architecture

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env: { POSTGRES_DB: ecppp_test, POSTGRES_USER: test_user, POSTGRES_PASSWORD: test_pass }
        ports: ['5432:5432']
        options: --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5
    env:
      DATABASE_NAME: ecppp_test
      DATABASE_USER: test_user
      DATABASE_PASSWORD: test_pass
      DATABASE_HOST: localhost
      DATABASE_PORT: 5432
      DJANGO_SECRET_KEY: test-secret-key-ci-only
      DJANGO_SETTINGS_MODULE: config.settings.development
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r requirements.txt
      - run: flake8 .
      - run: black --check .
      - run: python manage.py migrate
      - run: coverage run -m pytest
      - run: coverage report --fail-under=70
```

## Template Architecture

**base.html** blocks: `{% block title %}`, `{% block extra_css %}`, `{% block content %}`, `{% block extra_js %}`

```html
<!-- Key head elements -->
<script src="https://cdn.tailwindcss.com/3.4.17"></script>
<script>
  tailwind.config = {
    theme: { extend: { colors: {
      primary: '#2D5016', secondary: '#4A7C2F', accent: '#D4B942'
    }}}
  }
</script>
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.15.9/dist/cdn.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
```

**navbar.html**: Alpine.js `x-data="{ open: false }"` for mobile toggle. Role-based links rendered via template context variable `user_role` (mocked in Sprint 0).

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit (domain) | Entity creation, validation, value objects | pytest — pure Python, no DB |
| Unit (models) | ORM model constraints, choices, unique_together | pytest-django with `@pytest.mark.django_db` |
| Integration | Migrations apply cleanly, FK constraints | `manage.py migrate` in CI |
| Factories | All 7 aggregates have working factories | factory-boy `DjangoModelFactory` |

**conftest.py**: `@pytest.fixture` for `django_settings_module`, shared user fixtures.
**Coverage target**: ≥70% on domain layer (CI enforced via `--fail-under=70`).

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `.gitignore` | Create | Python/Django patterns (pycache, .env, venv, coverage) |
| `.env.example` | Create | 9 env vars template |
| `requirements.txt` | Create | 10 pinned dependencies |
| `pyproject.toml` | Create | black, flake8, pytest, coverage config |
| `README.md` | Create | Full setup guide |
| `.github/workflows/ci.yml` | Create | CI pipeline with PostgreSQL 16 |
| `manage.py` | Create | Django management, loads dotenv |
| `config/settings/{base,development,production}.py` | Create | Split settings with AUTH_USER_MODEL |
| `config/{urls,wsgi,asgi,__init__}.py` | Create | Django project plumbing |
| `apps/{5 apps}/` with DDD layers | Create | 5 apps × 4 layers = 20 packages |
| `templates/{base,partials/navbar,registration/login}.html` | Create | UI layout with CDN assets |
| `static/{css,js}/` | Create | Empty asset directories with .gitkeep |
| `docs/arquitectura-ddd.md` | Create | DDD architecture documentation |
| `tests/conftest.py` + `tests/factories.py` | Create | Test infrastructure |
| `tests/{5 apps}/test_models.py` | Create | Model tests per aggregate |

**Totals**: ~55 new files, 0 modified, 0 deleted.

## Migration / Rollout

No migration from existing data — greenfield project. First `migrate` creates all tables. `AUTH_USER_MODEL` MUST be set before first migration (AD-4). Rollback = `git reset --hard` to pre-bootstrap commit.

## Open Questions

- None — all stack decisions confirmed per PRD §6.B. Design is ready for task breakdown.
