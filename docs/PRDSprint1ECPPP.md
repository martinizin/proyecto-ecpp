# PRD — Sprint 1: Plataforma Web Academica ECPPP

| Campo | Valor |
|-------|-------|
| **Titulo** | Product Requirements Document — Sprint 1 |
| **Proyecto** | Plataforma Web Academica ECPPP |
| **Version** | 0.2.0 |
| **Fecha** | Abril 2026 |
| **Sprint** | S1 (Incremento 1) |
| **Rango de fechas** | 30/03/2026 – 10/04/2026 (2 semanas) |
| **Equipo** | 2 desarrolladores — Martin Jimenez, Junior Espin |
| **Metodologia** | Scrum |
| **Capacidad del sprint** | 16 puntos (reducida por Semana Santa: jueves 2 y viernes 3 de abril) |
| **Estado** | Draft |

> **Fuente:** Planificacion_Sprints_Capstone_ECPP.docx — Encabezado e Incremento 1

---

## 1. Resumen ejecutivo del Sprint 1

### 1.1 Objetivo del Sprint

Implementar el sistema de autenticacion completa (registro con OTP, login, recuperacion de contrasena, gestion de perfil) y la estructura academica base (periodos, tipos de licencia, asignaturas, paralelos), estableciendo el dominio central de la plataforma que habilita todos los modulos funcionales de sprints posteriores. Este sprint construye sobre la infraestructura del Sprint 0 (repositorio, CI, modelos base, layout UI) y entrega las 6 primeras historias de usuario funcionales del proyecto.

> **Fuente:** Planificacion_Sprints_Capstone_ECPP.docx — Objetivo Sprint 1; HistoriasUsuario_Sprints_ECPPP.docx — Seccion "Sprint 1"

### 1.2 Definition of Done del Sprint 1

- [ ] Las 6 HUs (HU01–HU06) completadas con sus criterios de aceptacion verificados.
- [ ] Sistema de registro con verificacion OTP por correo electronico funcional.
- [ ] Login con sesion segura, control de intentos fallidos y cierre de sesion.
- [ ] Recuperacion de contrasena con enlace de expiracion funcional.
- [ ] Modulo de perfil con edicion de datos personales y cambio de contrasena.
- [ ] CRUD de periodos academicos con restriccion de un solo periodo activo.
- [ ] Configuracion de tipos de licencia, asignaturas y paralelos con asignacion de docente.
- [ ] Navegacion diferenciada por rol funcional (no solo estructura, sino logica de permisos real).
- [ ] API REST interna (DRF) para catalogos academicos operativa.
- [ ] Cobertura de tests >= 70% en capa de dominio (Fuente: RR028).
- [ ] Pipeline CI ejecutandose en verde con todos los tests del Sprint 1.
- [ ] Codigo revisado via PR de `feature/*` a `develop`.

---

## 2. Alcance del Sprint 1

### 2.1 Incluye

| Aspecto | Detalle | Fuente |
|---------|---------|--------|
| Registro de usuario | Formulario de registro con nombre, cedula, correo, tipo de usuario, contrasena. Verificacion OTP por correo. Validacion de unicidad (cedula, correo) | HistoriasUsuario — HU01; Requerimientos — RR001 |
| Inicio de sesion | Login con correo, contrasena y tipo de usuario. Sesion segura por rol. Bloqueo tras 5 intentos. Registro en auditoria | HistoriasUsuario — HU02; Requerimientos — RR002 |
| Recuperacion de contrasena | Enlace de recuperacion con expiracion de 30 minutos. Nueva contrasena con politicas de seguridad. Mensaje generico para correos no registrados | HistoriasUsuario — HU03; Requerimientos — RR003 |
| Gestion de perfil | Consulta y edicion de datos personales (telefono, direccion). Cambio de contrasena con validacion de politica | HistoriasUsuario — HU04; Requerimientos — RR004 |
| Periodos academicos | CRUD de periodos (nombre, fecha inicio, fecha fin, estado). Restriccion de un periodo activo simultaneo. Auditoria | HistoriasUsuario — HU05; Requerimientos — RR005 |
| Licencias, asignaturas y paralelos | Configuracion de tipos de licencia (C, E, E Convalidada). CRUD de asignaturas con horas lectivas. Creacion de paralelos con asignacion de docente | HistoriasUsuario — HU06; Requerimientos — RR006, RR007 |
| Control de acceso por roles | Logica de permisos real: Estudiante, Docente, Inspector Academico. Decoradores/mixins de autorizacion | Planificacion — Sprint 1; Requerimientos — RR021 |
| API REST interna (DRF) | Endpoints para catalogos academicos (periodos, asignaturas, paralelos, licencias) y validacion de reglas base | Planificacion — Sprint 1; Requerimientos — RR028 |
| Layout UI con navegacion por rol | Activacion de la logica de permisos en la navegacion (menus dinamicos segun rol autenticado) | Planificacion — Sprint 1; Requerimientos — RR026 |
| Configuracion de email/SMTP | Backend de correo para envio de OTP, recuperacion de contrasena y notificaciones | Requerimientos — RR030 |

### 2.2 Excluye

| Aspecto | Razon |
|---------|-------|
| Matriculacion de estudiantes en paralelos | Sprint 2 — HU07 (Fuente: Planificacion — Sprint 2) |
| Registro de calificaciones y asistencia | Sprints 2–3 — HU08–HU13 (Fuente: Planificacion — Incrementos 2–3) |
| Reportes PDF/Excel | Sprint 3 — HU14 (Fuente: Planificacion — Sprint 3) |
| Solicitudes de rectificacion/justificacion | Sprint 3 — HU15 (Fuente: Planificacion — Sprint 3) |
| Copilot ECPP (asistente IA) | Sprint 4 — HU17 (Fuente: Planificacion — Sprint 4) |
| Despliegue en produccion | Sprint 5 — DEP-01, DEP-02 (Fuente: Planificacion — Sprint 5) |
| Foto de perfil | Pospuesta a sprint posterior (Decision D6 resuelta). No esta en los escenarios Gherkin de HU04. Requiere almacenamiento de archivos (media) (Fuente: RR004 menciona foto de perfil) |

---

## 3. Backlog del Sprint 1

> **Fuente:** Planificacion_Sprints_Capstone_ECPP.docx — Tabla Sprint 1; HistoriasUsuario_Sprints_ECPPP.docx — Seccion "Sprint 1"

