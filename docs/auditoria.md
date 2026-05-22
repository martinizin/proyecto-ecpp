# QA E2E — Sprint 03: Suite de Pruebas de Aceptación

**Proyecto:** ECPP — Plataforma Académica  
**Sprint:** 03 (HU13–HU19 + correcciones de stakeholder)  
**Fecha:** 18/05/2026  
**Responsable QA:** Martín Jiménez

---

## Instrucciones

- Marcar cada caso con ✅ (pasa) o ❌ (falla) + descripción del problema.
- Usar datos reales del entorno de desarrollo.
- Antes de iniciar: verificar que existe al menos 1 período activo, 1 paralelo con docente asignado, y estudiantes matriculados.

---

## 1. HU13 — Validación de rangos de notas

### 1.1 Validación en frontend (Alpine.js)

| # | Caso | Pasos | Resultado esperado | ✅/❌ |
|---|------|-------|--------------------|-------|
| 1.1.1 | Nota válida | Ingresar "15.50" en campo de nota | Se acepta, campo sin error | |
| 1.1.2 | Nota = 0 (borde inferior) | Ingresar "0" | Se acepta | |
| 1.1.3 | Nota = 20 (borde superior) | Ingresar "20" | Se acepta | |
| 1.1.4 | Nota negativa | Ingresar "-1" | Campo se marca rojo, no permite guardar | |
| 1.1.5 | Nota > 20 | Ingresar "20.01" | Campo se marca rojo, no permite guardar | |
| 1.1.6 | Texto no numérico | Ingresar "abc" | Campo rechaza la entrada | |

### 1.2 Validación en backend

| # | Caso | Pasos | Resultado esperado | ✅/❌ |
|---|------|-------|--------------------|-------|
| 1.2.1 | POST con nota fuera de rango | Manipular request con nota=25 | Respuesta error, nota no se guarda | |
| 1.2.2 | Pesos no suman 100% | Crear evaluaciones que sumen 80% e intentar enviar planilla | Error: "Los pesos suman X% (deben sumar 100%)" | |

---

## 2. HU14 — Registro de calificaciones (Docente)

### 2.1 Acceso y permisos

| # | Caso | Pasos | Resultado esperado | ✅/❌ |
|---|------|-------|--------------------|-------|
| 2.1.1 | Docente ve solo sus paralelos | Login como docente → Registro de Calificaciones | Solo aparecen paralelos asignados al docente | |
| 2.1.2 | Estudiante no accede | Login como estudiante → navegar a /calificaciones/paralelos/ | Redirect a dashboard o 403 | |
| 2.1.3 | Inspector no accede | Login como inspector → navegar a /calificaciones/paralelos/ | Redirect o 403 | |

### 2.2 Gestión de evaluaciones

| # | Caso | Pasos | Resultado esperado | ✅/❌ |
|---|------|-------|--------------------|-------|
| 2.2.1 | Crear evaluación | Click "Gestionar Evaluaciones" → crear parcial1 peso 25% | Evaluación aparece en listado | |
| 2.2.2 | Editar evaluación | Editar peso de evaluación existente | Peso actualizado | |
| 2.2.3 | Eliminar evaluación (modal Alpine) | Click eliminar → modal de confirmación → confirmar | Evaluación eliminada, NO usa confirm() nativo | |
| 2.2.4 | Verificar que NO aparece confirm() nativo | En todas las acciones de eliminar | Modal Tailwind+Alpine profesional | |

### 2.3 Registro de notas

| # | Caso | Pasos | Resultado esperado | ✅/❌ |
|---|------|-------|--------------------|-------|
| 2.3.1 | Guardar notas parciales | Ingresar notas para algunos estudiantes → Guardar | Notas se persisten, mensaje de éxito | |
| 2.3.2 | Cálculo promedio en tiempo real | Ingresar notas en todas las evaluaciones | Columna "Promedio" se calcula automáticamente (Alpine.js) | |
| 2.3.3 | Banner de notas faltantes | Dejar celdas vacías | Banner amarillo "Faltan X calificaciones" visible, celdas vacías con highlight ámbar | |
| 2.3.4 | Banner desaparece al completar | Llenar todas las celdas | Banner se oculta automáticamente | |
| 2.3.5 | Edición bloqueada post-envío | Enviar planilla → volver a la planilla | Campos deshabilitados, no se puede editar | |
| 2.3.6 | Edición permitida tras rechazo | Secretaría rechaza → docente vuelve a planilla | Campos habilitados, puede corregir y reenviar | |

