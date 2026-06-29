# Auditoría QA — HU33: Rol Director Académico (Solo Lectura)

**Rama:** `feature/HU33-rol-director-academico`
**Fecha:** 2026-06-29
**Auditor:** Junior Espín

---

## Contexto

HU33 introduce el rol `director_academico` con acceso de **solo lectura** a todos los módulos
del inspector, más acceso a Reportes ANT (generar y descargar PDF). Ninguna operación de escritura
(crear, editar, eliminar, aprobar, rechazar) debe estar disponible para este rol.

---

## Usuarios de prueba

| Rol | Username | Contraseña | Correo |
|---|---|---|---|
| director_academico | `humberto.espin` | `Directoracademico1234` | `humberto.espin.escobar@udla.edu.ec` |
| secretaria | `admin` | *(contraseña del proyecto)* | — |
| inspector | *(crear si no existe)* | — | — |
| estudiante | `estudiante_test` | `testpass123` | — |

---

## Bloque 1 — Autenticación y 2FA

### TC-01 Login con rol director_academico (flujo 2FA)
**Precondición:** Usuario `humberto.espin` existe con `rol='director_academico'`.

| # | Paso | Resultado esperado |
|---|---|---|
| 1 | Ir a `http://127.0.0.1:8000` | Redirige a `/usuarios/login/` |
| 2 | Ingresar email: `humberto.espin.escobar@udla.edu.ec` y contraseña: `Directoracademico1234` | Sistema redirige a pantalla de OTP |
| 3 | Revisar correo `@udla.edu.ec` y copiar el código OTP | Código de 6 dígitos recibido |
| 4 | Ingresar el código OTP en pantalla | Redirige al dashboard principal |
| 5 | Verificar URL final | `/usuarios/dashboard/` |

**Criterio de aceptación:** El director_academico completa el login con 2FA igual que inspector y docente.

---

### TC-02 Login con credenciales incorrectas
| # | Paso | Resultado esperado |
|---|---|---|
| 1 | Ingresar email correcto con contraseña incorrecta | Mensaje de error "Credenciales inválidas" |
| 2 | No se redirige al OTP | Permanece en `/usuarios/login/` |

---

### TC-03 Logout
| # | Paso | Resultado esperado |
|---|---|---|
| 1 | Estando logueado como director, hacer clic en "Cerrar Sesión" | Redirige a `/usuarios/login/` |
| 2 | Intentar acceder a `/usuarios/dashboard/` sin sesión | Redirige a login |

---

## Bloque 2 — Dashboard principal

### TC-04 Cards del dashboard para director_academico
**Precondición:** Logueado como `director_academico`.

| # | Elemento visible esperado | Resultado |
|---|---|---|
| 1 | Card "Períodos Académicos" | Visible |
| 2 | Card "Asignaturas" | Visible |
| 3 | Card "Paralelos" | Visible |
| 4 | Card "Tipos de Licencia" | Visible |
| 5 | Card "Supervisión" | Visible |
| 6 | Card "Auditorías" | Visible |
| 7 | Card "Justificaciones" | Visible |
| 8 | Card "Rendimiento" | Visible |

| # | Elemento NO visible esperado | Resultado |
|---|---|---|
| 9 | Cards de gestión de usuarios (secretaría) | NO debe aparecer |
| 10 | Cards de calificaciones docente | NO debe aparecer |
| 11 | Cards de asistencia estudiante | NO debe aparecer |

---

## Bloque 3 — Sidebar / Navegación

### TC-05 Secciones visibles en el sidebar para director_academico

| # | Sección del sidebar | Visible para director_academico |
|---|---|---|
| 1 | Dashboard | SI |
| 2 | **Gestión Académica** (Períodos, Asignaturas, Paralelos, Tipos Licencia) | SI |
| 3 | **Supervisión** (Supervisión asistencia, Rendimiento, Auditorías, Justificaciones) | SI |
| 4 | **Reportes ANT** | SI |
| 5 | Sección Secretaría (Usuarios, Matrículas, Validación) | NO |
| 6 | Sección Docente (Calificaciones, Asistencia, Horario) | NO |
| 7 | Sección Estudiante (Mi Asistencia, Mi Libreta, Solicitudes) | NO |