| ID | Nombre exacto | Descripcion | Puntos | Dependencias | Responsable sugerido | Output verificable |
|----|---------------|-------------|--------|--------------|----------------------|-------------------|
| HU01 | Registro de usuario | Formulario de registro con nombre completo, cedula, correo, tipo de usuario y contrasena. Envio de OTP por correo. Activacion de cuenta al verificar OTP. Validacion de unicidad de cedula y correo | 3 | Ninguna (requiere config SMTP) | Dev B (Backend) | Formulario de registro funcional, OTP enviado por correo, cuenta activada tras verificacion, tests de dominio |
| HU02 | Inicio de sesion | Login con correo, contrasena y tipo de usuario. Sesion segura con redireccion al dashboard por rol. Bloqueo tras 5 intentos fallidos. Registro de acceso en auditoria | 3 | HU01 | Dev B (Backend) + Dev A (Frontend) | Login funcional con redireccion por rol, bloqueo por intentos, registro de auditoria, tests |
| HU03 | Recuperacion de contrasena | Enlace de recuperacion enviado por correo con expiracion de 30 minutos. Formulario de nueva contrasena con politicas de seguridad. Mensaje generico para correos inexistentes | 2 | HU01 | Dev B (Backend) | Flujo de recuperacion completo, enlace con expiracion, politicas de contrasena aplicadas, tests |
| HU04 | Gestion de perfil de usuario | Consulta y edicion de datos personales (telefono, direccion). Cambio de contrasena con validacion de contrasena actual y politica de seguridad. Cierre de sesion tras cambio exitoso | 2 | HU02 | Dev A (Frontend) + Dev B (Backend) | Modulo de perfil funcional, edicion de datos, cambio de contrasena con politica, tests |
| HU05 | Gestion de periodos academicos | CRUD de periodos academicos (nombre, fecha inicio, fecha fin, estado). Restriccion de maximo un periodo activo simultaneo. Registro en auditoria. Modulos reconocen periodo activo automaticamente | 3 | HU02 (Inspector autenticado) | Dev B (Backend) | CRUD de periodos funcional, restriccion de periodo unico activo, auditoria, API REST, tests |
| HU06 | Gestion de licencias, asignaturas y paralelos | Configurar tipos de licencia (C, E, E Convalidada), CRUD de asignaturas con horas lectivas y asociacion a licencia, creacion de paralelos con asignacion de docente y horario | 3 | HU05, HU02 | Dev B (Backend) + Dev A (Frontend) | CRUD de licencias/asignaturas/paralelos, asociaciones correctas, API REST, tests |
| **Total** | | | **16** | | | |

---

## 4. Detalle por HU del Sprint 1

### 4.1 HU01 — Registro de usuario

**Proposito:**
Permitir que usuarios nuevos (Estudiante, Docente, Inspector Academico) se registren en la plataforma completando sus datos personales, seleccionando su tipo de usuario y creando una contrasena, con verificacion de identidad mediante codigo OTP enviado al correo registrado.

> **Fuente:** HistoriasUsuario_Sprints_ECPPP.docx — HU01; Requerimientos_ECPPP.docx — RR001

**Escenarios Gherkin (fuente: HistoriasUsuario — HU01):**

1. **Registro exitoso con activacion OTP**: Dado que me encuentro en la pantalla de registro, cuando ingreso nombre completo, cedula, correo electronico, tipo de usuario (Estudiante) y contrasena valida y envio el formulario, entonces el sistema valida los datos, crea la cuenta inactiva, envia un codigo OTP al correo registrado y muestra un mensaje indicando que debo verificar mi cuenta. Y al ingresar el codigo OTP correcto, el sistema activa la cuenta y me redirige al inicio de sesion.
2. **Registro fallido por cedula o correo duplicado**: Dado que existe un usuario con cedula '0912345678' o correo 'usuario@ecppp.edu.ec', cuando intento registrarme con los mismos datos, entonces el sistema impide el registro y muestra mensaje de error.
3. **Registro fallido por datos invalidos**: Dado que me encuentro en la pantalla de registro, cuando dejo campos obligatorios vacios o ingreso formato de correo invalido, entonces el sistema muestra mensajes de validacion especificos por campo y bloquea el envio.

**Pasos tecnicos sugeridos:**

1. Crear servicio de dominio `apps/usuarios/domain/services.py` con `RegistroUsuarioService` que encapsule las reglas de validacion (unicidad cedula/correo, formato de datos, politica de contrasena).
2. Crear value object `apps/usuarios/domain/value_objects.py` — extender `Cedula` existente con validacion de formato ecuatoriano (10 digitos + algoritmo modulo 10). Agregar `Email` value object con validacion de formato.
3. Crear modelo ORM `apps/usuarios/infrastructure/models.py` — agregar modelo `OTPToken` con campos: `usuario` (FK), `codigo` (CharField 6 digitos), `creado_en` (DateTimeField), `expira_en` (DateTimeField), `usado` (BooleanField). Agregar campo `is_active=False` por defecto en `Usuario` para flujo de activacion OTP.
4. Crear servicio de aplicacion `apps/usuarios/application/services.py` con `RegistroService` que orqueste: validacion de dominio → creacion de usuario inactivo → generacion de OTP → envio de correo → verificacion de OTP → activacion de cuenta.
5. Crear servicio de infraestructura para envio de email `apps/usuarios/infrastructure/email_service.py` usando `django.core.mail.send_mail` con template HTML para el OTP.
6. Crear vistas en `apps/usuarios/presentation/views.py`: `RegistroView` (formulario), `VerificacionOTPView` (verificacion), con formularios Django en `apps/usuarios/presentation/forms.py`.
7. Crear templates: `templates/usuarios/registro.html`, `templates/usuarios/verificar_otp.html`.
8. Crear serializer DRF en `apps/usuarios/presentation/serializers.py` para endpoint de registro API (si aplica).
9. Configurar URLs en `apps/usuarios/presentation/urls.py`.
10. Crear tests en `tests/usuarios/test_registro.py`: test de registro exitoso, test de cedula duplicada, test de correo duplicado, test de datos invalidos, test de OTP valido, test de OTP expirado.

**Criterios de aceptacion tecnicos (DoD):**

- [ ] Formulario de registro renderiza con campos: nombre completo, cedula, correo, tipo de usuario, contrasena, confirmar contrasena.
- [ ] Validacion de unicidad de cedula y correo a nivel de dominio y base de datos.
- [ ] Contrasena cumple politica de seguridad (>= 8 chars, mayuscula, numero, simbolo) (Fuente: RR022).
- [ ] Cuenta se crea con `is_active=False` hasta verificacion OTP.
- [ ] OTP de 6 digitos generado y enviado por correo electronico.
- [ ] OTP expira tras 10 minutos (Decision D7).
- [ ] Tras verificacion OTP exitosa, cuenta se activa y redirige a login.
- [ ] Mensajes de error descriptivos por campo (Fuente: RR026).
- [ ] Rol asignado automaticamente segun tipo de usuario seleccionado (Fuente: RR001).
- [ ] Tests de dominio y aplicacion con cobertura >= 70%.
- [ ] Formulario responsive (desktop + movil) (Fuente: RR026).

**Riesgos y mitigacion:**

| Riesgo | Mitigacion |
|--------|-----------|
| SMTP no configurado o bloqueado en entorno de desarrollo | Usar `django.core.mail.backends.console.EmailBackend` en development.py para imprimir emails en consola. Configurar SMTP real solo en produccion |
| OTP interceptado en transmision | OTP de un solo uso con expiracion corta. HTTPS en produccion (Fuente: RR021). Considerar rate limiting en el endpoint de verificacion |
| Validacion de cedula ecuatoriana compleja | Implementar algoritmo modulo 10 como value object testeable. Permitir cedulas de 10 y 13 caracteres (RUC) |

**Evidencia de completitud:**
- Captura del formulario de registro renderizado.
- Log de correo con OTP enviado (consola en dev).
- Captura de cuenta activada tras OTP.
- Output de `pytest tests/usuarios/test_registro.py` en verde.

---

### 4.2 HU02 — Inicio de sesion

**Proposito:**
Permitir a usuarios registrados y verificados iniciar sesion con credenciales seguras (correo, contrasena, tipo de usuario), accediendo al panel academico correspondiente a su rol, con proteccion contra ataques de fuerza bruta y registro de accesos en auditoria.

> **Fuente:** HistoriasUsuario_Sprints_ECPPP.docx — HU02; Requerimientos_ECPPP.docx — RR002

**Escenarios Gherkin (fuente: HistoriasUsuario — HU02):**