### 2.4 Envío a validación

| # | Caso | Pasos | Resultado esperado | ✅/❌ |
|---|------|-------|--------------------|-------|
| 2.4.1 | Envío exitoso | Completar todas las notas → "Enviar a validación" | Estado cambia a COMPLETO, mensaje de éxito | |
| 2.4.2 | Envío con notas faltantes | Intentar enviar con celdas vacías | Error: "Faltan calificaciones por registrar" | |
| 2.4.3 | Envío con pesos ≠ 100% | Evaluaciones con pesos que no suman 100 → enviar | Error de pesos | |
| 2.4.4 | Notificación a secretaría | Enviar planilla correctamente | Secretaría recibe notificación in-app + email | |

---

## 3. HU15 — Auditorías de calificaciones

### 3.1 Visualización

| # | Caso | Pasos | Resultado esperado | ✅/❌ |
|---|------|-------|--------------------|-------|
| 3.1.1 | Acceso como inspector | Login inspector → Auditorías | Vista carga correctamente | |
| 3.1.2 | Acceso como secretaría | Login secretaría → Auditorías | Vista carga correctamente | |
| 3.1.3 | Log de envío muestra info | Enviar planilla → ir a Auditorías | Fila con badge "Envío de Planilla", columna Evaluación muestra asignatura + paralelo | |
| 3.1.4 | Log de aprobación muestra info | Aprobar planilla → ir a Auditorías | Badge "Aprobación de Planilla" + info de asignatura/paralelo | |
| 3.1.5 | Log de rechazo muestra info | Rechazar planilla → ir a Auditorías | Badge "Rechazo de Planilla" + info + motivo visible | |
| 3.1.6 | Log de recalificación | Resolver recalificación → Auditorías | Badge "Recalificación" con estudiante, evaluación, nota anterior/nueva | |
| 3.1.7 | Log de justificación | Aprobar justificación → Auditorías | Badge "Justificación" con info | |

### 3.2 Filtros

| # | Caso | Pasos | Resultado esperado | ✅/❌ |
|---|------|-------|--------------------|-------|
| 3.2.1 | Dropdown NO contiene tipos obsoletos | Abrir dropdown "Tipo de acción" | NO aparecen "Creación", "Modificación", "Eliminación" | |
| 3.2.2 | Tipos disponibles | Abrir dropdown | Solo: Recalificación, Envío de Planilla, Aprobación de Planilla, Rechazo de Planilla, Justificación de Asistencia | |
| 3.2.3 | Filtro por rango de fechas | Seleccionar desde/hasta | Solo logs dentro del rango | |
| 3.2.4 | Filtro por docente | Seleccionar un docente | Solo logs de ese docente | |
| 3.2.5 | Filtro por estudiante | Buscar por nombre/cédula | Solo logs del estudiante | |
| 3.2.6 | Botón "Limpiar" | Click Limpiar | Todos los filtros se resetean | |

---

## 4. HU16 — Validación por secretaría

### 4.1 Listado de pendientes

| # | Caso | Pasos | Resultado esperado | ✅/❌ |
|---|------|-------|--------------------|-------|
| 4.1.1 | Secretaría ve planillas pendientes | Login secretaría → Pendientes de validación | Lista de paralelos en estado COMPLETO | |
| 4.1.2 | Docente no accede | Login docente → /calificaciones/pendientes-validacion/ | Redirect o 403 | |

### 4.2 Aprobación