**Validación adicional:** Hacer clic en cada link del sidebar visible y confirmar que carga la página correctamente sin error 403 ni 500.

---

## Bloque 4 — Gestión Académica (Solo Lectura)

### TC-06 Períodos Académicos — acceso y restricciones
**URL:** `/academico/periodos/`

| # | Paso | Resultado esperado |
|---|---|---|
| 1 | Ir a `/academico/periodos/` como director | Carga la lista de períodos sin error |
| 2 | Verificar botón "Nuevo Periodo" | **NO debe aparecer** |
| 3 | Verificar botón "Editar" en cada fila | **NO debe aparecer** |
| 4 | Verificar botón "Desactivar" en períodos activos | **NO debe aparecer** |
| 5 | Acceder directamente a `/academico/periodos/crear/` | Debe retornar **403 Forbidden** |
| 6 | Acceder directamente a `/academico/periodos/1/editar/` | Debe retornar **403 Forbidden** |

---

### TC-07 Asignaturas — acceso y restricciones
**URL:** `/academico/asignaturas/`

| # | Paso | Resultado esperado |
|---|---|---|
| 1 | Ir a `/academico/asignaturas/` como director | Carga la lista sin error |
| 2 | Verificar botón "Nueva Asignatura" | **NO debe aparecer** |
| 3 | Verificar botón "Editar" en cada fila | **NO debe aparecer** |
| 4 | Verificar ícono de eliminación (basura) en cada fila | **NO debe aparecer** |
| 5 | Acceder directamente a `/academico/asignaturas/crear/` | Debe retornar **403 Forbidden** |
| 6 | Acceder directamente a `/academico/asignaturas/1/editar/` | Debe retornar **403 Forbidden** |

---

### TC-08 Paralelos — acceso y restricciones
**URL:** `/academico/paralelos/`

| # | Paso | Resultado esperado |
|---|---|---|
| 1 | Ir a `/academico/paralelos/` como director | Carga la lista agrupada sin error |
| 2 | Verificar botón "Crear en Lote" | **NO debe aparecer** |
| 3 | Verificar botón "Nuevo Individual" | **NO debe aparecer** |
| 4 | Verificar link "Editar Grupo" en cada grupo | **NO debe aparecer** |
| 5 | Verificar íconos de reloj (editar horario), "Editar" y basura por paralelo | **NO deben aparecer** |
| 6 | Verificar panel inline de edición de horario | **NO debe abrirse** |
| 7 | Acceder directamente a `/academico/paralelos/crear/` | Debe retornar **403 Forbidden** |
| 8 | Acceder directamente a `/academico/paralelos/crear-lote/` | Debe retornar **403 Forbidden** |
| 9 | Acceder directamente a `/academico/paralelos/1/editar/` | Debe retornar **403 Forbidden** |

---

### TC-09 Tipos de Licencia — solo lectura
**URL:** `/academico/tipos-licencia/`

| # | Paso | Resultado esperado |
|---|---|---|
| 1 | Ir a `/academico/tipos-licencia/` como director | Carga la lista sin error |
| 2 | Confirmar que no hay botones de escritura | Solo visualización |

---

### TC-10 Dashboard de Rendimiento
**URL:** `/academico/dashboard-rendimiento/`

| # | Paso | Resultado esperado |
|---|---|---|
| 1 | Ir al Dashboard de Rendimiento como director | Carga sin error, muestra métricas |
| 2 | Filtrar por tipo de licencia | El gráfico/tabla actualiza correctamente |
| 3 | Confirmar que no hay botones de escritura | Solo visualización de datos |

---

## Bloque 5 — Supervisión

### TC-11 Supervisión de Asistencia
**URL:** `/asistencia/supervision/`

| # | Paso | Resultado esperado |
|---|---|---|
| 1 | Ir a `/asistencia/supervision/` como director | Carga sin error |
| 2 | Hacer clic en un estudiante para ver detalle | Carga detalle de inasistencias |
| 3 | Verificar que no hay botones para registrar/modificar asistencia | Solo visualización |
| 4 | Acceder directamente a registrar asistencia (URL docente/inspector) | Debe retornar **403 Forbidden** |

---

### TC-12 Auditoría de Calificaciones
**URL:** `/calificaciones/auditoria/`