1. **Login exitoso**: Dado cuenta activa con correo y tipo 'Docente', cuando ingreso credenciales correctas, entonces el sistema valida, crea sesion segura, redirige al dashboard del Docente y registra el acceso exitoso en auditoria con timestamp.
2. **Login fallido por credenciales incorrectas**: Dado cuenta activa, cuando ingreso contrasena incorrecta, entonces error sin revelar que campo es incorrecto. Tras 5 intentos fallidos consecutivos, bloquea temporalmente la cuenta y notifica por correo.
3. **Cierre de sesion**: Dado sesion activa, cuando presiono 'Cerrar sesion', entonces invalida la sesion, elimina el token y redirige al login.

**Pasos tecnicos sugeridos:**

1. Crear backend de autenticacion personalizado `apps/usuarios/infrastructure/auth_backend.py` que autentique por correo + contrasena + tipo de usuario (en lugar del `username` default de Django). Registrar en `settings.AUTHENTICATION_BACKENDS`.
2. Crear modelo `apps/usuarios/infrastructure/models.py` — agregar modelo `RegistroAuditoria` con campos: `usuario` (FK nullable), `accion` (CharField: 'login_exitoso', 'login_fallido', 'logout', 'bloqueo'), `ip` (GenericIPAddressField), `timestamp` (DateTimeField auto), `detalle` (TextField).
3. Crear servicio de dominio `apps/usuarios/domain/services.py` — agregar `LoginService` con logica de: validacion de credenciales, conteo de intentos fallidos, bloqueo temporal (15 minutos tras 5 intentos), desbloqueo automatico.
4. Agregar campos al modelo `Usuario`: `intentos_fallidos` (IntegerField default 0), `bloqueado_hasta` (DateTimeField nullable), para control de bloqueo por intentos.
5. Crear vistas en `apps/usuarios/presentation/views.py`: `LoginView`, `LogoutView`, `DashboardView` (redireccion segun rol).
6. Crear templates: `templates/usuarios/login.html`, `templates/usuarios/dashboard_estudiante.html`, `templates/usuarios/dashboard_docente.html`, `templates/usuarios/dashboard_inspector.html` (o un dashboard unico con contenido condicional por rol).
7. Configurar `LOGIN_URL`, `LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL` en `settings/base.py`.
8. Implementar middleware o decoradores de autorizacion por rol: `@rol_required('inspector')`.
9. Crear tests: test de login exitoso por rol, test de intentos fallidos, test de bloqueo, test de logout, test de auditoria.

**Criterios de aceptacion tecnicos (DoD):**

- [ ] Login funcional con correo + contrasena + tipo de usuario.
- [ ] Redireccion automatica al dashboard correspondiente al rol (Estudiante, Docente, Inspector).
- [ ] Mensaje de error generico ante credenciales incorrectas (sin revelar que campo falla) (Fuente: RR022).
- [ ] Bloqueo temporal de cuenta tras 5 intentos fallidos consecutivos (Fuente: RR022).
- [ ] Notificacion por correo al bloquear cuenta.
- [ ] Registro de acceso en auditoria con timestamp y IP (Fuente: RR002).
- [ ] Cierre de sesion invalida sesion del servidor y redirige a login.
- [ ] Sesion segura: cookies `HttpOnly`, `Secure` (en produccion), `SESSION_COOKIE_AGE` configurado.
- [ ] Tests de autenticacion con cobertura >= 70%.

**Riesgos y mitigacion:**

| Riesgo | Mitigacion |
|--------|-----------|
| Backend de autenticacion personalizado introduce bugs de seguridad | Extender `ModelBackend` de Django en lugar de reimplementar desde cero. Tests exhaustivos |
| Bloqueo por intentos puede ser explotado para DoS | Bloqueo temporal (15 min), no permanente. Considerar rate limiting por IP a futuro |
| Multiples dashboards por rol aumentan complejidad de templates | Usar un unico template dashboard con bloques condicionales por `user.rol` |

**Evidencia de completitud:**
- Captura de login exitoso y redireccion al dashboard por rol.
- Captura de bloqueo tras 5 intentos fallidos.
- Registro de auditoria en Django Admin mostrando accesos.
- Output de tests en verde.

---

### 4.3 HU03 — Recuperacion de contrasena

**Proposito:**
Permitir a usuarios registrados que olvidaron su contrasena solicitar un enlace de recuperacion enviado a su correo, para restablecer el acceso de forma segura sin intervencion del administrador.

> **Fuente:** HistoriasUsuario_Sprints_ECPPP.docx — HU03; Requerimientos_ECPPP.docx — RR003

**Escenarios Gherkin (fuente: HistoriasUsuario — HU03):**

1. **Recuperacion exitosa**: Dado que estoy en pantalla de login, cuando presiono 'Olvidaste tu contrasena?' e ingreso mi correo registrado, entonces el sistema envia un enlace de recuperacion con expiracion de 30 minutos. Al acceder al enlace, puedo establecer nueva contrasena que cumpla politicas de seguridad.
2. **Correo no registrado**: Dado que estoy en pantalla de recuperacion, cuando ingreso un correo que no existe, entonces mensaje generico indicando que si el correo existe recibiras instrucciones, sin revelar si existe o no.

**Pasos tecnicos sugeridos:**

1. Evaluar uso del sistema built-in de Django: `django.contrib.auth.views.PasswordResetView`, `PasswordResetDoneView`, `PasswordResetConfirmView`, `PasswordResetCompleteView`. Estos views ya manejan generacion de tokens, expiracion y seguridad.
2. Si se usa el sistema built-in, personalizar los templates: `templates/registration/password_reset_form.html`, `templates/registration/password_reset_done.html`, `templates/registration/password_reset_confirm.html`, `templates/registration/password_reset_complete.html`.
3. Configurar `PASSWORD_RESET_TIMEOUT` en `settings/base.py` a `1800` (30 minutos, expresado en segundos) (Fuente: HU03 — "expiracion de 30 minutos").
4. Personalizar el template de email de recuperacion: `templates/registration/password_reset_email.html` con branding ECPPP.
5. Asegurar que el formulario de nueva contrasena aplica las politicas de seguridad de `AUTH_PASSWORD_VALIDATORS` (>= 8 chars, mayuscula, numero, simbolo).
6. Verificar que el mensaje para correos no registrados es generico (Django ya hace esto por defecto).
7. Crear tests: test de solicitud con correo valido, test de correo inexistente (mismo response), test de token expirado, test de nueva contrasena con politica.

**Criterios de aceptacion tecnicos (DoD):**

- [ ] Enlace "Olvidaste tu contrasena?" visible en pantalla de login.
- [ ] Formulario de solicitud de recuperacion solicita unicamente el correo.
- [ ] Enlace de recuperacion enviado por correo con token unico.
- [ ] Token expira a los 30 minutos (`PASSWORD_RESET_TIMEOUT=1800`) (Fuente: HU03).
- [ ] Formulario de nueva contrasena valida politicas de seguridad (>= 8 chars, mayuscula, numero, simbolo) (Fuente: RR022).
- [ ] Mensaje generico para correos no registrados (no revela existencia) (Fuente: RR022).
- [ ] Templates con branding ECPPP (paleta corporativa, logo).
- [ ] Tests de recuperacion con cobertura >= 70%.

**Riesgos y mitigacion:**

| Riesgo | Mitigacion |
|--------|-----------|
| Abuso del endpoint de recuperacion (spam de emails) | Implementar rate limiting: maximo 3 solicitudes por hora por IP/correo |
| Token de recuperacion predecible | Usar `PasswordResetTokenGenerator` de Django que genera tokens HMAC seguros |
| Correo de recuperacion llega a spam | Configurar SPF/DKIM en el dominio de envio. En desarrollo, usar console backend |