| # | Caso | Pasos | Resultado esperado | ✅/❌ |
|---|------|-------|--------------------|-------|
| 4.2.1 | Aprobar planilla (modal) | Click aprobar → modal de confirmación → confirmar | Estado → VALIDADO, modal Alpine (NO confirm() nativo) | |
| 4.2.2 | Notificación al docente | Aprobar planilla | Docente recibe notificación in-app "Planilla aprobada" | |
| 4.2.3 | Email al docente | Aprobar planilla | Docente recibe email HTML profesional con logo ECPP | |
| 4.2.4 | Notas visibles para estudiante | Aprobar → login como estudiante | Estudiante ve notas en su libreta | |

### 4.3 Rechazo

| # | Caso | Pasos | Resultado esperado | ✅/❌ |
|---|------|-------|--------------------|-------|
| 4.3.1 | Rechazo requiere observaciones | Click rechazar sin observaciones | Error: "Debe indicar las observaciones" | |
| 4.3.2 | Rechazo con observaciones | Escribir motivo → rechazar | Estado → RECHAZADO, observaciones guardadas | |
| 4.3.3 | Notificación al docente | Rechazar planilla | Docente recibe notificación "Planilla rechazada" con observaciones | |
| 4.3.4 | Email al docente | Rechazar planilla | Email HTML con observaciones del rechazo | |
| 4.3.5 | Docente puede reenviar | Tras rechazo, docente vuelve a planilla | Puede editar y reenviar | |

---

## 5. HU17 — Libreta de calificaciones (Estudiante)

### 5.1 Visibilidad de notas

| # | Caso | Pasos | Resultado esperado | ✅/❌ |
|---|------|-------|--------------------|-------|
| 5.1.1 | Notas NO visibles en BORRADOR | Docente guarda notas sin enviar → login estudiante | Libreta muestra "Pendiente" para esa materia, sin notas | |
| 5.1.2 | Notas visibles en COMPLETO | Docente envía planilla → login estudiante | Estudiante VE las notas (evaluaciones + promedio) | |
| 5.1.3 | Notas visibles en VALIDADO | Secretaría aprueba → login estudiante | Notas siguen visibles | |
| 5.1.4 | Notas visibles tras rechazo+reenvío | Secretaría rechaza → docente reenvía → estudiante | Notas visibles con el reenvío | |

### 5.2 Contenido de la libreta

| # | Caso | Pasos | Resultado esperado | ✅/❌ |
|---|------|-------|--------------------|-------|
| 5.2.1 | Cards por materia | Login estudiante → Mi Libreta | Una card por cada materia matriculada | |
| 5.2.2 | Detalle de evaluaciones | Click/expandir materia | Muestra cada evaluación con tipo, peso y nota | |
| 5.2.3 | Promedio por materia | Todas las notas ingresadas | Promedio ponderado calculado correctamente | |
| 5.2.4 | Promedio general | Varias materias con notas | Promedio general = promedio de promedios | |
| 5.2.5 | Estado correcto | Promedio ≥ 16 → "Aprobado", < 14 → "Reprobado", 14-15.99 → "En riesgo" | Colores y badges correspondientes | |

---

## 6. HU18 — Solicitudes (Recalificación + Justificación)

### 6.1 Solicitud de recalificación

| # | Caso | Pasos | Resultado esperado | ✅/❌ |
|---|------|-------|--------------------|-------|
| 6.1.1 | Crear solicitud | Login estudiante → Solicitudes → Nueva recalificación → seleccionar evaluación + motivo | Solicitud creada con número automático | |
| 6.1.2 | Archivo adjunto ≤ 5MB | Adjuntar PDF de 3MB | Se sube correctamente | |
| 6.1.3 | Archivo adjunto > 5MB | Adjuntar archivo de 6MB | Error: excede tamaño máximo | |
| 6.1.4 | Nueva nota ≥ nota actual | Solicitar recalificación | No se puede pedir una nota menor a la actual | |
| 6.1.5 | Notificación al docente | Crear solicitud | Docente recibe notificación in-app + email | |
| 6.1.6 | 2da+ recalificación → notifica secretaría | Crear segunda solicitud para misma evaluación | Secretaría recibe notificación adicional | |

### 6.2 Solicitud de justificación de inasistencia

