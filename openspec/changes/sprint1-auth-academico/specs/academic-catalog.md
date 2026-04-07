# Capability: academic-catalog

## Purpose

Management of the academic catalog: license types (TipoLicencia), subjects (Asignatura) with M2M association to license types, and parallels (Paralelo) with teacher assignment. Inspector-only access with REST API endpoints and filtering.

## Requirements

### Requirement: License Type Management (TipoLicencia)

The system MUST provide a `TipoLicencia` model with: nombre, codigo (unique), duracion_meses, num_asignaturas, and activo. The system MUST seed initial data via data migration: Tipo C (codigo='C', 6 meses, 13 asignaturas), Tipo E (codigo='E', 5 meses, 17 asignaturas), Tipo E Convalidada (codigo='EC', duracion_meses TBD, 8 asignaturas). License types SHOULD be read-only in the UI (managed via seed data), but the system MAY allow Inspector to update them. (Source: HU06, RR006)

#### Scenario: SCN-CAT-01 — List license types with seed data

- GIVEN the system has been initialized with data migration
- WHEN the Inspector navigates to the license types view
- THEN the system displays Tipo C, Tipo E, and Tipo E Convalidada with their attributes

#### Scenario: SCN-CAT-02 — License types available via API

- GIVEN I am authenticated as Inspector
- WHEN I perform GET on `/api/tipos-licencia/`
- THEN the system returns the list of license types with nombre, codigo, duracion_meses, num_asignaturas, activo

### Requirement: Subject CRUD with License Type Association

The system MUST allow the Inspector to create, read, update, and delete subjects (Asignatura). Each subject MUST have: nombre, codigo (unique), horas_lectivas (default 40). Each subject MUST be associated to one or more TipoLicencia via ManyToManyField (Decision D5). The system MUST validate: codigo unique, horas_lectivas > 0, at least one TipoLicencia associated. The system MUST restrict operations to Inspector role. (Source: HU06, RR006)

#### Scenario: SCN-CAT-03 — Create subject and associate to license type

- GIVEN I am on the 'Asignaturas' tab of the 'Gestion Academica' module
- WHEN I create a subject with nombre, codigo, 40 horas lectivas, and associate it to 'Tipo C'
- THEN the system saves the subject, links it to the license type, and it becomes available for parallels

#### Scenario: SCN-CAT-04 — Subject associated to multiple license types

- GIVEN I am creating a subject 'Legislacion de Transito'
- WHEN I associate it to both 'Tipo C' and 'Tipo E'
- THEN the system saves the M2M relationship and the subject appears under both license types

#### Scenario: SCN-CAT-05 — Subject creation fails due to duplicate codigo

- GIVEN a subject with codigo 'LEG-001' already exists
- WHEN I attempt to create another subject with the same codigo
- THEN the system rejects the creation and shows a uniqueness error

#### Scenario: SCN-CAT-06 — Subject creation fails with invalid horas_lectivas

- GIVEN I am creating a subject
- WHEN I enter horas_lectivas <= 0
- THEN the system rejects the creation and shows a validation error

### Requirement: Parallel CRUD with Teacher Assignment

The system MUST allow the Inspector to create, read, update, and delete parallels (Paralelo). Each parallel MUST be associated to: an active period, a TipoLicencia, an Asignatura, a docente (teacher), and a horario. The system MUST validate that the assigned user has `rol='docente'`. The system MUST validate uniqueness of the combination (periodo, tipo_licencia, asignatura, nombre). Each parallel MUST have a capacidad_maxima field. The system MUST restrict operations to Inspector role. (Source: HU06, RR007)

#### Scenario: SCN-CAT-07 — Create parallel with teacher assignment

- GIVEN subjects and registered teachers exist in the active period
- WHEN I create a parallel selecting periodo, tipo_licencia, asignatura, horario, and a docente
- THEN the system saves the parallel and enables it for future student enrollment and attendance/grade recording