**Evidencia de completitud:**
- Captura del formulario de solicitud de recuperacion.
- Log de correo con enlace de recuperacion (consola en dev).
- Captura de formulario de nueva contrasena con validacion de politica.
- Output de tests en verde.

---

### 4.4 HU04 — Gestion de perfil de usuario

**Proposito:**
Permitir a usuarios autenticados (Estudiante, Docente, Inspector) consultar y actualizar su informacion personal y cambiar su contrasena desde el modulo de perfil, manteniendo datos actualizados y protegiendo el acceso a la cuenta.

> **Fuente:** HistoriasUsuario_Sprints_ECPPP.docx — HU04; Requerimientos_ECPPP.docx — RR004

**Escenarios Gherkin (fuente: HistoriasUsuario — HU04):**

1. **Actualizacion exitosa de datos personales**: Dado sesion activa y acceso a 'Mi Perfil', cuando modifico telefono y/o direccion y presiono 'Guardar Cambios', entonces el sistema valida, actualiza y muestra confirmacion.
2. **Cambio de contrasena exitoso**: Dado pestana 'Cambiar Contrasena', cuando ingreso contrasena actual correcta + nueva + confirmacion, entonces actualiza con hash seguro y cierra sesion solicitando nuevo inicio.
3. **Cambio de contrasena fallido por politica de seguridad**: Dado pestana 'Cambiar Contrasena', cuando nueva contrasena no cumple politica (< 8 chars, sin mayuscula, sin numero), entonces bloquea y muestra requisitos no cumplidos.

**Pasos tecnicos sugeridos:**

1. Agregar campo `direccion` (TextField, blank=True) al modelo `Usuario` en `apps/usuarios/infrastructure/models.py` si no existe. **Nota:** el modelo actual tiene `cedula` y `telefono` pero NO `direccion`.
2. Crear vista `apps/usuarios/presentation/views.py` — `PerfilView` con dos formularios: `DatosPersonalesForm` (telefono, direccion) y `CambiarContrasenaForm` (contrasena actual, nueva, confirmacion).
3. Para el cambio de contrasena, usar `django.contrib.auth.views.PasswordChangeView` personalizado o implementar en `PerfilView` usando `user.check_password()` + `user.set_password()`.
4. Crear servicio de aplicacion `apps/usuarios/application/services.py` — agregar `PerfilService` que orqueste validacion y actualizacion de datos personales.
5. Crear template `templates/usuarios/perfil.html` con pestanas (tabs) para "Datos Personales" y "Cambiar Contrasena" usando Alpine.js para interactividad de tabs.
6. Asegurar que campos no editables (nombre, cedula, correo, rol) se muestran en modo lectura.
7. Tras cambio de contrasena exitoso, invalida la sesion actual y redirige a login con mensaje de confirmacion.
8. Crear tests: test de visualizacion de perfil, test de actualizacion de datos, test de cambio de contrasena exitoso, test de contrasena que no cumple politica, test de contrasena actual incorrecta.

**Criterios de aceptacion tecnicos (DoD):**

- [ ] Pagina "Mi Perfil" accesible para usuarios autenticados de cualquier rol.
- [ ] Datos personales mostrados: nombre, cedula (read-only), correo (read-only), telefono (editable), direccion (editable), rol (read-only).
- [ ] Actualizacion exitosa de telefono y direccion con mensaje de confirmacion.
- [ ] Cambio de contrasena requiere contrasena actual correcta.
- [ ] Nueva contrasena validada contra `AUTH_PASSWORD_VALIDATORS` (>= 8 chars, mayuscula, numero, simbolo).
- [ ] Sesion cerrada tras cambio de contrasena exitoso con redireccion a login.
- [ ] Mensajes de error descriptivos para cada requisito de contrasena no cumplido (Fuente: RR026).
- [ ] Vista protegida con `@login_required`.
- [ ] Tests con cobertura >= 70%.

**Riesgos y mitigacion:**

| Riesgo | Mitigacion |
|--------|-----------|
| Campo `direccion` no existe en el modelo actual | Crear migracion para agregar el campo antes de implementar la vista |
| Foto de perfil mencionada en RR004 pero no en la HU04 | Posponer foto de perfil a sprint posterior (Decision D6 resuelta) |
| Edicion de campos sensibles (cedula, correo) sin control | Campos de cedula y correo deben ser de solo lectura en el formulario de perfil. Cambio de correo requiere flujo separado con re-verificacion |

**Evidencia de completitud:**
- Captura de la pagina "Mi Perfil" con datos personales.
- Captura de edicion exitosa de telefono/direccion.
- Captura de cambio de contrasena con validacion de politica.
- Output de tests en verde.

---

### 4.5 HU05 — Gestion de periodos academicos

**Proposito:**
Permitir al Inspector Academico crear, editar, consultar y desactivar periodos academicos para organizar la estructura temporal del ciclo formativo, garantizando que solo un periodo pueda estar activo simultaneamente.

> **Fuente:** HistoriasUsuario_Sprints_ECPPP.docx — HU05; Requerimientos_ECPPP.docx — RR005

**Escenarios Gherkin (fuente: HistoriasUsuario — HU05):**

1. **Creacion exitosa de periodo**: Dado modulo 'Gestion Academica' pestana 'Periodos', cuando presiono '+ Nuevo Periodo', ingreso nombre, fecha inicio, fecha fin y marco como 'Activo', entonces guarda, muestra en listado y registra en auditoria. Los demas modulos reconocen el periodo activo automaticamente.
2. **No se permite mas de un periodo activo simultaneo**: Dado que existe un periodo 'Activo', cuando intento activar un segundo, entonces muestra advertencia y solicita confirmar desactivar el actual antes de activar el nuevo.

**Pasos tecnicos sugeridos:**

1. Extender el modelo `Periodo` existente en `apps/academico/infrastructure/models.py`: agregar campo `creado_por` (FK a Usuario, nullable) y `modificado_en` (DateTimeField auto_now) para auditoria.
2. Crear regla de dominio en `apps/academico/domain/services.py` — `PeriodoService` con invariante: "solo un periodo activo a la vez". Metodo `activar_periodo(periodo_id)` que desactiva el actual antes de activar el nuevo, requiriendo confirmacion.
3. Crear validacion de dominio: `fecha_inicio < fecha_fin`, nombre no vacio, nombre unico.
4. Crear vistas CRUD en `apps/academico/presentation/views.py`: `PeriodoListView`, `PeriodoCreateView`, `PeriodoUpdateView`. Proteger con decorador `@rol_required('inspector')`.
5. Crear serializer DRF en `apps/academico/presentation/serializers.py`: `PeriodoSerializer` con validacion de reglas de negocio.
6. Crear viewset DRF en `apps/academico/presentation/api_views.py`: `PeriodoViewSet` con permisos de Inspector.
7. Crear templates: `templates/academico/periodo_list.html`, `templates/academico/periodo_form.html`, con confirmacion modal (Alpine.js) para activacion de periodo.
8. Registrar en auditoria la creacion, edicion y cambio de estado de periodos.
9. Crear metodo o propiedad global para obtener el periodo activo: `Periodo.objects.get_activo()` (custom manager o metodo de clase).
10. Crear tests: test de creacion, test de periodo unico activo, test de edicion, test de permisos (solo inspector), test de API REST.

**Criterios de aceptacion tecnicos (DoD):**