| # | Caso | Pasos | Resultado esperado | ✅/❌ |
|---|------|-------|--------------------|-------|
| 6.2.1 | Crear justificación | Login estudiante → Solicitudes → Nueva justificación → seleccionar sesión + motivo + archivo | Solicitud creada | |
| 6.2.2 | Solo sesiones con AUSENTE | Al crear justificación | Solo se listan sesiones donde el estudiante está ausente | |

### 6.3 Mis solicitudes

| # | Caso | Pasos | Resultado esperado | ✅/❌ |
|---|------|-------|--------------------|-------|
| 6.3.1 | Listado del estudiante | Login estudiante → Mis Solicitudes | Todas sus solicitudes con estado actual | |
| 6.3.2 | Estados visibles | Solicitudes en distintos estados | Badges: Pendiente, En revisión, Aprobada, Rechazada | |

---

## 7. HU19 — Flujo de aprobación de rectificaciones

### 7.1 Flujo 1ra recalificación (docente directo)

| # | Caso | Pasos | Resultado esperado | ✅/❌ |
|---|------|-------|--------------------|-------|
| 7.1.1 | Docente ve pendientes | Login docente → Solicitudes Pendientes | Lista de recalificaciones de sus paralelos | |
| 7.1.2 | Docente aprueba (nueva nota) | Ingresar nueva nota → Aprobar | Nota se actualiza, solicitud → APROBADA, log de recalificación creado | |
| 7.1.3 | Docente rechaza | Escribir motivo → Rechazar | Solicitud → RECHAZADA, nota no cambia | |
| 7.1.4 | Notificación al estudiante | Docente resuelve | Estudiante recibe notificación + email | |

### 7.2 Flujo 2da+ recalificación (escalamiento)

| # | Caso | Pasos | Resultado esperado | ✅/❌ |
|---|------|-------|--------------------|-------|
| 7.2.1 | Secretaría ve escaladas | Login secretaría → Solicitudes | Lista de solicitudes que requieren validación | |
| 7.2.2 | Secretaría escala al docente | Secretaría valida y escala | Estado → EN_REVISION, docente puede resolver | |

### 7.3 Justificación de inasistencia

| # | Caso | Pasos | Resultado esperado | ✅/❌ |
|---|------|-------|--------------------|-------|
| 7.3.1 | Inspector ve justificaciones | Login inspector → Justificaciones | Lista de justificaciones pendientes | |
| 7.3.2 | Aprobar justificación | Inspector aprueba | Registro de asistencia cambia a JUSTIFICADO, log creado | |
| 7.3.3 | Rechazar justificación | Inspector rechaza con motivo | Solicitud → RECHAZADA, asistencia queda AUSENTE | |

---

## 8. Supervisión (Inspector) — Correcciones stakeholder

### 8.1 Vista unificada con tabs

| # | Caso | Pasos | Resultado esperado | ✅/❌ |
|---|------|-------|--------------------|-------|
| 8.1.1 | Un solo link en sidebar | Login inspector → ver sidebar | Solo UN link "Supervisión" (no duplicado) | |
| 8.1.2 | Tab Asistencia | Click tab "Asistencia" | Tabla con estudiantes, % inasistencia, estado | |
| 8.1.3 | Detalle asistencia expandible | Click en un estudiante | Desglose por materia con cards (asignatura, paralelo, docente, % inasistencia) | |
| 8.1.4 | Tab Calificaciones | Click tab "Calificaciones" | Tabla con estudiantes, promedio general, estado | |
| 8.1.5 | Detalle calificaciones expandible | Click en un estudiante | Desglose por materia con cards (asignatura, evaluaciones, notas, promedio) | |
| 8.1.6 | Card en dashboard | Login inspector → Dashboard | Card "Supervisión" presente, lleva a vista correcta | |
| 8.1.7 | Filtro por tipo de licencia | Seleccionar tipo en dropdown | Ambas tabs se filtran correctamente | |

### 8.2 Cards de resumen

| # | Caso | Pasos | Resultado esperado | ✅/❌ |
|---|------|-------|--------------------|-------|
| 8.2.1 | Asistencia: Total, En Riesgo, Normal | Tab Asistencia | Los 3 contadores son consistentes | |
| 8.2.2 | Calificaciones: Total, En Riesgo, Aprobados | Tab Calificaciones | Los 3 contadores suman el total | |

