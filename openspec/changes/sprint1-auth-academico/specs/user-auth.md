# Capability: user-auth

## Purpose

Authentication system for the ECPPP platform covering user registration with OTP email verification, session-based login with brute-force protection, logout, password recovery, and audit logging.

## Requirements

### Requirement: User Registration with OTP Verification

The system MUST allow new users (Estudiante, Docente, Inspector Academico) to register by providing nombre completo, cedula, correo electronico, tipo de usuario, and contrasena. The system MUST create the account as inactive (`is_active=False`) and send a 6-digit OTP code to the registered email. The OTP MUST expire after 10 minutes (Decision D7). Upon successful OTP verification, the system MUST activate the account and redirect to login. The system MUST validate uniqueness of cedula and correo at domain level and database level. The system MUST assign the role automatically based on the selected tipo_usuario. (Source: HU01, RR001)

#### Scenario: SCN-AUTH-01 — Successful registration with OTP activation

- GIVEN I am on the registration screen
- WHEN I enter valid nombre completo, cedula, correo electronico, tipo de usuario (Estudiante), and a valid password, and submit the form
- THEN the system validates the data, creates an inactive account, sends a 6-digit OTP to the registered email, and shows a message indicating I must verify my account
- AND when I enter the correct OTP code, the system activates the account and redirects me to the login screen

#### Scenario: SCN-AUTH-02 — Registration fails due to duplicate cedula or correo

- GIVEN a user exists with cedula '0912345678' or correo 'usuario@ecppp.edu.ec'
- WHEN I attempt to register with the same data
- THEN the system prevents registration and shows an error message

#### Scenario: SCN-AUTH-03 — Registration fails due to invalid data

- GIVEN I am on the registration screen
- WHEN I leave required fields empty or enter an invalid email format
- THEN the system shows specific validation messages per field and blocks submission

#### Scenario: SCN-AUTH-04 — OTP expires after 10 minutes

- GIVEN I registered and received an OTP code
- WHEN I attempt to verify the OTP after 10 minutes have elapsed
- THEN the system rejects the code and shows an expiration error message
- AND the system SHOULD allow requesting a new OTP

#### Scenario: SCN-AUTH-05 — Password does not meet security policy

- GIVEN I am on the registration screen
- WHEN I enter a password that does not meet the policy (< 8 chars, or missing uppercase, number, or symbol)
- THEN the system shows specific messages indicating which requirements are not met
- AND blocks form submission

### Requirement: Session-Based Login with Role-Based Redirect