- [ ] CRUD completo de periodos accesible solo para Inspector Academico.
- [ ] Validacion: `fecha_inicio < fecha_fin`, nombre unico.
- [ ] Restriccion de un solo periodo activo. Al activar uno nuevo, se solicita confirmacion y se desactiva el anterior.
- [ ] Listado de periodos con estado visible (Activo/Inactivo).
- [ ] Registro en auditoria de creacion, edicion y cambio de estado (Fuente: RR005).
- [ ] API REST (`/api/periodos/`) con permisos de Inspector.
- [ ] Metodo global para obtener periodo activo disponible para otros modulos.
- [ ] Tests de dominio, aplicacion y API con cobertura >= 70%.

**Riesgos y mitigacion:**

| Riesgo | Mitigacion |
|--------|-----------|
| Modelo `Periodo` existente no tiene campos de auditoria | Agregar campos via migracion. No requiere recrear la tabla |
| Condicion de carrera al activar periodos simultaneamente | Usar `select_for_update()` en la transaccion de activacion para bloqueo a nivel de DB |
| Inspector no autenticado accede a CRUD | Decorador `@rol_required('inspector')` + tests de permisos |

**Evidencia de completitud:**
- Captura del listado de periodos con estados.
- Captura de creacion de periodo con validacion.
- Captura de activacion con confirmacion modal.
- Output de tests en verde.
- Evidencia de API REST funcional (Postman/curl).

---

### 4.6 HU06 — Gestion de licencias, asignaturas y paralelos

**Proposito:**
Permitir al Inspector Academico configurar los tipos de licencia profesional, las asignaturas del curriculo y los paralelos del periodo activo, estableciendo la malla curricular y estructura de cursos necesaria para la operacion academica.

> **Fuente:** HistoriasUsuario_Sprints_ECPPP.docx — HU06; Requerimientos_ECPPP.docx — RR006, RR007

**Escenarios Gherkin (fuente: HistoriasUsuario — HU06):**

1. **Creacion de asignatura y asociacion a tipo de licencia**: Dado pestana 'Asignaturas' del modulo Gestion Academica, cuando creo asignatura con nombre, codigo, 40 horas lectivas y la asocio al tipo 'Tipo C', entonces guarda, vincula al tipo de licencia y queda disponible para paralelos.
2. **Creacion de paralelo y asignacion de docente**: Dado que existen asignaturas y docentes registrados en el periodo activo, cuando creo paralelo seleccionando periodo, tipo de licencia, asignatura, horario y docente responsable, entonces guarda y habilita para matricula de estudiantes y registro de asistencia/calificaciones.

**Pasos tecnicos sugeridos:**

1. **Crear modelo `TipoLicencia`** en `apps/academico/infrastructure/models.py`. Este modelo NO existe en Sprint 0 y es necesario para Sprint 1. Campos: `nombre` (CharField: 'Tipo C', 'Tipo E', 'Tipo E Convalidada'), `codigo` (CharField unique: 'C', 'E', 'EC'), `duracion_meses` (IntegerField), `num_asignaturas` (IntegerField), `activo` (BooleanField default True).
2. Agregar campo `horas_lectivas` (IntegerField default 40) al modelo `Asignatura`. Agregar relacion `tipo_licencia` (FK o M2M a `TipoLicencia`) al modelo `Asignatura`. **Nota:** el modelo actual no tiene `horas_lectivas` ni relacion con tipo de licencia.
3. Agregar campo `tipo_licencia` (FK a `TipoLicencia`) al modelo `Paralelo`. Agregar campo `capacidad_maxima` (IntegerField) al modelo `Paralelo` (Fuente: RR007).
4. Crear entidad de dominio `apps/academico/domain/entities.py` — agregar `TipoLicenciaEntity`.
5. Crear servicio de dominio `apps/academico/domain/services.py` — `AsignaturaService` con validaciones: codigo unico, horas lectivas > 0, asociacion a tipo de licencia valido.
6. Crear servicio de dominio — `ParaleloService` con validaciones: docente debe tener rol 'docente', periodo debe estar activo, combinacion (periodo, tipo_licencia, asignatura, nombre) unica.
7. Crear vistas CRUD en `apps/academico/presentation/views.py`: `TipoLicenciaListView`, `AsignaturaListView`, `AsignaturaCreateView`, `AsignaturaUpdateView`, `ParaleloListView`, `ParaleloCreateView`, `ParaleloUpdateView`. Proteger con `@rol_required('inspector')`.
8. Crear serializers DRF: `TipoLicenciaSerializer`, `AsignaturaSerializer`, `ParaleloSerializer`.
9. Crear viewsets DRF con filtros por periodo, tipo de licencia y estado (Fuente: RR006).
10. Crear templates: `templates/academico/asignatura_list.html`, `templates/academico/asignatura_form.html`, `templates/academico/paralelo_list.html`, `templates/academico/paralelo_form.html`, `templates/academico/tipo_licencia_list.html`.
11. Crear datos iniciales (fixture o migracion de datos) para tipos de licencia: Tipo C (6 meses, 13 asignaturas), Tipo E (5 meses, 17 asignaturas), Tipo E Convalidada (8 asignaturas) (Fuente: RR006).
12. Crear tests: test de creacion de asignatura, test de asociacion a licencia, test de creacion de paralelo, test de asignacion de docente, test de filtros API, test de permisos.

**Criterios de aceptacion tecnicos (DoD):**

- [ ] Modelo `TipoLicencia` creado con datos iniciales: Tipo C, Tipo E, Tipo E Convalidada (Fuente: RR006).
- [ ] CRUD de asignaturas con nombre, codigo, horas lectivas (default 40h) y asociacion a tipo de licencia.
- [ ] CRUD de paralelos con asociacion a periodo activo, tipo de licencia, asignatura, docente y horario.
- [ ] Docente asignado a paralelo debe tener `rol='docente'` (validacion de dominio).
- [ ] Filtros de busqueda por periodo, tipo de licencia y estado disponibles en API y listados (Fuente: RR006).
- [ ] Paralelo queda habilitado para futura matricula de estudiantes (Sprint 2 — HU07).
- [ ] API REST (`/api/asignaturas/`, `/api/paralelos/`, `/api/tipos-licencia/`) con permisos de Inspector.
- [ ] Tests de dominio, aplicacion y API con cobertura >= 70%.

**Riesgos y mitigacion:**

| Riesgo | Mitigacion |
|--------|-----------|
| Modelo `TipoLicencia` no existe en Sprint 0 — requiere nueva migracion | Crear modelo y migracion al inicio de la HU. Coordinar con HU05 para evitar conflictos de migracion |
| Modelo `Asignatura` necesita campos nuevos (`horas_lectivas`, relacion con `TipoLicencia`) | Migracion de alteracion. Asegurar compatibilidad hacia atras con datos existentes |
| Relacion Asignatura-TipoLicencia: FK vs M2M | Usar ManyToManyField (Decision D5 resuelta). Una asignatura puede pertenecer a multiples tipos de licencia (ej: Legislacion de Transito en Tipo C y Tipo E) |
| Datos iniciales de tipos de licencia deben ser consistentes | Crear data migration o fixture con los 3 tipos confirmados en RR006 |

**Evidencia de completitud:**
- Captura del listado de tipos de licencia con datos iniciales.
- Captura de creacion de asignatura con asociacion a licencia.
- Captura de creacion de paralelo con asignacion de docente.
- Output de tests en verde.
- Evidencia de API REST funcional con filtros.

---

## 5. Requerimientos trazables al Sprint 1

> **Fuente:** Requerimientos_ECPPP.docx — Tabla de requerimientos; Planificacion_Sprints_Capstone_ECPP.docx — Tabla Sprint 1

### 5.1 Requerimientos funcionales trazables

