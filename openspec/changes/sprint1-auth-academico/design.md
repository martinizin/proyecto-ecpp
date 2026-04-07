# Design: Sprint 1 — Auth + Academic Structure

## Technical Approach

Extend Sprint 0's DDD scaffold (placeholder layers) with real domain logic across `usuarios` and `academico` apps. Models-first approach: migrate new/modified ORM models, then build domain services → application services → auth backend → presentation (views + DRF ViewSets) → settings. All auth uses Django sessions + SessionAuthentication for DRF (D4). OTP is a custom infrastructure model (D2), no external libs.

## Architecture Decisions

| # | Decision | Choice | Alternatives Rejected | Rationale | Specs |
|---|----------|--------|----------------------|-----------|-------|
| AD1 | Auth backend | Custom `ECPPPAuthBackend(ModelBackend)` — authenticate by `email` + `password` + `tipo_usuario` | Overriding `USERNAME_FIELD` to email globally | Need triple-field auth (email+pass+tipo). Extending ModelBackend preserves Django's security layer; override only `authenticate()` | AC-AUTH-07 |
| AD2 | OTP model | Infrastructure model `OTPToken` with domain service `OTPService` | django-otp package | Zero deps, full control. Simple 6-digit code + expiry + used flag. Domain service validates expiry/usage rules (D2, D7) | AC-AUTH-04,05,06 |
| AD3 | Audit model | `RegistroAuditoria` in `usuarios` app, shared via cross-context FK strings | Separate `auditoria` app; per-app audit tables | Sprint 1 only audits auth + period events (same 2 contexts). Separate app is premature. Uses `'usuarios.RegistroAuditoria'` string FK from academico | AC-AUTH-15, AC-PER-05 |
| AD4 | TipoLicencia seed | Data migration (`RunPython`) in `academico/migrations/` | JSON fixture + `loaddata` | Migrations run automatically in CI/deploy. Fixtures require manual `loaddata`. Data migration is idempotent and version-controlled (NFR-CAT-03) | AC-CAT-01 |
| AD5 | Role-based access | DRF: custom `IsInspector` permission class. Views: `RolRequeridoMixin(UserPassesTestMixin)` + `@login_required` | Decorators only; django-guardian | Permission class is DRF-idiomatic. Mixin is Django CBV-idiomatic. No need for object-level permissions yet | AC-PER-01, AC-CAT-09 |
| AD6 | Password symbol validator | Custom `SymbolValidator` registered in `AUTH_PASSWORD_VALIDATORS` | Regex in form clean; third-party package | Django's validator pipeline is composable; adding one custom validator follows the framework pattern. Reusable across registration, profile, and recovery (D9) | AC-AUTH-03 |

## Data Model Changes

### New Models

**`usuarios.OTPToken`** — `apps/usuarios/infrastructure/models.py`
```python
class OTPToken(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='otp_tokens')
    codigo = models.CharField(max_length=6)
    creado_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField()
    usado = models.BooleanField(default=False)
    class Meta:
        indexes = [models.Index(fields=['usuario', 'usado', 'expira_en'])]
```

**`usuarios.RegistroAuditoria`** — `apps/usuarios/infrastructure/models.py`
```python
class RegistroAuditoria(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    accion = models.CharField(max_length=50)  # login_exitoso, login_fallido, logout, bloqueo, etc.
    ip = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    detalle = models.TextField(blank=True)
    class Meta:
        ordering = ['-timestamp']
        indexes = [models.Index(fields=['usuario', 'accion', 'timestamp'])]
```

**`academico.TipoLicencia`** — `apps/academico/infrastructure/models.py`
```python
class TipoLicencia(models.Model):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=5, unique=True)
    duracion_meses = models.PositiveIntegerField()
    num_asignaturas = models.PositiveIntegerField()
    activo = models.BooleanField(default=True)
    class Meta:
        verbose_name_plural = "Tipos de Licencia"
```

