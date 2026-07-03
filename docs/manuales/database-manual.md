# Manual de Base de Datos — ECPPP

## Metadatos

| Campo | Valor |
|---|---|
| Título | Manual de Base de Datos — ECPPP |
| Versión | 1.0 |
| Fecha | 2026-07-01 |
| Rama fuente | feature/HU29-documentacion-final |
| Último snapshot revisado | feature/HU29-documentacion-final @ 9081194 |
| Documentos relacionados | [README](../README.md) · [Manual de Arquitectura](architecture-manual.md) · [Manual de Usuario](user-manual.md) |

## Propósito

Este manual documenta los modelos ORM que definen el contrato de datos actual. Se deriva de los archivos fuente del repositorio y no debe interpretarse como un esquema futuro.

## Fuente de verdad

| App | Archivo principal de modelos | Notas |
|---|---|---|
| Usuarios | `apps/usuarios/infrastructure/models.py` | Usuario custom, OTP y bitácora de auditoría |
| Académico | `apps/academico/infrastructure/models.py` | Períodos, tipos de licencia, asignaturas, paralelos, matrícula |
| Calificaciones | `apps/calificaciones/infrastructure/models.py` | Evaluaciones, calificaciones, registro de validación y bitácora |
| Asistencia | `apps/asistencia/infrastructure/models.py` | Registros de asistencia |
| Solicitudes | `apps/solicitudes/infrastructure/models.py` | Solicitudes, historial, certificados, adjuntos y configuración singleton |
| Reportes | `apps/reportes/infrastructure/models.py` | Reporte ANT consolidado |

## Inventario principal de modelos

### Usuarios

| Modelo | Campos clave | Restricciones / índices | Valores enum |
|---|---|---|---|
| `Usuario` | `rol`, `cedula`, `telefono`, `direccion`, `intentos_fallidos`, `bloqueado_hasta`, `debe_cambiar_password` | `cedula` única; `AUTH_USER_MODEL` apunta a este modelo | `estudiante`, `docente`, `inspector`, `secretaria`, `director_academico` |
| `OTPToken` | `usuario`, `codigo`, `creado_en`, `expira_en`, `usado` | Índices sobre `usuario`, `usado`, `expira_en` | N/A |
| `RegistroAuditoria` | `usuario`, `accion`, `ip`, `timestamp`, `detalle` | Índices sobre `usuario`, `accion`, `timestamp`; ordenado por más reciente | N/A |

### Académico

| Modelo | Campos clave | Restricciones / índices | Valores enum |
|---|---|---|---|
| `TipoLicencia` | `nombre`, `codigo`, `duracion_meses`, `num_asignaturas`, `activo` | `codigo` único | N/A |
| `Periodo` | `nombre`, `tipo_licencia`, `fecha_inicio`, `fecha_fin`, `activo`, `creado_por`, `modificado_en` | Par único `(nombre, tipo_licencia)`; ordenado por `fecha_inicio` desc | N/A |
| `Asignatura` | `nombre`, `codigo`, `descripcion`, `tipos_licencia` | `codigo` único | N/A |
| `AsignaturaLicencia` | `asignatura`, `tipo_licencia`, `horas_lectivas` | Par único `(asignatura, tipo_licencia)` | N/A |
| `Paralelo` | `asignatura`, `periodo`, `tipo_licencia`, `docente`, `nombre`, `capacidad_maxima` | Tupla única `(periodo, tipo_licencia, asignatura, nombre)` | N/A |
| `BloqueHorario` | `paralelo`, `dia_semana`, `hora_inicio`, `hora_fin` | Tupla única `(paralelo, dia_semana, hora_inicio)` | `lunes`, `martes`, `miercoles`, `jueves`, `viernes`, `sabado` |
| `Matricula` | `estudiante`, `paralelo`, `estado`, `fecha_matricula`, `matriculado_por` | Par único `(estudiante, paralelo)` | `activa`, `retirada`, `suspendida` |

### Calificaciones

