# ddd-architecture Specification (SP0-03)

## Purpose

DDD layer structure, 5 Django apps, 7 aggregate root models with fields and relationships, and architecture documentation.

## Requirements

### Requirement: DDD Layer Structure

Each Django app under `apps/` MUST contain 4 DDD layer subdirectories: `domain/`, `application/`, `infrastructure/`, `presentation/`. Each subdirectory MUST contain an `__init__.py`.

The `domain/` layer MUST contain `models.py` (aggregate root entities). The `application/` layer MUST contain `services.py` (placeholder). The `infrastructure/` layer MUST contain `repositories.py` (placeholder). The `presentation/` layer MUST contain `views.py` and `urls.py` (placeholders).

The app's root `models.py` MUST re-export domain models (e.g., `from .domain.models import *`).

#### Scenario: Layer directories exist

- GIVEN the project is bootstrapped
- WHEN listing contents of `apps/usuarios/`
- THEN directories `domain/`, `application/`, `infrastructure/`, `presentation/` exist, each with `__init__.py`

#### Scenario: Models discoverable by Django

- GIVEN models are defined in `apps/usuarios/domain/models.py`
- WHEN running `python manage.py makemigrations`
- THEN Django discovers and generates migrations for all models

### Requirement: Five Django Apps

The project MUST contain exactly 5 apps under `apps/`: `usuarios`, `academico`, `calificaciones`, `asistencia`, `solicitudes`. Each app MUST have an `apps.py` with `name = 'apps.<app_name>'`.

| App | Aggregate Roots | Bounded Context |
|-----|-----------------|-----------------|
| usuarios | Usuario | User identity and roles |
| academico | Periodo, Asignatura, Paralelo | Academic structure |
| calificaciones | Evaluacion | Grading |
| asistencia | Asistencia | Attendance tracking |
| solicitudes | Solicitud | Student requests |

#### Scenario: All apps created

- GIVEN the project structure is complete
- WHEN running `python manage.py check`
- THEN all 5 apps are recognized without errors

### Requirement: Usuario Aggregate Root

`apps/usuarios/domain/models.py` MUST define `Usuario` extending `AbstractUser`. It MUST add a `rol` field as CharField with choices: `estudiante`, `docente`, `inspector`. The `rol` field MUST NOT be blank or null. `__str__` MUST return `"{username} ({rol})"`.

#### Scenario: Create user with role

- GIVEN the Usuario model is migrated
- WHEN creating a Usuario with `username="jperez"`, `rol="estudiante"`
- THEN the user is saved and `str(user)` returns `"jperez (estudiante)"`

#### Scenario: Reject user without role

- GIVEN the Usuario model
- WHEN attempting to create a Usuario with `rol=""`
- THEN a validation error is raised

### Requirement: Periodo Aggregate Root

`apps/academico/domain/models.py` MUST define `Periodo` with fields: `nombre` (CharField, max_length=100, unique), `fecha_inicio` (DateField), `fecha_fin` (DateField), `activo` (BooleanField, default=False). `__str__` MUST return `nombre`.

#### Scenario: Create academic period

- GIVEN the Periodo model is migrated
- WHEN creating a Periodo with `nombre="2026-I"`, start/end dates, `activo=True`
- THEN the record is persisted and `str(periodo)` returns `"2026-I"`

### Requirement: Asignatura Aggregate Root

`apps/academico/domain/models.py` MUST define `Asignatura` with fields: `nombre` (CharField, max_length=200), `codigo` (CharField, max_length=20, unique), `descripcion` (TextField, blank=True). `__str__` MUST return `"{codigo} - {nombre}"`.

#### Scenario: Create subject with code

- GIVEN the Asignatura model is migrated
- WHEN creating Asignatura with `codigo="MAT101"`, `nombre="Matematicas I"`
- THEN the record is persisted and `str(a)` returns `"MAT101 - Matematicas I"`

### Requirement: Paralelo Aggregate Root