| RR | Enunciado resumido | HU relacionada | Evidencia esperada |
|----|--------------------|-----------------|--------------------|
| RR001 | Registro con nombre, cedula, correo, tipo usuario, contrasena. OTP. Validacion unicidad. Asignacion automatica de rol | HU01 | Formulario de registro funcional, OTP enviado, cuenta activada |
| RR002 | Login con correo, contrasena, tipo usuario. Sesion segun rol. Registro en auditoria con timestamp | HU02 | Login funcional con redireccion por rol, auditoria |
| RR003 | Recuperacion contrasena con enlace/codigo. Nueva contrasena con politicas. Cierre de sesion seguro | HU03, HU02 (logout) | Flujo de recuperacion completo, logout funcional |
| RR004 | Consultar/editar info personal: nombre, correo, telefono, cedula, direccion. Foto de perfil. Cambio de contrasena seguro | HU04 | Modulo de perfil funcional (foto de perfil pospuesta — Decision D6) |
| RR005 | CRUD periodos academicos: nombre, fecha inicio, fecha fin, estado. Un periodo activo. Auditoria | HU05 | CRUD de periodos con restriccion de periodo unico activo |
| RR006 | Gestionar tipos de licencia: Tipo C (6 meses, 13 asignaturas), Tipo E (5 meses, 17 asignaturas), Tipo E Convalidada (8 asignaturas). CRUD asignaturas con nombre, codigo, horas lectivas (40h default), asociacion a licencia. Buscar/filtrar | HU06 | CRUD de asignaturas y tipos de licencia con filtros |
| RR007 | Crear paralelos asociados a periodo, tipo licencia, asignatura, capacidad maxima, horario. Asignar docentes | HU06 (parcial: creacion de paralelos y asignacion de docente). Matricula de estudiantes es Sprint 2 — HU07 | CRUD de paralelos con asignacion de docente |

### 5.2 Requerimientos no funcionales trazables

| RR | Enunciado resumido | HU/Tarea relacionada | Evidencia |
|----|--------------------|-----------------------|-----------|
| RR021 | ISO 27001 — Control de acceso por roles, cifrado bcrypt/Argon2, HTTPS/TLS, clasificacion datos sensibles | HU01 (hash contrasena), HU02 (control acceso) | Contrasenas hasheadas con PBKDF2/Argon2, permisos por rol, sesiones seguras |
| RR022 | OWASP Top 10, politicas contrasenas (8 chars, mayuscula, numero, simbolo), bloqueo tras 5 intentos, rate limiting, logs inmutables | HU01 (politica contrasena), HU02 (bloqueo intentos), HU03 (politica contrasena) | Validadores de contrasena configurados, bloqueo funcional, auditoria |
| RR026 | Responsive, flujos por rol, mensajes error descriptivos | HU01–HU06 (todos) | Formularios responsive con mensajes descriptivos |
| RR027 | Paleta #2D5016/#4A7C2F/#D4B942, Inter, componentes reutilizables | HU01–HU06 (templates) | Templates con paleta corporativa aplicada |
| RR028 | DDD monolitico, DRF API REST, cobertura 70% | HU01–HU06 (arquitectura) | Servicios de dominio, viewsets DRF, tests >= 70% |
| RR030 | SMTP/Email para OTP, recuperacion, notificaciones | HU01 (OTP), HU02 (bloqueo), HU03 (recuperacion) | Correos enviados para OTP, bloqueo y recuperacion |

---

## 6. Decisiones de arquitectura y stack

### 6.A Decisiones confirmadas por documentos (heredadas de Sprint 0)

Las siguientes decisiones estan confirmadas desde Sprint 0 y aplican a Sprint 1:

| Decision | Detalle | Fuente |
|----------|---------|--------|
| Framework web | Django 5.1.x | Planificacion — Encabezado; PRD Sprint 0 — Seccion 6.B |
| Base de datos | PostgreSQL 18.x | Planificacion — Encabezado; PRD Sprint 0 — Seccion 6.B |
| Arquitectura | Monolitica con DDD (4 capas) | Requerimientos — RR028 |
| API REST interna | Django REST Framework 3.16.x | Requerimientos — RR028; requirements.txt |
| CSS | Tailwind CSS 3.4.17 CDN | PRD Sprint 0 — Seccion 6.B; templates/base.html |
| JS | Alpine.js 3.15.9 CDN | PRD Sprint 0 — Seccion 6.B; templates/base.html |
| Testing | pytest + pytest-django + coverage + factory-boy | PRD Sprint 0 — Seccion 6.B; requirements.txt |
| Custom User Model | `AUTH_USER_MODEL = 'usuarios.Usuario'` (AbstractUser) | config/settings/base.py |
| Correo electronico | SMTP/Email para OTP, recuperacion, notificaciones | Requerimientos — RR030 |
| Cifrado contrasenas | bcrypt o Argon2 (Django default: PBKDF2. Migrar si se requiere Argon2) | Requerimientos — RR021 |

### 6.B Decisiones confirmadas por el equipo para Sprint 1

| Decision | Detalle | Fuente |
|----------|---------|--------|
| Convencion de ramas Sprint 1 | `feature/HU01-registro-usuario`, `feature/HU02-inicio-sesion`, etc. | PRD Sprint 0 — Seccion 7.1 |
| Versionado | `0.2.0` para Sprint 1 | PRD Sprint 0 — Seccion 7.1 |
| Gestion del proyecto | Jira | Decision de equipo (Sprint 0) |

### 6.C Decisiones resueltas para Sprint 1

Sprint 1 introduce funcionalidades nuevas que requerian decisiones de arquitectura. Todas resueltas:

| # | Decision | Resolucion | Razon | HU afectada |
|---|----------|-----------|-------|-------------|
| D1 | **Backend de email en desarrollo** | `console.EmailBackend` en development.py. SMTP real solo en produccion | Zero config en desarrollo, emails visibles en consola para debugging | HU01, HU02, HU03 |
| D2 | **Mecanismo de OTP** | Modelo custom `OTPToken` (codigo 6 digitos, expiracion 10 min) | Mas simple que `django-otp`, sin dependencias extra, control total sobre el flujo | HU01 |
| D3 | **Algoritmo de hash de contrasena** | PBKDF2 (default Django) | Ya es seguro y cumple RR021. Argon2 agrega dependencia C sin beneficio real para el volumen de usuarios esperado | HU01, HU03, HU04 |
| D4 | **Backend de autenticacion** | Sesiones Django (server-side) + `SessionAuthentication` de DRF para API interna | No hay mobile app ni API publica. JWT es overengineering. Sesiones server-side son mas seguras para web | HU02 |
| D5 | **Relacion Asignatura-TipoLicencia** | ManyToManyField (1 asignatura puede pertenecer a N tipos de licencia) | RR006 indica asignaturas compartidas entre licencias (ej: Legislacion de Transito en Tipo C y Tipo E) | HU06 |
| D6 | **Foto de perfil** | Posponer a sprint posterior | No esta en los escenarios Gherkin de HU04. Agrega scope innecesario (Pillow, MEDIA_ROOT, ImageField) | HU04 |
| D7 | **Tiempo de expiracion OTP** | 10 minutos | Balance seguridad/usabilidad. 30 min es excesivo para un codigo de 6 digitos | HU01 |
| D8 | **Duracion del bloqueo por intentos fallidos** | 15 minutos (temporal, automatico) | Bloqueo temporal evita DoS por bloqueo manual. 15 min es estandar de industria | HU02 |
| D9 | **Politica de contrasena: simbolo obligatorio** | Si (>= 8 chars + mayuscula + numero + simbolo) | RR022 lo requiere explicitamente. Validador custom de Django | HU01, HU03, HU04 |

> Todas las decisiones resueltas el 06/04/2026 por el equipo de desarrollo.

