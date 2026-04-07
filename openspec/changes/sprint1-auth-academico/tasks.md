# Tasks: Sprint 1 — Auth + Academic Structure

## Phase 1: Settings & Configuration

- [x] 1.1 **[S]** Update `config/settings/base.py` — add `AUTHENTICATION_BACKENDS`, `LOGIN_URL`/`LOGIN_REDIRECT_URL`/`LOGOUT_REDIRECT_URL`, `SESSION_COOKIE_*` settings, `PASSWORD_RESET_TIMEOUT`, `OTP_EXPIRATION_MINUTES`/`ACCOUNT_LOCKOUT_MINUTES`/`MAX_LOGIN_ATTEMPTS` constants, `REST_FRAMEWORK` dict. Update `AUTH_PASSWORD_VALIDATORS` to include `SymbolValidator`+`UppercaseValidator` (paths only — classes in 2.5). Refs: AC-AUTH-16, NFR-AUTH-02, NFR-AUTH-05
- [x] 1.2 **[S]** Update `config/settings/development.py` — add `EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'`. Ref: NFR-AUTH-03

## Phase 2: Models & Migrations

- [x] 2.1 **[M]** Modify `apps/usuarios/infrastructure/models.py` — add `direccion`, `intentos_fallidos`, `bloqueado_hasta` fields to `Usuario`. Generate migration `usuarios/0002`. Refs: AC-PROF-03, AC-AUTH-10
- [x] 2.2 **[M]** Create `OTPToken` and `RegistroAuditoria` models in `apps/usuarios/infrastructure/models.py`. Generate migration `usuarios/0003`. Refs: AC-AUTH-04, AC-AUTH-05, AC-AUTH-15
- [x] 2.3 **[M]** Create `TipoLicencia` model in `apps/academico/infrastructure/models.py`. Add `horas_lectivas` + `tipos_licencia` M2M to `Asignatura`. Add `creado_por` + `modificado_en` to `Periodo`. Generate migration `academico/0003`. Refs: AC-CAT-01, AC-CAT-02, AC-PER-05
- [x] 2.4 **[M]** Add `tipo_licencia` FK + `capacidad_maxima` to `Paralelo`. Alter `unique_together` to `['periodo','tipo_licencia','asignatura','nombre']`. Generate migration `academico/0004`. Refs: AC-CAT-03, AC-CAT-08, SCN-CAT-10
- [x] 2.5 **[S]** Data migration `academico/0005` — seed 3 `TipoLicencia` rows (C, E, EC). `duracion_meses` for EC = 0 with TODO. Ref: AC-CAT-01, NFR-CAT-03
- [x] 2.6 **[S]** Update `apps/usuarios/models.py` and `apps/academico/models.py` re-exports to include new models (`OTPToken`, `RegistroAuditoria`, `TipoLicencia`).

## Phase 3: Domain Layer — Usuarios

- [x] 3.1 **[M]** Extend `apps/usuarios/domain/entities.py` — add `direccion`, `is_active` to `UsuarioEntity`. Add `OTPTokenEntity`, `RegistroAuditoriaEntity` dataclasses.
- [x] 3.2 **[S]** Extend `apps/usuarios/domain/value_objects.py` — implement modulo-10 Cedula validation. Add `Email` value object with format validation.
- [x] 3.3 **[M]** Extend `apps/usuarios/domain/exceptions.py` — add `CorreoDuplicadoError`, `CuentaBloqueadaError`, `OTPExpiradoError`, `OTPInvalidoError`.
- [x] 3.4 **[M]** Extend `apps/usuarios/domain/repositories.py` — add `OTPTokenRepository(ABC)` and `AuditoriaRepository(ABC)` with abstract methods. Add `get_by_email` to `UsuarioRepository`.
- [x] 3.5 **[L]** Create `apps/usuarios/domain/services.py` — implement `RegistroService` (cedula/email uniqueness, password policy check), `LoginService` (lockout check, attempt counting), `OTPService` (generate 6-digit, verify expiry/usage). Pure Python, no Django. Refs: SCN-AUTH-01→05, SCN-AUTH-06→10

## Phase 4: Domain Layer — Academico

- [x] 4.1 **[M]** Extend `apps/academico/domain/entities.py` — add `creado_por` to `PeriodoEntity`. Add `TipoLicenciaEntity`. Extend `AsignaturaEntity` (+horas_lectivas). Extend `ParaleloEntity` (+tipo_licencia, +capacidad_maxima).
- [x] 4.2 **[S]** Extend `apps/academico/domain/exceptions.py` — add `PeriodoActivoExistenteError`, `AsignaturaCodigoDuplicadoError`, `DocenteInvalidoError`, `PeriodoInactivoError`.
- [x] 4.3 **[M]** Extend `apps/academico/domain/repositories.py` — add `TipoLicenciaRepository(ABC)`. Add CRUD methods to `PeriodoRepository`, `AsignaturaRepository`, `ParaleloRepository`.
- [x] 4.4 **[L]** Create `apps/academico/domain/services.py` — implement `PeriodoService` (single-active invariant), `AsignaturaService` (codigo unique, horas>0, >=1 tipo), `ParaleloService` (docente role, active period, unique combo). Refs: SCN-PER-05→08, SCN-CAT-03→10

