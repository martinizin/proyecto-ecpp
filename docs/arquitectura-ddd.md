# Arquitectura DDD — ECPPP

## Descripcion General

El proyecto ECPPP (Evaluacion, Calificaciones y Procesos Pedagogicos) sigue una arquitectura **Domain-Driven Design (DDD) monolitica** con 5 contextos delimitados (bounded contexts), cada uno implementado como una app Django independiente.

## Capas de la Arquitectura

Cada app sigue una estructura de 4 capas:

```
apps/{contexto}/
├── domain/           # Capa de Dominio (pura Python, SIN imports de Django)
│   ├── entities.py       # Entidades del dominio (dataclasses)
│   ├── value_objects.py  # Objetos de valor (inmutables)
│   ├── repositories.py  # Interfaces abstractas de repositorios (ABC)
│   └── exceptions.py    # Excepciones especificas del dominio
├── application/      # Capa de Aplicacion
│   └── services.py       # Casos de uso / servicios de aplicacion
├── infrastructure/   # Capa de Infraestructura
│   ├── models.py         # Modelos ORM de Django
│   └── repositories.py  # Implementaciones concretas de repositorios
└── presentation/     # Capa de Presentacion
    ├── views.py          # Vistas de Django
    ├── urls.py           # Patrones de URL
    └── forms.py          # Formularios de Django
```

### Reglas de Dependencia

```
Presentacion → Aplicacion → Dominio ← Infraestructura
```

- **Dominio**: NO depende de ninguna otra capa. Python puro.
- **Aplicacion**: Depende SOLO del dominio. Orquesta los casos de uso.
- **Infraestructura**: Implementa las interfaces del dominio usando Django ORM.
- **Presentacion**: Coordina entre la capa de aplicacion y el usuario (HTTP).

### Descubrimiento de Modelos por Django

Para que Django encuentre los modelos ORM que viven en `infrastructure/models.py`, cada app tiene un archivo `models.py` en la raiz que re-exporta:

```python
# apps/{contexto}/models.py
from apps.{contexto}.infrastructure.models import *
```

## Contextos Delimitados (Bounded Contexts)

### 1. Usuarios (`apps/usuarios`)
**Responsabilidad**: Identidad y autenticacion de usuarios.

**Aggregate Root**: `Usuario`
- Extiende `AbstractUser` de Django
- Campo `rol` con 3 valores: `estudiante`, `docente`, `inspector`
- Campos adicionales: `cedula` (unico), `telefono`

### 2. Academico (`apps/academico`)
**Responsabilidad**: Estructura academica — periodos, asignaturas y paralelos.

**Aggregate Roots**:
- `Periodo` — Periodo academico (e.g. "2026-1") con fechas y estado activo
- `Asignatura` — Materia con codigo unico
- `Paralelo` — Seccion que vincula asignatura + periodo + docente + estudiantes

**Relaciones**:
- `Paralelo` → `Asignatura` (FK, CASCADE)
- `Paralelo` → `Periodo` (FK, CASCADE)
- `Paralelo` → `Usuario` (FK docente, limit_choices_to=docente)
- `Paralelo` ↔ `Usuario` (M2M estudiantes, limit_choices_to=estudiante)

### 3. Calificaciones (`apps/calificaciones`)
**Responsabilidad**: Evaluaciones y notas de los estudiantes.

**Aggregate Roots**:
- `Evaluacion` — Tipo de evaluacion dentro de un paralelo (6 tipos, peso porcentual)
- `Calificacion` — Nota individual de un estudiante en una evaluacion

**Relaciones**:
- `Evaluacion` → `Paralelo` (FK, CASCADE)
- `Calificacion` → `Evaluacion` (FK, CASCADE)
- `Calificacion` → `Usuario` (FK estudiante)

**Restricciones**:
- `unique_together`: (paralelo, tipo) en Evaluacion
- `unique_together`: (evaluacion, estudiante) en Calificacion