---

## 7. Modelo de datos — Cambios del Sprint 1

> **Nota:** Sprint 0 creo 8 modelos base: `Usuario`, `Periodo`, `Asignatura`, `Paralelo`, `Evaluacion`, `Calificacion`, `Asistencia`, `Solicitud`. Sprint 1 requiere nuevos modelos y modificaciones a los existentes.

### 7.1 Nuevos modelos

| Modelo | App | Campos principales | Fuente |
|--------|-----|-------------------|--------|
| `TipoLicencia` | `academico` | `nombre` (CharField), `codigo` (CharField unique), `duracion_meses` (IntegerField), `num_asignaturas` (IntegerField), `activo` (BooleanField) | RR006 — Tipos de licencia: C, E, E Convalidada |
| `OTPToken` | `usuarios` | `usuario` (FK), `codigo` (CharField 6), `creado_en` (DateTimeField), `expira_en` (DateTimeField), `usado` (BooleanField) | RR001 — Verificacion OTP en registro |
| `RegistroAuditoria` | `usuarios` | `usuario` (FK nullable), `accion` (CharField), `ip` (GenericIPAddressField), `timestamp` (DateTimeField auto), `detalle` (TextField) | RR002 — Registro de accesos en auditoria |

### 7.2 Modificaciones a modelos existentes

| Modelo | Cambio | Razon | Fuente |
|--------|--------|-------|--------|
| `Usuario` | Agregar `direccion` (TextField, blank=True) | Edicion de direccion en perfil | RR004 |
| `Usuario` | Agregar `intentos_fallidos` (IntegerField, default=0) | Conteo de intentos de login fallidos | RR022 |
| `Usuario` | Agregar `bloqueado_hasta` (DateTimeField, nullable) | Bloqueo temporal tras 5 intentos | RR022 |
| `Usuario` | Cambiar default `is_active=False` en creacion (logica de negocio, no campo del modelo) | Flujo de activacion OTP | RR001 |
| `Asignatura` | Agregar `horas_lectivas` (IntegerField, default=40) | Horas lectivas por asignatura | RR006 |
| `Asignatura` | Agregar relacion con `TipoLicencia` (ManyToManyField — Decision D5 resuelta) | Asociacion asignatura-licencia. Una asignatura puede pertenecer a multiples tipos de licencia | RR006 |
| `Paralelo` | Agregar `tipo_licencia` (FK a `TipoLicencia`) | Asociacion paralelo-licencia | RR007 |
| `Paralelo` | Agregar `capacidad_maxima` (IntegerField) | Capacidad maxima del paralelo | RR007 |
| `Periodo` | Agregar `creado_por` (FK a Usuario, nullable) | Auditoria de quien creo el periodo | RR005 |
| `Periodo` | Agregar `modificado_en` (DateTimeField, auto_now) | Auditoria de ultima modificacion | RR005 |

### 7.3 Entidades de dominio nuevas

| Entidad | App | Ubicacion |
|---------|-----|-----------|
| `TipoLicenciaEntity` | `academico` | `apps/academico/domain/entities.py` |
| `OTPTokenEntity` | `usuarios` | `apps/usuarios/domain/entities.py` |
| `RegistroAuditoriaEntity` | `usuarios` | `apps/usuarios/domain/entities.py` |

### 7.4 Datos iniciales (fixtures / data migrations)

| Dato | Valores | Fuente |
|------|---------|--------|
| Tipos de licencia | Tipo C (6 meses, 13 asignaturas), Tipo E (5 meses, 17 asignaturas), Tipo E Convalidada (duracion **TODO: confirmar con stakeholders**, 8 asignaturas) | RR006 |

---

## 8. Configuracion de entorno — Cambios del Sprint 1

### 8.1 Nuevas variables de entorno

> Sprint 0 definio variables de BD y Django. Sprint 1 agrega variables de email/SMTP.

```env
# === Variables heredadas de Sprint 0 (sin cambios) ===
# DATABASE_NAME, DATABASE_USER, DATABASE_PASSWORD, DATABASE_HOST, DATABASE_PORT
# DJANGO_SECRET_KEY, DJANGO_DEBUG, DJANGO_SETTINGS_MODULE, DJANGO_ALLOWED_HOSTS

# === Nuevas variables Sprint 1 ===

# Email/SMTP (Fuente: RR030 — envio de OTP, recuperacion, notificaciones)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=<definir>
EMAIL_PORT=587
EMAIL_HOST_USER=<definir>
EMAIL_HOST_PASSWORD=<definir>
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@ecppp.edu.ec

# Seguridad (Fuente: RR022)
PASSWORD_RESET_TIMEOUT=1800   # 30 minutos en segundos (Fuente: HU03)
OTP_EXPIRATION_MINUTES=10     # Decision D7: 10 minutos
ACCOUNT_LOCKOUT_MINUTES=15    # Decision D8: 15 minutos
MAX_LOGIN_ATTEMPTS=5          # Fuente: RR022
```

### 8.2 Nuevas dependencias (`requirements.txt`)

No se agregan dependencias nuevas para Sprint 1. Las decisiones D3 (PBKDF2 default) y D4 (sesiones Django) evitan agregar paquetes adicionales. El mecanismo de OTP (D2) y el bloqueo por intentos (D8) se implementan con modelos custom sin librerias externas.

### 8.3 Configuracion de `settings/development.py`

Agregar para Sprint 1:

```python
# Email backend para desarrollo — imprime emails en consola
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Password reset timeout (30 min)
PASSWORD_RESET_TIMEOUT = 1800
```

### 8.4 Configuracion de `settings/base.py`

Agregar para Sprint 1:

```python
# Login/Logout URLs
LOGIN_URL = '/usuarios/login/'
LOGIN_REDIRECT_URL = '/usuarios/dashboard/'
LOGOUT_REDIRECT_URL = '/usuarios/login/'

# Password validators — actualizar segun politica RR022
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
    # Validador custom para mayuscula + simbolo (Decision D9: simbolo obligatorio)
]

# Session security
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 3600  # 1 hora
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
```

---

## 9. Riesgos del Sprint 1

| # | Riesgo | Probabilidad | Impacto | Mitigacion | Responsable |
|---|--------|-------------|---------|-----------|-------------|
| R1 | Capacidad reducida por Semana Santa (jueves 2 y viernes 3 de abril) — 2 dias habiles menos en una iteracion de 2 semanas | Alta (confirmado) | Alto | 16 puntos ya ajustados a capacidad reducida. Priorizar HU01 y HU02 (criticas para las demas). Si hay retraso, HU04 (2 pts) es la mas sacrificable | Dev A + Dev B |
| R2 | Configuracion SMTP bloqueada o no disponible en entorno de desarrollo | Media | Alto | Usar `console.EmailBackend` en desarrollo. SMTP real solo en CI/produccion. Probar con Mailtrap si se necesita visualizacion | Dev B |
| R3 | Modelo `TipoLicencia` no existe — requiere nueva migracion y posibles conflictos con modelos existentes | Baja | Medio | Crear la migracion al inicio del sprint. Coordinar orden de migraciones entre HU05 y HU06 | Dev B |
| R4 | 9 decisiones de arquitectura pendientes (Seccion 6.C) — bloquean implementacion si no se resuelven | Alta | Alto | Resolver las 9 decisiones en la reunion de planificacion del Sprint 1 (dia 1: 30/03). Documentar en Jira | Dev A + Dev B |
| R5 | Backend de autenticacion personalizado introduce vulnerabilidades de seguridad | Media | Alto | Extender `ModelBackend` de Django, no reimplementar. Tests exhaustivos de autenticacion. Code review obligatorio | Dev B |
| R6 | Dependencias entre HUs crean bloqueos (HU02→HU01, HU04→HU02, HU05→HU02, HU06→HU05) | Media | Alto | Planificar ejecucion secuencial: Semana 1 → HU01, HU02, HU03. Semana 2 → HU04, HU05, HU06. Trabajar en paralelo donde sea posible | Dev A + Dev B |
| R7 | Migraciones de modelos existentes (Usuario, Asignatura, Paralelo) causan perdida de datos de prueba | Baja | Bajo | Sprint 0 tiene datos de prueba minimos. Las migraciones de alteracion no destruyen datos existentes. Verificar con `python manage.py migrate --plan` | Dev B |
| R8 | Politica de contrasena con simbolo obligatorio (RR022) complejiza la experiencia de usuario | Media | Bajo | Implementar validadores custom con mensajes claros sobre cada requisito no cumplido. Alpine.js para feedback en tiempo real en formularios | Dev A |