| # | Paso | Resultado esperado |
|---|---|---|
| 1 | Ir a auditoría de calificaciones como director | Carga sin error |
| 2 | Visualizar registros de calificaciones | Datos visibles |
| 3 | Verificar que no hay botones de validación ni edición | Solo visualización |

---

### TC-13 Supervisión de Calificaciones
| # | Paso | Resultado esperado |
|---|---|---|
| 1 | Acceder a supervisión de calificaciones como director | Carga sin error |
| 2 | Ver detalle de calificaciones de un estudiante | Carga correctamente |
| 3 | Confirmar ausencia de botones de edición | Solo lectura |

---

## Bloque 6 — Justificaciones (Solo Lectura con es_solo_lectura)

### TC-14 Dashboard de Justificaciones — vista de solo lectura
**URL:** `/solicitudes/inspector/justificaciones/`

| # | Paso | Resultado esperado |
|---|---|---|
| 1 | Ir al dashboard de justificaciones como director | Carga sin error, lista visible |
| 2 | Verificar checkbox de selección en cada fila | **NO debe aparecer** |
| 3 | Verificar toolbar "Acción masiva" | **NO debe aparecer** |
| 4 | Verificar modal de acción masiva | **NO debe aparecer** |
| 5 | Hacer clic en "Detalle →" de una solicitud | Carga el detalle correctamente |
| 6 | Intentar POST directo a `/solicitudes/inspector/bulk/` | Debe retornar **403 Forbidden** |

---

### TC-15 Detalle de Justificación — resolución bloqueada
**URL:** `/solicitudes/inspector/justificaciones/<id>/`

| # | Paso | Resultado esperado |
|---|---|---|
| 1 | Abrir una justificación **pendiente** como director | Carga correctamente |
| 2 | Verificar formulario con botones "Aprobar" / "Rechazar" | **NO debe aparecer** |
| 3 | Verificar aviso de solo lectura | Debe aparecer mensaje amarillo "Vista de solo lectura. Esta solicitud está pendiente de resolución." |
| 4 | Abrir una justificación **ya resuelta** como director | Muestra estado "ya fue resuelta" (igual que inspector) |
| 5 | Intentar POST directo a `/solicitudes/inspector/justificaciones/<id>/resolver/` | Debe retornar **403 Forbidden** |

---

## Bloque 7 — Reportes ANT

### TC-16 Acceso al listado de Reportes ANT
**URL:** `/reportes/ant/`

| # | Paso | Resultado esperado |
|---|---|---|
| 1 | Ir a `/reportes/ant/` como director | Carga sin error |
| 2 | Verificar link "Reportes ANT" en el sidebar | Visible y funcional |
| 3 | Verificar que se listan los reportes generados | Lista visible |

---

### TC-17 Generación de Reporte ANT como director
**URL:** `/reportes/ant/generar/`

| # | Paso | Resultado esperado |
|---|---|---|
| 1 | Ir a `/reportes/ant/generar/` como director | Carga el formulario sin error |
| 2 | Seleccionar un período activo y hacer clic en "Generar" | Sistema procesa y genera el reporte |
| 3 | Verificar que aparece en el listado | Reporte visible en `/reportes/ant/` |

---

### TC-18 Descarga de PDF como director
| # | Paso | Resultado esperado |
|---|---|---|
| 1 | En el listado de reportes, hacer clic en "Descargar" de un reporte | Descarga el PDF sin error |
| 2 | Verificar que el PDF se abre/descarga correctamente | Archivo PDF válido |
| 3 | Acceder a `/reportes/ant/` como **estudiante** | Debe retornar **403 Forbidden** |
| 4 | Acceder a `/reportes/ant/` como **docente** | Debe retornar **403 Forbidden** |

---

## Bloque 8 — Restricciones de Seguridad (Pruebas de Acceso Directo por URL)

> Estas pruebas validan que el control de acceso es a nivel de **vista**, no solo a nivel de template.
> Todas deben hacerse con sesión activa del usuario `director_academico`.

### TC-19 URLs de escritura bloqueadas para director_academico

