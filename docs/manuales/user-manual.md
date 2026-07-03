# Manual de Usuario — ECPPP

## Metadatos

| Campo | Valor |
|---|---|
| Título | Manual de Usuario — ECPPP |
| Versión | 1.0 |
| Fecha | 2026-07-01 |
| Rama fuente | feature/HU29-documentacion-final |
| Último snapshot revisado | feature/HU29-documentacion-final @ 9081194 |
| Documentos relacionados | [README](../README.md) · [Manual de Arquitectura](architecture-manual.md) · [Manual de Base de Datos](database-manual.md) |

## Propósito

Este manual describe los flujos actuales por rol y las rutas/plantillas reales que los renderizan. Usa las pantallas vivas de Django como fuente de verdad.

## Fuente de verdad

| Artefacto | Ruta |
|---|---|
| Rutas | `apps/*/presentation/urls.py` |
| Vistas | `apps/*/presentation/views.py` |
| Plantillas | `templates/**/*.html` |

## Guía de capturas

- Guardar las imágenes en `docs/manuales/assets/user/<rol>/`.
- Usar el nombre de ruta o de pantalla como base del archivo.
- Titular cada imagen con la ruta y la plantilla asociada.
- Reemplazar cada nota TODO por una captura real antes del cierre.

## Flujo de estudiante

| Paso | Ruta | Plantilla | Notas |
|---|---|---|---|
| Iniciar sesión | `usuarios:login` | `usuarios/login.html` | Inicia la sesión autenticada. |
| Verificar 2FA cuando aplique | `usuarios:verificar_2fa` | `usuarios/verificar_2fa.html` | Aplica a accesos que requieren OTP. |
| Abrir panel principal | `usuarios:dashboard` | `usuarios/dashboard.html` | Punto de entrada después del login. |
| Revisar calificaciones | `calificaciones:mi_libreta` | `calificaciones/mi_libreta.html` | Vista de solo lectura. |
| Revisar asistencia | `asistencia:mi_asistencia` | `asistencia/mi_asistencia.html` | Resumen de asistencia de solo lectura. |
| Crear una solicitud | `solicitudes:seleccionar_inasistencia` / `solicitudes:crear_recalificacion` | `solicitudes/seleccionar_inasistencia.html`, `solicitudes/crear_recalificacion.html` | Usar la ruta según el tipo de solicitud. |
| Adjuntar evidencia | `solicitudes:crear_justificacion_certificado` | `solicitudes/justificacion_certificado.html` | Requerido para justificaciones. |
| Revisar solicitudes enviadas | `solicitudes:mis_solicitudes` | `solicitudes/mis_solicitudes.html` | Muestra estado e historial. |

### Capturas de estudiante

| Captura pendiente | Ruta de marcador | Nota requerida |
|---|---|---|
| Login | `docs/manuales/assets/user/student/login.png` | Capturar el formulario de acceso actual. |
| Panel | `docs/manuales/assets/user/student/dashboard.png` | Capturar la pantalla posterior al login. |
| Calificaciones | `docs/manuales/assets/user/student/grades.png` | Capturar `calificaciones:mi_libreta`. |
| Asistencia | `docs/manuales/assets/user/student/attendance.png` | Capturar `asistencia:mi_asistencia`. |
| Solicitudes | `docs/manuales/assets/user/student/requests.png` | Capturar `solicitudes:mis_solicitudes`. |

## Flujo de docente

| Paso | Ruta | Plantilla | Notas |
|---|---|---|---|
| Iniciar sesión | `usuarios:login` | `usuarios/login.html` | El docente también puede pasar por 2FA. |
| Abrir panel principal | `usuarios:dashboard` | `usuarios/dashboard.html` | Pantalla de inicio según el rol. |
| Seleccionar paralelo para calificaciones | `calificaciones:seleccionar_paralelo` | `calificaciones/seleccionar_paralelo.html` | Entrada exclusiva de docente. |
| Registrar calificaciones | `calificaciones:registrar_calificaciones` | `calificaciones/registrar_calificaciones.html` | Usa la planilla del paralelo seleccionado. |
| Gestionar evaluaciones | `calificaciones:gestionar_evaluaciones` | `calificaciones/gestionar_evaluaciones.html` | Crear, editar o eliminar evaluaciones antes de validar. |
| Seleccionar paralelo para asistencia | `asistencia:seleccionar_paralelo` | `asistencia/seleccionar_paralelo.html` | Entrada para asistencia. |
| Registrar asistencia | `asistencia:registrar_asistencia` | `asistencia/registrar_asistencia.html` | Planilla diaria de asistencia. |

### Capturas de docente

