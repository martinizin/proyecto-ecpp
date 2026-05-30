# ADR-ECPPP — Guía de Defensa del Proyecto
> Plataforma Académica ECPPP · Avance de Proyecto · 2026

---

## Índice

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Arquitectura General](#2-arquitectura-general)
3. [Patrones Arquitectónicos y de Diseño](#3-patrones-arquitectónicos-y-de-diseño)
4. [Stack Tecnológico y Librerías](#4-stack-tecnológico-y-librerías)
5. [Base de Datos](#5-base-de-datos)
6. [Seguridad](#6-seguridad)
7. [Almacenamiento de Archivos](#7-almacenamiento-de-archivos)
8. [Despliegue](#8-despliegue)
9. [Calidad de Software — ISO 25010](#9-calidad-de-software--iso-25010)
10. [CI/CD y Testing](#10-cicd-y-testing)
11. [Módulos del Sistema](#11-módulos-del-sistema)
12. [Banco de Preguntas y Respuestas](#12-banco-de-preguntas-y-respuestas)

---

## 1. Resumen Ejecutivo

**ECPPP** es una plataforma académica web orientada a la gestión educativa de una institución. Permite administrar usuarios (estudiantes, docentes, inspectores y secretaría), periodos académicos, matrículas, asignaturas, paralelos, calificaciones, asistencia, solicitudes estudiantiles y notificaciones.

| Atributo | Valor |
|---|---|
| Lenguaje | Python 3.12 |
| Framework Backend | Django 5.1.7 |
| Base de datos | PostgreSQL 18 |
| Frontend | Django Templates + Tailwind CSS + Alpine.js |
| Arquitectura | Hexagonal / DDD por Bounded Context |
| Cobertura de tests | ≥ 70% (umbral forzado en CI) |
| Control de calidad | ISO 25010 |

---

## 2. Arquitectura General

El proyecto implementa **Arquitectura Hexagonal (Ports & Adapters)** combinada con principios de **Domain-Driven Design (DDD)**. Cada módulo funcional del sistema es un *Bounded Context* independiente.

### 2.1 Estructura por app (Bounded Context)

```
apps/
├── usuarios/          ← Gestión de usuarios, autenticación, OTP, auditoría
├── academico/         ← Periodos, tipos de licencia, asignaturas, paralelos, matrículas
├── calificaciones/    ← Evaluaciones y notas
├── asistencia/        ← Control de asistencia
├── solicitudes/       ← Solicitudes estudiantiles (rectificación, justificación)
├── secretaria/        ← Funciones administrativas de secretaría
├── notificaciones/    ← Sistema de notificaciones internas
├── core/              ← Utilidades transversales
└── shared/            ← Componentes compartidos entre bounded contexts
```

### 2.2 Capas internas por app

Cada app sigue estrictamente la separación en 4 capas:

```
apps/<contexto>/
├── domain/
│   ├── entities.py        ← Entidades de dominio (Python puro, sin Django)
│   ├── value_objects.py   ← Objetos de valor inmutables
│   ├── repositories.py    ← Interfaces/puertos de acceso a datos
│   ├── services.py        ← Lógica de negocio pura
│   └── exceptions.py      ← Excepciones del dominio
├── application/           ← Casos de uso / orquestación
├── infrastructure/
│   ├── models.py          ← Modelos ORM (Django)
│   ├── repositories.py    ← Implementación de los puertos
│   └── ...                ← Adaptadores externos (email, auth backend, etc.)
└── presentation/          ← Vistas Django, formularios, URLs
```

### 2.3 Flujo de una solicitud HTTP

```
Browser
  │
  ▼
[Nginx] ──proxy──► [Gunicorn / Django WSGI]
                        │
                   Middleware stack
                        │
                   Router (config/urls.py)
                        │
              presentation/views.py
                        │
              application/use_cases.py
                        │
              domain/services.py
                        │
           infrastructure/repositories.py
                        │
                  PostgreSQL DB
```

---

## 3. Patrones Arquitectónicos y de Diseño

### 3.1 Patrones Arquitectónicos

| Patrón | Dónde se aplica |
|---|---|
| **Hexagonal Architecture (Ports & Adapters)** | Estructura de cada bounded context |
| **Domain-Driven Design (DDD)** | Entidades, Value Objects, Repos por contexto |
| **MVT (Model-View-Template)** | Presentación con Django nativo |
| **Repository Pattern** | `domain/repositories.py` (interfaz) + `infrastructure/repositories.py` (impl.) |
| **Settings por entorno** | `config/settings/base.py` → `development.py` / `production.py` |

### 3.2 Patrones de Diseño (GoF / Aplicados)

| Patrón | Aplicación concreta |
|---|---|
| **Strategy** | `AUTHENTICATION_BACKENDS`: `ECPPPAuthBackend` + `ModelBackend` intercambiables |
| **Template Method** | `AbstractUser` extendido por `Usuario` — Django usa Template Method en su sistema de auth |
| **Observer / Signals** | Django signals para efectos secundarios (notificaciones) |
| **Factory** | `factory-boy` en tests — `UserFactory`, etc. para generación de fixtures |
| **Decorator** | Decoradores `@login_required`, `@permission_required` en vistas |
| **Middleware Chain** | `ForzarCambioPasswordMiddleware` como parte del pipeline de middlewares |
| **Value Object** | Entidades de dominio como `@dataclass(frozen=True)` — inmutables por diseño |

### 3.3 Principios SOLID aplicados

- **S** (Single Responsibility): cada capa tiene una sola razón de cambio.
- **O** (Open/Closed): repositorios dependen de interfaces; se pueden cambiar de ORM sin tocar el dominio.
- **L** (Liskov): `ECPPPAuthBackend` extiende `ModelBackend` correctamente.
- **I** (Interface Segregation): repositorios del dominio exponen solo lo que necesita cada contexto.
- **D** (Dependency Inversion): la capa de dominio no importa Django; las capas superiores dependen de abstracciones.

---

## 4. Stack Tecnológico y Librerías

### 4.1 Backend

| Librería | Versión | Propósito |
|---|---|---|
| **Django** | 5.1.7 | Framework web principal (MVT, ORM, Auth, Admin) |
| **djangorestframework** | 3.16.0 | API REST (actualmente usado en módulo académico) |
| **psycopg2-binary** | 2.9.10 | Adaptador PostgreSQL para Django |
| **python-dotenv** | 1.1.0 | Carga de variables de entorno desde `.env` |
| **python-dateutil** | 2.9.0 | Manejo avanzado de fechas (periodos académicos) |

### 4.2 Frontend

| Librería | Versión | Propósito |
|---|---|---|
| **Tailwind CSS** | 3.4.17 (CDN) | Framework de utilidades CSS — todo el estilizado |
| **Alpine.js** | 3.15.9 (CDN) | Reactividad ligera en templates (sidebar, modals, alerts) |
| **Tom Select** | 2.3.1 (CDN) | Selects enriquecidos con búsqueda |
| **Inter (Google Fonts)** | — | Tipografía principal del sistema |

> **Nota sobre el uso de CDN:** En producción se evaluará la estrategia de self-hosting de estos assets para eliminar dependencias externas y mejorar el tiempo de carga.

### 4.3 Calidad / Testing / Linting

| Herramienta | Versión | Propósito |
|---|---|---|
| **pytest** | 8.3.5 | Framework de tests |
| **pytest-django** | 4.10.0 | Integración pytest con Django |
| **coverage** | 7.8.0 | Medición de cobertura (umbral ≥ 70%) |
| **factory-boy** | 3.3.1 | Generación de fixtures en tests |
| **flake8** | 7.2.0 | Linter de estilo (PEP8) |
| **black** | 25.1.0 | Formateador de código |

### 4.4 Entorno de ejecución

- **Python** 3.12.x
- **PostgreSQL** 18.x
- **GitHub Actions** para CI/CD

---

## 5. Base de Datos

### 5.1 Motor elegido: PostgreSQL (SQL Relacional)

Se eligió **PostgreSQL** por las siguientes razones técnicas:

| Razón | Explicación |
|---|---|
| **Datos altamente relacionales** | Usuarios → Matrículas → Paralelos → Calificaciones → Asistencia. Todas las entidades tienen FK fuertemente tipadas. |
| **Integridad referencial** | `ON DELETE CASCADE`, `SET NULL`, `PROTECT` — PostgreSQL garantiza integridad sin lógica extra en la app. |
| **ACID compliance** | Transacciones atómicas críticas para el registro académico (crear usuario + asignar matrícula, por ejemplo). |
| **Índices compuestos** | Se definen índices en campos de búsqueda frecuente: `(usuario, accion, timestamp)`, `(usuario, usado, expira_en)`. |
| **Soporte nativo en Django** | El ORM de Django está optimizado para PG; funciones como `DISTINCT ON`, `F expressions`, migraciones robustas. |

**¿Por qué NO NoSQL?** Los datos del sistema son estructurados, con esquemas fijos y relaciones bien definidas. Un motor documental (MongoDB, etc.) agregaría complejidad sin beneficio real dado que no hay datos semiestructurados ni escala que lo justifique.

### 5.2 Modelos principales

```
Usuario (AbstractUser extendido)
  ├── rol: estudiante | docente | inspector | secretaria
  ├── cedula: CharField (único, obligatorio, inmutable post-creación)
  ├── intentos_fallidos, bloqueado_hasta   ← seguridad de cuenta
  └── debe_cambiar_password               ← contraseña temporal

OTPToken
  └── FK → Usuario (token de 6 dígitos, expirable, one-use)

RegistroAuditoria
  └── FK → Usuario (audit log: login, logout, lockout, etc.)

TipoLicencia → Periodo → Asignatura → Paralelo → Matricula
  └── Calificacion / Asistencia → Solicitud
```

### 5.3 Configuración de entornos

- **Desarrollo:** PostgreSQL local vía `.env`
- **Producción:** PostgreSQL en VPS (misma instancia o servicio gestionado) con credenciales por variables de entorno
- **No hay SQLite** como fallback — el proyecto fuerza PostgreSQL desde el inicio

---

## 6. Seguridad

### 6.1 Autenticación

El sistema usa un backend de autenticación **personalizado** (`ECPPPAuthBackend`) que autentica por **triple factor**: `email + contraseña + rol`. El rol se selecciona en la pantalla de login y actúa como un factor adicional de verificación.

### 6.2 Contraseñas — Encriptación

Las contraseñas se almacenan usando el **hasher por defecto de Django: PBKDF2 con SHA-256** (iterable, salteado automáticamente). Además se aplican los siguientes validadores:

| Validador | Regla |
|---|---|
| `MinimumLengthValidator` | Mínimo 8 caracteres |
| `CommonPasswordValidator` | Rechaza las 20.000 contraseñas más comunes |
| `NumericPasswordValidator` | No puede ser solo numérica |
| `UppercaseValidator` (custom) | Al menos una mayúscula |
| `SymbolValidator` (custom) | Al menos un símbolo especial |
| `UserAttributeContainmentValidator` (custom) | No puede contener nombre, apellido, email ni rol del usuario |
| `UserAttributeSimilarityValidator` | No puede ser similar a atributos del usuario |

> **Resumen:** Las contraseñas **nunca se almacenan en texto plano**. Django usa PBKDF2-SHA256 con salt aleatorio por defecto. Ninguna contraseña es legible desde la base de datos.

### 6.3 Control de intentos de login

- Máximo **5 intentos fallidos** antes del bloqueo.
- Bloqueo de cuenta por **15 minutos**.
- Los intentos y la fecha de bloqueo se almacenan en el modelo `Usuario`.

### 6.4 OTP (One-Time Password)

- Sistema de verificación por email con códigos de 6 dígitos.
- Expiración configurable (default: 10 minutos).
- Tokens marcados como `usado = True` tras su uso, evitando reutilización.

### 6.5 Seguridad de sesión

```python
SESSION_COOKIE_HTTPONLY = True        # JS no puede acceder a la cookie
SESSION_COOKIE_AGE = 3600             # Sesión expira en 1 hora
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Cierra al cerrar el browser
```

En producción se agrega:
```python
CSRF_COOKIE_SECURE = True      # CSRF solo por HTTPS
SESSION_COOKIE_SECURE = True   # Sesión solo por HTTPS
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
```

### 6.6 CSRF

Django activa el middleware `CsrfViewMiddleware` por defecto. Todos los formularios POST requieren `{% csrf_token %}`. Los endpoints DRF usan `SessionAuthentication` que también valida CSRF.

### 6.7 Auditoría

El modelo `RegistroAuditoria` registra acciones sensibles (login, logout, bloqueo, reset de password) con timestamp, IP del cliente y usuario involucrado.

### 6.8 Middleware de contraseña temporal

`ForzarCambioPasswordMiddleware` intercepta toda petición autenticada y redirige al usuario al formulario de cambio de contraseña si `debe_cambiar_password = True` (activado cuando Secretaría crea el usuario).

---

## 7. Almacenamiento de Archivos

### 7.1 Estado actual

Django gestiona los archivos subidos (PDFs e imágenes) mediante su sistema de **Media Files**:

```python
MEDIA_URL  = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```

Los archivos se almacenan en el **filesystem local** del servidor, dentro de la carpeta `media/`. Django sirve los archivos en desarrollo vía `django.views.static.serve`. El sistema permite previsualización inline (PDFs vía `<iframe>`, imágenes vía `<img>`).

### 7.2 En producción (VPS)

Nginx sirve los archivos estáticos y de media directamente sin pasar por Django:

```nginx
location /media/ {
    alias /var/www/ecppp/media/;
}
location /static/ {
    alias /var/www/ecppp/staticfiles/;
}
```

### 7.3 Alternativa escalable (futuro)

Si el volumen de archivos crece o se requiere CDN, la migración natural es **Amazon S3** o compatible (DigitalOcean Spaces) usando `django-storages`. El cambio solo afecta la capa de infraestructura — el dominio no se toca.

---

## 8. Despliegue

### 8.1 Estrategia — VPS con Nginx + Gunicorn

La opción elegida para producción es un **VPS** (Ubuntu 22.04 LTS recomendado) con el siguiente stack:

```
┌─────────────────────────────────────────────┐
│                  INTERNET                   │
└────────────────────┬────────────────────────┘
                     │ HTTPS :443
                     ▼
          ┌─────────────────────┐
          │       Nginx         │  Reverse proxy + static/media files
          │  (TLS via Certbot)  │
          └──────────┬──────────┘
                     │ Unix socket / :8000
                     ▼
          ┌─────────────────────┐
          │    Gunicorn (WSGI)  │  Django app server (4 workers)
          │  config.wsgi:app    │
          └──────────┬──────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │   Django 5.1.7      │  Lógica de negocio
          │   Python 3.12       │
          └──────────┬──────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │   PostgreSQL 18     │  Base de datos relacional
          │   (mismo VPS)       │
          └─────────────────────┘
```

### 8.2 Diagrama de despliegue detallado

```
[Cliente / Navegador]
        │
        │ HTTPS (443) - TLS/SSL via Let's Encrypt
        ▼
┌───────────────────────────────────────────────┐
│               VPS (Ubuntu 22.04)               │
│                                               │
│  ┌─────────────────────────────────────────┐  │
│  │             NGINX                       │  │
│  │  • Termina TLS                          │  │
│  │  • Redirige HTTP → HTTPS                │  │
│  │  • Sirve /static/ y /media/ directo     │  │
│  │  • Proxy pass → Gunicorn socket         │  │
│  └──────────────────┬──────────────────────┘  │
│                     │                         │
│  ┌──────────────────▼──────────────────────┐  │
│  │          GUNICORN (WSGI)                │  │
│  │  • 4 workers síncronos                  │  │
│  │  • Gestionado por systemd               │  │
│  │  • Bind: unix:/run/ecppp.sock           │  │
│  └──────────────────┬──────────────────────┘  │
│                     │                         │
│  ┌──────────────────▼──────────────────────┐  │
│  │           DJANGO APP                    │  │
│  │  • DJANGO_SETTINGS_MODULE=production    │  │
│  │  • Variables de entorno en /etc/ecppp   │  │
│  │  • collectstatic → /staticfiles/        │  │
│  │  • media/ → /var/www/ecppp/media/       │  │
│  └──────────────────┬──────────────────────┘  │
│                     │                         │
│  ┌──────────────────▼──────────────────────┐  │
│  │          POSTGRESQL 18                  │  │
│  │  • DB: ecppp_db                         │  │
│  │  • Puerto 5432 (solo localhost)         │  │
│  │  • Backups automáticos (cron + pg_dump) │  │
│  └─────────────────────────────────────────┘  │
│                                               │
│  ┌─────────────────────────────────────────┐  │
│  │           EMAIL (SMTP externo)          │  │
│  │  Gmail / Brevo / Mailgun               │  │
│  └─────────────────────────────────────────┘  │
└───────────────────────────────────────────────┘
```

### 8.3 Pasos del despliegue

1. Provisionar VPS (DigitalOcean Droplet / Hetzner / AWS Lightsail)
2. Instalar Python 3.12, PostgreSQL 18, Nginx
3. Clonar repositorio, crear virtualenv, `pip install -r requirements.txt`
4. Configurar `.env` de producción con `DJANGO_DEBUG=False`
5. `python manage.py migrate` + `python manage.py collectstatic`
6. Configurar Gunicorn como servicio systemd
7. Configurar Nginx como reverse proxy
8. Obtener certificado TLS con `certbot --nginx`
9. Configurar backups periódicos con `pg_dump` via cron

### 8.4 Variables de entorno críticas en producción

```
DJANGO_SECRET_KEY=<clave_segura_generada>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=tudominio.com
DATABASE_NAME=ecppp_db
DATABASE_USER=ecppp_user
DATABASE_PASSWORD=<password_seguro>
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=noreply@tudominio.com
EMAIL_HOST_PASSWORD=<app_password>
```

---

## 9. Calidad de Software — ISO 25010

El proyecto toma como referencia la norma **ISO/IEC 25010:2011** (SQuaRE) que define 8 características de calidad del producto software.

---

### 9.1 Adecuación Funcional

**Definición:** El sistema proporciona funciones que satisfacen las necesidades declaradas e implícitas.

**Cumplimiento actual:**
- Gestión completa de usuarios con roles diferenciados (estudiante, docente, inspector, secretaría).
- Control de periodos académicos, asignaturas, paralelos y matrículas con validaciones de negocio (cupo máximo, duración de periodos, horas lectivas, conflictos de horario docente/estudiante — HU21).
- Módulos de calificaciones, asistencia y solicitudes estudiantiles implementados con entidades de dominio.
- Casos de uso cubiertos con especificaciones formales (SDD specs en `openspec/`).

**En progreso:** Flujos de calificaciones, asistencia y solicitudes en desarrollo activo.

---

### 9.2 Eficiencia de Desempeño

**Definición:** Relación entre el desempeño del sistema y la cantidad de recursos usados bajo condiciones establecidas.

**Cumplimiento actual:**
- Índices de base de datos definidos sobre campos de búsqueda frecuente: `(usuario, accion, timestamp)`, `(usuario, usado, expira_en)`.
- Paginación configurada en DRF (`PAGE_SIZE = 20`) para evitar cargas masivas.
- Assets estáticos y media servidos directamente por Nginx (sin pasar por Django) en producción.
- Consultas ORM optimizadas con `select_related` / `prefetch_related` donde aplica.

**Pendiente:** Análisis de performance en carga y eventual caché (Redis/Memcached) para rutas frecuentes.

---

### 9.3 Compatibilidad

**Definición:** Grado en que el sistema puede intercambiar información o coexistir con otros sistemas.

**Cumplimiento actual:**
- API REST con Django REST Framework (DRF) disponible para integración con sistemas externos.
- Autenticación por sesión compatible con cualquier cliente web estándar.
- Formatos de fecha internacionalizados (`LANGUAGE_CODE = "es-ec"`, `TIME_ZONE = "America/Guayaquil"`).
- El dominio es Python puro — sin acoplamiento a Django en las entidades, facilitando integración futura.

---

### 9.4 Usabilidad

**Definición:** Grado en que el sistema puede ser usado por usuarios específicos para alcanzar metas con efectividad, eficiencia y satisfacción.

**Cumplimiento actual:**
- Interfaz construida con **Tailwind CSS** siguiendo un sistema de diseño consistente (tokens de color, tipografía Inter, espaciado uniforme).
- **Alpine.js** para interacciones reactivas (sidebar colapsable, modales de confirmación, alertas con auto-dismiss).
- **Tom Select** para selects con búsqueda en listas largas (docentes, asignaturas, etc.).
- Mensajes de feedback claros con indicadores visuales por tipo (success, error, warning, info).
- Formularios con validación del lado servidor con errores en contexto.
- Sidebar colapsable con persistencia en `localStorage`.
- Responsive design para pantallas medianas/grandes.

---

### 9.5 Fiabilidad

**Definición:** Grado en que el sistema ejecuta funciones bajo condiciones específicas durante un período de tiempo.

**Cumplimiento actual:**
- Sistema de bloqueo de cuentas tras 5 intentos fallidos (previene ataques de fuerza bruta).
- Tokens OTP con expiración y uso único — evitan condiciones de race o reutilización.
- Transacciones atómicas en operaciones críticas (registro de usuario con cédula única).
- Registros de auditoría persistentes para trazabilidad ante fallos.
- Umbral de cobertura de tests del **70%** forzado en CI — ningún merge pasa sin pasar los tests.

**En producción:** systemd garantiza que Gunicorn se reinicie automáticamente ante fallos.

---

### 9.6 Seguridad

**Definición:** Grado en que el sistema protege la información y los datos de personas o sistemas no autorizados.

**Cumplimiento actual (ver Sección 6 para detalle):**
- Contraseñas con hash PBKDF2-SHA256 (nunca en texto plano).
- Autenticación triple: email + contraseña + rol.
- CSRF habilitado en todos los formularios.
- Cookies de sesión con `HttpOnly`, expiración de 1 hora y cierre al cerrar navegador.
- Cabeceras de seguridad HTTP en producción (`XSS filter`, `Content-Type nosniff`, `X-Frame-Options: SAMEORIGIN`).
- Auditoría de acciones sensibles con IP y timestamp.
- Variables de entorno para credenciales — ningún secreto en el repositorio.

---

### 9.7 Mantenibilidad

**Definición:** Grado de efectividad y eficiencia con que el sistema puede ser modificado.

**Cumplimiento actual:**
- Arquitectura hexagonal que permite cambiar la infraestructura (base de datos, email, auth) sin tocar el dominio.
- Separación estricta en capas (domain / application / infrastructure / presentation).
- Código formateado con **Black** y verificado con **Flake8** en cada push.
- Tests automatizados con **pytest** + cobertura medida — los cambios se validan antes de mergear.
- CI/CD con GitHub Actions ejecuta lint + tests en cada PR.
- Especificaciones formales en `openspec/` (SDD) que documentan decisiones y escenarios.
- Migraciones de Django versionadas y rastreables en git.

---

### 9.8 Portabilidad

**Definición:** Grado en que el sistema puede ser transferido de un entorno a otro.

**Cumplimiento actual:**
- Variables de entorno centralizadas en `.env` — cambio de entorno es solo cambiar el archivo.
- Settings separados por entorno (`base.py`, `development.py`, `production.py`).
- `requirements.txt` con versiones fijadas — reproducibilidad garantizada.
- Sin dependencia de sistema operativo específico (Django + PostgreSQL corren en cualquier Linux/macOS/Windows).
- El proyecto puede dockerizarse sin cambios estructurales (la separación de settings ya lo contempla).

---

## 10. CI/CD y Testing

### 10.1 Pipeline GitHub Actions (`.github/workflows/ci.yml`)

En cada **push** y **pull request** se ejecuta:

```
1. flake8 .                           → Verificación de estilo PEP8
2. black --check .                    → Verificación de formato
3. python manage.py migrate           → Validación de migraciones
4. coverage run -m pytest             → Tests con medición de cobertura
5. coverage report --fail-under=70    → Falla si cobertura < 70%
```

### 10.2 Estrategia de testing

- **Unit tests:** Lógica de dominio y servicios (Python puro, sin BD).
- **Integration tests:** Vistas Django con `pytest-django` y base de datos de test.
- **Fixtures:** Generadas con `factory-boy` — datos consistentes y reutilizables.
- **TDD (Strict Mode):** Las últimas features (HU21, registro inmutable) se desarrollaron con ciclo RED → GREEN → REFACTOR.

### 10.3 Cobertura actual

- Umbral mínimo: **70%**
- Las apps con lógica de dominio compleja (usuarios, académico) tienen cobertura superior.

---

## 11. Módulos del Sistema

### 11.1 Roles y accesos

| Rol | Accesos principales |
|---|---|
| **Secretaría** | Gestión de usuarios, periodos, asignaturas, paralelos, matrículas |
| **Docente** | Registro de calificaciones y asistencia de sus paralelos |
| **Inspector** | Revisión de asistencia, gestión de solicitudes estudiantiles |
| **Estudiante** | Consulta de notas, asistencia, historial, solicitudes propias |

### 11.2 Funcionalidades implementadas

- [x] Autenticación con triple factor (email + password + rol)
- [x] OTP por email para verificación
- [x] Bloqueo de cuentas por intentos fallidos
- [x] Forzar cambio de contraseña en primer login
- [x] CRUD completo de usuarios (Secretaría) con cédula obligatoria e inmutable
- [x] Gestión de periodos académicos con validaciones de duración
- [x] Tipos de licencia, asignaturas y paralelos con cupo máximo
- [x] Matrículas con control de conflictos de horario (docente y estudiante)
- [x] Dashboard diferenciado por rol
- [x] Sidebar colapsable con estado persistente
- [x] Notificaciones internas

---

## 12. Banco de Preguntas y Respuestas

---

### BLOQUE A — Arquitectura

**P1. ¿Qué arquitectura usa el proyecto y por qué se eligió?**
> Arquitectura Hexagonal (Ports & Adapters) con DDD. Se eligió para aislar la lógica de negocio de Django, permitiendo cambiar el ORM, el motor de BD o el framework de presentación sin tocar el dominio.

**P2. ¿Cómo se separa la lógica de negocio de la infraestructura?**
> Cada app tiene una capa `domain/` en Python puro (sin imports de Django). La capa `infrastructure/` contiene los modelos ORM y es la única que "toca" la base de datos.

**P3. ¿Qué es un Bounded Context en este proyecto?**
> Es una app (`usuarios`, `academico`, `calificaciones`, etc.) con su propio modelo de dominio, reglas de negocio y repositorios. Cada contexto es independiente y se comunica con los demás a través de sus interfaces.

**P4. ¿Cómo se comunican los bounded contexts entre sí?**
> A través de FKs de base de datos (infraestructura) y referencias por ID en el dominio. No hay imports cruzados entre capas de dominio; la integración ocurre en la capa de aplicación o infraestructura.

**P5. ¿Por qué no usaron microservicios?**
> El tamaño del equipo y el alcance académico hacen que un monolito modular sea la decisión correcta. La arquitectura hexagonal permite migrar a microservicios extrayendo bounded contexts si fuera necesario en el futuro.

**P6. ¿Qué es un Value Object y dónde lo usan?**
> Es un objeto inmutable que se define por sus atributos, no por una identidad. En el proyecto se implementan como `@dataclass(frozen=True)` — por ejemplo, `UsuarioEntity`, `PeriodoEntity` son frozen dataclasses.

**P7. ¿Qué rol cumple el Repository Pattern?**
> Define interfaces en `domain/repositories.py` (qué se puede hacer con los datos) y las implementaciones en `infrastructure/repositories.py` (cómo se hace con Django ORM). El dominio nunca sabe que existe PostgreSQL.

---

### BLOQUE B — Tecnología y Librerías

**P8. ¿Qué librerías usan para estilizar la interfaz?**
> Tailwind CSS 3.4.17 como framework CSS, Alpine.js 3.15.9 para reactividad ligera en el HTML, y Tom Select 2.3.1 para selects enriquecidos con búsqueda. Todos se cargan desde CDN actualmente.

**P9. ¿Por qué eligieron Tailwind y no Bootstrap?**
> Tailwind permite un sistema de diseño más preciso mediante clases de utilidad. Evita el CSS sobrante que genera Bootstrap y se integra naturalmente con la semántica HTML del template de Django sin conflictos de componentes.

**P10. ¿Qué hace Alpine.js en el proyecto?**
> Maneja estado reactivo pequeño sin necesidad de un SPA completo: sidebar colapsable, modales de confirmación, auto-dismiss de alertas, toggle de visibilidad de contraseñas. Todo dentro del HTML, sin un bundle JS separado.

**P11. ¿Usan algún framework JavaScript como React o Vue?**
> No. La interfaz es server-side rendering (Django Templates). Alpine.js cubre las interacciones reactivas necesarias sin la complejidad de un SPA. Esto simplifica el deploy y el mantenimiento.

**P12. ¿Por qué Django y no FastAPI o Flask?**
> Django incluye ORM, migraciones, autenticación, admin, CSRF, sesiones y la estructura de un proyecto web completo "out of the box". Para el alcance del proyecto, reduce el tiempo de desarrollo y garantiza convenciones establecidas.

**P13. ¿Usan Django REST Framework? ¿Para qué?**
> Sí, DRF 3.16.0 está instalado y se usa en el módulo académico para exponer endpoints REST. Actualmente la autenticación en DRF es por sesión, lo que mantiene compatibilidad con el login web existente.

**P14. ¿Cómo manejan las variables de entorno?**
> Con `python-dotenv`: las variables se definen en un `.env` local (ignorado en git) y se cargan en `settings/base.py`. El `.env.example` documenta todas las variables requeridas sin exponer valores reales.

---

### BLOQUE C — Base de Datos

**P15. ¿Por qué eligieron SQL (PostgreSQL) y no NoSQL?**
> Los datos son altamente relacionales y estructurados: usuarios → matrículas → paralelos → calificaciones. PostgreSQL garantiza integridad referencial, ACID y consistencia de datos que NoSQL no asegura por defecto.

**P16. ¿Cómo funciona la base de datos actualmente?**
> PostgreSQL 18 con el ORM de Django. Cada app tiene sus modelos con FKs entre ellos. Las migraciones versionan el esquema. En desarrollo se conecta a una instancia local; en producción, a una instancia en el VPS.

**P17. ¿Tienen índices en la base de datos?**
> Sí. Se definen índices compuestos en `OTPToken (usuario, usado, expira_en)` y en `RegistroAuditoria (usuario, accion, timestamp)` para optimizar las consultas más frecuentes.

**P18. ¿Cómo manejan las migraciones de base de datos?**
> Con el sistema de migraciones de Django (`makemigrations` / `migrate`). Las migraciones están versionadas en git junto al código y se ejecutan automáticamente en el pipeline CI.

**P19. ¿Tienen backup de la base de datos?**
> En el plan de producción se configura `pg_dump` periódico via cron o un servicio de snapshot del VPS. Actualmente en desarrollo no aplica.

**P20. ¿El modelo Usuario usa el sistema de auth nativo de Django?**
> Sí, `Usuario` extiende `AbstractUser`. Esto mantiene todo el sistema de permisos, grupos y admin de Django. Se agrega rol, cédula, teléfono, dirección y campos de seguridad (intentos, bloqueo).

---

### BLOQUE D — Seguridad

**P21. ¿Están usando algún método de encriptación para contraseñas?**
> Sí. Django aplica PBKDF2 con SHA-256 y salt aleatorio automáticamente. Las contraseñas NUNCA se almacenan en texto plano. Ningún campo de la base de datos contiene la contraseña original.

**P22. ¿Qué es PBKDF2 y por qué es seguro?**
> Password-Based Key Derivation Function 2: aplica la función de hash miles de iteraciones con un salt aleatorio, haciendo que los ataques de fuerza bruta sean computacionalmente costosos.

**P23. ¿Cómo previenen ataques de fuerza bruta en el login?**
> Tras 5 intentos fallidos, la cuenta se bloquea por 15 minutos. Los intentos y la fecha de bloqueo se persisten en el modelo `Usuario`. El límite y el tiempo son configurables en settings.

**P24. ¿Qué es el OTP y para qué se usa?**
> One-Time Password: código numérico de 6 dígitos enviado por email con expiración de 10 minutos. Se usa para verificación de identidad en flujos sensibles (registro, reset de contraseña). Cada código es de un solo uso.

**P25. ¿Cómo protegen contra CSRF?**
> Django activa `CsrfViewMiddleware` por defecto. Todos los formularios incluyen `{% csrf_token %}`. En producción, las cookies CSRF solo se envían por HTTPS (`CSRF_COOKIE_SECURE = True`).

**P26. ¿Qué hace el middleware `ForzarCambioPasswordMiddleware`?**
> Intercepta cada request de un usuario autenticado y verifica si `debe_cambiar_password = True`. Si es así, redirige al formulario de cambio de contraseña independientemente de la URL solicitada.

**P27. ¿Cómo auditan las acciones del sistema?**
> El modelo `RegistroAuditoria` persiste acción, usuario, IP y timestamp para eventos como login, logout, bloqueo de cuenta y reset de contraseña. Esto permite trazabilidad ante incidentes.

**P28. ¿Qué cabeceras de seguridad HTTP aplican?**
> En producción: `X-XSS-Protection`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, cookies de sesión y CSRF solo por HTTPS. Se heredan de Django y se configuran en `settings/production.py`.

**P29. ¿Cómo manejan los secretos del sistema (claves, tokens)?**
> Todas las credenciales (SECRET_KEY, DATABASE_PASSWORD, EMAIL_HOST_PASSWORD) se cargan desde variables de entorno. El `.env` está en `.gitignore` — ningún secreto está commiteado en el repositorio.

**P30. ¿Qué tan seguro es el sistema de autenticación triple (email + password + rol)?**
> Agrega una capa de verificación: incluso si alguien conoce email y contraseña, debe conocer el rol para autenticarse. Reduce la superficie de ataque en sesiones compartidas (ej.: estudiante vs. docente en el mismo equipo).

---

### BLOQUE E — Almacenamiento de Archivos

**P31. ¿Cómo manejan el almacenamiento de archivos como PDFs e imágenes?**
> Django almacena los archivos subidos en el filesystem local bajo `media/` (configurado en `MEDIA_ROOT`). En producción, Nginx sirve esos archivos directamente sin pasar por Django para máximo rendimiento.

**P32. ¿Qué sucede si los archivos crecen mucho en el VPS?**
> La estrategia de migración es `django-storages` con un bucket S3 o DigitalOcean Spaces. Al estar en la capa de infraestructura, el cambio no afecta al dominio ni a las vistas — solo la configuración del storage backend.

**P33. ¿Cómo se sirven los archivos media en producción?**
> Nginx con la directiva `alias /var/www/ecppp/media/` para `/media/`. Django no interviene en la entrega de archivos estáticos ni media una vez en producción.

**P34. ¿Pueden los usuarios acceder a archivos de otros usuarios?**
> Las URLs de media son directas actualmente. Para archivos sensibles se implementará validación de permisos en el view que genera la URL o firmado de URLs temporales (similar a S3 presigned URLs).

---

### BLOQUE F — Despliegue

**P35. ¿Cómo se realizará el despliegue del proyecto?**
> En un VPS Linux (Ubuntu 22.04) con Nginx como reverse proxy, Gunicorn como servidor WSGI, PostgreSQL como base de datos, Certbot para TLS/HTTPS y systemd para gestión de procesos.

**P36. ¿Por qué un VPS y no Heroku, Railway o Render?**
> El VPS da control total sobre la configuración, sin límites de RAM o restricciones del plan. Para un sistema académico institucional, tener la base de datos y los archivos media en el mismo servidor simplifica la operación.

**P37. ¿Qué es Gunicorn y por qué se usa?**
> Gunicorn es un servidor WSGI de producción para Python. Django's `runserver` no es apto para producción. Gunicorn maneja múltiples workers concurrentes y es la opción estándar con Nginx.

**P38. ¿Cómo se configura el dominio y el HTTPS?**
> Se apunta el DNS del dominio al IP del VPS. Nginx escucha en el puerto 80 y 443. Certbot (Let's Encrypt) emite y renueva automáticamente el certificado TLS gratuito.

**P39. ¿Cómo se manejan las actualizaciones del sistema en producción?**
> Pull del repositorio → `pip install -r requirements.txt` → `python manage.py migrate` → `python manage.py collectstatic` → `systemctl restart ecppp`. Se puede automatizar con GitHub Actions (CD).

**P40. ¿Tienen plan de rollback?**
> Cada feature se desarrolla en ramas separadas. Las migraciones de Django son reversibles con `migrate <app> <numero>`. Los snapshots del VPS permiten restaurar el sistema completo ante un fallo crítico.

---

### BLOQUE G — Testing y Calidad

**P41. ¿Qué herramientas de testing usan?**
> `pytest` como framework de tests, `pytest-django` para integración con Django, `factory-boy` para fixtures, y `coverage` para medir cobertura. El umbral mínimo es 70%.

**P42. ¿Por qué 70% de cobertura y no 100%?**
> El 100% es un objetivo razonable a largo plazo, pero irrealista en un proyecto en curso. El 70% garantiza que la lógica crítica (autenticación, validaciones de negocio, reglas académicas) está cubierta sin paralizar el desarrollo.

**P43. ¿Qué es TDD y lo aplican en el proyecto?**
> Test-Driven Development: escribir el test antes que el código. Se aplica en modo Strict para las features más complejas (HU21 conflictos de horario, registro inmutable de usuarios) con ciclo RED → GREEN → REFACTOR.

**P44. ¿Cómo funciona el pipeline de CI?**
> GitHub Actions ejecuta en cada push/PR: flake8, black, migrate, pytest con coverage, y falla el build si la cobertura cae de 70%. Ningún código se integra a `develop` sin pasar todos los checks.

**P45. ¿Qué es flake8 y black?**
> Flake8 es un linter que verifica conformidad con PEP8 (estilo de código Python). Black es un formateador automático y opinado que garantiza que todo el código tiene el mismo formato. Juntos eliminan debates sobre estilo.

---

### BLOQUE H — Proceso y Metodología

**P46. ¿Qué metodología de desarrollo usan?**
> Desarrollo iterativo por sprints con SDD (Spec-Driven Development) para features complejas. Cada cambio significativo pasa por: exploración → propuesta → especificación → diseño → tareas → implementación → verificación.

**P47. ¿Qué es SDD?**
> Spec-Driven Development: se documenta el cambio con especificaciones y diseño técnico antes de escribir código. Garantiza que el equipo entiende el "qué" y el "por qué" antes del "cómo".

**P48. ¿Cómo gestionan las ramas en git?**
> Estrategia feature branches: `develop` es la rama principal de integración. Cada feature/fix se desarrolla en `feature/<nombre>` o `hotfix/<nombre>` y se integra via Pull Request con CI aprobado.

**P49. ¿Cómo documentan las decisiones técnicas?**
> Con ADRs (Architecture Decision Records) y specs SDD almacenados en `openspec/`. Cada cambio tiene artefactos de propuesta, spec, diseño y tareas que quedan en el repositorio.

**P50. ¿Cómo planifican las funcionalidades que faltan?**
> Las funcionalidades pendientes (calificaciones, asistencia, solicitudes completas) están identificadas como bounded contexts con sus entidades de dominio ya definidas. El backlog se prioriza por dependencias entre módulos.

---

### BLOQUE I — Preguntas adicionales

**P51. ¿El sistema maneja internacionalización (i18n)?**
> Sí, Django está configurado con `LANGUAGE_CODE = "es-ec"` y `TIME_ZONE = "America/Guayaquil"`. Los mensajes de validación están en español. La infraestructura de i18n de Django está disponible para expansión.

**P52. ¿Cómo manejan los errores 404 y 500 en producción?**
> Django renderiza páginas de error personalizadas cuando `DEBUG = False`. Los errores 500 pueden enviarse a un email de administrador via `ADMINS` + `LOGGING` de Django.

**P53. ¿Qué diferencia hay entre `staticfiles` y `media`?**
> `staticfiles` son archivos del código fuente (CSS, JS, imágenes del sistema) — inmutables y versionados con el código. `media` son archivos subidos por usuarios (PDFs, imágenes de perfil) — dinámicos y almacenados fuera del código.

**P54. ¿El sistema envía emails? ¿Para qué?**
> Sí, vía SMTP. Se envían emails para: verificación OTP, reset de contraseña, y notificaciones del sistema. El backend de email es configurable (Gmail, Brevo, Mailgun) sin cambiar el código.

**P55. ¿Qué es el `AUTH_USER_MODEL` personalizado y por qué es importante?**
> Es la configuración que le dice a Django qué modelo usar como "usuario" del sistema. Debe definirse antes de la primera migración. Al extender `AbstractUser`, heredamos todo el sistema de auth de Django y le sumamos campos propios (rol, cédula, etc.).

**P56. ¿Por qué el modelo `RegistroAuditoria` usa `SET_NULL` en vez de `CASCADE`?**
> Porque si se elimina un usuario, los registros de auditoría deben mantenerse por razones de trazabilidad y seguridad. Con `CASCADE` se perderían evidencias de acciones pasadas de ese usuario.

**P57. ¿Cómo se garantiza que la cédula sea única e inmutable?**
> `cedula` tiene `unique=True` en el modelo, garantizado a nivel de base de datos. La inmutabilidad se enforcea en el formulario y la vista: el campo `cedula` se excluye del formulario de edición y la secretaría no puede modificarlo post-creación.

**P58. ¿Tienen panel de administración?**
> Sí, Django Admin en `/admin/`. Es la interfaz de administración nativa de Django, accesible solo a superusuarios. Se usa para gestión de datos internos y soporte.

**P59. ¿Cómo escala el sistema si crece el número de usuarios?**
> A corto plazo: optimización de queries (índices, select_related). A mediano plazo: caché con Redis para sesiones y queries frecuentes. A largo plazo: separación de la BD a un servidor dedicado o servicio gestionado, múltiples workers Gunicorn.

**P60. ¿Qué diferencia hay entre `development.py` y `production.py` en los settings?**
> En `development.py`: `DEBUG=True`, se permite cualquier host, no se fuerza HTTPS. En `production.py`: `DEBUG=False`, ALLOWED_HOSTS explícito, cookies solo por HTTPS, cabeceras de seguridad activadas. Esto evita que configuraciones inseguras lleguen a producción.

---

*Documento generado para la defensa del avance del proyecto ECPPP — Mayo 2026.*
