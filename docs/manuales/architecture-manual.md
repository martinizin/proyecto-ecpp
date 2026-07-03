# Manual de Arquitectura — ECPPP

## Metadatos

| Campo | Valor |
|---|---|
| Título | Manual de Arquitectura — ECPPP |
| Versión | 1.0 |
| Fecha | 2026-07-01 |
| Rama fuente | feature/HU29-documentacion-final |
| Último snapshot revisado | feature/HU29-documentacion-final @ 9081194 |
| Documentos relacionados | [README](../README.md) · [Manual de Base de Datos](database-manual.md) · [Manual de Usuario](user-manual.md) |

## Propósito

Este manual resume la arquitectura DDD monolítica de ECPPP desde el código real. Sirve como guía para desarrollo, soporte y revisión de cambios.

## Mapa de fuentes

| Tema | Archivos fuente |
|---|---|
| Base arquitectónica | `docs/arquitectura-ddd.md` |
| Settings y ruteo Django | `config/settings/base.py`, `config/urls.py` |
| Reexportación de modelos | `apps/*/models.py` |
| Implementación por capas | `apps/*/{domain,application,infrastructure,presentation}/` |

## Contextos delimitados

| Contexto | Responsabilidad | Rutas de código clave |
|---|---|---|
| Usuarios | Identidad, acceso, perfiles, OTP, auditoría y cierre por inactividad | `apps/usuarios/...` |
| Académico | Períodos, tipos de licencia, asignaturas, paralelos, horarios y matrículas | `apps/academico/...` |
| Calificaciones | Evaluaciones, notas, validación y trazabilidad de cambios | `apps/calificaciones/...` |
| Asistencia | Registro diario y supervisión de asistencia | `apps/asistencia/...` |
| Solicitudes | Rectificaciones, justificaciones, adjuntos e historial | `apps/solicitudes/...` |
| Reportes | Reporte ANT, exportaciones y panel de reportes | `apps/reportes/...` |
| Copilot | Asistente conversacional y moderación | `apps/copilot/...` |

## Fronteras de capa

| Capa | Regla |
|---|---|
| Dominio | Solo Python puro; no importa Django. |
| Aplicación | Orquesta casos de uso y depende solo del dominio. |
| Infraestructura | ORM, repositorios, persistencia y adaptadores. |
| Presentación | Vistas, URLs, formularios, permisos, plantillas y JSON. |

### Dirección de dependencias

`Presentación → Aplicación → Dominio ← Infraestructura`

El dominio permanece independiente. La infraestructura implementa la persistencia. La presentación invoca servicios de aplicación y muestra el resultado.

## Convención de estructura por app

```text
apps/<contexto>/
├── domain/
├── application/
├── infrastructure/
└── presentation/
```

### Regla de reexportación

Django descubre los modelos ORM por medio de `apps/<contexto>/models.py`, que reexporta las definiciones reales de `infrastructure/models.py`. Ese archivo es el punto de entrada público.

## Convenciones de nombres

- Una app por contexto delimitado.
- Plantillas y rutas deben usar nombres consistentes.
- Los modelos se mantienen en singular (`Usuario`, `Periodo`, `Solicitud`).
- Las FKs entre contextos se expresan como strings cuando cruzan apps.
- Los nombres de roles y namespaces deben coincidir con el código real.

## Lista de verificación

- [ ] Cada contexto mapea a una app real.
- [ ] Las dependencias entre capas van en un solo sentido.
- [ ] `AUTH_USER_MODEL` sigue siendo `usuarios.Usuario`.
- [ ] Ningún módulo de dominio importa Django.
- [ ] Los módulos de reexportación permanecen activos para el descubrimiento ORM.

## Ver también

- [README](../README.md)
- [Manual de Base de Datos](database-manual.md)
- [Manual de Usuario](user-manual.md)