### Modified Models

**`Usuario`** — add fields:
- `direccion = models.TextField(blank=True, default='')` (AC-PROF-03)
- `intentos_fallidos = models.PositiveIntegerField(default=0)` (AC-AUTH-10)
- `bloqueado_hasta = models.DateTimeField(null=True, blank=True)` (AC-AUTH-10)

**`Asignatura`** — add fields:
- `horas_lectivas = models.PositiveIntegerField(default=40)` (AC-CAT-02)
- `tipos_licencia = models.ManyToManyField('TipoLicencia', related_name='asignaturas', blank=True)` (D5, AC-CAT-02)

**`Paralelo`** — add fields + modify unique_together:
- `tipo_licencia = models.ForeignKey('TipoLicencia', on_delete=models.CASCADE, related_name='paralelos')` (AC-CAT-03)
- `capacidad_maxima = models.PositiveIntegerField(default=30)` (AC-CAT-08)
- `unique_together` changes from `['asignatura', 'periodo', 'nombre']` to `['periodo', 'tipo_licencia', 'asignatura', 'nombre']` (SCN-CAT-10)

**`Periodo`** — add fields:
- `creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)` (AC-PER-05)
- `modificado_en = models.DateTimeField(auto_now=True)` (AC-PER-05)

### Migration Order
1. `usuarios/0002` — add `direccion`, `intentos_fallidos`, `bloqueado_hasta` to Usuario
2. `usuarios/0003` — create `OTPToken`, `RegistroAuditoria`
3. `academico/0002` — create `TipoLicencia`; add `horas_lectivas`, `tipos_licencia` M2M to Asignatura; add `creado_por`, `modificado_en` to Periodo
4. `academico/0003` — add `tipo_licencia` FK, `capacidad_maxima` to Paralelo; alter `unique_together`
5. `academico/0004` — data migration: seed 3 TipoLicencia rows

## Module Structure

### `apps/usuarios/` — Sprint 1 additions

