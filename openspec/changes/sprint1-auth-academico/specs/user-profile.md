# Capability: user-profile

## Purpose

User profile management allowing authenticated users to view their personal information, update editable fields (telefono, direccion), and change their password with security policy enforcement.

## Requirements

### Requirement: View User Profile

The system MUST provide a "Mi Perfil" page accessible to all authenticated users (Estudiante, Docente, Inspector). The profile MUST display read-only fields: nombre, cedula, correo, rol. The profile MUST display editable fields: telefono, direccion. The system MUST NOT display a profile photo field (Decision D6 — deferred). (Source: HU04, RR004)

#### Scenario: SCN-PROF-01 — View profile with read-only and editable fields

- GIVEN I am authenticated and navigate to 'Mi Perfil'
- WHEN the page loads
- THEN I see nombre, cedula, correo, and rol as read-only
- AND I see telefono and direccion as editable fields

#### Scenario: SCN-PROF-02 — Unauthenticated user cannot access profile

- GIVEN I am not authenticated
- WHEN I try to access the profile URL directly
- THEN the system redirects me to the login page

### Requirement: Update Personal Data

The system MUST allow authenticated users to update their telefono and direccion. The system MUST validate the data before saving. The system MUST show a confirmation message after successful update. The system MUST NOT allow editing nombre, cedula, correo, or rol from the profile page. (Source: HU04, RR004)

#### Scenario: SCN-PROF-03 — Successful update of personal data

- GIVEN I have an active session and I am on 'Mi Perfil'
- WHEN I modify telefono and/or direccion and press 'Guardar Cambios'
- THEN the system validates, updates the data, and shows a confirmation message

#### Scenario: SCN-PROF-04 — Attempt to modify read-only fields

- GIVEN I am on 'Mi Perfil'
- WHEN I inspect the form
- THEN nombre, cedula, correo, and rol fields are rendered as read-only (disabled/readonly attribute)
- AND submission does not alter those fields even if manipulated via browser tools

### Requirement: Change Password

The system MUST allow users to change their password from the profile page. The system MUST require the current password for verification. The new password MUST comply with the security policy (>= 8 chars + uppercase + number + symbol — Decision D9). The system MUST require password confirmation (new + confirm match). Upon successful password change, the system MUST invalidate the current session and redirect to login. (Source: HU04, RR004, RR022)

#### Scenario: SCN-PROF-05 — Successful password change

- GIVEN I am on the 'Cambiar Contrasena' tab
- WHEN I enter correct current password + new password + confirmation that meets the policy
- THEN the system updates the password with a secure hash and closes the session, requiring a new login

#### Scenario: SCN-PROF-06 — Password change fails due to security policy

- GIVEN I am on the 'Cambiar Contrasena' tab
- WHEN the new password does not meet the policy (< 8 chars, missing uppercase, missing number, or missing symbol)
- THEN the system blocks the change and shows which specific requirements are not met

#### Scenario: SCN-PROF-07 — Password change fails due to incorrect current password

- GIVEN I am on the 'Cambiar Contrasena' tab
- WHEN I enter an incorrect current password
- THEN the system rejects the change and shows an error indicating the current password is incorrect

#### Scenario: SCN-PROF-08 — Password change fails due to confirmation mismatch

- GIVEN I am on the 'Cambiar Contrasena' tab
- WHEN the new password and confirmation do not match
- THEN the system blocks the change and shows a mismatch error

## Acceptance Criteria

- AC-PROF-01: 'Mi Perfil' page accessible to all authenticated users regardless of role (Source: HU04)
- AC-PROF-02: Read-only display of nombre, cedula, correo, rol (Source: HU04, RR004)
- AC-PROF-03: Editable fields: telefono, direccion with confirmation on save (Source: HU04)
- AC-PROF-04: No profile photo field displayed (Source: D6)
- AC-PROF-05: Password change requires correct current password (Source: HU04)
- AC-PROF-06: New password validated against AUTH_PASSWORD_VALIDATORS (>= 8 chars + uppercase + number + symbol) (Source: RR022, D9)
- AC-PROF-07: Session invalidated after password change, redirect to login (Source: HU04)
- AC-PROF-08: Descriptive error messages for each unmet password requirement (Source: RR026)
- AC-PROF-09: View protected with `@login_required` (Source: RR021)

## Non-Functional Requirements

- NFR-PROF-01: Profile page MUST be responsive — desktop + mobile (Source: RR026)
- NFR-PROF-02: Test coverage MUST be >= 70% for profile domain and application layers (Source: RR028)
- NFR-PROF-03: Editing of read-only fields MUST be prevented server-side, not only via HTML attributes (Source: RR022)
