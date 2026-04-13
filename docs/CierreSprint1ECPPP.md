# Cierre Sprint 1 — Plataforma Web Académica ECPPP

| Campo | Valor |
|-------|-------|
| **Proyecto** | Plataforma Web Académica ECPPP |
| **Sprint** | S1 (Incremento 1) |
| **Versión** | 0.2.0 |
| **Rango de fechas** | 30/03/2026 – 13/04/2026 |
| **Equipo** | 2 desarrolladores — Martín Jiménez, Junior Espín |
| **Estado** | ✅ Completado |
| **Tests** | 243 passed, 0 errors, 0 failures |
| **Stack** | Django 5.1.7 · PostgreSQL 18 · Tailwind CSS 3.4.17 (CDN) · Alpine.js 3.15.9 · DRF 3.16 |

---

## 1. Resumen ejecutivo

El Sprint 1 entregó las 6 Historias de Usuario planificadas (HU01–HU06) cubriendo autenticación multirrol, recuperación de contraseña, gestión de perfil y la estructura académica base (períodos, tipos de licencia, asignaturas, paralelos). Posteriormente se aplicaron **2 observaciones del cliente** que modificaron el flujo de autenticación:

1. **Eliminación del registro público** — La secretaría crea usuarios desde Django Admin con contraseña temporal enviada por email.
2. **2FA por OTP email para estudiantes** — Solo estudiantes requieren verificación OTP al hacer login. Docentes e inspectores acceden directo.

El sprint cierra con **243 tests pasando**, arquitectura DDD monolítica limpia, UI responsive alineada con el prototipo Figma, y todos los flujos funcionales verificados.

---

## 2. Checklist de Historias de Usuario

### 2.1 HU01 — Registro de usuario → MODIFICADA POR FEEDBACK

| Criterio original | Estado | Nota |
|-------------------|--------|------|
| Formulario de registro con nombre, cédula, correo, tipo de usuario, contraseña | ⚠️ Modificado | Registro público **eliminado** por observación del cliente |
| Validación de unicidad de cédula y correo | ✅ | Migrada a `UsuarioCreationForm` en Django Admin |
| Contraseña cumple política de seguridad (≥8 chars, mayúscula, número, símbolo) | ✅ | Validadores custom: `UppercaseValidator`, `SymbolValidator` + Django defaults |
| Cuenta creada con `is_active=False` hasta verificación OTP | ⚠️ Modificado | Ahora `is_active=True` desde creación (secretaría crea usuarios activos) |
| OTP de 6 dígitos generado y enviado por correo | ✅ | Reutilizado para 2FA en login de estudiantes |
| OTP expira tras 10 minutos | ✅ | `OTP_EXPIRATION_MINUTES=10` |
| Mensajes de error descriptivos por campo | ✅ | |
| Formulario responsive (desktop + móvil) | ✅ | Mobile-first con Tailwind |
| Tests de dominio y aplicación | ✅ | `TestRegistroAppService` (5 tests), domain tests |

**Flujo actual (post-feedback):**
1. Secretaría accede a `/admin/` → crea usuario con email, nombre, rol, cédula
2. Se auto-genera contraseña temporal de 12 caracteres
3. Se envía email con credenciales al usuario
4. Se activa `debe_cambiar_password=True`
5. En primer login, middleware redirige a cambiar contraseña

---

### 2.2 HU02 — Inicio de sesión → MODIFICADA POR FEEDBACK

| Criterio | Estado | Nota |
|----------|--------|------|
| Login con correo + contraseña + tipo de usuario | ✅ | `LoginView` con `LoginForm` |
| Redirección al dashboard por rol | ✅ | Inspector→periodos, Docente→paralelos, Estudiante→home |
| Bloqueo tras 5 intentos fallidos consecutivos | ✅ | `LoginService.registrar_intento_fallido()`, 15 min lockout |
| Notificación por correo al bloquear cuenta | ✅ | `send_lockout_notification()` |
| Registro de acceso en auditoría con timestamp e IP | ✅ | Modelo `RegistroAuditoria`, `DjangoAuditoriaRepository` |
| Cierre de sesión invalida sesión y redirige a login | ✅ | `LogoutView` |
| 2FA OTP para estudiantes | ✅ | **NUEVO** — `Verificacion2FAView` + `Login2FAService` |
| Middleware forzar cambio de contraseña temporal | ✅ | **NUEVO** — `ForzarCambioPasswordMiddleware` |
| Tests de autenticación | ✅ | `TestLoginView` (5), `TestVerificacion2FAView` (4), `TestLogoutView` (1) |

