# project-infrastructure Specification (SP0-01)

## Purpose

Repository configuration, CI pipeline, dependency management, and development environment setup for a Python 3.12 / Django 5.1 project.

## Requirements

### Requirement: Git Ignore Configuration

The repository MUST include a `.gitignore` file covering Python/Django patterns.

Entries MUST include: `__pycache__/`, `*.pyc`, `*.pyo`, `.env`, `db.sqlite3`, `*.sqlite3`, `media/`, `staticfiles/`, `.venv/`, `venv/`, `*.egg-info/`, `dist/`, `build/`, `htmlcov/`, `.coverage`, `.pytest_cache/`, `*.log`, `.idea/`, `.vscode/`, `*.swp`.

#### Scenario: Ignored files not tracked

- GIVEN a fresh clone of the repository
- WHEN a developer creates a virtual environment and runs the project
- THEN `__pycache__/`, `.env`, `db.sqlite3`, `.venv/` MUST NOT appear in `git status`

### Requirement: README Documentation

The repository MUST include a `README.md` with sections: Project Description, Prerequisites (Python 3.12, PostgreSQL 16), Installation Steps, Environment Variables, Running Locally, Running Tests, CI Pipeline, Project Structure, Contributing.

#### Scenario: Developer onboarding

- GIVEN a new developer clones the repository
- WHEN they follow README.md instructions sequentially
- THEN they MUST be able to install dependencies, configure `.env`, run migrations, and start the server without external help

### Requirement: Dependency Management

The repository MUST include `requirements.txt` with ALL dependencies pinned to exact versions.

Required packages: `Django==5.1.*`, `psycopg2-binary==2.9.*`, `python-dotenv==1.1.*`, `djangorestframework==3.16.*`, `flake8==7.2.*`, `black==25.1.*`, `pytest==8.3.*`, `pytest-django==4.10.*`, `coverage==7.8.*`, `factory-boy==3.3.*`.

#### Scenario: Reproducible install

- GIVEN a clean Python 3.12 virtual environment
- WHEN running `pip install -r requirements.txt`
- THEN all packages install without conflicts and with deterministic versions

### Requirement: Tool Configuration

The repository MUST include `pyproject.toml` with configuration for: black (line-length=99, target-version py312), flake8 (max-line-length=99, exclude=migrations), pytest (DJANGO_SETTINGS_MODULE, pythonpath, testpaths), coverage (source, omit patterns, fail_under=70).

#### Scenario: Linting passes on clean project

- GIVEN a freshly generated Django project formatted with black
- WHEN running `flake8 .`
- THEN zero violations are reported

#### Scenario: Formatter is idempotent

- GIVEN a project formatted with `black .`
- WHEN running `black --check .`
- THEN exit code is 0 (no changes needed)

### Requirement: CI Pipeline

The repository MUST include `.github/workflows/ci.yml` that triggers on push and pull_request events. The pipeline MUST run on `ubuntu-latest` with Python 3.12 and a PostgreSQL 16 service container.

Pipeline steps MUST execute in order: checkout, setup Python, install dependencies, run `flake8 .`, run `black --check .`, run `python manage.py migrate`, run `coverage run -m pytest`, run `coverage report --fail-under=70`.

The PostgreSQL service MUST use health checks (`pg_isready`) and expose port 5432. Database credentials MUST be passed via environment variables.

#### Scenario: CI green on compliant code

- GIVEN code that passes linting, formatting, and tests with >=70% coverage
- WHEN a push or PR is made
- THEN the CI pipeline completes successfully (exit code 0)

#### Scenario: CI fails on lint violation

- GIVEN code with a flake8 violation
- WHEN the CI pipeline runs
- THEN the pipeline fails at the flake8 step

#### Scenario: CI fails on low coverage

- GIVEN tests that achieve <70% coverage
- WHEN the CI pipeline runs
- THEN the pipeline fails at the coverage report step

## Files Affected

| File | Action |
|------|--------|
| `.gitignore` | Create |
| `README.md` | Create |
| `requirements.txt` | Create |
| `pyproject.toml` | Create |
| `.github/workflows/ci.yml` | Create |

## Dependencies

None — this is the first capability in the chain.
