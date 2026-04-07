# Capability: academic-periods

## Purpose

CRUD management of academic periods with a single-active-period invariant, Inspector-only access control, audit trail, and REST API endpoint.

## Requirements

### Requirement: Period CRUD Operations

The system MUST allow the Inspector Academico to create, read, update, and deactivate academic periods. Each period MUST have: nombre, fecha_inicio, fecha_fin, and estado (Activo/Inactivo). The system MUST validate that `fecha_inicio < fecha_fin` and that nombre is unique. The system MUST restrict all CRUD operations to users with the 'inspector' role. (Source: HU05, RR005)

#### Scenario: SCN-PER-01 — Successful period creation

- GIVEN I am authenticated as Inspector Academico in the 'Gestion Academica' module, 'Periodos' tab
- WHEN I press '+ Nuevo Periodo', enter nombre, fecha_inicio, fecha_fin, and mark as 'Activo'
- THEN the system saves the period, displays it in the list, and registers the action in the audit log
- AND other modules automatically recognize the active period

#### Scenario: SCN-PER-02 — Period creation fails due to invalid dates

- GIVEN I am creating a new period
- WHEN I enter fecha_inicio >= fecha_fin
- THEN the system rejects the creation and shows a validation error

#### Scenario: SCN-PER-03 — Period creation fails due to duplicate name

- GIVEN a period named 'Periodo 2026-A' already exists
- WHEN I attempt to create another period with the same name
- THEN the system rejects the creation and shows a uniqueness error

#### Scenario: SCN-PER-04 — Non-inspector user denied access

- GIVEN I am authenticated as Docente or Estudiante
- WHEN I attempt to access the periods CRUD
- THEN the system denies access with a 403 Forbidden response

### Requirement: Single Active Period Invariant

The system MUST enforce that at most one period can be active at any time. When attempting to activate a new period while another is active, the system MUST show a warning and request confirmation to deactivate the current period before activating the new one. The system MUST use `select_for_update()` to prevent race conditions on concurrent activation. (Source: HU05, RR005)

#### Scenario: SCN-PER-05 — Activating a period when another is already active

- GIVEN a period 'Periodo 2026-A' is currently active
- WHEN I attempt to activate 'Periodo 2026-B'
- THEN the system shows a warning and asks for confirmation to deactivate 'Periodo 2026-A' before activating 'Periodo 2026-B'

#### Scenario: SCN-PER-06 — Confirming deactivation of current period

- GIVEN the system shows the deactivation confirmation dialog
- WHEN I confirm the deactivation
- THEN the system deactivates 'Periodo 2026-A', activates 'Periodo 2026-B', and logs both changes in audit

#### Scenario: SCN-PER-07 — Cancelling activation preserves current state

- GIVEN the system shows the deactivation confirmation dialog
- WHEN I cancel the operation
- THEN no changes are made and 'Periodo 2026-A' remains active

#### Scenario: SCN-PER-08 — Activating a period when none is active

- GIVEN no period is currently active
- WHEN I activate 'Periodo 2026-A'
- THEN the system activates it directly without confirmation dialog

### Requirement: Period Audit Trail

The system MUST log creation, update, and state change events of periods in the audit log. Logs MUST include the usuario who performed the action, the timestamp, and the action detail. (Source: RR005)

#### Scenario: SCN-PER-09 — Audit entry on period state change

- GIVEN I change a period's estado from 'Inactivo' to 'Activo'
- WHEN the change is saved
- THEN an audit entry is created with usuario, accion='cambio_estado_periodo', timestamp, and detail including the period name and state transition

### Requirement: Period REST API

The system MUST expose a REST API endpoint (`/api/periodos/`) for period management using DRF ViewSet with `SessionAuthentication`. The endpoint MUST be restricted to Inspector users. The system MUST provide a method or queryset to retrieve the currently active period, available to all authenticated users and other modules. (Source: HU05, RR028)

#### Scenario: SCN-PER-10 — API CRUD for periods (Inspector)

- GIVEN I am authenticated as Inspector via API
- WHEN I perform GET/POST/PUT/PATCH/DELETE on `/api/periodos/`
- THEN the system returns appropriate responses with period data and enforces the single-active invariant

#### Scenario: SCN-PER-11 — Get active period via API (any authenticated user)

- GIVEN I am authenticated (any role)
- WHEN I request GET `/api/periodos/activo/` or filter by `?estado=activo`
- THEN the system returns the currently active period (or empty if none active)

## Acceptance Criteria

- AC-PER-01: Full CRUD for periods accessible only to Inspector Academico (Source: HU05)
- AC-PER-02: Validation: fecha_inicio < fecha_fin, nombre unique (Source: HU05)
- AC-PER-03: Single active period enforced with confirmation dialog (Source: HU05, RR005)
- AC-PER-04: Period list shows estado (Activo/Inactivo) visually (Source: HU05)
- AC-PER-05: Audit log entries for creation, update, and state change (Source: RR005)
- AC-PER-06: REST API at `/api/periodos/` with Inspector permissions (Source: RR028)
- AC-PER-07: Global method to retrieve active period for other modules (Source: HU05)
- AC-PER-08: Race condition protection via `select_for_update()` on activation (Source: RR005)

## Non-Functional Requirements

- NFR-PER-01: Test coverage MUST be >= 70% for domain, application, and API layers (Source: RR028)
- NFR-PER-02: API MUST use DRF ViewSet with `SessionAuthentication` (Source: D4, RR028)
- NFR-PER-03: Templates MUST follow ECPPP branding (palette #2D5016/#4A7C2F/#D4B942, Inter font) (Source: RR027)
