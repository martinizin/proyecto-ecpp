# PRD — Sprint 2: Plataforma Web Académica ECPPP

| Campo | Valor |
|-------|-------|
| **Título** | Product Requirements Document — Sprint 2 |
| **Proyecto** | Plataforma Web Académica ECPPP |
| **Versión** | 0.3.0 |
| **Fecha** | Abril 2026 |
| **Sprint** | S2 (Incremento 2) |
| **Rango de fechas** | 13/04/2026 – 24/04/2026 (2 semanas, ~8 días hábiles) |
| **Equipo** | 2 desarrolladores fullstack — Martín Jiménez, Junior Espín |
| **Metodología** | Scrum + Git Flow (`develop` → `feature/*` → PR) |
| **Estado** | Draft |

---

## 1. Resumen ejecutivo del Sprint 2

### 1.1 Objetivo del Sprint

Implementar el ciclo completo de gestión académica operativa: matrícula de estudiantes en paralelos, registro y consulta de asistencia diaria, cálculo automático de porcentajes y sistema de alertas por inasistencia. Este sprint construye sobre la autenticación multirrol y estructura académica del Sprint 1, habilitando la operación diaria de la escuela de conducción.

### 1.2 Resumen de funcionalidades

| # | Funcionalidad | Descripción |
|---|---------------|-------------|
| 1 | Registro y gestión de matrículas | Secretaría inscribe estudiantes en paralelos desde Django Admin |
| 2 | Registro de asistencia diaria (Docente/Inspector) | Planilla con checkboxes para marcar presentes de forma individual y masiva |
| 3 | Consulta de asistencia (Estudiante) | Dashboard con cards por asignatura mostrando % de inasistencia |
| 4 | Supervisión y alertas de riesgo | Identificación de estudiantes con asistencia inferior al 95% |
| 5 | Lógica de cálculo de porcentajes | Servicio de cálculo automático por asignatura y general |
| 6 | Notificaciones de inasistencia | Email al inspector + indicador visual al estudiante al guardar asistencia |

### 1.3 Definition of Done del Sprint 2

- [ ] Secretaría puede matricular estudiantes en paralelos desde Django Admin con validación de cupo.
- [ ] Docente/Inspector puede registrar asistencia diaria con planilla de checkboxes (individual + masivo).
- [ ] Estudiante puede consultar su porcentaje de inasistencia general y por asignatura.
- [ ] Sistema calcula automáticamente porcentajes: (presentes+justificadas)/total_sesiones.
- [ ] Alertas por email al inspector cuando un estudiante supera 5% de inasistencia.
- [ ] Indicador visual con gama de colores (verde/rojo) en dashboard del estudiante.
- [ ] Estados de matrícula funcionales: Activa, Retirada (secretaría), Suspendida (inspector).
- [ ] Modelo `Asistencia` migrado para vincularse a paralelo (que ya tiene FK a asignatura).
- [ ] Tests con cobertura ≥ 70% en capa de dominio.
- [ ] Pipeline CI en verde con todos los tests.
- [ ] Código revisado vía PR de `feature/*` a `develop`.

---

## 2. Alcance del Sprint 2

### 2.1 Incluye

| Aspecto | Detalle |
|---------|---------|
| Matrícula de estudiantes | Inscripción desde Django Admin con validación de cupo, período activo, y estados (activa/retirada/suspendida) |
| Registro de asistencia | Planilla diaria por paralelo con checkboxes. Checkbox "marcar todos". Docente e inspector pueden registrar |
| Consulta de asistencia | Dashboard estudiante con cards por asignatura + porcentaje general. Gama de colores rojo/verde |
| Cálculo de porcentajes | Servicio de dominio: % por asignatura + % general. Justificado = presente. Fórmula: (presentes+justificadas)/total_sesiones |
| Alertas de inasistencia | Al guardar planilla: recalcular %, si supera umbral → email al inspector. Indicador visual al estudiante |
| Migración modelo Asistencia | Ajustar unique_together, eliminar estado AUSENTE de choices (no marcado = ausente) |
| API REST interna | Endpoints DRF donde aporten valor (registro masivo de asistencia, cálculo de porcentajes) |