**Flujo login estudiante (post-feedback):**
1. Estudiante ingresa email + contraseña + tipo "estudiante"
2. Credenciales válidas → se genera OTP y envía por email
3. Se guarda `2fa_user_id` en sesión, redirige a `/usuarios/verificar-2fa/`
4. Estudiante ingresa código OTP → se completa `login()` → dashboard

**Flujo login docente/inspector:**
1. Ingresa credenciales → login directo → dashboard

---

### 2.3 HU03 — Recuperación de contraseña

| Criterio | Estado | Nota |
|----------|--------|------|
| Enlace "¿Olvidó su contraseña?" en login | ✅ | Link en `login.html` |
| Formulario solicita únicamente el correo | ✅ | `ECPPPPasswordResetForm` |
| Enlace de recuperación enviado con token único | ✅ | Django `PasswordResetTokenGenerator` |
| Token expira a los 30 minutos | ✅ | `PASSWORD_RESET_TIMEOUT=1800` |
| Nueva contraseña valida políticas de seguridad | ✅ | `ECPPPSetPasswordForm` con validadores |
| Mensaje genérico para correos no registrados | ✅ | Django default behavior |
| Templates con branding ECPPP | ✅ | 4 templates custom en `registration/` |
| Tests | ✅ | `TestPasswordRecovery` (1 test) |

---

### 2.4 HU04 — Gestión de perfil de usuario

| Criterio | Estado | Nota |
|----------|--------|------|
| Página "Mi Perfil" accesible para cualquier rol | ✅ | `PerfilView` con `@login_required` |
| Datos mostrados: nombre, cédula (read-only), correo (read-only), teléfono, dirección, rol | ✅ | `DatosPersonalesForm` |
| Actualización exitosa de teléfono y dirección | ✅ | `PerfilAppService.actualizar_datos()` |
| Cambio de contraseña requiere contraseña actual | ✅ | `CambiarContrasenaView` |
| Nueva contraseña validada contra `AUTH_PASSWORD_VALIDATORS` | ✅ | |
| Re-login tras cambio de contraseña (actualizar session hash) | ✅ | `login()` post cambio |
| Limpieza de flag `debe_cambiar_password` | ✅ | **NUEVO** — Se resetea a `False` tras cambio exitoso |
| Tests | ✅ | `TestPerfilView` (3), `TestCambiarContrasenaView` (3), `TestForzarCambioPasswordMiddleware` (3) |

---

### 2.5 HU05 — Gestión de períodos académicos

| Criterio | Estado | Nota |
|----------|--------|------|
| CRUD completo accesible solo para Inspector | ✅ | `PeriodoListView`, `PeriodoCreateView`, `PeriodoUpdateView` con `rol_requerido="inspector"` |
| Validación: `fecha_inicio < fecha_fin`, nombre único | ✅ | `PeriodoService.validar_fechas()` |
| Restricción de un solo período activo | ✅ | `PeriodoService.validar_activacion()` con confirmación |
| Listado con estado visible (Activo/Inactivo) | ✅ | Badge verde/gris en template |
| API REST `/api/periodos/` con permisos de Inspector | ✅ | `PeriodoViewSet` + `IsInspector` permission |
| Endpoint `/api/periodos/activo/` | ✅ | Custom action en viewset |
| Tests | ✅ | `TestPeriodoViews` (7), `TestPeriodoAPI` (9), `TestPeriodoService` (7) |

---

### 2.6 HU06 — Gestión de licencias, asignaturas y paralelos