### 4. Asistencia (`apps/asistencia`)
**Responsabilidad**: Registro diario de asistencia.

**Aggregate Root**: `Asistencia`
- Estados: `presente`, `ausente`, `justificado`
- Vincula estudiante + paralelo + fecha

**Restricciones**:
- `unique_together`: (estudiante, paralelo, fecha) — un registro por dia por estudiante por paralelo

### 5. Solicitudes (`apps/solicitudes`)
**Responsabilidad**: Peticiones de estudiantes (rectificaciones, justificaciones).

**Aggregate Root**: `Solicitud`
- Tipos: `rectificacion` (de calificacion), `justificacion` (de inasistencia)
- Estados: `pendiente` (default), `aprobada`, `rechazada`
- Campos de resolucion: `resuelto_por`, `respuesta`, `fecha_resolucion`

## Diagrama de Relaciones entre Aggregates

```
┌──────────────┐
│   Usuario    │  AUTH_USER_MODEL = 'usuarios.Usuario'
│ (AbstractUser)│
│  + rol       │──────────────────────────────────┐
└──────┬───────┘                                  │
       │ FK (docente)                             │ FK (estudiante)
       ▼                                          ▼
┌──────────────┐  FK   ┌──────────────┐   ┌──────────────┐
│  Paralelo    │◄──────│  Evaluacion  │   │  Asistencia  │
│  + nombre    │       │  + tipo      │   │  + fecha     │
│  + horario   │       │  + peso      │   │  + estado    │
└──┬───┬───────┘       └──────┬───────┘   └──────────────┘
   │   │                      │
   │   │ FK                   │ FK
   │   ▼                      ▼
   │ ┌──────────────┐  ┌──────────────┐   ┌──────────────┐
   │ │  Periodo     │  │ Calificacion │   │  Solicitud   │
   │ │  + nombre    │  │  + nota      │   │  + tipo      │
   │ │  + activo    │  │  + fecha_reg │   │  + estado    │
   │ └──────────────┘  └──────────────┘   │  + desc      │
   │ FK                                   └──────────────┘
   ▼
┌──────────────┐
│ Asignatura   │
│  + codigo    │
│  + nombre    │
└──────────────┘
```

## Invariantes y Restricciones Clave

| Invariante | Donde se Aplica |
|------------|----------------|
| Un usuario tiene exactamente un rol | `Usuario.rol` CharField con choices |
| Cedula es unica si se proporciona | `Usuario.cedula` unique=True, null=True |
| Codigo de asignatura es unico | `Asignatura.codigo` unique=True |
| Nombre de periodo es unico | `Periodo.nombre` unique=True |
| Un paralelo es unico por asignatura+periodo+nombre | `Paralelo` unique_together |
| Solo un tipo de evaluacion por paralelo | `Evaluacion` unique_together |
| Una nota por estudiante por evaluacion | `Calificacion` unique_together |
| Una asistencia por estudiante por paralelo por dia | `Asistencia` unique_together |
| Solo docentes pueden ser asignados a paralelos | `limit_choices_to={'rol': 'docente'}` |
| Solo estudiantes pueden ser matriculados | `limit_choices_to={'rol': 'estudiante'}` |
| Solicitudes inician en estado pendiente | `Solicitud.estado` default='pendiente' |

## Convenciones

- **Modelos ORM** viven en `infrastructure/models.py` — NUNCA en el dominio
- **Entidades de dominio** son dataclasses inmutables (`frozen=True`) — NUNCA usan Django
- **Repositorios abstractos** definen la interfaz en el dominio; las implementaciones concretas usan Django ORM en infraestructura
- **FK entre contextos** usan strings (`'usuarios.Usuario'`) en vez de imports directos
- **`AUTH_USER_MODEL`** esta configurado en `config/settings/base.py` como `'usuarios.Usuario'`