### 2.2 Excluye

| Aspecto | Razón |
|---------|-------|
| Registro de calificaciones | Sprint 3 |
| Reportes PDF/Excel | Sprint 3 |
| Solicitudes de justificación (flujo completo) | Sprint 3 — el modelo `Solicitud` ya existe pero la UI de gestión es Sprint 3 |
| Validación automática de conflictos de horarios | Campo `horario` es CharField libre — validación manual por secretaría |
| Frontend separado (React/Vue) | Se mantiene Django templates + Alpine.js/fetch con DRF interno |

---

## 3. Backlog del Sprint 2

| ID | Nombre | Puntos | Responsable | Día(s) objetivo |
|----|--------|--------|-------------|-----------------|
| HU07 | Registro y gestión de matrículas | 3 | Junior | Día 1–2 |
| HU08 | Registro de asistencia diaria (Docente/Inspector) | 5 | Martín | Día 1–3 |
| HU09 | Consulta de asistencia (Estudiante) | 3 | Junior | Día 3–4 |
| HU10 | Lógica de cálculo de porcentajes de asistencia | 3 | Martín | Día 2–3 |
| HU11 | Supervisión y alertas de riesgo | 3 | Junior | Día 4–5 |
| HU12 | Sistema de notificaciones de inasistencia | 3 | Martín | Día 4–5 |
| **Total** | | **20** | | |

---

## 4. Detalle por HU

### 4.1 HU07 — Registro y gestión de matrículas

**Propósito:** Permitir a la secretaría inscribir estudiantes en paralelos del período activo, controlando cupo máximo y estados de matrícula.

**Reglas de negocio confirmadas:**
- La secretaría matricula desde Django Admin (personalización mínima del admin).
- Un estudiante se matricula en UN paralelo (que ya tiene asignatura asociada).
- Un estudiante PUEDE estar en paralelos de diferentes tipos de licencia simultáneamente.
- Solo se puede matricular en el período activo.
- Se valida cupo máximo (`capacidad_maxima` del paralelo).
- Estados de matrícula: `activa`, `retirada`, `suspendida`.
- Secretaría: cambia Activa ↔ Retirada (gestión administrativa).
- Inspector: cambia a Suspendida (regla académica/disciplinaria) y autoriza retorno a Activa.

**Modelo de datos — Nuevo modelo `Matricula`:**

```python
class Matricula(models.Model):
    class Estado(models.TextChoices):
        ACTIVA = "activa", "Activa"
        RETIRADA = "retirada", "Retirada"
        SUSPENDIDA = "suspendida", "Suspendida"

    estudiante = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="matriculas")
    paralelo = models.ForeignKey(Paralelo, on_delete=models.CASCADE, related_name="matriculas")
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.ACTIVA)
    fecha_matricula = models.DateTimeField(auto_now_add=True)
    matriculado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name="matriculas_realizadas")

    class Meta:
        unique_together = ["estudiante", "paralelo"]
```

> **Nota:** El M2M `Paralelo.estudiantes` existente del Sprint 0 se reemplaza por este modelo `Matricula` para soportar estados y auditoría. Se debe crear migración para eliminar el M2M y crear la tabla nueva.

**Criterios de aceptación:**
- [ ] Modelo `Matricula` creado con migración aplicada.
- [ ] M2M `Paralelo.estudiantes` eliminado (reemplazado por `Matricula`).
- [ ] Django Admin configurado: `MatriculaAdmin` con filtros por período, tipo licencia, estado.
- [ ] Validación de cupo máximo al crear matrícula.
- [ ] Validación de período activo al crear matrícula.
- [ ] Validación de que el estudiante tenga `rol="estudiante"`.
- [ ] Transiciones de estado correctas según rol (secretaría vs inspector).
- [ ] Tests de modelo, validaciones y admin.

**Branch:** `feature/HU07-registro-matriculas`

---