---

## 9. Notificaciones y emails

### 9.1 Notificaciones in-app

| # | Caso | Pasos | Resultado esperado | ✅/❌ |
|---|------|-------|--------------------|-------|
| 9.1.1 | Badge de no leídas | Recibir notificación → ver header | Icono campana con badge numérico | |
| 9.1.2 | Click abre URL correcta | Click en notificación de planilla enviada | Navega a /calificaciones/pendientes-validacion/ | |
| 9.1.3 | Marcar como leída | Abrir notificación | Badge se actualiza | |

### 9.2 Emails HTML profesionales

| # | Caso | Pasos | Resultado esperado | ✅/❌ |
|---|------|-------|--------------------|-------|
| 9.2.1 | Logo visible | Recibir cualquier email | Logo ECPP circular visible en header verde | |
| 9.2.2 | Estructura profesional | Ver email en cliente de correo | Header con marca, contenido con tipografía limpia, footer institucional | |
| 9.2.3 | Email de OTP | Solicitar código OTP | Email con código grande, tiempo de expiración | |
| 9.2.4 | Email de credenciales | Crear usuario desde admin | Email con correo + contraseña temporal + aviso de cambio obligatorio | |
| 9.2.5 | Email de bloqueo | Fallar login N veces | Email con aviso de bloqueo y minutos de espera | |
| 9.2.6 | Email alerta inasistencia | Registrar asistencia con >5% | Inspector recibe email con detalle del estudiante | |
| 9.2.7 | Email envío planilla | Docente envía planilla | Secretaría recibe email con info de asignatura/paralelo | |
| 9.2.8 | Email aprobación planilla | Secretaría aprueba | Docente recibe email confirmando aprobación | |
| 9.2.9 | Email rechazo planilla | Secretaría rechaza con observaciones | Docente recibe email con observaciones | |
| 9.2.10 | Email solicitud recalificación | Estudiante solicita recalificación | Docente recibe email con detalle | |
| 9.2.11 | Fallback plain-text | Ver email en cliente sin HTML | Texto legible como fallback | |

---

## 10. UI/UX — Modales y responsive

### 10.1 Modales Alpine+Tailwind (NO confirm() nativo)

| # | Caso | Pasos | Resultado esperado | ✅/❌ |
|---|------|-------|--------------------|-------|
| 10.1.1 | Aprobar planilla (detalle_validacion) | Click aprobar | Modal profesional con overlay, NO alert/confirm del navegador | |
| 10.1.2 | Eliminar evaluación | Click eliminar en gestionar evaluaciones | Modal Alpine de confirmación | |
| 10.1.3 | Desactivar período | Click desactivar en períodos | Modal Alpine de confirmación | |
| 10.1.4 | Cerrar modal con Escape | Abrir modal → presionar Escape | Modal se cierra | |
| 10.1.5 | Cerrar modal click fuera | Click en overlay oscuro | Modal se cierra | |

### 10.2 Responsive (mobile-first)

| # | Caso | Pasos | Resultado esperado | ✅/❌ |
|---|------|-------|--------------------|-------|
| 10.2.1 | Planilla en mobile | Abrir planilla de notas en 375px | Tabla con scroll horizontal, usable | |
| 10.2.2 | Libreta en mobile | Login estudiante mobile | Cards se apilan verticalmente | |
| 10.2.3 | Supervisión en mobile | Login inspector mobile | Tabs y tablas usables | |
| 10.2.4 | Sidebar colapsado en mobile | Pantalla < 768px | Sidebar oculto, hamburger visible | |

---

## 11. Sidebar y navegación

| # | Caso | Pasos | Resultado esperado | ✅/❌ |
|---|------|-------|--------------------|-------|
| 11.1 | Inspector — links correctos | Login inspector | Sidebar: Asignaturas, Paralelos, Tipos de Licencia, Supervisión (1 solo), Auditorías, Justificaciones, Registro de Asistencia | |
| 11.2 | Docente — links correctos | Login docente | Sidebar: Registro de Calificaciones, Registro de Asistencia, Solicitudes Pendientes | |
| 11.3 | Secretaría — links correctos | Login secretaría | Sidebar: Pendientes de Validación, Auditorías, Solicitudes | |
| 11.4 | Estudiante — links correctos | Login estudiante | Sidebar: Mi Libreta, Mi Asistencia, Mis Solicitudes | |
| 11.5 | Dashboard cards coinciden con sidebar | Cada rol | Cards del dashboard llevan a las mismas URLs que el sidebar | |