---

## 10. Metricas de exito del Sprint 1

| # | Metrica | Criterio de exito | Metodo de verificacion |
|---|---------|-------------------|----------------------|
| M1 | HUs completadas | 6/6 HUs (HU01–HU06) marcadas como "Done" con evidencia de completitud | Revision del tablero Jira al cierre del sprint (10/04) |
| M2 | Puntos completados | 16/16 puntos entregados | Burndown chart de Jira |
| M3 | Pipeline CI en verde | Pipeline ejecutandose sin errores con todos los tests del Sprint 1 | Enlace al pipeline en GitHub Actions |
| M4 | Cobertura de tests | >= 70% en capa de dominio (Fuente: RR028) | Output de `coverage report --fail-under=70` en CI |
| M5 | Flujo de registro + OTP funcional | Usuario puede registrarse, recibir OTP, activar cuenta e iniciar sesion | Demo en la reunion de cierre del Sprint 1 |
| M6 | Control de acceso por rol | Inspector accede a CRUD academico; Docente y Estudiante NO | Demo de permisos por rol en la reunion de cierre |
| M7 | API REST funcional | Endpoints de periodos, asignaturas, paralelos y tipos de licencia operativos con permisos | Evidencia con Postman/curl o tests de API |
| M8 | Seguridad basica | Bloqueo por intentos, politica de contrasena, mensajes genericos, sesiones seguras | Tests automatizados + revision de configuracion |
| M9 | Velocidad del equipo | Comparar puntos completados (objetivo: 16) vs planificados (16) para calibrar Sprint 2 | Registro al cierre del sprint |

---

## 11. Conflictos detectados o decisiones pendientes

### 11.1 Modelo `TipoLicencia` ausente en Sprint 0 — RESUELTO

| Conflicto | Detalle |
|-----------|---------|
| **Donde** | Sprint 0 definio 8 modelos base (Usuario, Periodo, Asignatura, Paralelo, Evaluacion, Calificacion, Asistencia, Solicitud) pero NO incluyo `TipoLicencia` |
| **Inconsistencia** | RR006 requiere gestion de tipos de licencia (Tipo C, Tipo E, Tipo E Convalidada) con atributos especificos (duracion, numero de asignaturas). El modelo `Asignatura` actual no tiene relacion con tipo de licencia ni campo `horas_lectivas` |
| **Resolucion propuesta** | Crear modelo `TipoLicencia` en Sprint 1 como parte de HU06. Relacion Asignatura→TipoLicencia via ManyToManyField (Decision D5 resuelta) |

### 11.2 Foto de perfil (RR004) no mencionada en HU04 — RESUELTO

| Conflicto | Detalle |
|-----------|---------|
| **Donde** | Requerimientos — RR004 menciona "foto de perfil" como dato editable. HistoriasUsuario — HU04 NO incluye foto de perfil en sus escenarios Gherkin |
| **Inconsistencia** | HU04 permite editar telefono y direccion, pero no foto. RR004 la incluye |
| **Resolucion** | Foto de perfil pospuesta a sprint posterior (Decision D6 resuelta). No esta en los escenarios Gherkin de HU04 y agrega scope innecesario (Pillow, MEDIA_ROOT, ImageField) |

### 11.3 Campo `direccion` no existe en modelo `Usuario` actual — RESUELTO

| Conflicto | Detalle |
|-----------|---------|
| **Donde** | El modelo `Usuario` actual (Sprint 0) tiene: `rol`, `cedula`, `telefono`. NO tiene `direccion` |
| **Inconsistencia** | HU04 requiere edicion de direccion. RR004 incluye direccion como dato del perfil |
| **Resolucion** | Agregar campo `direccion` (TextField, blank=True) al modelo `Usuario` via migracion en Sprint 1 |

### 11.4 Tipo de autenticacion: sesiones vs JWT — RESUELTO

| Conflicto | Detalle |
|-----------|---------|
| **Donde** | HU02 menciona "sesion segura" y "elimina el token". No queda claro si se refiere a session cookie o JWT |
| **Inconsistencia** | Django por defecto usa sesiones server-side. Si la API REST (DRF) requiere autenticacion stateless, podria necesitar JWT |
| **Resolucion** | Sesiones Django (server-side) para la interfaz web + `SessionAuthentication` de DRF para la API interna (Decision D4 resuelta). No hay mobile app ni API publica que justifique JWT |

### 11.5 Duracion de Tipo E Convalidada no especificada — PENDIENTE

| Conflicto | Detalle |
|-----------|---------|
| **Donde** | RR006 especifica: Tipo C (6 meses, 13 asignaturas), Tipo E (5 meses, 17 asignaturas), Tipo E Convalidada (8 asignaturas) |
| **Inconsistencia** | La duracion en meses de Tipo E Convalidada NO esta especificada en los documentos fuente |
| **Resolucion propuesta** | **TODO: confirmar con el equipo la duracion de Tipo E Convalidada** |

### 11.6 Capacidad maxima de paralelo (RR007) no mencionada en HU06 — RESUELTO

| Conflicto | Detalle |
|-----------|---------|
| **Donde** | RR007 menciona "capacidad maxima" como atributo de paralelos. HU06 no lo menciona explicitamente en sus escenarios Gherkin |
| **Inconsistencia** | El modelo `Paralelo` actual no tiene campo `capacidad_maxima` |
| **Resolucion propuesta** | Incluir campo `capacidad_maxima` en el modelo `Paralelo` como parte de HU06. Necesario para Sprint 2 — HU07 (matriculacion) |

---

## 12. Referencias

| # | Documento | Archivo | Version | Fecha |
|---|-----------|---------|---------|-------|
| 1 | Planificacion de Sprints — Capstone ECPP | `Planificacion_Sprints_Capstone_ECPP.docx` | 1.0 | Marzo 2026 |
| 2 | Levantamiento de Requerimientos — Plataforma Web Academica ECPPP | `Requerimientos_ECPPP.docx` | 1.0 | Marzo 2026 |
| 3 | Historias de Usuario y Criterios de Aceptacion — ECPPP | `HistoriasUsuario_Sprints_ECPPP.docx` | 1.0 | Marzo 2026 |
| 4 | PRD Sprint 0 | `docs/PRDSprint0ECPPP.md` | 0.1.0 | Abril 2026 |

---

*Documento generado como parte del Sprint 1 del proyecto Plataforma Web Academica ECPPP.*
*Estado: Draft — pendiente de revision y aprobacion por el equipo.*
*Las 9 decisiones de arquitectura de la Seccion 6.C han sido resueltas. Solo queda pendiente la duracion de Tipo E Convalidada (Seccion 11.5).*