### 4.2 HU08 — Registro de asistencia diaria (Docente/Inspector)

**Propósito:** Permitir al docente e inspector registrar la asistencia diaria de estudiantes matriculados en un paralelo, mediante una planilla con checkboxes.

**Reglas de negocio confirmadas:**
- Asistencia vinculada al paralelo (que ya tiene FK a asignatura).
- Una vez por asignatura por día (unique_together: estudiante + paralelo + fecha).
- Estados: Presente (checkbox marcado) y Ausente (checkbox no marcado). Justificado solo se establece vía solicitud aprobada.
- Planilla: tabla con nombres de estudiantes, checkbox individual + checkbox "marcar todos".
- Al GUARDAR: se crean registros de asistencia + se recalculan porcentajes + se evalúan alertas.
- Docente: solo SUS paralelos. Inspector: todos los paralelos (puede auditar).
- Solo estudiantes con matrícula ACTIVA aparecen en la planilla.

**Cambios al modelo `Asistencia`:**
- El modelo actual ya vincula a `paralelo` — esto es correcto porque paralelo tiene FK a asignatura.
- Mantener estado `AUSENTE` en choices (se crea automáticamente para los no marcados).
- Mantener `unique_together = ["estudiante", "paralelo", "fecha"]`.
- Estado default cambia a `AUSENTE` (no marcar = ausente).

**Vista principal:**
- URL: `/asistencia/<paralelo_id>/registrar/` o similar.
- GET: Muestra planilla con lista de estudiantes matriculados activos.
- POST: Recibe IDs de estudiantes presentes → crea registros (presente para marcados, ausente para no marcados).

**Criterios de aceptación:**
- [ ] Vista de registro de asistencia accesible para docente (sus paralelos) e inspector (todos).
- [ ] Planilla muestra solo estudiantes con matrícula activa en el paralelo.
- [ ] Checkbox individual por estudiante + checkbox "marcar todos" con Alpine.js.
- [ ] Selección de fecha (default: hoy).
- [ ] Validación: no duplicar asistencia del mismo día para el mismo paralelo.
- [ ] Al guardar: crear registros `PRESENTE` para marcados, `AUSENTE` para no marcados.
- [ ] Al guardar: disparar recálculo de porcentajes y evaluación de alertas.
- [ ] Mensaje de confirmación tras guardar.
- [ ] Vista de historial de asistencia del paralelo (tabla con fechas y estados).
- [ ] Template responsive con estilo Sprint 1.
- [ ] Tests de vista, servicio y modelo.

**Branch:** `feature/HU08-registro-asistencia`

---

### 4.3 HU09 — Consulta de asistencia (Estudiante)

**Propósito:** Permitir al estudiante visualizar su porcentaje de inasistencia general y por asignatura en un dashboard con cards.

**Reglas de negocio confirmadas:**
- Estudiante ve cards con cada asignatura en la que está matriculado (matrícula activa).
- Cada card muestra: nombre de asignatura, porcentaje de inasistencia, indicador de color.
- Porcentaje general visible en la parte superior del dashboard.
- Gama de colores: verde (<5% inasistencia), rojo (≥5% inasistencia).
- El porcentaje inicia en 0% de inasistencia.
- Justificado cuenta como presente en el cálculo.

**Vista principal:**
- URL: `/asistencia/mi-asistencia/` o dashboard del estudiante.
- Solo accesible para rol `estudiante`.
- Muestra datos del período activo.

**Criterios de aceptación:**
- [ ] Dashboard de asistencia accesible solo para estudiantes autenticados.
- [ ] Card por cada paralelo/asignatura con matrícula activa.
- [ ] Porcentaje de inasistencia por asignatura calculado correctamente.
- [ ] Porcentaje general de inasistencia en encabezado.
- [ ] Indicador de color: verde (<5%), rojo (≥5%).
- [ ] Muestra "Sin registros" cuando no hay asistencia tomada.
- [ ] Template responsive (cards en grid).
- [ ] Tests de vista y cálculos.

**Branch:** `feature/HU09-consulta-asistencia`

---