| Modelo | Campos clave | Restricciones / índices | Valores enum |
|---|---|---|---|
| `Evaluacion` | `paralelo`, `tipo`, `peso`, `fecha`, `descripcion` | Par único `(paralelo, tipo)` | `parcial1`, `parcial2_10h`, `parcial3`, `parcial4_10h`, `proyecto`, `examen_final` |
| `Calificacion` | `evaluacion`, `estudiante`, `nota`, `fecha_registro`, `observaciones` | Par único `(evaluacion, estudiante)`; `nota` limitada a 0..20 | N/A |
| `RegistroCalificacionParalelo` | `paralelo`, `estado`, `fecha_envio`, `fecha_validacion`, `validado_por`, `observaciones_secretaria` | Relación uno a uno con `Paralelo` | `borrador`, `completo`, `validado`, `rechazado` |
| `LogCalificacion` | `calificacion`, `evaluacion_info`, `estudiante_info`, `accion`, `valor_anterior`, `valor_nuevo`, `realizado_por`, `ip`, `motivo`, `timestamp` | Índices sobre `calificacion`, `timestamp` y `realizado_por`, `timestamp`; ordenado por más reciente | `creacion`, `modificacion`, `recalificacion`, `eliminacion`, `envio_planilla`, `aprobacion_planilla`, `rechazo_planilla`, `justificacion` |

### Asistencia

| Modelo | Campos clave | Restricciones / índices | Valores enum |
|---|---|---|---|
| `Asistencia` | `estudiante`, `paralelo`, `fecha`, `estado`, `observaciones` | Tupla única `(estudiante, paralelo, fecha)` | `presente`, `ausente`, `justificado` |

### Solicitudes

| Modelo | Campos clave | Restricciones / índices | Valores enum |
|---|---|---|---|
| `Solicitud` | `tipo`, `estudiante`, `estado`, `descripcion`, `fecha_creacion`, `fecha_resolucion`, `resuelto_por`, `respuesta`, `calificacion`, `asistencia`, `archivo_adjunto`, `requiere_secretaria`, `numero_solicitud` | Validador de extensión en adjuntos; ordenado por más reciente | `rectificacion`, `justificacion`; `pendiente`, `en_revision`, `aprobada`, `rechazada` |
| `HistorialSolicitud` | `solicitud`, `estado_anterior`, `estado_nuevo`, `cambiado_por`, `comentario`, `timestamp` | Ordenado por más reciente | Usa `Solicitud.EstadoSolicitud` |
| `CertificadoJustificacion` | `solicitud`, `tipo`, `institucion_emisora`, `fecha_certificado`, `numero_documento`, campos específicos | Índices sobre `tipo` y `fecha_certificado` | `medico`, `laboral`, `calamidad` |
| `ArchivoSolicitud` | `solicitud`, `archivo`, `nombre_original`, `tipo_mime`, `tamanio_bytes`, `subido_en` | Restricción de tamaño <= 5 MB; índice sobre `solicitud` | N/A |
| `ConfiguracionJustificacion` | `deadline_dias`, `alerta_dias`, `actualizado_en` | Fila singleton forzada a `pk=1` | N/A |

### Reportes

| Modelo | Campos clave | Restricciones / índices | Valores enum |
|---|---|---|---|
| `ReporteANT` | `periodo`, `numero_resolucion`, `generado_por`, `fecha_generacion`, `total_estudiantes`, `total_aprobados`, `total_reprobados`, `total_desertores`, `total_en_curso`, `archivo_pdf`, `archivo_excel`, `hash_sha256`, `firma_responsable_imagen`, `nombre_firmante`, `cedula_firmante`, `cargo_firmante`, `notas` | Índice sobre `(periodo, fecha_generacion)`; snapshot inmutable | N/A |

## Relaciones entre apps

| Desde | Hacia | Regla |
|---|---|---|
| `Periodo.tipo_licencia` | `TipoLicencia` | El período académico pertenece a un tipo de licencia. |
| `Paralelo.docente` | `Usuario` | Limitado a `rol='docente'`. |
| `Matricula.estudiante` | `Usuario` | Limitado a `rol='estudiante'`. |
| `Evaluacion.paralelo` | `Paralelo` | Las notas se vinculan a un paralelo específico. |
| `Calificacion.estudiante` | `Usuario` | Limitado a `rol='estudiante'`. |
| `Solicitud.calificacion` | `Calificacion` | Se usa para rectificaciones de notas. |
| `Solicitud.asistencia` | `Asistencia` | Se usa para justificaciones de asistencia. |
| `ReporteANT.periodo` | `Periodo` | El reporte consolida un período académico. |

## Invariantes a preservar

- `AUTH_USER_MODEL` permanece como `usuarios.Usuario`.
- Las FKs entre contextos siguen siendo strings.
- Las restricciones únicas se mantienen alineadas con las reglas del dominio.
- No deben aparecer volcados SQL ni supuestos de esquema futuro.

## Ver también

- [README](../README.md)
- [Manual de Arquitectura](architecture-manual.md)
- [Manual de Usuario](user-manual.md)