| Criterio | Estado | Nota |
|----------|--------|------|
| Modelo `TipoLicencia` con datos iniciales (C, E, EC) | ✅ | Data migration `0007_seed_tipolicencia` |
| CRUD de asignaturas con horas lectivas y asociación a tipo de licencia | ✅ | `AsignaturaListView`, `AsignaturaCreateView`, `AsignaturaUpdateView` |
| CRUD de paralelos con período, tipo licencia, asignatura, docente, horario | ✅ | `ParaleloListView`, `ParaleloCreateView`, `ParaleloUpdateView` |
| Docente asignado debe tener `rol='docente'` | ✅ | `ParaleloService.validar_datos()` |
| Filtros por período y tipo de licencia en API | ✅ | `django-filter` en viewsets |
| API REST para asignaturas, paralelos, tipos de licencia | ✅ | 3 viewsets con permisos |
| Solo Inspector accede a CRUDs | ✅ | `rol_requerido="inspector"` |
| Tests | ✅ | `TestAsignaturaViews` (4), `TestParaleloViews` (4), `TestTipoLicenciaViews` (2), APIs (14), `TestAsignaturaService` (4), `TestParaleloService` (10) |

---

## 3. Correcciones por feedback del cliente

### 3.1 Observación 1: Eliminar registro público

| Tarea | Descripción | Estado |
|-------|-------------|--------|
| Eliminar rutas `registro/` y `verificar-otp/` | URLs removidas de `urls.py` | ✅ |
| Eliminar `RegistroView` y `VerificacionOTPView` | Clases e imports eliminados de `views.py` | ✅ |
| Eliminar links "Regístrese" de templates | Removidos de `login.html`, `home.html`, `base.html` | ✅ |
| Campo `debe_cambiar_password` en modelo Usuario | `BooleanField(default=False)` + migración `0003` | ✅ |
| `UsuarioCreationForm` custom sin campos de password | Formulario en `admin.py` con validación email/cédula únicos | ✅ |
| `UsuarioAdmin.save_model()` auto-genera password | 12 chars con `get_random_string()` + letras/dígitos/símbolos | ✅ |
| Email con credenciales temporales | `send_credenciales_email()` en `email_service.py` | ✅ |
| Fallback si email falla | Muestra contraseña en warning del admin | ✅ |
| `ForzarCambioPasswordMiddleware` | Redirige a cambiar contraseña si `debe_cambiar_password=True` | ✅ |
| `CambiarContrasenaView` limpia el flag | `debe_cambiar_password=False` tras cambio exitoso | ✅ |

### 3.2 Observación 2: 2FA por OTP email para estudiantes

| Tarea | Descripción | Estado |
|-------|-------------|--------|
| Bifurcar `LoginView.post()` por rol | Estudiantes → 2FA, otros → login directo | ✅ |
| `Login2FAService` | `generar_otp_login()` + `verificar_otp_login()` en `services.py` | ✅ |
| `Verificacion2FAView` | Nueva vista con GET/POST para verificación OTP | ✅ |
| Ruta `verificar-2fa/` | Nueva URL en `urls.py` | ✅ |
| Template `verificar_2fa.html` | Formulario OTP con estilo consistente | ✅ |
| Sesión `2fa_user_id` | Se guarda pre-login, se elimina post-verificación | ✅ |

### 3.3 Bugfix: Django Admin login

| Tarea | Descripción | Estado |
|-------|-------------|--------|
| Agregar `ModelBackend` como fallback | `ECPPPAuthBackend` usa `email`, admin usa `username` → login fallaba | ✅ |

---

## 4. Alineación UI/UX con prototipo Figma

Se realizaron 6 lotes de alineación visual (A–F) + pulido final:

| Lote | Descripción | Templates afectados |
|------|-------------|---------------------|
| **A** | Layout sidebar + topbar responsive | `base.html`, `sidebar.html` (nuevo), `topbar.html` (nuevo) |
| **B** | Design tokens alineados con Figma | `base.html` (Tailwind config), `sidebar.html` |
| **C** | Formularios estilizados | Todos los `_form.html` de académico y usuarios |
| **D** | Auth branding full-screen | `base_auth.html` (nuevo), 7 templates de auth migrados |
| **E** | UI Components upgrade | 11 templates de páginas autenticadas |
| **F** | Toast notifications, password toggles, focus styles | `base.html`, `base_auth.html`, login, cambiar contraseña, registro |
| **Final** | Logo oficial, favicon, fix overflow email perfil | `sidebar.html`, `base_auth.html`, `base.html`, `perfil.html` |

---

## 5. Suite de tests

### 5.1 Resultado final

```
243 passed in ~55s
0 errors
0 failures
```

### 5.2 Distribución por módulo