| URL | Método | Resultado esperado |
|---|---|---|
| `/academico/periodos/crear/` | GET | 403 |
| `/academico/periodos/1/editar/` | GET | 403 |
| `/academico/asignaturas/crear/` | GET | 403 |
| `/academico/asignaturas/1/editar/` | GET | 403 |
| `/academico/paralelos/crear/` | GET | 403 |
| `/academico/paralelos/crear-lote/` | GET | 403 |
| `/academico/paralelos/1/editar/` | GET | 403 |
| `/solicitudes/inspector/bulk/` | POST | 403 |
| `/solicitudes/inspector/justificaciones/1/resolver/` | POST | 403 |

---

## Bloque 9 — Regresión de Otros Roles

> Verificar que los cambios de HU33 no rompieron el acceso de los roles existentes.

### TC-20 Inspector — acceso completo sin cambios
**Logueado como inspector.**

| # | Verificación | Resultado esperado |
|---|---|---|
| 1 | Accede a dashboard de justificaciones | Carga con checkboxes y botón "Acción masiva" visible |
| 2 | Accede al detalle de justificación pendiente | Muestra botones "Aprobar" y "Rechazar" |
| 3 | Accede a `/academico/periodos/crear/` | Carga el formulario (no 403) |
| 4 | Accede a supervisión de asistencia | Carga correctamente |

---

### TC-21 Secretaria — acceso completo sin cambios
**Logueado como secretaria.**

| # | Verificación | Resultado esperado |
|---|---|---|
| 1 | Accede a gestión de usuarios | Carga correctamente |
| 2 | Accede a gestión de matrículas | Carga correctamente |
| 3 | Accede a validación de calificaciones | Carga correctamente |
| 4 | Accede a Reportes ANT | Carga correctamente |
| 5 | Sidebar muestra sección "Secretaría" completa | Visible |
| 6 | Sidebar muestra "Reportes ANT" | Visible |

---

### TC-22 Estudiante — no ve nada del director_academico
**Logueado como estudiante.**

| # | Verificación | Resultado esperado |
|---|---|---|
| 1 | Accede a `/academico/periodos/` | 403 |
| 2 | Accede a `/reportes/ant/` | 403 |
| 3 | Accede a `/asistencia/supervision/` | 403 |
| 4 | Dashboard solo muestra cards de estudiante | Correcto |

---

### TC-23 Docente — no ve nada del director_academico
**Logueado como docente.**

| # | Verificación | Resultado esperado |
|---|---|---|
| 1 | Accede a `/academico/periodos/` | 403 |
| 2 | Accede a `/reportes/ant/` | 403 |
| 3 | Accede a `/solicitudes/inspector/justificaciones/` | 403 |

---

## Bloque 10 — Validación del Modelo

### TC-24 Los 5 roles existen en el sistema

| # | Rol | Valor en BD |
|---|---|---|
| 1 | Estudiante | `estudiante` |
| 2 | Docente | `docente` |
| 3 | Inspector | `inspector` |
| 4 | Secretaría | `secretaria` |
| 5 | Director Académico | `director_academico` |

**Validación:** Ir a Django Admin > Usuarios > Crear usuario > campo Rol debe mostrar las 5 opciones.

---

## Resumen de Criterios de Aceptación

| ID | Criterio | Estado |
|---|---|---|
| CA-01 | Director_academico puede autenticarse con 2FA | Pendiente prueba |
| CA-02 | Director_academico ve las secciones de inspector en sidebar | Pendiente prueba |
| CA-03 | Director_academico ve Reportes ANT en sidebar | Pendiente prueba |
| CA-04 | Director_academico NO ve botones de crear/editar/eliminar en gestión académica | Pendiente prueba |
| CA-05 | Director_academico NO puede ejecutar escrituras por URL directa (403) | Pendiente prueba |
| CA-06 | Director_academico ve justificaciones pero sin checkbox ni acción masiva | Pendiente prueba |
| CA-07 | Director_academico ve aviso "solo lectura" en justificaciones pendientes | Pendiente prueba |
| CA-08 | Director_academico puede generar y descargar Reportes ANT en PDF | Pendiente prueba |
| CA-09 | Inspector conserva todos sus permisos de escritura sin cambios | Pendiente prueba |
| CA-10 | Secretaria conserva todos sus permisos sin cambios | Pendiente prueba |
| CA-11 | Estudiante y docente no pueden acceder a vistas del director | Pendiente prueba |