`apps/academico/domain/models.py` MUST define `Paralelo` with fields: `asignatura` (FK to Asignatura), `periodo` (FK to Periodo), `docente` (FK to Usuario, limit_choices_to `{'rol': 'docente'}`), `nombre` (CharField, max_length=10, e.g. "A", "B"), `horario` (TextField, blank=True). `__str__` MUST return `"{asignatura.codigo} - Paralelo {nombre}"`.

#### Scenario: Create paralelo linked to subject and teacher

- GIVEN Asignatura, Periodo, and a docente Usuario exist
- WHEN creating a Paralelo linking them
- THEN the record is persisted with valid FK relationships

### Requirement: Evaluacion Aggregate Root

`apps/calificaciones/domain/models.py` MUST define `Evaluacion` with fields: `paralelo` (FK to Paralelo), `tipo` (CharField with choices: `parcial1`, `parcial2_10h`, `parcial3`, `parcial4_10h`, `proyecto`, `examen`), `peso` (DecimalField, max_digits=5, decimal_places=2), `fecha` (DateField, null=True, blank=True). `__str__` MUST return `"{paralelo} - {get_tipo_display()}"`.

#### Scenario: Create evaluation with type

- GIVEN a Paralelo exists
- WHEN creating an Evaluacion with `tipo="parcial2_10h"`, `peso=20.00`
- THEN the record is persisted and type display is human-readable

### Requirement: Asistencia Aggregate Root

`apps/asistencia/domain/models.py` MUST define `Asistencia` with fields: `estudiante` (FK to Usuario, limit_choices_to `{'rol': 'estudiante'}`), `paralelo` (FK to Paralelo), `fecha` (DateField), `estado` (CharField with choices: `presente`, `ausente`, `justificado`). A unique_together constraint MUST enforce `(estudiante, paralelo, fecha)`.

#### Scenario: Record attendance

- GIVEN a student and paralelo exist
- WHEN recording attendance for a specific date
- THEN the record is persisted with the given estado

#### Scenario: Reject duplicate attendance

- GIVEN attendance for student X, paralelo Y, date Z already exists
- WHEN attempting to create another record with the same combination
- THEN an IntegrityError is raised

### Requirement: Solicitud Aggregate Root

`apps/solicitudes/domain/models.py` MUST define `Solicitud` with fields: `tipo` (CharField with choices: `rectificacion`, `justificacion`), `estudiante` (FK to Usuario, limit_choices_to `{'rol': 'estudiante'}`), `estado` (CharField with choices: `pendiente`, `aprobada`, `rechazada`, default=`pendiente`), `descripcion` (TextField), `fecha_creacion` (DateTimeField, auto_now_add=True). `__str__` MUST return `"{tipo} - {estudiante.username} ({estado})"`.

#### Scenario: Student creates request

- GIVEN a student Usuario exists
- WHEN creating a Solicitud with `tipo="justificacion"`
- THEN `estado` defaults to `"pendiente"` and `fecha_creacion` is auto-set

### Requirement: Architecture Documentation

The project MUST include `docs/arquitectura-ddd.md` documenting: DDD layer definitions (presentation, application, domain, infrastructure), the 5 bounded contexts and their aggregate roots, model relationships, and the Django-to-DDD mapping convention.

#### Scenario: Documentation covers all aggregates

- GIVEN the documentation file exists
- WHEN reading `docs/arquitectura-ddd.md`
- THEN all 7 aggregates (Usuario, Periodo, Asignatura, Paralelo, Evaluacion, Asistencia, Solicitud) are documented with their fields and relationships

## Files Affected

| File | Action |
|------|--------|
| `apps/__init__.py` | Create |
| `apps/{app}/` (x5) with DDD layers | Create |
| `apps/usuarios/domain/models.py` | Create |
| `apps/academico/domain/models.py` | Create |
| `apps/calificaciones/domain/models.py` | Create |
| `apps/asistencia/domain/models.py` | Create |
| `apps/solicitudes/domain/models.py` | Create |
| `docs/arquitectura-ddd.md` | Create |

## Dependencies

- **django-project-config** (SP0-02): requires Django project and settings to exist.