## Phase 5: Infrastructure Layer

- [x] 5.1 **[M]** Create `apps/usuarios/infrastructure/auth_backend.py` — `ECPPPAuthBackend(ModelBackend)` with `authenticate(request, email, password, tipo_usuario)`. Ref: AC-AUTH-07, AD1
- [x] 5.2 **[S]** Create `apps/usuarios/infrastructure/password_validators.py` — `SymbolValidator` + `UppercaseValidator` with `validate()` and `get_help_text()`. Ref: AC-AUTH-03, AD6
- [x] 5.3 **[M]** Create `apps/usuarios/infrastructure/email_service.py` — `send_otp_email(usuario, codigo)` + `send_lockout_notification(usuario)`. Ref: AC-AUTH-05, AC-AUTH-11
- [x] 5.4 **[M]** Create `apps/usuarios/infrastructure/repositories.py` — implement `DjangoUsuarioRepository`, `DjangoOTPTokenRepository`, `DjangoAuditoriaRepository` (concrete ORM implementations). Note: file exists as placeholder, replace content.
- [x] 5.5 **[M]** Create `apps/academico/infrastructure/repositories.py` — implement `DjangoPeriodoRepository` (with `select_for_update`), `DjangoAsignaturaRepository`, `DjangoParaleloRepository`, `DjangoTipoLicenciaRepository`. Note: file exists as placeholder, replace content. Ref: AC-PER-08

## Phase 6: Application Layer

- [x] 6.1 **[L]** Implement `apps/usuarios/application/services.py` — `RegistroAppService` (validate→create inactive→OTP→email), `LoginAppService` (lockout→auth→audit→session), `PerfilAppService` (update data, change password), `PasswordRecoveryAppService`. Refs: SCN-AUTH-01, SCN-AUTH-06, SCN-PROF-03, SCN-PROF-05
- [x] 6.2 **[L]** Implement `apps/academico/application/services.py` — `PeriodoAppService` (CRUD+activation+audit), `AsignaturaAppService` (CRUD+validation), `ParaleloAppService` (CRUD+docente check+active period). Refs: SCN-PER-01, SCN-CAT-03, SCN-CAT-07

## Phase 7: Presentation — Auth (HU01-HU03)

- [x] 7.1 **[M]** Create `apps/usuarios/presentation/permissions.py` — `RolRequeridoMixin(UserPassesTestMixin)`, `IsInspector(BasePermission)`, `IsDocente(BasePermission)`. Ref: AD5
- [x] 7.2 **[M]** Implement `apps/usuarios/presentation/forms.py` — add `RegistroForm`, `VerificacionOTPForm`, `LoginForm` (email+password+tipo_usuario). Refs: AC-AUTH-01, AC-AUTH-03
- [x] 7.3 **[L]** Implement `apps/usuarios/presentation/views.py` — `RegistroView`, `VerificacionOTPView`, `LoginView`, `LogoutView`, `DashboardRedirectView` + password recovery wiring (Django built-in views with custom templates). Refs: SCN-AUTH-01→14
- [x] 7.4 **[M]** Create templates `templates/usuarios/registro.html`, `templates/usuarios/verificar_otp.html`, `templates/usuarios/login.html`, `templates/usuarios/dashboard.html`. Ref: AC-AUTH-01, AC-AUTH-06
- [x] 7.5 **[M]** Create templates `templates/registration/password_reset_form.html`, `password_reset_done.html`, `password_reset_confirm.html`, `password_reset_complete.html`, `password_reset_email.html`. Ref: AC-AUTH-13

## Phase 8: Presentation — Profile (HU04)

- [x] 8.1 **[S]** Add `DatosPersonalesForm`, `CambiarContrasenaForm` to `apps/usuarios/presentation/forms.py`. Refs: AC-PROF-03, AC-PROF-05
- [x] 8.2 **[M]** Add `PerfilView`, `CambiarContrasenaView` to `apps/usuarios/presentation/views.py`. Refs: SCN-PROF-01→08
- [x] 8.3 **[S]** Create templates `templates/usuarios/perfil.html`, `templates/usuarios/cambiar_contrasena.html`. Ref: AC-PROF-01

## Phase 9: Presentation — Academic CRUD (HU05-HU06)