| Layer | File | Contents |
|-------|------|----------|
| domain | `entities.py` | Extend `UsuarioEntity` (+direccion, +is_active). Add `OTPTokenEntity`, `RegistroAuditoriaEntity` |
| domain | `value_objects.py` | Extend `Cedula` (modulo-10 validation). Add `Email` VO |
| domain | `services.py` (**new**) | `RegistroService` (validate uniqueness, password policy). `LoginService` (attempt counting, lockout check). `OTPService` (generate, verify, expire) |
| domain | `exceptions.py` | Add `CorreoDuplicadoError`, `CuentaBloqueadaError`, `OTPExpiradoError`, `OTPInvalidoError` |
| domain | `repositories.py` | Add `OTPTokenRepository(ABC)`, `AuditoriaRepository(ABC)` |
| application | `services.py` | `RegistroAppService` (orchestrate: validate → create inactive user → generate OTP → send email). `LoginAppService` (orchestrate: check lockout → authenticate → audit → redirect). `PerfilAppService` (update personal data, change password). `PasswordRecoveryAppService` (wraps Django's built-in flow) |
| infrastructure | `models.py` | Add `OTPToken`, `RegistroAuditoria` models. Modify `Usuario` |
| infrastructure | `repositories.py` (**new**) | `DjangoUsuarioRepository`, `DjangoOTPTokenRepository`, `DjangoAuditoriaRepository` |
| infrastructure | `auth_backend.py` (**new**) | `ECPPPAuthBackend(ModelBackend)` — authenticate(email, password, tipo_usuario) |
| infrastructure | `email_service.py` (**new**) | `send_otp_email(usuario, codigo)`, `send_lockout_notification(usuario)` |
| infrastructure | `password_validators.py` (**new**) | `SymbolValidator`, `UppercaseValidator` |
| presentation | `views.py` | `RegistroView`, `VerificacionOTPView`, `LoginView`, `LogoutView`, `DashboardRedirectView`, `PerfilView`, `CambiarContrasenaView` |
| presentation | `forms.py` | `RegistroForm`, `VerificacionOTPForm`, `LoginForm`, `DatosPersonalesForm`, `CambiarContrasenaForm` |
| presentation | `serializers.py` (**new**) | `UsuarioSerializer` (read-only, for API if needed) |
| presentation | `urls.py` | All usuario URL patterns |
| presentation | `permissions.py` (**new**) | `RolRequeridoMixin`, `IsInspector(BasePermission)`, `IsDocente`, `IsAuthenticated` |

### `apps/academico/` — Sprint 1 additions

| Layer | File | Contents |
|-------|------|----------|
| domain | `entities.py` | Extend `PeriodoEntity` (+creado_por). Add `TipoLicenciaEntity`. Extend `AsignaturaEntity` (+horas_lectivas). Extend `ParaleloEntity` (+tipo_licencia, +capacidad_maxima) |
| domain | `services.py` (**new**) | `PeriodoService` (single-active invariant with `select_for_update`). `AsignaturaService` (validate codigo unique, horas > 0, at least one tipo_licencia). `ParaleloService` (validate docente role, active period, unique combo) |
| domain | `exceptions.py` | Add `PeriodoActivoExistenteError`, `AsignaturaCodigoDuplicadoError`, `DocenteInvalidoError`, `PeriodoInactivoError` |
| domain | `repositories.py` | Add methods to existing repos. Add `TipoLicenciaRepository(ABC)` |
| application | `services.py` | `PeriodoAppService`, `AsignaturaAppService`, `ParaleloAppService` (orchestrate CRUD + audit) |
| infrastructure | `models.py` | Add `TipoLicencia`. Modify `Asignatura`, `Paralelo`, `Periodo` |
| infrastructure | `repositories.py` (**new**) | `DjangoPeriodoRepository`, `DjangoAsignaturaRepository`, `DjangoParaleloRepository`, `DjangoTipoLicenciaRepository` |
| presentation | `views.py` | `PeriodoListView`, `PeriodoCreateView`, `PeriodoUpdateView`, `AsignaturaListView`, `AsignaturaCreateView`, `AsignaturaUpdateView`, `ParaleloListView`, `ParaleloCreateView`, `ParaleloUpdateView`, `TipoLicenciaListView` |
| presentation | `forms.py` | `PeriodoForm`, `AsignaturaForm`, `ParaleloForm` |
| presentation | `serializers.py` (**new**) | `PeriodoSerializer`, `AsignaturaSerializer`, `ParaleloSerializer`, `TipoLicenciaSerializer` |
| presentation | `api_views.py` (**new**) | `PeriodoViewSet`, `AsignaturaViewSet`, `ParaleloViewSet`, `TipoLicenciaViewSet` |
| presentation | `urls.py` | Web + API URL patterns (using `DefaultRouter`) |
| presentation | `filters.py` (**new**) | `ParaleloFilter` (by periodo, tipo_licencia, estado) using django-filter or manual queryset filtering |

## API Design

| Endpoint | Methods | Permission | Description | Spec |
|----------|---------|------------|-------------|------|
| `/api/periodos/` | GET, POST, PUT, PATCH, DELETE | GET: `IsAuthenticated`, Write: `IsInspector` | Period CRUD | AC-PER-06 |
| `/api/periodos/activo/` | GET | `IsAuthenticated` | Get active period | AC-PER-07 |
| `/api/tipos-licencia/` | GET | `IsAuthenticated` | List license types (read-only) | AC-CAT-07 |
| `/api/asignaturas/` | GET, POST, PUT, PATCH, DELETE | GET: `IsAuthenticated`, Write: `IsInspector` | Subject CRUD | AC-CAT-07 |
| `/api/asignaturas/?tipo_licencia={id}` | GET | `IsAuthenticated` | Filter subjects by license type | AC-CAT-05 |
| `/api/paralelos/` | GET, POST, PUT, PATCH, DELETE | GET: `IsAuthenticated`, Write: `IsInspector` | Parallel CRUD | AC-CAT-07 |
| `/api/paralelos/?periodo={id}&tipo_licencia={id}` | GET | `IsAuthenticated` | Filter parallels | AC-CAT-05 |

All API ViewSets use `SessionAuthentication` + `IsAuthenticated` as default. Pagination: `PageNumberPagination` with `page_size=20`.

DRF config in `settings/base.py`:
```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.SessionAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}
```

## URL Patterns

### `apps/usuarios/presentation/urls.py`
```python
app_name = 'usuarios'
urlpatterns = [
    path('registro/', RegistroView.as_view(), name='registro'),
    path('verificar-otp/', VerificacionOTPView.as_view(), name='verificar_otp'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('dashboard/', DashboardRedirectView.as_view(), name='dashboard'),
    path('perfil/', PerfilView.as_view(), name='perfil'),
    path('perfil/cambiar-contrasena/', CambiarContrasenaView.as_view(), name='cambiar_contrasena'),
    # Password recovery — Django built-in views with custom templates
    path('recuperar/', PasswordResetView.as_view(...), name='password_reset'),
    path('recuperar/enviado/', PasswordResetDoneView.as_view(...), name='password_reset_done'),
    path('recuperar/<uidb64>/<token>/', PasswordResetConfirmView.as_view(...), name='password_reset_confirm'),
    path('recuperar/completo/', PasswordResetCompleteView.as_view(...), name='password_reset_complete'),
]
```

### `apps/academico/presentation/urls.py`
```python
app_name = 'academico'
router = DefaultRouter()
router.register('periodos', PeriodoViewSet)
router.register('tipos-licencia', TipoLicenciaViewSet)
router.register('asignaturas', AsignaturaViewSet)
router.register('paralelos', ParaleloViewSet)

urlpatterns = [
    # Web views
    path('periodos/', PeriodoListView.as_view(), name='periodo_list'),
    path('periodos/crear/', PeriodoCreateView.as_view(), name='periodo_create'),
    path('periodos/<int:pk>/editar/', PeriodoUpdateView.as_view(), name='periodo_update'),
    path('asignaturas/', AsignaturaListView.as_view(), name='asignatura_list'),
    path('asignaturas/crear/', AsignaturaCreateView.as_view(), name='asignatura_create'),
    path('asignaturas/<int:pk>/editar/', AsignaturaUpdateView.as_view(), name='asignatura_update'),
    path('paralelos/', ParaleloListView.as_view(), name='paralelo_list'),
    path('paralelos/crear/', ParaleloCreateView.as_view(), name='paralelo_create'),
    path('paralelos/<int:pk>/editar/', ParaleloUpdateView.as_view(), name='paralelo_update'),
    path('tipos-licencia/', TipoLicenciaListView.as_view(), name='tipo_licencia_list'),
    # API
    path('api/', include(router.urls)),
]
```

### `config/urls.py` — update
```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='pages/home.html'), name='home'),
    path('usuarios/', include('apps.usuarios.presentation.urls')),
    path('academico/', include('apps.academico.presentation.urls')),
]
```

## Template Architecture

```
templates/
├── base.html                              (existing — no changes)
├── partials/
│   └── navbar.html                        (modify — add role-based menu items)
├── usuarios/
│   ├── registro.html                      (new — registration form)
│   ├── verificar_otp.html                 (new — OTP input form)
│   ├── login.html                         (new — replaces registration/login.html)
│   ├── dashboard.html                     (new — role-based dashboard)
│   ├── perfil.html                        (new — profile with tabs)
│   └── cambiar_contrasena.html            (new — password change form)
├── registration/
│   ├── password_reset_form.html           (new — recovery request)
│   ├── password_reset_done.html           (new — "check your email")
│   ├── password_reset_confirm.html        (new — new password form)
│   ├── password_reset_complete.html       (new — success message)
│   └── password_reset_email.html          (new — email template)
└── academico/
    ├── periodo_list.html                  (new — period list with status badges)
    ├── periodo_form.html                  (new — create/edit period)
    ├── asignatura_list.html               (new — subject list)
    ├── asignatura_form.html               (new — create/edit subject)
    ├── paralelo_list.html                 (new — parallel list)
    ├── paralelo_form.html                 (new — create/edit parallel)
    └── tipo_licencia_list.html            (new — license type list, read-only)
```

## Settings Changes

### `config/settings/base.py` — additions
```python
# Authentication
AUTHENTICATION_BACKENDS = ['apps.usuarios.infrastructure.auth_backend.ECPPPAuthBackend']
LOGIN_URL = '/usuarios/login/'
LOGIN_REDIRECT_URL = '/usuarios/dashboard/'
LOGOUT_REDIRECT_URL = '/usuarios/login/'

# Password validators — add custom validators
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
    {'NAME': 'apps.usuarios.infrastructure.password_validators.UppercaseValidator'},
    {'NAME': 'apps.usuarios.infrastructure.password_validators.SymbolValidator'},
]

# Session security
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 3600
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Password reset
PASSWORD_RESET_TIMEOUT = 1800

# App-specific constants
OTP_EXPIRATION_MINUTES = 10
ACCOUNT_LOCKOUT_MINUTES = 15
MAX_LOGIN_ATTEMPTS = 5

# DRF
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.SessionAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}
```

### `config/settings/development.py` — additions
```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

## Testing Strategy

| Layer | What | Approach | File |
|-------|------|----------|------|
| Domain | `Cedula` modulo-10 validation, `OTPService` expiry/usage logic, `LoginService` lockout logic, `PeriodoService` single-active invariant | Pure unit tests (no DB), pytest parametrize | `tests/usuarios/test_domain.py`, `tests/academico/test_domain.py` |
| Infrastructure | `ECPPPAuthBackend` authentication, `OTPToken` model creation/querying, model migrations | pytest-django with `db` fixture, factory-boy | `tests/usuarios/test_auth_backend.py`, `tests/usuarios/test_models.py` |
| Application | `RegistroAppService`, `LoginAppService`, `PerfilAppService`, `PeriodoAppService` end-to-end | Integration tests with DB, mock email backend | `tests/usuarios/test_services.py`, `tests/academico/test_services.py` |
| API | DRF ViewSets — CRUD, permissions (inspector vs others), filtering | `APIClient` with session auth, assert status codes + response data | `tests/academico/test_api.py` |
| Views | Registration form, login flow, profile update, period CRUD | `Client` with `login()`, assert redirects + template context | `tests/usuarios/test_views.py`, `tests/academico/test_views.py` |
| Password | Custom validators (`SymbolValidator`, `UppercaseValidator`) | Unit tests with valid/invalid passwords | `tests/usuarios/test_validators.py` |

New factories to add in `tests/factories.py`: `OTPTokenFactory`, `RegistroAuditoriaFactory`, `TipoLicenciaFactory`.
Update `UsuarioFactory` to include `is_active=True` explicitly (since registration creates inactive users).

## Sequence Diagrams

### Registration + OTP Verification
```
User ──POST /registro/──→ RegistroView
                           │ validate RegistroForm
                           │ call RegistroAppService.registrar()
                           │   ├─ domain: validate cedula, email uniqueness
                           │   ├─ infra: create Usuario(is_active=False)
                           │   ├─ domain: OTPService.generar() → 6-digit code
                           │   ├─ infra: save OTPToken(expira_en=now+10min)
                           │   └─ infra: send_otp_email(user, code)
                           └─ redirect → /verificar-otp/ (user_id in session)

User ──POST /verificar-otp/──→ VerificacionOTPView
                                │ call RegistroAppService.verificar_otp(user_id, code)
                                │   ├─ infra: get OTPToken(usuario, usado=False)
                                │   ├─ domain: OTPService.verificar(token, code)
                                │   │   ├─ check expira_en > now
                                │   │   └─ check codigo matches
                                │   ├─ infra: mark token usado=True
                                │   └─ infra: user.is_active = True; save
                                └─ redirect → /login/ + success message
```

### Login with Lockout
```
User ──POST /login/──→ LoginView
                        │ validate LoginForm (email, password, tipo_usuario)
                        │ call LoginAppService.intentar_login(email, password, tipo, request)
                        │   ├─ domain: check bloqueado_hasta > now → CuentaBloqueadaError
                        │   ├─ infra: ECPPPAuthBackend.authenticate(email, password, tipo)
                        │   ├─ IF success:
                        │   │   ├─ domain: reset intentos_fallidos = 0
                        │   │   ├─ infra: audit(login_exitoso, IP)
                        │   │   └─ django.contrib.auth.login(request, user)
                        │   └─ IF failure:
                        │       ├─ domain: increment intentos_fallidos
                        │       ├─ IF intentos >= 5:
                        │       │   ├─ domain: set bloqueado_hasta = now+15min
                        │       │   ├─ infra: audit(bloqueo, IP)
                        │       │   └─ infra: send_lockout_notification(user)
                        │       └─ infra: audit(login_fallido, IP)
                        └─ redirect → /dashboard/ (role-based) or show error
```

### Period Activation (Single-Active Invariant)
```
Inspector ──POST /academico/periodos/{id}/editar/──→ PeriodoUpdateView
                                                      │ call PeriodoAppService.activar(periodo_id, user)
                                                      │   ├─ infra: Periodo.objects.select_for_update()
                                                      │   ├─ domain: check if another period is active
                                                      │   ├─ IF active exists AND confirmed:
                                                      │   │   ├─ deactivate current
                                                      │   │   ├─ activate new
                                                      │   │   └─ infra: audit(cambio_estado_periodo x2)
                                                      │   ├─ IF active exists AND NOT confirmed:
                                                      │   │   └─ return confirmation_needed=True (show modal)
                                                      │   └─ IF none active:
                                                      │       ├─ activate directly
                                                      │       └─ infra: audit(cambio_estado_periodo)
                                                      └─ redirect → periodo_list + success message
```

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `apps/usuarios/infrastructure/models.py` | Modify | Add `direccion`, `intentos_fallidos`, `bloqueado_hasta` to Usuario. Add `OTPToken`, `RegistroAuditoria` models |
| `apps/usuarios/infrastructure/auth_backend.py` | Create | `ECPPPAuthBackend(ModelBackend)` |
| `apps/usuarios/infrastructure/email_service.py` | Create | OTP + lockout email functions |
| `apps/usuarios/infrastructure/password_validators.py` | Create | `SymbolValidator`, `UppercaseValidator` |
| `apps/usuarios/infrastructure/repositories.py` | Create | Django ORM repository implementations |
| `apps/usuarios/domain/entities.py` | Modify | Extend entities, add OTP/Audit entities |
| `apps/usuarios/domain/value_objects.py` | Modify | Enhance `Cedula`, add `Email` |
| `apps/usuarios/domain/services.py` | Create | `RegistroService`, `LoginService`, `OTPService` |
| `apps/usuarios/domain/exceptions.py` | Modify | Add new exception types |
| `apps/usuarios/domain/repositories.py` | Modify | Add OTP/Audit repository interfaces |
| `apps/usuarios/application/services.py` | Modify | Add `RegistroAppService`, `LoginAppService`, `PerfilAppService` |
| `apps/usuarios/presentation/views.py` | Modify | Add all auth + profile views |
| `apps/usuarios/presentation/forms.py` | Modify | Add all forms |
| `apps/usuarios/presentation/urls.py` | Modify | Add all URL patterns |
| `apps/usuarios/presentation/serializers.py` | Create | `UsuarioSerializer` |
| `apps/usuarios/presentation/permissions.py` | Create | `RolRequeridoMixin`, `IsInspector`, `IsDocente` |
| `apps/usuarios/models.py` | Verify | Re-exports from `infrastructure.models` |
| `apps/academico/infrastructure/models.py` | Modify | Add `TipoLicencia`. Modify `Asignatura`, `Paralelo`, `Periodo` |
| `apps/academico/infrastructure/repositories.py` | Create | Django ORM repository implementations |
| `apps/academico/domain/entities.py` | Modify | Add `TipoLicenciaEntity`, extend others |
| `apps/academico/domain/services.py` | Create | `PeriodoService`, `AsignaturaService`, `ParaleloService` |
| `apps/academico/domain/exceptions.py` | Modify | Add new exception types |
| `apps/academico/domain/repositories.py` | Modify | Add methods, `TipoLicenciaRepository` |
| `apps/academico/application/services.py` | Modify | Add `PeriodoAppService`, `AsignaturaAppService`, `ParaleloAppService` |
| `apps/academico/presentation/views.py` | Modify | Add all CRUD views |
| `apps/academico/presentation/forms.py` | Modify | Add `PeriodoForm`, `AsignaturaForm`, `ParaleloForm` |
| `apps/academico/presentation/urls.py` | Modify | Add web + API URLs |
| `apps/academico/presentation/serializers.py` | Create | DRF serializers |
| `apps/academico/presentation/api_views.py` | Create | DRF ViewSets |
| `apps/academico/presentation/filters.py` | Create | Queryset filters |
| `apps/academico/models.py` | Verify | Re-exports from `infrastructure.models` |
| `config/settings/base.py` | Modify | Auth backends, validators, session, DRF, login URLs |
| `config/settings/development.py` | Modify | Email console backend |
| `config/urls.py` | Modify | Include usuarios + academico URL confs |
| `templates/usuarios/*` | Create | 6 new templates |
| `templates/registration/*` | Create | 5 new templates (password recovery + email) |
| `templates/academico/*` | Create | 7 new templates |
| `templates/partials/navbar.html` | Modify | Role-based menu items |
| `tests/factories.py` | Modify | Add `OTPTokenFactory`, `RegistroAuditoriaFactory`, `TipoLicenciaFactory` |
| `tests/conftest.py` | Modify | Add fixtures for active periods, authenticated clients |
| `tests/usuarios/test_domain.py` | Create | Domain service unit tests |
| `tests/usuarios/test_auth_backend.py` | Create | Auth backend tests |
| `tests/usuarios/test_services.py` | Create | Application service integration tests |
| `tests/usuarios/test_views.py` | Create | View tests |
| `tests/usuarios/test_validators.py` | Create | Password validator tests |
| `tests/academico/test_domain.py` | Create | Domain service unit tests |
| `tests/academico/test_services.py` | Create | Application service integration tests |
| `tests/academico/test_api.py` | Create | DRF ViewSet tests |
| `tests/academico/test_views.py` | Create | View tests |

**Totals**: ~25 new files, ~18 modified files

## Migration / Rollout

5 migrations in sequence (see Migration Order above). Data migration seeds 3 TipoLicencia rows. All migrations are additive (no destructive changes). `TipoLicencia E Convalidada` has `duracion_meses` pending stakeholder confirmation — use placeholder value `0` with TODO comment.

## Open Questions

- [x] All 9 architecture decisions resolved (PRD 6.C)
- [ ] `TipoLicencia E Convalidada` `duracion_meses` — pending stakeholder input (PRD 11.5). Use `0` as placeholder.