| Captura pendiente | Ruta de marcador | Nota requerida |
|---|---|---|
| Selector de paralelo | `docs/manuales/assets/user/teacher/select-parallel.png` | Capturar el selector de paralelos. |
| Carga de notas | `docs/manuales/assets/user/teacher/register-grades.png` | Capturar la planilla de notas. |
| Gestión de evaluaciones | `docs/manuales/assets/user/teacher/evaluations.png` | Capturar el CRUD de evaluaciones. |
| Asistencia | `docs/manuales/assets/user/teacher/attendance.png` | Capturar el registro de asistencia. |

## Flujo de secretaría

| Paso | Ruta | Plantilla | Notas |
|---|---|---|---|
| Iniciar sesión | `usuarios:login` | `usuarios/login.html` | Secretaría no pasa por el flujo OTP de estudiante por defecto. |
| Abrir panel principal | `usuarios:dashboard` | `usuarios/dashboard.html` | Punto de partida para tareas administrativas. |
| Gestionar usuarios | `secretaria:usuario_list` / `secretaria:usuario_create` | `secretaria/usuario_list.html`, `secretaria/usuario_form.html` | Crear y mantener registros de usuarios. |
| Revisar detalle de usuario | `secretaria:usuario_detail` | `secretaria/usuario_detail.html` | Revisar perfil y controles. |
| Restablecer contraseña | `secretaria:resetear_password` | `secretaria/resetear_password.html` | Restablecimiento asistido. |
| Gestionar matrículas | `secretaria:matricula_list` / `secretaria:matricula_create` / `secretaria:matricula_create_lote` | `secretaria/matricula_list.html`, `secretaria/matricula_form.html`, `secretaria/matricula_form_lote.html` | Ciclo de vida de matrícula. |
| Validación pendiente de calificaciones | `calificaciones:pendientes_validacion` / `calificaciones:detalle_validacion` | `calificaciones/pendientes_validacion.html`, `calificaciones/detalle_validacion.html` | Aprobar o rechazar planillas enviadas. |
| Solicitudes pendientes | `solicitudes:pendientes_secretaria` / `solicitudes:resolver_solicitud` | `solicitudes/pendientes_secretaria.html`, `solicitudes/resolver_solicitud.html` | Resolver solicitudes entrantes. |

### Capturas de secretaría

| Captura pendiente | Ruta de marcador | Nota requerida |
|---|---|---|
| Lista de usuarios | `docs/manuales/assets/user/secretary/users.png` | Capturar la lista de gestión. |
| Lista de matrículas | `docs/manuales/assets/user/secretary/enrollments.png` | Capturar el tablero de matrículas. |
| Cola de validación | `docs/manuales/assets/user/secretary/grade-validation.png` | Capturar las validaciones pendientes. |

## Flujo de inspectoría

| Paso | Ruta | Plantilla | Notas |
|---|---|---|---|
| Iniciar sesión | `usuarios:login` | `usuarios/login.html` | El acceso de inspectoría comienza aquí. |
| Abrir panel principal | `usuarios:dashboard` | `usuarios/dashboard.html` | Pantalla unificada de entrada. |
| Gestionar estructura académica | `academico:periodo_list`, `academico:asignatura_list`, `academico:paralelo_list` | `academico/periodo_list.html`, `academico/asignatura_list.html`, `academico/paralelo_list.html` | Mantener la estructura académica. |
| Revisar supervisión de asistencia | `asistencia:supervision` | `asistencia/supervision.html` | Espacio de supervisión transversal. |
| Revisar supervisión de calificaciones | `calificaciones:supervision_calificaciones` | redirige a la vista de supervisión | Usa la pantalla unificada. |
| Inspeccionar justificaciones | `solicitudes:inspector_justificaciones_dashboard` | `solicitudes/inspector/dashboard.html` | Flujo principal de inspectoría. |
| Abrir detalle de justificación | `solicitudes:inspector_justificacion_detalle` | `solicitudes/inspector/detalle.html` | Pantalla de detalle y resolución. |
| Resolver en lote o individualmente | `solicitudes:inspector_justificaciones_bulk`, `solicitudes:inspector_justificacion_resolver` | plantillas de dashboard/detalle | Acciones masivas y por caso. |

### Capturas de inspectoría

| Captura pendiente | Ruta de marcador | Nota requerida |
|---|---|---|
| Panel académico | `docs/manuales/assets/user/inspector/academico-dashboard.png` | Capturar el estado de inicio. |
| Vista de supervisión | `docs/manuales/assets/user/inspector/supervision.png` | Capturar la vista unificada. |
| Tablero de justificaciones | `docs/manuales/assets/user/inspector/justifications-dashboard.png` | Capturar la cola de trabajo. |
| Detalle de justificación | `docs/manuales/assets/user/inspector/justification-detail.png` | Capturar la pantalla de resolución. |

## Marcadores de capturas

Los archivos anteriores están pendientes a propósito. Reemplazar cada marcador por una captura real y mantener la leyenda alineada con la ruta y la plantilla indicadas.

## Ver también

- [README](../README.md)
- [Manual de Arquitectura](architecture-manual.md)
- [Manual de Base de Datos](database-manual.md)