---

## 12. Flujo E2E completo (Happy path)

Este flujo prueba la integración de todas las HUs en secuencia:

| Paso | Acción | Actor | Verificar |
|------|--------|-------|-----------|
| 1 | Crear evaluaciones (parcial1 25%, parcial2 25%, examen 50%) | Docente | Pesos suman 100% |
| 2 | Registrar todas las notas de los estudiantes | Docente | Banner desaparece al completar |
| 3 | Enviar planilla a validación | Docente | Estado → COMPLETO, secretaría notificada |
| 4 | Verificar que estudiante ve notas en su libreta | Estudiante | Notas y promedios visibles |
| 5 | Estudiante solicita recalificación (nota incorrecta) | Estudiante | Solicitud creada, docente notificado |
| 6 | Docente aprueba recalificación con nueva nota | Docente | Nota actualizada, log auditoría creado, estudiante notificado |
| 7 | Secretaría aprueba la planilla | Secretaría | Estado → VALIDADO, docente notificado por email |
| 8 | Verificar auditorías | Inspector | Logs de envío, recalificación, aprobación visibles con info completa |
| 9 | Verificar supervisión | Inspector | Tab Calificaciones muestra promedio actualizado del estudiante, expandible por materia |

---

## 13. Flujo E2E — Rechazo y reenvío

| Paso | Acción | Actor | Verificar |
|------|--------|-------|-----------|
| 1 | Docente envía planilla | Docente | Secretaría notificada |
| 2 | Secretaría rechaza con observaciones "Nota de Juan Pérez incorrecta" | Secretaría | Docente recibe notificación + email con observaciones |
| 3 | Docente corrige la nota | Docente | Campo editable de nuevo |
| 4 | Docente reenvía | Docente | Estado → COMPLETO, secretaría notificada nuevamente |
| 5 | Secretaría aprueba | Secretaría | Estado → VALIDADO |
| 6 | Verificar auditorías | Inspector | Logs de envío, rechazo, 2do envío, aprobación — todos con info |

---

## 14. Flujo E2E — Justificación de inasistencia

| Paso | Acción | Actor | Verificar |
|------|--------|-------|-----------|
| 1 | Docente registra asistencia con 1 estudiante AUSENTE | Docente | Sesión registrada |
| 2 | Estudiante solicita justificación para esa sesión | Estudiante | Solicitud creada con archivo adjunto |
| 3 | Inspector aprueba la justificación | Inspector | Registro cambia a JUSTIFICADO, log creado |
| 4 | Verificar % inasistencia en supervisión | Inspector | Porcentaje recalculado (ya no cuenta como ausente) |

---

## Resumen de resultados

| Sección | Total casos | Pasaron | Fallaron |
|---------|-------------|---------|----------|
| HU13 — Validación rangos | 8 | | |
| HU14 — Registro calificaciones | 15 | | |
| HU15 — Auditorías | 13 | | |
| HU16 — Validación secretaría | 9 | | |
| HU17 — Libreta estudiante | 9 | | |
| HU18 — Solicitudes | 8 | | |
| HU19 — Flujo aprobación | 7 | | |
| Supervisión | 8 | | |
| Notificaciones/Emails | 14 | | |
| UI/UX Modales/Responsive | 9 | | |
| Sidebar/Navegación | 5 | | |
| Flujos E2E | 19 | | |
| **TOTAL** | **124** | | |

---

**Notas finales:**
- Si algún caso falla, documentar con screenshot y pasos para reproducir.
- Los emails se verifican en la consola de desarrollo (si EMAIL_BACKEND=console) o en la bandeja real si está configurado Brevo.
- Para pruebas de responsive, usar DevTools del navegador (F12 → toggle device toolbar).