- [x] 9.1 **[M]** Implement `apps/academico/presentation/forms.py` — `PeriodoForm`, `AsignaturaForm`, `ParaleloForm`. Refs: AC-PER-02, AC-CAT-02, AC-CAT-03
- [x] 9.2 **[L]** Implement `apps/academico/presentation/views.py` — `PeriodoListView`, `PeriodoCreateView`, `PeriodoUpdateView`, `AsignaturaListView`, `AsignaturaCreateView`, `AsignaturaUpdateView`, `ParaleloListView`, `ParaleloCreateView`, `ParaleloUpdateView`, `TipoLicenciaListView`. All with `RolRequeridoMixin(inspector)`. Refs: AC-PER-01, AC-CAT-09
- [x] 9.3 **[M]** Create `apps/academico/presentation/serializers.py` — `PeriodoSerializer`, `AsignaturaSerializer`, `ParaleloSerializer`, `TipoLicenciaSerializer`. Ref: AC-PER-06, AC-CAT-07
- [x] 9.4 **[M]** Create `apps/academico/presentation/filters.py` — `ParaleloFilter` (periodo, tipo_licencia), `AsignaturaFilter` (tipo_licencia). Ref: AC-CAT-05
- [x] 9.5 **[M]** Create `apps/academico/presentation/api_views.py` — `PeriodoViewSet` (with `@action activo`), `AsignaturaViewSet`, `ParaleloViewSet`, `TipoLicenciaViewSet`. `IsInspector` for writes, `IsAuthenticated` for reads. Refs: AC-PER-06, AC-PER-07, AC-CAT-07
- [x] 9.6 **[M]** Create templates: `templates/academico/periodo_list.html`, `periodo_form.html`, `asignatura_list.html`, `asignatura_form.html`, `paralelo_list.html`, `paralelo_form.html`, `tipo_licencia_list.html`. Ref: AC-PER-04

## Phase 10: URL Wiring & Navigation

- [ ] 10.1 **[M]** Update `apps/usuarios/presentation/urls.py` — all auth, profile, password-recovery URL patterns per design. Ref: design URL Patterns
- [ ] 10.2 **[M]** Update `apps/academico/presentation/urls.py` — web views + DRF `DefaultRouter` for API. Ref: design URL Patterns
- [ ] 10.3 **[S]** Update `config/urls.py` — include `usuarios` and `academico` URL confs.
- [ ] 10.4 **[S]** Update `templates/partials/navbar.html` — role-based menu items (Inspector: academic CRUD links; all: profile, logout).

## Phase 11: Testing

- [ ] 11.1 **[M]** Update `tests/factories.py` — add `OTPTokenFactory`, `RegistroAuditoriaFactory`, `TipoLicenciaFactory`. Update `UsuarioFactory` with `is_active=True`, `cedula` sequence. Update `AsignaturaFactory`/`ParaleloFactory` for new fields.
- [ ] 11.2 **[S]** Update `tests/conftest.py` — add fixtures: `active_periodo`, `inspector_client`, `docente_client`, `estudiante_client`.
- [ ] 11.3 **[L]** Create `tests/usuarios/test_domain.py` — unit tests for `OTPService` (generate, verify, expired, used), `LoginService` (lockout, reset), `RegistroService` (uniqueness), `Cedula` modulo-10. Parametrize. Refs: SCN-AUTH-01→10
- [ ] 11.4 **[M]** Create `tests/usuarios/test_validators.py` — unit tests for `SymbolValidator`, `UppercaseValidator` with valid/invalid passwords. Ref: AC-AUTH-03
- [ ] 11.5 **[M]** Create `tests/usuarios/test_auth_backend.py` — test `ECPPPAuthBackend`: success, wrong password, wrong tipo, inactive user. Ref: AC-AUTH-07
- [ ] 11.6 **[L]** Create `tests/usuarios/test_services.py` — integration tests for `RegistroAppService`, `LoginAppService`, `PerfilAppService` with DB. Mock email. Refs: SCN-AUTH-01, SCN-AUTH-06, SCN-PROF-05
- [ ] 11.7 **[L]** Create `tests/usuarios/test_views.py` — view tests: registration flow, OTP verification, login+redirect, logout, profile update, password change, password recovery. Use Django `Client`. Refs: SCN-AUTH-01→14, SCN-PROF-01→08
- [ ] 11.8 **[L]** Create `tests/academico/test_domain.py` — unit tests for `PeriodoService` (single-active invariant, date validation), `AsignaturaService`, `ParaleloService` (docente check). Refs: SCN-PER-05→08, SCN-CAT-08→10
- [ ] 11.9 **[L]** Create `tests/academico/test_api.py` — DRF `APIClient` tests: CRUD all endpoints, `IsInspector` permission, filters, pagination, `/api/periodos/activo/`. Refs: SCN-PER-10→11, SCN-CAT-11→14
- [ ] 11.10 **[M]** Create `tests/academico/test_views.py` — view tests: period list/create/update, subject CRUD, parallel CRUD, TipoLicencia list. Role enforcement (403 for non-inspector). Refs: SCN-PER-01→04, SCN-CAT-03→07
