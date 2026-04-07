# Proposal: Sprint 1 — Auth + Academic Structure

## Intent

Deliver the authentication system (registration with OTP, login with brute-force protection, password recovery, profile management) and academic structure CRUD (periods, license types, subjects, parallels) for the ECPPP platform. This is the foundational domain logic that enables ALL subsequent sprints — no module works without authenticated users and active academic periods.

**Source**: PRD Sprint 1 (docs/PRDSprint1ECPPP.md) — 6 HUs, 16 story points, 30/03–10/04/2026.

## Scope

### In Scope
- **HU01** (3pts): User registration with OTP email verification, cedula/email uniqueness, password policy
- **HU02** (3pts): Login with email+password+role, session-based auth, brute-force lockout (5 attempts/15min), audit logging
- **HU03** (2pts): Password recovery via Django's built-in PasswordReset views, 30min token expiry
- **HU04** (2pts): Profile view/edit (phone, address), password change with policy enforcement
- **HU05** (3pts): Period CRUD (Inspector only), single-active-period invariant, audit trail, REST API
- **HU06** (3pts): TipoLicencia model + seed data, subject CRUD with M2M license association, parallel CRUD with teacher assignment, REST API
- **Cross-cutting**: Role-based access (`@rol_required`), email config (console backend dev), password validators (D9), session security

### Out of Scope
- Student enrollment in parallels (Sprint 2 — HU07)
- Grades and attendance (Sprints 2–3)
- Profile photo upload (Decision D6 — deferred)
- PDF/Excel reports (Sprint 3)
- Production deployment (Sprint 5)
- Rate limiting by IP (future hardening)

## Capabilities

### New Capabilities
- `user-auth`: Registration with OTP, login with lockout, logout, password recovery, password policy enforcement
- `user-profile`: Profile display and edit (phone, address), password change with session invalidation
- `academic-periods`: Period CRUD with single-active invariant, audit, REST API
- `academic-catalog`: TipoLicencia management, subject CRUD with M2M license relation, parallel CRUD with teacher assignment, REST API with filters

### Modified Capabilities
- None (openspec/specs/ is empty post-Sprint-0-archive; all capabilities are new)

## Approach

1. **Models first**: Create 3 new models (OTPToken, RegistroAuditoria, TipoLicencia) + 10 field additions to existing models (Usuario, Asignatura, Paralelo, Periodo) via migrations
2. **Domain services**: Business rules in `domain/services.py` — registration validation, login/lockout logic, period activation invariant, parallel creation rules
3. **Application layer**: Orchestration services coordinating domain + infrastructure (email, ORM)
4. **Auth backend**: Custom `EmailBackend` extending Django's `ModelBackend` for email+role authentication
5. **Presentation**: Django views + templates (Tailwind/Alpine.js) for web UI; DRF ViewSets + Serializers for REST API (SessionAuthentication)
6. **Settings**: Password validators, LOGIN_URL/REDIRECT, session security, console email backend
7. **Tests**: pytest + factory-boy per HU, targeting >= 70% domain coverage

**Execution order** (respecting HU dependencies): HU01 → HU02 → HU03/HU04 (parallel) → HU05 → HU06

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `apps/usuarios/domain/` | New | Services (registro, login), value objects (Cedula validation, Email), entities (OTPToken, RegistroAuditoria) |
| `apps/usuarios/infrastructure/` | New + Modified | OTPToken model, RegistroAuditoria model, Usuario field additions (direccion, intentos_fallidos, bloqueado_hasta), email service, custom auth backend |
| `apps/usuarios/application/` | New | RegistroService, LoginService, PerfilService |
| `apps/usuarios/presentation/` | New | Views (registro, OTP, login, logout, perfil, dashboard), forms, serializers, URLs |
| `apps/academico/domain/` | New | PeriodoService, AsignaturaService, ParaleloService, TipoLicenciaEntity |
| `apps/academico/infrastructure/` | New + Modified | TipoLicencia model, Asignatura fields (horas_lectivas, M2M tipo_licencia), Paralelo fields (tipo_licencia FK, capacidad_maxima), Periodo fields (creado_por, modificado_en) |
| `apps/academico/presentation/` | New | CRUD views, DRF ViewSets/Serializers, templates, URLs |
| `config/settings/base.py` | Modified | LOGIN_URL, AUTH_PASSWORD_VALIDATORS, SESSION_* settings |
| `config/settings/development.py` | Modified | EMAIL_BACKEND = console |
| `templates/usuarios/` | New | registro, verificar_otp, login, dashboard, perfil |
| `templates/academico/` | New | periodo_list/form, asignatura_list/form, paralelo_list/form, tipo_licencia_list |
| `templates/registration/` | New | password_reset_form/done/confirm/complete, password_reset_email |
| `tests/usuarios/` | New | test_registro, test_login, test_recuperacion, test_perfil |
| `tests/academico/` | New | test_periodos, test_asignaturas, test_paralelos, test_tipo_licencia |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Reduced capacity (Semana Santa: Apr 2-3) | High (confirmed) | 16 pts already adjusted. Prioritize HU01→HU02 first. HU04 is most sacrificable (2pts) |
| Custom auth backend introduces security bugs | Medium | Extend Django's `ModelBackend`, don't reimplement. Exhaustive auth tests |
| Migration conflicts between HU05 and HU06 (both touch `academico`) | Medium | Coordinate migration ordering: HU05 (Periodo fields) before HU06 (TipoLicencia + Asignatura/Paralelo fields) |
| TipoLicencia E Convalidada duration undefined | Low | PRD Section 11.5 — pending stakeholder confirmation. Use nullable field, don't block on it |
| Race condition on period activation | Low | Use `select_for_update()` in activation transaction |

## Rollback Plan

- **Models**: Revert migrations with `python manage.py migrate <app> <previous_migration>` — all changes are additive (new models, new fields), no destructive alterations
- **Settings**: Revert `base.py` and `development.py` changes via git
- **Views/Templates**: All new files, simple `git revert` of the feature commits
- **Data**: Seed data for TipoLicencia via data migration — reversible

## Dependencies

- Sprint 0 infrastructure complete (confirmed: 32/32 tasks, 42 tests passing)
- PostgreSQL 18 running for migrations
- 9 architecture decisions resolved (PRD Section 6.C — all resolved 06/04/2026)
- TipoLicencia E Convalidada duration: **pending stakeholder confirmation** (PRD Section 11.5)

## Success Criteria

- [ ] 6/6 HUs (HU01–HU06) completed with acceptance criteria verified
- [ ] Registration → OTP → activation → login flow works end-to-end
- [ ] Role-based access enforced: Inspector accesses academic CRUD; Docente/Estudiante cannot
- [ ] Single-active-period invariant enforced at domain level
- [ ] REST API operational: `/api/periodos/`, `/api/asignaturas/`, `/api/paralelos/`, `/api/tipos-licencia/`
- [ ] Brute-force protection: account locks after 5 failed attempts for 15 minutes
- [ ] Password policy enforced: >= 8 chars + uppercase + number + symbol
- [ ] Test coverage >= 70% on domain layer
- [ ] CI pipeline green with all Sprint 1 tests
- [ ] 16/16 story points delivered