| Módulo | Archivo | Tests |
|--------|---------|-------|
| **Académico** | `test_api.py` | 23 |
| | `test_models.py` | 12 |
| | `test_views.py` | 17 |
| | `test_domain.py` | 24 |
| **Asistencia** | `test_models.py` | 6 |
| **Calificaciones** | `test_models.py` | 8 |
| **Solicitudes** | `test_models.py` | 8 |
| **Usuarios** | `test_auth_backend.py` | 8 |
| | `test_models.py` | 10 |
| | `test_services.py` | 14 |
| | `test_views.py` | 27 |
| | `test_domain.py` | 44 |
| | `test_validators.py` | 42 |
| **Total** | | **243** |

### 5.3 Tests nuevos del feedback (Tarea 6)

| Clase | Tests | Qué verifica |
|-------|-------|-------------|
| `TestLoginView` | 5 (1 nuevo) | Login docente directo + estudiante redirige a 2FA |
| `TestVerificacion2FAView` | 4 (todos nuevos) | GET sin/con sesión, POST exitoso/incorrecto |
| `TestForzarCambioPasswordMiddleware` | 3 (todos nuevos) | Redirige con flag, permite cambiar contraseña, no redirige sin flag |
| `TestUsuarioAdmin` | 3 (todos nuevos) | Creación genera password, email falla muestra password, valida email duplicado |
| `TestCambiarContrasenaView` | 3 (1 nuevo) | Limpia `debe_cambiar_password` tras cambio exitoso |

Tests eliminados: `TestRegistroView` (3) y `TestVerificacionOTPView` (4) — rutas eliminadas.

---

## 6. Stack técnico y configuración

### 6.1 Dependencias principales

| Paquete | Versión | Uso |
|---------|---------|-----|
| Django | 5.1.7 | Framework web |
| PostgreSQL | 18.x | Base de datos |
| djangorestframework | 3.16.x | API REST interna |
| Tailwind CSS | 3.4.17 (CDN) | Estilos CSS |
| Alpine.js | 3.15.9 (CDN) | Interactividad JS |
| pytest / pytest-django | 8.3.5 / 4.10.0 | Testing |
| factory-boy | — | Factories de test |
| Faker | 40.12.0 | Datos de prueba |

### 6.2 Variables de entorno clave

```env
# Email/SMTP
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=<gmail>
EMAIL_HOST_PASSWORD=<app_password>

# Seguridad
PASSWORD_RESET_TIMEOUT=1800       # 30 minutos
OTP_EXPIRATION_MINUTES=10         # Expiración OTP
ACCOUNT_LOCKOUT_MINUTES=15        # Bloqueo por intentos
MAX_LOGIN_ATTEMPTS=5              # Máximo intentos
```

### 6.3 Authentication backends

```python
AUTHENTICATION_BACKENDS = [
    "apps.usuarios.infrastructure.auth_backend.ECPPPAuthBackend",  # email+password+tipo
    "django.contrib.auth.backends.ModelBackend",                    # fallback para Django Admin
]
```

---

## 7. Decisiones de arquitectura post-feedback

| # | Decisión | Resolución | Razón |
|---|----------|-----------|-------|
| D10 | Panel de secretaría | Reutilizar Django Admin en `/admin/` | Menos código, ya tiene CRUD de Usuario, delivery más rápido |
| D11 | Mecanismo de 2FA | OTP por email (reutilizar infraestructura existente) | Pragmático para contexto institucional (escuela de conducción). TOTP diferido |
| D12 | Contraseña temporal | 12 chars con `get_random_string()` (letras + dígitos + símbolos) | Balance seguridad/usabilidad |
| D13 | Forzar cambio de contraseña | Campo `debe_cambiar_password` + middleware | Intercepta TODA request, exempt: cambiar contraseña, logout, admin |
| D14 | Auth backend para admin | Agregar `ModelBackend` como fallback | `ECPPPAuthBackend` usa `email`, admin usa `username` — sin fallback, admin no funciona |

---

## 8. Archivos creados y modificados

### 8.1 Archivos nuevos