### 4.4 HU10 — Lógica de cálculo de porcentajes de asistencia

**Propósito:** Desarrollar el servicio de dominio que calcula porcentajes de asistencia por asignatura y general para un estudiante.

**Fórmula confirmada:**
```
% asistencia por asignatura = (presentes + justificadas) / total_sesiones_registradas × 100
% asistencia general = Σ(presentes + justificadas de todas las asignaturas) / Σ(total_sesiones de todas) × 100
% inasistencia = 100 - % asistencia
```

**Reglas:**
- `total_sesiones` = cantidad de registros de asistencia existentes para ese paralelo (clases dictadas hasta la fecha, no planificadas).
- Justificado cuenta como asistencia efectiva (equivalente a Presente).
- Si no hay sesiones registradas → 0% de inasistencia.
- Si justificativo es rechazado, el registro vuelve a `AUSENTE` (esto se maneja en el flujo de solicitudes — Sprint 3).

**Servicio de dominio:**
```python
# apps/asistencia/domain/services.py
class AsistenciaCalculoService:
    def calcular_porcentaje_asignatura(sesiones_asistidas, total_sesiones) -> Decimal
    def calcular_porcentaje_general(datos_por_asignatura: list) -> Decimal
    def evaluar_riesgo(porcentaje_inasistencia) -> str  # "verde" | "rojo"
```

**Criterios de aceptación:**
- [ ] Servicio de dominio puro (sin dependencias de ORM).
- [ ] Cálculo correcto por asignatura.
- [ ] Cálculo correcto general (agregado de todas las asignaturas).
- [ ] Manejo de edge cases: 0 sesiones, todas ausentes, todas presentes.
- [ ] Evaluación de riesgo: verde (<5%), rojo (≥5%).
- [ ] Tests unitarios exhaustivos con parametrize.

**Branch:** `feature/HU10-calculo-porcentajes` (puede integrarse en HU08/HU09 branch)

---

### 4.5 HU11 — Supervisión y alertas de riesgo

**Propósito:** Permitir al inspector visualizar un panel con estudiantes en riesgo de inasistencia (≥5% de inasistencia general).

**Vista principal:**
- URL: `/asistencia/supervision/` o similar.
- Solo accesible para inspector.
- Tabla con: estudiante, tipo licencia, % inasistencia general, indicador de color.
- Filtros por período activo, tipo de licencia.
- Ordenable por % de inasistencia (más grave primero).

**Criterios de aceptación:**
- [ ] Vista de supervisión accesible solo para inspector.
- [ ] Tabla con todos los estudiantes matriculados en el período activo.
- [ ] Porcentaje de inasistencia general calculado para cada estudiante.
- [ ] Indicador de color: verde/rojo.
- [ ] Filtro por tipo de licencia.
- [ ] Ordenamiento por % de inasistencia descendente.
- [ ] Template responsive.
- [ ] Tests de vista.

**Branch:** `feature/HU11-supervision-alertas`

---

### 4.6 HU12 — Sistema de notificaciones de inasistencia

**Propósito:** Enviar alertas automáticas por email al inspector cuando un estudiante supera el umbral de inasistencia al guardar la planilla de asistencia.

**Reglas de negocio confirmadas:**
- Alerta se dispara al GUARDAR la planilla de asistencia (no batch).
- Se recalcula el porcentaje del estudiante después de guardar.
- Si el % de inasistencia ≥ 5% → email al inspector del paralelo.
- El estudiante ve el indicador visual actualizado en su dashboard (no email al estudiante — es visual).
- Email real usando Gmail App Password (ya configurado en Sprint 1).

**Criterios de aceptación:**
- [ ] Al guardar asistencia con ausentes, se recalcula % de cada estudiante ausente.
- [ ] Si % inasistencia ≥ 5%, se envía email al inspector con detalles (nombre estudiante, asignatura, % actual).
- [ ] Email con template HTML con branding ECPPP.
- [ ] No enviar emails duplicados si el estudiante ya fue notificado previamente para el mismo umbral.
- [ ] Log de notificaciones enviadas (reutilizar `RegistroAuditoria`).
- [ ] Tests con mock de email.