#### Scenario: SCN-CAT-08 — Parallel creation fails with non-docente user

- GIVEN I am creating a parallel
- WHEN I assign a user whose rol is NOT 'docente'
- THEN the system rejects the creation and shows a validation error indicating the user must be a docente

#### Scenario: SCN-CAT-09 — Parallel requires active period

- GIVEN no period is currently active
- WHEN I attempt to create a parallel
- THEN the system prevents creation and shows an error indicating an active period is required

#### Scenario: SCN-CAT-10 — Duplicate parallel combination rejected

- GIVEN a parallel exists for (Periodo 2026-A, Tipo C, Legislacion, Paralelo A)
- WHEN I attempt to create another with the same combination
- THEN the system rejects the creation and shows a uniqueness error

### Requirement: Academic Catalog REST API with Filters

The system MUST expose REST API endpoints: `/api/asignaturas/`, `/api/paralelos/`, `/api/tipos-licencia/`. All endpoints MUST use DRF ViewSets with `SessionAuthentication`. Write operations MUST be restricted to Inspector. The system MUST support filters by periodo, tipo_licencia, and estado on parallels and subjects. (Source: RR006, RR028)

#### Scenario: SCN-CAT-11 — API filter parallels by period and license type

- GIVEN parallels exist for different periods and license types
- WHEN I perform GET `/api/paralelos/?periodo=1&tipo_licencia=2`
- THEN the system returns only parallels matching those filters

#### Scenario: SCN-CAT-12 — API filter subjects by license type

- GIVEN subjects associated to different license types
- WHEN I perform GET `/api/asignaturas/?tipo_licencia=1`
- THEN the system returns only subjects associated to that license type

#### Scenario: SCN-CAT-13 — Non-inspector user denied write access to API

- GIVEN I am authenticated as Docente
- WHEN I attempt POST/PUT/DELETE on `/api/asignaturas/`
- THEN the system returns 403 Forbidden

#### Scenario: SCN-CAT-14 — Read access for authenticated users

- GIVEN I am authenticated as any role
- WHEN I perform GET on `/api/asignaturas/` or `/api/paralelos/`
- THEN the system returns the catalog data (read access MAY be allowed for all authenticated users)

## Acceptance Criteria

- AC-CAT-01: TipoLicencia model created with seed data: Tipo C, Tipo E, Tipo E Convalidada (Source: RR006)
- AC-CAT-02: Subject CRUD with nombre, codigo, horas_lectivas (default 40h) and M2M to TipoLicencia (Source: RR006, D5)
- AC-CAT-03: Parallel CRUD with association to active period, tipo_licencia, asignatura, docente, horario (Source: RR007)
- AC-CAT-04: Docente role validation on parallel teacher assignment (Source: HU06)
- AC-CAT-05: Search/filter by periodo, tipo_licencia, and estado on API and list views (Source: RR006)
- AC-CAT-06: Parallel enabled for future enrollment in Sprint 2 (Source: HU06, RR007)
- AC-CAT-07: REST API at `/api/asignaturas/`, `/api/paralelos/`, `/api/tipos-licencia/` with Inspector write permissions (Source: RR028)
- AC-CAT-08: capacidad_maxima field on Paralelo model (Source: RR007)
- AC-CAT-09: All CRUD operations restricted to Inspector role (Source: HU06)

## Non-Functional Requirements

- NFR-CAT-01: Test coverage MUST be >= 70% for domain, application, and API layers (Source: RR028)
- NFR-CAT-02: API MUST use DRF ViewSets with `SessionAuthentication` (Source: D4, RR028)
- NFR-CAT-03: Seed data MUST be loaded via Django data migration, not fixtures (Source: RR006)
- NFR-CAT-04: Templates MUST follow ECPPP branding (palette #2D5016/#4A7C2F/#D4B942, Inter font) (Source: RR027)
- NFR-CAT-05: TipoLicencia E Convalidada `duracion_meses` is pending stakeholder confirmation (Source: PRD 11.5)