| Archivo | Descripción |
|---------|-------------|
| `apps/usuarios/presentation/middleware.py` | `ForzarCambioPasswordMiddleware` |
| `apps/usuarios/migrations/0003_add_debe_cambiar_password.py` | Migración campo `debe_cambiar_password` |
| `templates/usuarios/verificar_2fa.html` | Template verificación OTP 2FA |
| `templates/partials/sidebar.html` | Sidebar responsive (Lote A UI) |
| `templates/partials/topbar.html` | Topbar responsive (Lote A UI) |
| `templates/base_auth.html` | Layout standalone para pantallas de auth (Lote D UI) |

### 8.2 Archivos modificados (feedback del cliente)

| Archivo | Cambio |
|---------|--------|
| `apps/usuarios/presentation/urls.py` | Eliminadas rutas registro/verificar-otp, agregada verificar-2fa |
| `apps/usuarios/presentation/views.py` | Eliminadas RegistroView/VerificacionOTPView, bifurcado LoginView, agregada Verificacion2FAView |
| `apps/usuarios/application/services.py` | Agregado `Login2FAService` |
| `apps/usuarios/infrastructure/models.py` | Agregado `debe_cambiar_password` |
| `apps/usuarios/infrastructure/email_service.py` | Agregada `send_credenciales_email()` |
| `apps/usuarios/admin.py` | Reescrito: `UsuarioCreationForm`, `UsuarioAdmin` custom, `OTPTokenAdmin`, `RegistroAuditoriaAdmin` |
| `config/settings/base.py` | Middleware registrado + `ModelBackend` fallback |
| `templates/usuarios/cambiar_contrasena.html` | Aviso amarillo de contraseña temporal |
| `templates/usuarios/login.html` | Eliminado link "Regístrese" |
| `templates/pages/home.html` | Eliminado botón "Registrarse" |
| `templates/base.html` | Eliminado link "Registrarse" de navbar |
| `tests/usuarios/test_views.py` | Eliminados 7 tests obsoletos, agregados 12 nuevos |

---

## 9. Arquitectura DDD — Bounded Contexts

```
proyecto-ecpp/
├── apps/
│   ├── usuarios/              # BC: Autenticación, perfil, 2FA, auditoría
│   │   ├── domain/            # Entities, value objects, services, exceptions
│   │   ├── application/       # App services (use cases)
│   │   ├── infrastructure/    # Models ORM, repositories, email, auth backend
│   │   └── presentation/      # Views, forms, URLs, middleware
│   ├── academico/             # BC: Períodos, asignaturas, paralelos, tipos licencia
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── presentation/
│   ├── asistencia/            # BC: Asistencia (Sprint 2+)
│   ├── calificaciones/        # BC: Calificaciones (Sprint 2+)
│   └── solicitudes/           # BC: Solicitudes (Sprint 3+)
├── config/settings/           # base.py, development.py, production.py
├── templates/                 # Django templates (Tailwind + Alpine.js)
├── tests/                     # 243 tests organizados por BC
└── docs/                      # PRDs, arquitectura, cierre de sprint
```

---

## 10. Notas para Sprint 2

### 10.1 Lo que queda pendiente / diferido

| Item | Razón | Sprint sugerido |
|------|-------|-----------------|
| TOTP con Authenticator App | Diferido por decisión D11 — implementar si cliente lo solicita | Sprint 2+ |
| Foto de perfil | No está en escenarios Gherkin de HU04 (decisión D6) | Sprint posterior |
| `IsEstudiante` DRF permission | No hay endpoints de estudiante en Sprint 1 | Sprint 2 (matrícula) |
| Delete views web para Período/Asignatura/Paralelo | Solo existen via DRF API, no hay DeleteView web | Sprint 2 si se requiere |
| Rate limiting en endpoints de auth | Mitigación de abuso — no implementado | Sprint posterior |
| `reenviar_otp()` no tiene URL/view | Función existe en service pero no está expuesta | Sprint 2 si se necesita |

### 10.2 Bugs conocidos

Ninguno al cierre del sprint.

### 10.3 Credenciales de acceso a Django Admin

Para probar el panel de secretaría en `/admin/`:

```bash
python manage.py createsuperuser
# Username: adminecppp (o el que se prefiera)
# Email: admin@ecppp.edu.ec
# Password: (cumplir política: ≥8 chars, mayúscula, número, símbolo)
```

**Importante:** El backend de autenticación custom (`ECPPPAuthBackend`) usa `email`, pero Django Admin usa `username`. El fallback `ModelBackend` resuelve esto (decisión D14).