**Branch:** `feature/HU12-notificaciones-inasistencia`

---

## 5. Modelo de datos — Cambios del Sprint 2

### 5.1 Nuevo modelo

| Modelo | App | Ubicación |
|--------|-----|-----------|
| `Matricula` | `academico` | `apps/academico/infrastructure/models.py` |

### 5.2 Modificaciones a modelos existentes

| Modelo | Cambio | Razón |
|--------|--------|-------|
| `Paralelo` | Eliminar M2M `estudiantes` | Reemplazado por modelo `Matricula` con estados |
| `Asistencia` | Cambiar default de `estado` a `AUSENTE` | No marcar checkbox = ausente |

### 5.3 Migraciones necesarias

1. Crear modelo `Matricula` en `apps/academico/`.
2. Migrar datos existentes del M2M `Paralelo.estudiantes` a `Matricula` (si hay datos).
3. Eliminar M2M `Paralelo.estudiantes`.
4. Alterar default de `Asistencia.estado` a `AUSENTE`.

---

## 6. Distribución de trabajo — 5 días (Git Flow)

> **Convención:** `develop` → `feature/HU0X-nombre` → PR → merge a `develop`.
> Ambos devs son fullstack. Trabajo en paralelo con PRs cruzados.

### Día 1 (Lunes 13/04) — Fundamentos

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Junior** | HU07: Modelo `Matricula`, migración, eliminar M2M, `MatriculaAdmin` con validaciones | `feature/HU07-registro-matriculas` | Modelo + admin funcional, PR abierto |
| **Martín** | HU10: Servicio de dominio `AsistenciaCalculoService` + tests unitarios exhaustivos | `feature/HU10-calculo-porcentajes` | Servicio puro + 15+ tests con parametrize, PR abierto |

### Día 2 (Martes 14/04) — Asistencia core

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Junior** | HU07: Tests de matrícula, validaciones de cupo/período/rol. Merge PR | `feature/HU07-registro-matriculas` | PR merged a develop |
| **Martín** | HU08: Modelo Asistencia ajustado, vista registro asistencia (GET planilla), template con checkboxes | `feature/HU08-registro-asistencia` | Planilla renderiza con estudiantes matriculados |

### Día 3 (Miércoles 15/04) — Integración asistencia

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Junior** | HU09: Vista dashboard estudiante, template cards, integración con servicio de cálculo | `feature/HU09-consulta-asistencia` | Dashboard estudiante funcional |
| **Martín** | HU08: POST guardar asistencia, integración con servicio de cálculo, historial de asistencia. Merge PR HU10 | `feature/HU08-registro-asistencia` | Registro completo funcional, PR HU10 merged |

### Día 4 (Jueves 16/04) — Supervisión y alertas

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Junior** | HU11: Vista supervisión inspector, tabla con filtros, indicadores de color. Tests | `feature/HU11-supervision-alertas` | Panel de supervisión funcional |
| **Martín** | HU12: Servicio de notificaciones email, integración al guardar asistencia, template email, tests | `feature/HU12-notificaciones-inasistencia` | Alertas email funcionales |

### Día 5 (Viernes 17/04) — Integración, tests y cierre

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Junior** | Merge PRs pendientes, integración final, fix bugs, tests de integración HU09+HU11 | `develop` | Todos los PRs merged, suite verde |
| **Martín** | Merge PRs pendientes, tests de integración HU08+HU12, fix bugs, suite completa verde | `develop` | 0 failures, documentación de cierre |

> **Días 6-8 (semana 2):** Buffer para testing E2E manual, fix de bugs encontrados, pulido UI responsive, y documentación.

### Tareas no técnicas (en paralelo durante el sprint)