The system MUST authenticate users via correo + contrasena + tipo_usuario using a custom authentication backend (extending Django's `ModelBackend`). The system MUST use Django server-side sessions (Decision D4). Upon successful login, the system MUST create a secure session and redirect to the role-appropriate dashboard. The system MUST register all access attempts (successful and failed) in the audit log with timestamp and IP address. (Source: HU02, RR002)

#### Scenario: SCN-AUTH-06 — Successful login

- GIVEN an active account with correo and tipo 'Docente'
- WHEN I enter correct credentials
- THEN the system validates, creates a secure session, redirects to the Docente dashboard, and registers the successful access in audit with timestamp

#### Scenario: SCN-AUTH-07 — Login fails with incorrect credentials

- GIVEN an active account
- WHEN I enter an incorrect password
- THEN the system shows a generic error without revealing which field is incorrect

### Requirement: Account Lockout After Failed Attempts

The system MUST lock the account temporarily after 5 consecutive failed login attempts (Decision D8: 15 minutes). The system MUST notify the user by email when their account is locked. The system MUST automatically unlock the account after the lockout period expires. The system MUST reset the failed attempt counter upon successful login. (Source: HU02, RR022)

#### Scenario: SCN-AUTH-08 — Account lockout after 5 failed attempts

- GIVEN an active account
- WHEN I enter an incorrect password 5 consecutive times
- THEN the system temporarily locks the account, notifies by email, and shows a lockout message

#### Scenario: SCN-AUTH-09 — Automatic unlock after lockout period

- GIVEN an account locked due to failed attempts
- WHEN 15 minutes have elapsed since lockout
- THEN the system allows login attempts again with reset counter

#### Scenario: SCN-AUTH-10 — Login attempt on locked account within lockout period

- GIVEN an account locked 5 minutes ago
- WHEN I attempt to login with correct credentials
- THEN the system rejects the attempt and shows the remaining lockout time

### Requirement: Logout

The system MUST invalidate the server-side session and clear the session cookie when the user logs out. The system MUST redirect to the login screen after logout. (Source: HU02, RR003)

#### Scenario: SCN-AUTH-11 — Successful logout

- GIVEN an active session
- WHEN I press 'Cerrar sesion'
- THEN the system invalidates the session, removes the cookie, and redirects to login

### Requirement: Password Recovery

The system MUST allow users to request a password recovery link sent to their email. The recovery token MUST expire after 30 minutes (`PASSWORD_RESET_TIMEOUT=1800`). The system MUST show a generic message regardless of whether the email exists (no email enumeration). The new password MUST comply with the security policy (>= 8 chars + uppercase + number + symbol). The system SHOULD use Django's built-in `PasswordResetView` and related views. (Source: HU03, RR003)

#### Scenario: SCN-AUTH-12 — Successful password recovery

- GIVEN I am on the login screen
- WHEN I press 'Olvidaste tu contrasena?' and enter my registered email
- THEN the system sends a recovery link with 30-minute expiration
- AND when I access the link, I can set a new password that meets the security policy

#### Scenario: SCN-AUTH-13 — Recovery with unregistered email

- GIVEN I am on the recovery screen
- WHEN I enter an email that does not exist in the system
- THEN the system shows a generic message indicating 'if the email exists, you will receive instructions' without revealing whether the email is registered

#### Scenario: SCN-AUTH-14 — Recovery token expired

- GIVEN I received a recovery link
- WHEN I access the link after 30 minutes
- THEN the system rejects the token and shows an expiration error

### Requirement: Audit Logging

The system MUST log all authentication events (login success, login failure, logout, account lockout) in the `RegistroAuditoria` model with: usuario (FK nullable), accion, IP address, timestamp, and detalle. (Source: RR002)

#### Scenario: SCN-AUTH-15 — Audit trail for login events

- GIVEN authentication events occur (login, failed login, logout, lockout)
- WHEN queried, the audit log
- THEN contains entries with usuario, accion, IP, timestamp, and detalle for each event

## Acceptance Criteria

- AC-AUTH-01: Registration form renders with fields: nombre completo, cedula, correo, tipo de usuario, contrasena, confirmar contrasena (Source: HU01)
- AC-AUTH-02: Cedula and correo uniqueness validated at domain and DB level (Source: RR001)
- AC-AUTH-03: Password complies with policy >= 8 chars + uppercase + number + symbol (Source: RR022, D9)
- AC-AUTH-04: Account created with `is_active=False` until OTP verification (Source: HU01)
- AC-AUTH-05: 6-digit OTP sent by email, expires in 10 minutes (Source: HU01, D7)
- AC-AUTH-06: Successful OTP activates account and redirects to login (Source: HU01)
- AC-AUTH-07: Login via correo + contrasena + tipo_usuario with custom auth backend (Source: HU02, D4)
- AC-AUTH-08: Role-based dashboard redirect after login (Source: HU02)
- AC-AUTH-09: Generic error messages — no field-level credential leaking (Source: RR022)
- AC-AUTH-10: Account locked after 5 failed attempts for 15 minutes (Source: RR022, D8)
- AC-AUTH-11: Email notification on account lockout (Source: HU02)
- AC-AUTH-12: Logout invalidates server session and redirects to login (Source: HU02)
- AC-AUTH-13: Password recovery link with 30-minute expiration (Source: HU03)
- AC-AUTH-14: Generic response for unregistered emails on recovery (Source: RR022)
- AC-AUTH-15: All auth events logged in RegistroAuditoria with IP and timestamp (Source: RR002)
- AC-AUTH-16: Session cookies configured with HttpOnly, Secure (prod), SESSION_COOKIE_AGE (Source: RR021)
- AC-AUTH-17: Forms are responsive — desktop + mobile (Source: RR026)

## Non-Functional Requirements

- NFR-AUTH-01: Passwords MUST be hashed with PBKDF2 (Django default, Decision D3) (Source: RR021)
- NFR-AUTH-02: Sessions MUST use Django server-side sessions with `SessionAuthentication` for DRF (Source: D4)
- NFR-AUTH-03: Email backend MUST be `console.EmailBackend` in development, SMTP in production (Source: D1, RR030)
- NFR-AUTH-04: Test coverage MUST be >= 70% for domain and application layers (Source: RR028)
- NFR-AUTH-05: Session cookie age MUST be 3600 seconds (1 hour), expire on browser close (Source: RR021)
- NFR-AUTH-06: OTP MUST be single-use — once used, MUST NOT be reusable (Source: RR022)