| Tarea | Responsable | Día |
|-------|-------------|-----|
| Solicitar formato de planilla de asistencia actual (papel/Excel) a la ECPPP | Junior | Día 1 |
| Solicitar listado real de estudiantes y paralelos del período actual | Junior | Día 1 |
| Configurar rama `develop` en repo y protección de branch (require PR) | Martín | Día 1 |
| Code review cruzado de cada PR (mínimo 1 approval antes de merge) | Ambos | Continuo |
| Testing manual de flujos completos (crear matrícula → tomar asistencia → ver dashboard) | Ambos | Día 5+ |
| Crear data fixtures/seeds para demo (estudiantes, matrículas, asistencia de ejemplo) | Martín | Día 5 |

---

## 7. Flujos de usuario completos

### 7.1 Flujo: Matricular estudiante (Secretaría)

```
1. Secretaría accede a /admin/
2. Va a Académico → Matrículas → Agregar matrícula
3. Selecciona estudiante, paralelo (filtrado por período activo)
4. Sistema valida: cupo disponible, período activo, rol estudiante
5. Se crea matrícula con estado "Activa"
6. Estudiante aparece en planillas de asistencia del paralelo
```

### 7.2 Flujo: Tomar asistencia (Docente)

```
1. Docente accede a su dashboard
2. Ve lista de SUS paralelos del período activo
3. Selecciona paralelo → "Registrar asistencia"
4. Ve planilla: tabla con nombres de estudiantes matriculados (activos)
5. Selecciona fecha (default: hoy)
6. Marca checkboxes de los presentes (checkbox "todos" disponible)
7. Presiona "Guardar asistencia"
8. Sistema:
   a. Crea registros PRESENTE para marcados, AUSENTE para no marcados
   b. Recalcula % de inasistencia de cada estudiante
   c. Si algún estudiante supera 5% → envía email al inspector
9. Mensaje de confirmación: "Asistencia registrada para [paralelo] - [fecha]"
```

### 7.3 Flujo: Consultar asistencia (Estudiante)

```
1. Estudiante accede a su dashboard
2. Ve barra/card superior con % de inasistencia GENERAL y color
3. Ve grid de cards, una por cada asignatura matriculada (activa)
4. Cada card: nombre asignatura, % inasistencia, color (verde/rojo)
5. Si no hay registros → "Sin registros de asistencia aún"
```

### 7.4 Flujo: Supervisar riesgo (Inspector)

```
1. Inspector accede a panel de supervisión
2. Ve tabla con todos los estudiantes del período activo
3. Columnas: nombre, tipo licencia, % inasistencia general, indicador
4. Filtra por tipo de licencia
5. Ordena por % inasistencia (más grave primero)
6. Estudiantes en rojo (≥5%) son los que requieren atención
```

---

## 8. Decisiones de arquitectura — Sprint 2

| # | Decisión | Resolución | Razón |
|---|----------|-----------|-------|
| D15 | Modelo de matrícula | Modelo `Matricula` explícito en vez de M2M `Paralelo.estudiantes` | Necesita estados (activa/retirada/suspendida), auditoría (fecha, quién matriculó), y reglas de transición |
| D16 | Ubicación de `Matricula` | En app `academico` (no nueva app) | Es parte del bounded context académico — vincula estudiante con paralelo |
| D17 | Asistencia vinculada a paralelo | Mantener FK a `Paralelo` (que ya tiene FK a `Asignatura`) | No se necesita FK directa a asignatura — el paralelo ya la contiene |
| D18 | Estado por defecto de asistencia | `AUSENTE` (no marcar checkbox = ausente) | UX confirmada: el docente marca los presentes, los no marcados se registran como ausentes |
| D19 | Validación de conflictos de horarios | Manual por secretaría, no automática | Campo `horario` es CharField libre — no se puede parsear automáticamente |
| D20 | Cálculo de porcentajes | Servicio de dominio puro (sin ORM) | Testeable, reutilizable, cumple DDD |
| D21 | Umbral de riesgo | 5% de inasistencia (= 95% de asistencia requerida) | Confirmado por el cliente |
| D22 | Trigger de alertas | Al guardar planilla de asistencia (síncrono, no batch) | Feedback inmediato, simplicidad, sin necesidad de Celery/cron |
| D23 | Notificación al estudiante | Visual en dashboard (no email) | Email solo al inspector. Estudiante ve su % actualizado al entrar a su dashboard |
| D24 | Matrícula desde Django Admin | Personalización mínima del admin | Coherente con Sprint 1 (secretaría usa admin para crear usuarios) |

---

## 9. Riesgos del Sprint 2

| # | Riesgo | Probabilidad | Impacto | Mitigación |
|---|--------|-------------|---------|-----------|
| R1 | Eliminar M2M `Paralelo.estudiantes` puede romper código/tests existentes que lo referencien | Media | Alto | Buscar todas las referencias antes de migrar. Reemplazar por queries a `Matricula` |
| R2 | Planilla de asistencia con 30 estudiantes puede ser lenta con Alpine.js | Baja | Bajo | 30 estudiantes es poco — no hay problema de rendimiento. Si fuera 200+, paginar |
| R3 | Cálculo de porcentajes recorre muchos registros en paralelos con historia larga | Baja | Medio | Usar agregaciones de Django ORM (`Count`, `Q`) en vez de iterar en Python |
| R4 | Email de alertas puede fallar (SMTP) y bloquear el guardado de asistencia | Media | Alto | Enviar email en try/except — no bloquear el flujo principal. Loguear fallo |
| R5 | No tener datos reales de planillas de asistencia de la ECPPP | Alta | Medio | Solicitar documentos Día 1. Mientras tanto, diseñar con datos de prueba realistas |
| R6 | Sprint de 20 puntos con 2 devs en 5 días es ambicioso | Media | Alto | Buffer de 3 días en semana 2. HU12 (notificaciones) es la más sacrificable si hay retraso |

---

## 10. Configuración técnica — Sprint 2

### 10.1 Nuevas URLs

```python
# apps/asistencia/presentation/urls.py
urlpatterns = [
    path("paralelo/<int:paralelo_id>/registrar/", RegistrarAsistenciaView, name="registrar_asistencia"),
    path("paralelo/<int:paralelo_id>/historial/", HistorialAsistenciaView, name="historial_asistencia"),
    path("mi-asistencia/", MiAsistenciaView, name="mi_asistencia"),
    path("supervision/", SupervisionView, name="supervision"),
]
```

### 10.2 Nuevos servicios de dominio

```python
# apps/asistencia/domain/services.py
class AsistenciaCalculoService:
    """Servicio puro de cálculo de porcentajes de asistencia."""

# apps/asistencia/application/services.py
class RegistroAsistenciaAppService:
    """Orquesta: guardar asistencia → recalcular % → evaluar alertas → notificar."""

class ConsultaAsistenciaAppService:
    """Calcula porcentajes para dashboard de estudiante."""

class SupervisionAppService:
    """Calcula porcentajes para panel de supervisión del inspector."""
```

### 10.3 Nuevas funciones de email

```python
# apps/asistencia/infrastructure/email_service.py (o reutilizar usuarios)
def send_alerta_inasistencia(inspector, estudiante, porcentaje, asignatura):
    """Envía email al inspector alertando inasistencia crítica de un estudiante."""
```

### 10.4 Fixtures/Seeds para demo

Para la demo de cierre de sprint, crear un management command o data migration con:
- 5 estudiantes de ejemplo matriculados en 2 paralelos.
- 10 días de asistencia registrada (con algunas inasistencias).
- 1 estudiante en rojo (>5% inasistencia).

---

## 11. Métricas de éxito del Sprint 2

| # | Métrica | Criterio |
|---|---------|----------|
| M1 | HUs completadas | 6/6 (HU07–HU12) |
| M2 | Tests pasando | Suite completa verde + nuevos tests del sprint |
| M3 | Flujo E2E funcional | Matricular → tomar asistencia → ver dashboard → alerta email |
| M4 | Cobertura dominio | ≥ 70% |
| M5 | PRs mergeados | Todos los feature branches mergeados a develop vía PR |
| M6 | Responsive | Todas las vistas nuevas responsive (mobile + desktop) |
