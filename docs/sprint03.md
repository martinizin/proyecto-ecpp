# PRD — Sprint 3: Plataforma Web Académica ECPPP

| Campo | Valor |
|-------|-------|
| **Título** | Product Requirements Document — Sprint 3 |
| **Proyecto** | Plataforma Web Académica ECPPP |
| **Versión** | 0.4.0 |
| **Fecha** | Mayo 2026 |
| **Sprint** | S3 (Incremento 3) |
| **Rango de fechas** | 11/05/2026 – 23/05/2026 (2 semanas, ~10 días hábiles) |
| **Equipo** | 2 desarrolladores fullstack — Martín Jiménez, Junior Espín |
| **Metodología** | Scrum + Git Flow (`develop` → `feature/*` → PR) |
| **Estado** | Draft |

---

## 1. Resumen ejecutivo del Sprint 3

### 1.1 Objetivo del Sprint

Implementar el ciclo completo de gestión de calificaciones: registro de notas parciales/finales por docente, validación por secretaría, visualización de libreta del estudiante, sistema de recalificación con flujo de aprobación multinivel, logs de auditoría inmutables y validación de rangos de notas. Este sprint construye sobre la autenticación multirrol (Sprint 1) y la gestión de asistencia/matrículas (Sprint 2).

### 1.2 Resumen de funcionalidades

| # | Funcionalidad | Descripción |
|---|---------------|-------------|
| 1 | Logs de auditoría (calificaciones) | Registro inmutable de cambios antes/después en calificaciones con reportes para secretaría e inspector |
| 2 | Registro de notas parciales y finales | Carga de calificaciones (4 parciales + examen) con pesos configurables y validación de secretaría |
| 3 | Visualización de libreta de calificaciones | Panel estudiante con promedio por materia, promedio general y estado de aprobación |
| 4 | Solicitud formal de recalificación | Formulario de reclamo con motivo y evidencia adjunta |
| 5 | Flujo de aprobación de rectificaciones | Gestión de solicitudes por docente/inspector/secretaría con trazabilidad y estados |
| 6 | Validación de rangos de notas | Reglas de negocio para escala 0–20 (aprobación ≥16/20) y tipos de evaluación |

### 1.3 Pendientes ECPPP por consultar

> **IMPORTANTE:** Estas consultas deben resolverse el Día 1 del sprint antes de implementar. Afectan directamente el diseño.

| # | Consulta pendiente | Impacto en implementación | Valor por defecto si no se resuelve |
|---|-------------------|---------------------------|--------------------------------------|
| P1 | ¿La inasistencia debe ser validada/aprobada por secretaría? | Define flujo de `Solicitud` tipo `justificacion` — si requiere aprobación de secretaría o solo del inspector | Solo inspector aprueba (comportamiento actual) |
| P2 | ¿Existe fórmula de cálculo específica para el promedio final? (ej. pesos % por parcial/materia) | Define si el campo `peso` de `Evaluacion` se usa en el cálculo o si es promedio simple | Promedio ponderado usando campo `peso` de cada `Evaluacion` |
| P3 | ¿Secretaría solo valida la nota final o también las parciales? | Define en qué momento del flujo interviene secretaría | Secretaría valida solo cuando el registro completo (todos los parciales) está cargado |
| P4 | ¿Cuál es el tiempo límite de resolución de una solicitud de recalificación? | Define deadline para el docente/secretaría | 5 días hábiles desde la fecha de creación |
| P5 | ¿El peso del porcentaje es por tipo de evaluación o por materia? | Afecta granularidad del modelo `Evaluacion` | Por tipo de evaluación dentro de cada paralelo (ya modelado así) |

### 1.4 Definition of Done del Sprint 3

- [ ] Docente puede registrar calificaciones parciales (4 parciales + examen) con pesos configurables.
- [ ] Secretaría valida el registro completo de calificaciones de un paralelo.
- [ ] Estudiante puede consultar su libreta: notas por evaluación, promedio por materia y promedio general.
- [ ] Estado de aprobación visible: Aprobado (≥16/20), Reprobado (<16/20).
- [ ] Estudiante puede enviar solicitud de recalificación con motivo y evidencia adjunta.
- [ ] Primera solicitud de recalificación → aprobada directamente por docente.
- [ ] Segunda solicitud en adelante → requiere validación de secretaría.
- [ ] Flujo de estados: Pendiente → En revisión → Aprobada/Rechazada con trazabilidad completa.
- [ ] Notificación por email al docente y estudiante en cada cambio de estado.
- [ ] Log de auditoría inmutable: registra valor anterior y nuevo en cada cambio de calificación.
- [ ] Secretaría e inspector pueden generar reporte de auditoría.
- [ ] Validación de rango: notas entre 0 y 20, aprobación ≥16/20.
- [ ] Tests con cobertura ≥ 70% en capa de dominio.
- [ ] Pipeline CI en verde.

---

## 2. Alcance del Sprint 3

### 2.1 Incluye

| Aspecto | Detalle |
|---------|---------|
| Registro de calificaciones | Vista para docente: planilla por paralelo con 4 parciales + examen final. Campo de peso % por evaluación |
| Validación de secretaría | Secretaría revisa y aprueba/rechaza el registro completo de calificaciones de un paralelo |
| Libreta del estudiante | Dashboard con cards por materia: nota de cada evaluación, promedio ponderado, estado aprobación |
| Solicitud de recalificación | Formulario con: evaluación a reclamar, motivo detallado, archivo adjunto (PDF/imagen) |
| Flujo de aprobación | Estados: Pendiente → En revisión → Aprobada/Rechazada. 1ra vez: docente. 2da+: secretaría |
| Logs de auditoría | Modelo `LogCalificacion` inmutable: valor_anterior, valor_nuevo, usuario, timestamp, IP |
| Reportes de auditoría | Vista para secretaría/inspector: tabla filtrable de cambios en calificaciones |
| Validación de rangos | Escala 0–20 a nivel de dominio y modelo. Aprobación ≥16/20 |
| Notificaciones | Email al docente cuando recibe solicitud. Email al estudiante cuando se resuelve |
| Formulario de justificación de inasistencia | UI para que el estudiante envíe solicitud de justificación (reutiliza modelo `Solicitud`) |
| Formulario de recalificación | UI para que el estudiante envíe solicitud de recalificación |

### 2.2 Excluye

| Aspecto | Razón |
|---------|-------|
| Reportes PDF/Excel | Sprint 4 — se priorizó el flujo funcional completo |
| Recálculo automático de asistencia por justificación aprobada | Sprint 4 — se marca manualmente por ahora |
| Dashboard consolidado de secretaría | Sprint 4 |
| Firma digital de documentos | Fuera de alcance |

---

## 3. Backlog del Sprint 3

| ID | Nombre | Puntos | Responsable | Día(s) objetivo |
|----|--------|--------|-------------|-----------------|
| HU13 | Validación de rangos de notas | 2 | Junior | Día 1 |
| HU14 | Registro de notas parciales y finales (Docente) | 5 | Martín | Día 1–3 |
| HU15 | Logs de auditoría de calificaciones | 3 | Junior | Día 1–2 |
| HU16 | Validación de calificaciones por secretaría | 3 | Martín | Día 3–4 |
| HU17 | Visualización de libreta de calificaciones (Estudiante) | 3 | Junior | Día 3–4 |
| HU18 | Solicitud formal de recalificación + justificación de inasistencia | 5 | Martín | Día 4–6 |
| HU19 | Flujo de aprobación de rectificaciones | 5 | Junior | Día 5–7 |
| **Total** | | **26** | | |

---

## 4. Detalle por HU

### 4.1 HU13 — Validación de rangos de notas

**Propósito:** Implementar reglas de negocio para la escala de calificación 0–20 y tipos de evaluación, como capa de dominio reutilizable.

**Reglas de negocio:**
- Escala de calificación: 0.00 a 20.00 (2 decimales).
- Aprobación: nota final ≥ 16.00 / 20.00.
- Cada tipo de evaluación tiene un peso % configurable.
- La suma de pesos de todas las evaluaciones de un paralelo DEBE ser exactamente 100%.
- Tipos válidos: `parcial1`, `parcial2_10h`, `parcial3`, `parcial4_10h`, `proyecto`, `examen_final`.

**Implementación — Capa de dominio:**

```python
# apps/calificaciones/domain/value_objects.py
@dataclass(frozen=True)
class Nota:
    """Value object que encapsula validación de rango."""
    valor: Decimal

    def __post_init__(self):
        if not (Decimal("0") <= self.valor <= Decimal("20")):
            raise NotaFueraDeRangoError(self.valor)

    @property
    def aprobado(self) -> bool:
        return self.valor >= Decimal("16")

# apps/calificaciones/domain/services.py
class CalificacionValidationService:
    """Valida reglas de negocio de calificaciones."""

    @staticmethod
    def validar_nota(valor: Decimal) -> Nota:
        return Nota(valor=valor)

    @staticmethod
    def validar_pesos_evaluaciones(pesos: list[Decimal]) -> bool:
        return sum(pesos) == Decimal("100")

    @staticmethod
    def calcular_promedio_ponderado(notas_con_peso: list[tuple[Decimal, Decimal]]) -> Decimal:
        """Recibe lista de (nota, peso%). Retorna promedio ponderado."""
        total = sum(nota * peso / Decimal("100") for nota, peso in notas_con_peso)
        return total.quantize(Decimal("0.01"))

    @staticmethod
    def estado_aprobacion(promedio: Decimal) -> str:
        return "aprobado" if promedio >= Decimal("16") else "reprobado"
```

**Cambios al modelo `Calificacion`:**

```python
# apps/calificaciones/infrastructure/models.py — agregar validación
from django.core.validators import MinValueValidator, MaxValueValidator

class Calificacion(models.Model):
    nota = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("20"))]
    )
```

**Criterios de aceptación:**
- [ ] Value object `Nota` con validación 0–20 y propiedad `aprobado`.
- [ ] Excepción de dominio `NotaFueraDeRangoError`.
- [ ] Servicio `CalificacionValidationService` con cálculo de promedio ponderado.
- [ ] Validación de que pesos sumen 100%.
- [ ] Validators de Django en modelo `Calificacion` (0–20).
- [ ] Tests unitarios con parametrize: bordes (0, 16, 20), fuera de rango (-1, 20.01), pesos.

**Branch:** `feature/HU13-validacion-rangos-notas`

---

### 4.2 HU14 — Registro de notas parciales y finales (Docente)

**Propósito:** Permitir al docente registrar calificaciones de sus estudiantes conforme al esquema de 4 parciales + examen final, con pesos configurables por evaluación.

**Reglas de negocio:**
- Docente solo puede registrar notas en SUS paralelos (paralelos donde es docente asignado).
- Esquema de evaluación por paralelo: 4 parciales + examen final (6 evaluaciones con tipos definidos).
- Cada evaluación tiene un peso % del total. La suma DEBE ser 100%.
- Las evaluaciones del paralelo se crean/configuran previamente (desde Django Admin o vista dedicada).
- Notas en escala 0–20 (validado por HU13).
- Docente puede registrar notas parcial por parcial (no necesita cargar todo de una vez).
- Una vez que TODAS las evaluaciones tienen notas para TODOS los estudiantes → el registro se considera "completo" y pasa a validación de secretaría.
- Campo `peso` ya existe en modelo `Evaluacion` — se configura al crear la evaluación.

**Vista principal — Planilla de calificaciones:**
- URL: `/calificaciones/paralelo/<paralelo_id>/registrar/`
- GET: Muestra tabla con estudiantes en filas y evaluaciones en columnas.
- POST: Guarda/actualiza las notas ingresadas.
- Cada celda es un input numérico (0–20, step 0.01).
- Columna final: promedio ponderado calculado (readonly).
- Indicador visual: verde (≥16) / rojo (<16) en el promedio.

**Modelo de estado del registro:**

```python
# apps/calificaciones/infrastructure/models.py — nuevo modelo
class RegistroCalificacionParalelo(models.Model):
    """Tracks the submission and validation state of grades for a paralelo."""

    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        COMPLETO = "completo", "Completo — Pendiente validación"
        VALIDADO = "validado", "Validado por Secretaría"
        RECHAZADO = "rechazado", "Rechazado por Secretaría"

    paralelo = models.OneToOneField(
        "academico.Paralelo", on_delete=models.CASCADE,
        related_name="registro_calificaciones"
    )
    estado = models.CharField(
        max_length=15, choices=Estado.choices, default=Estado.BORRADOR
    )
    fecha_envio = models.DateTimeField(null=True, blank=True)
    fecha_validacion = models.DateTimeField(null=True, blank=True)
    validado_por = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="registros_validados",
        limit_choices_to={"rol": "secretaria"},
    )
    observaciones_secretaria = models.TextField(blank=True)

    class Meta:
        verbose_name = "Registro de Calificaciones"
        verbose_name_plural = "Registros de Calificaciones"
```

**Criterios de aceptación:**
- [ ] Modelo `RegistroCalificacionParalelo` creado con migración.
- [ ] Vista de registro de calificaciones accesible solo para docente (sus paralelos).
- [ ] Planilla: filas=estudiantes matriculados activos, columnas=evaluaciones del paralelo.
- [ ] Input numérico validado 0–20 en frontend y backend.
- [ ] Promedio ponderado calculado y mostrado en tiempo real (Alpine.js).
- [ ] Indicador de color verde/rojo en promedio.
- [ ] Docente puede guardar parcialmente (no todas las notas de una vez).
- [ ] Al completar todas las notas → botón "Enviar a validación" → estado cambia a `COMPLETO`.
- [ ] Docente NO puede editar notas después de enviar a validación (estado `COMPLETO` o `VALIDADO`).
- [ ] Si secretaría rechaza → estado vuelve a `BORRADOR` y docente puede corregir.
- [ ] Cada guardado de nota registra log de auditoría (HU15).
- [ ] Tests de vista, servicio y modelo.

**Branch:** `feature/HU14-registro-calificaciones`

---

### 4.3 HU15 — Logs de auditoría de calificaciones

**Propósito:** Implementar un registro inmutable de todos los cambios en calificaciones, permitiendo trazabilidad completa del proceso y generación de reportes.

**Reglas de negocio:**
- Cada vez que se crea, modifica o elimina una calificación se registra un log.
- El log es INMUTABLE: no se puede editar ni eliminar (no `update`, no `delete` en la API).
- Registra: valor anterior, valor nuevo, quién lo hizo, cuándo, desde qué IP, motivo.
- Secretaría e inspector pueden consultar y filtrar los logs.
- Secretaría e inspector pueden generar un reporte (tabla filtrable por ahora, PDF en Sprint 4).

**Modelo — Log de calificación:**

```python
# apps/calificaciones/infrastructure/models.py
class LogCalificacion(models.Model):
    """Immutable audit log for grade changes."""

    class TipoAccion(models.TextChoices):
        CREACION = "creacion", "Creación"
        MODIFICACION = "modificacion", "Modificación"
        RECALIFICACION = "recalificacion", "Recalificación"
        ELIMINACION = "eliminacion", "Eliminación"

    calificacion = models.ForeignKey(
        Calificacion, on_delete=models.SET_NULL, null=True,
        related_name="logs"
    )
    evaluacion_info = models.CharField(max_length=200)  # snapshot: "Parcial 1 — MAT-101 A"
    estudiante_info = models.CharField(max_length=200)  # snapshot: "Juan Pérez (1234567890)"
    accion = models.CharField(max_length=20, choices=TipoAccion.choices)
    valor_anterior = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    valor_nuevo = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    realizado_por = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.SET_NULL, null=True,
        related_name="logs_calificacion"
    )
    ip = models.GenericIPAddressField(null=True, blank=True)
    motivo = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Log de Calificación"
        verbose_name_plural = "Logs de Calificaciones"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["calificacion", "timestamp"]),
            models.Index(fields=["realizado_por", "timestamp"]),
        ]
        # Protección contra eliminación/edición: se implementa a nivel de servicio

    def __str__(self):
        return f"[{self.timestamp}] {self.get_accion_display()} — {self.estudiante_info}"
```

**Servicio de auditoría:**

```python
# apps/calificaciones/application/services.py
class AuditoriaCalificacionService:
    """Registra logs inmutables de cambios en calificaciones."""

    @staticmethod
    def registrar_cambio(
        calificacion, accion, valor_anterior, valor_nuevo, usuario, ip, motivo=""
    ):
        LogCalificacion.objects.create(
            calificacion=calificacion,
            evaluacion_info=str(calificacion.evaluacion),
            estudiante_info=f"{calificacion.estudiante.get_full_name()} ({calificacion.estudiante.cedula})",
            accion=accion,
            valor_anterior=valor_anterior,
            valor_nuevo=valor_nuevo,
            realizado_por=usuario,
            ip=ip,
            motivo=motivo,
        )
```

**Vista de reporte:**
- URL: `/calificaciones/auditoria/`
- Accesible para: secretaría e inspector.
- Tabla filtrable por: fecha, docente, paralelo, estudiante, tipo de acción.
- Ordenable por timestamp descendente.

**Criterios de aceptación:**
- [ ] Modelo `LogCalificacion` creado con migración.
- [ ] Log se crea automáticamente al crear/modificar calificación (integrado en servicio de HU14).
- [ ] Log incluye snapshots de texto (no solo FK) para inmutabilidad.
- [ ] No se permite `update` ni `delete` del log (validación en servicio, no en DB).
- [ ] Vista de auditoría para secretaría e inspector con filtros.
- [ ] Tests unitarios del servicio de auditoría.
- [ ] Tests de integración: crear/modificar calificación → log generado.

**Branch:** `feature/HU15-logs-auditoria`

---

### 4.4 HU16 — Validación de calificaciones por secretaría

**Propósito:** Permitir a la secretaría revisar y aprobar/rechazar el registro completo de calificaciones de un paralelo antes de que sea oficial.

**Reglas de negocio:**
- Secretaría valida el registro COMPLETO (cuando todos los parciales y examen tienen notas para todos los estudiantes).
- El docente envía a validación → estado `COMPLETO`.
- Secretaría puede:
  - **Aprobar** → estado `VALIDADO`. Las notas quedan oficiales e inmutables (solo modificables vía recalificación).
  - **Rechazar** → estado `RECHAZADO` con observaciones. Docente puede corregir y reenviar.
- Se registra log de auditoría del cambio de estado.
- Se notifica al docente por email cuando secretaría valida/rechaza.

**Vista principal:**
- URL: `/secretaria/calificaciones/pendientes/`
- Lista de paralelos con estado `COMPLETO` (pendientes de validación).
- Detalle: ver planilla completa del paralelo (readonly) con promedios.
- Botones: "Aprobar" / "Rechazar" (con campo de observaciones si rechaza).

**Criterios de aceptación:**
- [ ] Vista de pendientes de validación accesible solo para secretaría.
- [ ] Secretaría puede ver planilla completa readonly.
- [ ] Botón aprobar → estado `VALIDADO`, timestamp, `validado_por`.
- [ ] Botón rechazar → estado `RECHAZADO` + observaciones obligatorias.
- [ ] Email al docente al aprobar/rechazar.
- [ ] Log de auditoría del cambio de estado.
- [ ] Notas no editables por docente cuando estado es `VALIDADO`.
- [ ] Tests de vista y flujo.

**Branch:** `feature/HU16-validacion-secretaria`

---

### 4.5 HU17 — Visualización de libreta de calificaciones (Estudiante)

**Propósito:** Panel para que el estudiante revise sus calificaciones por materia, promedio ponderado y estado de aprobación.

**Reglas de negocio:**
- El estudiante ve todas las materias (paralelos) en las que tiene matrícula activa del período activo.
- Por cada materia: nota de cada evaluación registrada, promedio ponderado (si hay notas), estado.
- Promedio general: promedio aritmético de los promedios ponderados de todas las materias.
- Estado de aprobación por materia: "Aprobado" (≥16/20), "Reprobado" (<16/20), "En curso" (si faltan notas).
- Las notas solo son visibles cuando el registro está `VALIDADO` por secretaría. Si está en `BORRADOR` o `COMPLETO`, el estudiante ve "Pendiente de publicación".

**Vista principal:**
- URL: `/calificaciones/mi-libreta/`
- Solo accesible para rol `estudiante`.
- Layout: card por materia con tabla interna de evaluaciones.

**Datos por card:**
```
┌──────────────────────────────────────────┐
│ MAT-101 — Matemáticas         [En curso] │
│ Paralelo A — Prof. García                │
├──────────────────────────────────────────┤
│ Parcial 1 (20%)       │  17.50           │
│ Parcial 2 10h (15%)   │  16.00           │
│ Parcial 3 (20%)       │  —               │
│ Parcial 4 10h (15%)   │  —               │
│ Proyecto (10%)        │  —               │
│ Examen Final (20%)    │  —               │
├──────────────────────────────────────────┤
│ Promedio parcial: 16.90      ✅ Aprobado  │
└──────────────────────────────────────────┘
```

**Sección superior:**
```
Promedio General: 16.45 / 20   Estado: En curso (4/6 materias con notas)
```

**Criterios de aceptación:**
- [ ] Vista accesible solo para estudiante autenticado.
- [ ] Card por cada paralelo con matrícula activa.
- [ ] Nota de cada evaluación visible (o "—" si no hay).
- [ ] Promedio ponderado calculado correctamente (solo con notas existentes).
- [ ] Estado: "Aprobado" / "Reprobado" / "En curso".
- [ ] Notas solo visibles si registro está `VALIDADO` por secretaría.
- [ ] Promedio general en sección superior.
- [ ] Template responsive.
- [ ] Tests de vista y cálculos.

**Branch:** `feature/HU17-libreta-calificaciones`

---

### 4.6 HU18 — Solicitud formal de recalificación + justificación de inasistencia

**Propósito:** Crear formularios para que el estudiante envíe solicitudes de recalificación (con motivo y evidencia) y de justificación de inasistencia.

**Reglas de negocio — Recalificación:**
- El estudiante puede solicitar recalificación de una evaluación específica.
- Debe indicar: evaluación a reclamar, motivo detallado, archivo adjunto (PDF/imagen, max 5MB).
- Solo puede reclamar evaluaciones que ya tienen calificación registrada.
- Solo puede reclamar en el período activo.
- Se notifica al docente por email cuando recibe una solicitud.

**Reglas de negocio — Justificación de inasistencia:**
- El estudiante selecciona la fecha y paralelo de la inasistencia.
- Debe indicar: motivo, archivo adjunto (certificado médico, etc.).
- Solo puede justificar inasistencias registradas como `AUSENTE`.

**Cambios al modelo `Solicitud`:**

```python
# apps/solicitudes/infrastructure/models.py — extender modelo existente
class Solicitud(models.Model):
    class TipoSolicitud(models.TextChoices):
        RECTIFICACION = "rectificacion", "Rectificación de Calificación"
        JUSTIFICACION = "justificacion", "Justificación de Inasistencia"

    class EstadoSolicitud(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EN_REVISION = "en_revision", "En Revisión"
        APROBADA = "aprobada", "Aprobada"
        RECHAZADA = "rechazada", "Rechazada"

    # --- Campos existentes ---
    tipo = models.CharField(max_length=20, choices=TipoSolicitud.choices)
    estudiante = models.ForeignKey(...)
    estado = models.CharField(max_length=15, choices=EstadoSolicitud.choices, default=EstadoSolicitud.PENDIENTE)
    descripcion = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    resuelto_por = models.ForeignKey(...)
    respuesta = models.TextField(blank=True)

    # --- Campos nuevos Sprint 3 ---
    # Para recalificación: referencia a la evaluación/calificación
    calificacion = models.ForeignKey(
        "calificaciones.Calificacion", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="solicitudes_recalificacion",
    )
    # Para justificación: referencia a la asistencia
    asistencia = models.ForeignKey(
        "asistencia.Asistencia", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="solicitudes_justificacion",
    )
    # Archivo adjunto (evidencia)
    archivo_adjunto = models.FileField(
        upload_to="solicitudes/%Y/%m/", null=True, blank=True,
        help_text="PDF o imagen. Máximo 5MB."
    )
    # Nivel de aprobación requerido
    requiere_secretaria = models.BooleanField(
        default=False,
        help_text="True si es la segunda solicitud o más del estudiante para la misma evaluación."
    )
    # Conteo de intentos (para lógica de escalamiento)
    numero_solicitud = models.PositiveIntegerField(default=1)
```

**Vistas:**
- `/solicitudes/recalificacion/nueva/` — Formulario de recalificación.
- `/solicitudes/justificacion/nueva/` — Formulario de justificación de inasistencia.
- `/solicitudes/mis-solicitudes/` — Lista de solicitudes del estudiante con estado.

**Criterios de aceptación:**
- [ ] Formulario de recalificación con: selección de evaluación, motivo, archivo adjunto.
- [ ] Formulario de justificación con: selección de fecha/paralelo, motivo, archivo adjunto.
- [ ] Validación de archivo: solo PDF/imagen, max 5MB.
- [ ] Solo estudiantes autenticados pueden crear solicitudes.
- [ ] Email al docente al crear solicitud de recalificación.
- [ ] Lista de "mis solicitudes" con estado actual.
- [ ] Cálculo automático de `numero_solicitud` y `requiere_secretaria`.
- [ ] Tests de formulario, vista y validaciones.

**Branch:** `feature/HU18-solicitudes-recalificacion`

---

### 4.7 HU19 — Flujo de aprobación de rectificaciones

**Propósito:** Gestionar el flujo de aprobación de solicitudes de recalificación y justificación con trazabilidad, estados y roles diferenciados.

**Reglas de negocio — Recalificación:**
- **1ra solicitud:** El docente recibe, revisa y aprueba/rechaza directamente.
  - Si aprueba → puede cambiar la nota (se registra log de auditoría como `recalificacion`).
  - Si rechaza → debe indicar motivo.
- **2da solicitud en adelante (misma evaluación):** Debe ser validada y aprobada por secretaría.
  - Flujo: Estudiante → Secretaría (valida procedencia) → Docente (resuelve) → Secretaría (confirma).
- Se notifica por email al estudiante en cada cambio de estado.
- Se notifica por email al docente cuando le asignan una solicitud.
- Tiempo límite de resolución: **5 días hábiles** (configurable — pendiente P4).
- Trazabilidad: cada cambio de estado queda registrado con usuario, fecha y comentario.

**Reglas de negocio — Justificación de inasistencia:**
- Inspector (o secretaría, pendiente P1) revisa y aprueba/rechaza.
- Si aprueba → la asistencia cambia de `AUSENTE` a `JUSTIFICADO`.

**Modelo de trazabilidad:**

```python
# apps/solicitudes/infrastructure/models.py — nuevo modelo
class HistorialSolicitud(models.Model):
    """Tracks every state change of a solicitud for full traceability."""

    solicitud = models.ForeignKey(
        Solicitud, on_delete=models.CASCADE, related_name="historial"
    )
    estado_anterior = models.CharField(max_length=15)
    estado_nuevo = models.CharField(max_length=15)
    cambiado_por = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.SET_NULL, null=True
    )
    comentario = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
```

**Vistas:**
- `/solicitudes/pendientes/` — Para docente: solicitudes asignadas a sus paralelos.
- `/secretaria/solicitudes/` — Para secretaría: solicitudes que requieren su validación.
- `/solicitudes/<id>/resolver/` — Detalle + botones Aprobar/Rechazar.

**Criterios de aceptación:**
- [ ] Docente ve lista de solicitudes pendientes de sus paralelos.
- [ ] Secretaría ve solicitudes que requieren su validación (`requiere_secretaria=True`).
- [ ] Flujo 1ra solicitud: Pendiente → En revisión (docente toma) → Aprobada/Rechazada.
- [ ] Flujo 2da+ solicitud: Pendiente → En revisión (secretaría valida) → En revisión (docente) → Aprobada/Rechazada.
- [ ] Al aprobar recalificación: docente puede ingresar nueva nota → log con `recalificacion`.
- [ ] Al aprobar justificación: asistencia cambia a `JUSTIFICADO`.
- [ ] `HistorialSolicitud` registra cada transición de estado.
- [ ] Email al estudiante en cada cambio de estado.
- [ ] Email al docente cuando se le asigna solicitud.
- [ ] Tiempo límite visible (fecha de creación + 5 días hábiles).
- [ ] Tests de flujo completo (1ra y 2da+ solicitud).

**Branch:** `feature/HU19-flujo-aprobacion`

---

## 5. Modelo de datos — Cambios del Sprint 3

### 5.1 Nuevos modelos

| Modelo | App | Ubicación |
|--------|-----|-----------|
| `LogCalificacion` | `calificaciones` | `apps/calificaciones/infrastructure/models.py` |
| `RegistroCalificacionParalelo` | `calificaciones` | `apps/calificaciones/infrastructure/models.py` |
| `HistorialSolicitud` | `solicitudes` | `apps/solicitudes/infrastructure/models.py` |

### 5.2 Modificaciones a modelos existentes

| Modelo | Cambio | Razón |
|--------|--------|-------|
| `Calificacion` | Agregar validators (0–20) | Validación de rango a nivel de modelo |
| `Solicitud` | Agregar campos: `calificacion`, `asistencia`, `archivo_adjunto`, `requiere_secretaria`, `numero_solicitud` | Soporte para recalificación y justificación con evidencia y escalamiento |
| `Solicitud` | Agregar estado `EN_REVISION` | Flujo de aprobación con trazabilidad |

### 5.3 Nuevos value objects de dominio

| Value Object | App | Ubicación |
|-------------|-----|-----------|
| `Nota` | `calificaciones` | `apps/calificaciones/domain/value_objects.py` |

### 5.4 Nuevos servicios de dominio

| Servicio | App | Ubicación |
|----------|-----|-----------|
| `CalificacionValidationService` | `calificaciones` | `apps/calificaciones/domain/services.py` |
| `PromedioCalculoService` | `calificaciones` | `apps/calificaciones/domain/services.py` |

### 5.5 Nuevos servicios de aplicación

| Servicio | App | Ubicación |
|----------|-----|-----------|
| `RegistroCalificacionAppService` | `calificaciones` | `apps/calificaciones/application/services.py` |
| `AuditoriaCalificacionService` | `calificaciones` | `apps/calificaciones/application/services.py` |
| `ValidacionSecretariaAppService` | `calificaciones` | `apps/calificaciones/application/services.py` |
| `SolicitudRecalificacionAppService` | `solicitudes` | `apps/solicitudes/application/services.py` |
| `FlujoAprobacionAppService` | `solicitudes` | `apps/solicitudes/application/services.py` |

### 5.6 Migraciones necesarias

1. Agregar validators a `Calificacion.nota`.
2. Crear modelo `LogCalificacion`.
3. Crear modelo `RegistroCalificacionParalelo`.
4. Agregar campos nuevos a `Solicitud` (calificacion, asistencia, archivo_adjunto, requiere_secretaria, numero_solicitud).
5. Agregar estado `EN_REVISION` a `Solicitud.EstadoSolicitud`.
6. Crear modelo `HistorialSolicitud`.

---

## 6. Distribución de trabajo — 10 días (Git Flow)

> **Convención:** `develop` → `feature/HU0X-nombre` → PR → merge a `develop`.
> Ambos devs son fullstack. Trabajo en paralelo con PRs cruzados.

### Semana 1 — Core de calificaciones

#### Día 1 (Lunes 11/05) — Fundamentos

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Junior** | HU13: Value object `Nota`, servicio de validación, validators en modelo, excepciones de dominio, tests unitarios exhaustivos | `feature/HU13-validacion-rangos-notas` | VO + servicio + 15+ tests, PR abierto |
| **Martín** | HU14: Modelo `RegistroCalificacionParalelo`, migración, vista GET planilla de calificaciones (tabla estudiantes × evaluaciones) | `feature/HU14-registro-calificaciones` | Planilla renderiza con estudiantes, PR abierto |

#### Día 2 (Martes 12/05) — Auditoría + registro

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Junior** | HU15: Modelo `LogCalificacion`, servicio de auditoría, integración con señales/servicio de calificación. Merge PR HU13 | `feature/HU15-logs-auditoria` | Modelo + servicio + tests, PR HU13 merged |
| **Martín** | HU14: POST guardar calificaciones, validación 0–20 (usa HU13), cálculo de promedio ponderado en vista, Alpine.js para cálculo en tiempo real | `feature/HU14-registro-calificaciones` | Registro funcional con validación |

#### Día 3 (Miércoles 13/05) — Completar registro + libreta

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Junior** | HU17: Vista libreta estudiante, cards por materia, promedio por materia, promedio general, estados. Merge PR HU15 | `feature/HU17-libreta-calificaciones` | Dashboard estudiante funcional, PR HU15 merged |
| **Martín** | HU14: Lógica "enviar a validación", bloqueo de edición post-envío, tests completos. Integración con auditoría (HU15) | `feature/HU14-registro-calificaciones` | HU14 completa, PR abierto |

#### Día 4 (Jueves 14/05) — Validación secretaría + libreta

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Junior** | HU17: Lógica de visibilidad (solo notas validadas), tests. Merge PR | `feature/HU17-libreta-calificaciones` | PR merged |
| **Martín** | HU16: Vista de pendientes de validación (secretaría), planilla readonly, aprobar/rechazar con observaciones | `feature/HU16-validacion-secretaria` | Validación funcional |

#### Día 5 (Viernes 15/05) — Cierre semana 1

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Junior** | HU15: Vista reporte de auditoría (secretaría/inspector), filtros, tabla. Merge PR pendientes | `feature/HU15-logs-auditoria` | Reporte funcional, PRs merged |
| **Martín** | HU16: Notificaciones email a docente, log de auditoría de validación, tests. Merge PR HU14 y HU16 | `feature/HU16-validacion-secretaria` | PRs merged, flujo calificaciones completo |

### Semana 2 — Solicitudes y flujo de aprobación

#### Día 6 (Lunes 18/05) — Migraciones solicitudes

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Junior** | HU19: Modelo `HistorialSolicitud`, migración, servicio de transición de estados | `feature/HU19-flujo-aprobacion` | Modelos + servicio de estado, PR abierto |
| **Martín** | HU18: Migración modelo `Solicitud` (campos nuevos), formulario de recalificación (selección evaluación, motivo, archivo) | `feature/HU18-solicitudes-recalificacion` | Formulario recalificación funcional |

#### Día 7 (Martes 19/05) — Formularios + flujo

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Junior** | HU19: Vista de pendientes para docente, vista de pendientes para secretaría, detalle con resolver | `feature/HU19-flujo-aprobacion` | Vistas de gestión funcionales |
| **Martín** | HU18: Formulario de justificación de inasistencia, lista "mis solicitudes", cálculo automático de `numero_solicitud` y `requiere_secretaria` | `feature/HU18-solicitudes-recalificacion` | Ambos formularios funcionales |

#### Día 8 (Miércoles 20/05) — Integración flujos

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Junior** | HU19: Flujo de aprobación 1ra solicitud (docente directo), integración con cambio de nota + log auditoría | `feature/HU19-flujo-aprobacion` | Flujo 1ra solicitud E2E |
| **Martín** | HU18: Notificaciones email (al docente al crear, al estudiante al resolver), validaciones de archivo 5MB, tests | `feature/HU18-solicitudes-recalificacion` | Notificaciones + tests, PR abierto |

#### Día 9 (Jueves 21/05) — Flujo avanzado

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Junior** | HU19: Flujo 2da+ solicitud (escalamiento a secretaría), justificación → cambio asistencia a JUSTIFICADO, tests completos | `feature/HU19-flujo-aprobacion` | Flujo completo + tests, PR abierto |
| **Martín** | Merge PR HU18. Integración final: testing E2E manual del flujo completo (registrar nota → estudiante ve → reclama → docente resuelve) | `develop` | PR HU18 merged, flujo probado |

#### Día 10 (Viernes 22/05) — Cierre sprint

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Junior** | Merge PR HU19. Fix bugs, tests de integración, suite completa verde | `develop` | PR merged, 0 failures |
| **Martín** | Testing E2E completo, fix bugs, data fixtures para demo, documentación cierre | `develop` | Suite verde, fixtures, documentación |

### Tareas no técnicas (en paralelo durante el sprint)

| Tarea | Responsable | Día |
|-------|-------------|-----|
| Resolver consultas pendientes P1–P5 con la ECPPP | Junior | Día 1 |
| Solicitar formato de libreta de calificaciones actual (papel/Excel) | Junior | Día 1 |
| Configurar `MEDIA_ROOT` y `MEDIA_URL` para archivos adjuntos | Martín | Día 1 |
| Code review cruzado de cada PR (mínimo 1 approval antes de merge) | Ambos | Continuo |
| Testing manual de flujos completos | Ambos | Día 9–10 |
| Crear data fixtures/seeds para demo | Martín | Día 10 |

---

## 7. Flujos de usuario completos

### 7.1 Flujo: Registrar calificaciones (Docente)

```
1. Docente accede a su dashboard
2. Ve lista de SUS paralelos del período activo
3. Selecciona paralelo → "Registrar calificaciones"
4. Ve planilla: filas = estudiantes, columnas = evaluaciones (parciales + examen)
5. Cada evaluación muestra su peso (%) en el encabezado
6. Ingresa notas en los inputs (0–20)
7. Ve promedio ponderado calculándose en tiempo real (Alpine.js)
8. Indicador verde/rojo en el promedio
9. Presiona "Guardar"
10. Sistema:
    a. Valida todas las notas (0–20)
    b. Guarda/actualiza calificaciones
    c. Registra log de auditoría por cada nota creada/modificada
11. Cuando TODAS las notas están cargadas → aparece botón "Enviar a validación"
12. Docente presiona "Enviar a validación"
13. Estado cambia a COMPLETO → docente ya no puede editar
14. Secretaría recibe notificación
```

### 7.2 Flujo: Validar calificaciones (Secretaría)

```
1. Secretaría accede a /secretaria/calificaciones/pendientes/
2. Ve lista de paralelos con estado "Completo — Pendiente validación"
3. Selecciona paralelo → ve planilla readonly con todos los promedios
4. Revisa las notas
5a. Si todo correcto → "Aprobar" → estado VALIDADO → notas oficiales
5b. Si hay errores → "Rechazar" + observaciones → estado RECHAZADO → docente puede corregir
6. Email al docente informando el resultado
```

### 7.3 Flujo: Consultar libreta (Estudiante)

```
1. Estudiante accede a /calificaciones/mi-libreta/
2. Ve promedio general en sección superior
3. Ve cards por cada materia matriculada:
   - Si registro VALIDADO → notas visibles con promedio y estado
   - Si no VALIDADO → "Pendiente de publicación"
4. Puede ver detalle de cada evaluación y su peso
```

### 7.4 Flujo: Solicitar recalificación (Estudiante — 1ra vez)

```
1. Estudiante accede a /solicitudes/recalificacion/nueva/
2. Selecciona la evaluación a reclamar (solo evaluaciones con nota)
3. Escribe motivo detallado
4. Adjunta evidencia (PDF/imagen, max 5MB)
5. Sistema calcula: numero_solicitud = 1, requiere_secretaria = False
6. Envía solicitud → estado PENDIENTE
7. Email al docente
8. Docente accede a /solicitudes/pendientes/
9. Revisa solicitud → "En revisión" → evalúa
10a. Aprueba → ingresa nueva nota → log "recalificación" → email al estudiante
10b. Rechaza → motivo → email al estudiante
```

### 7.5 Flujo: Solicitar recalificación (Estudiante — 2da+ vez)

```
1–5. Igual que flujo 7.4
5. Sistema calcula: numero_solicitud = 2+, requiere_secretaria = True
6. Envía solicitud → estado PENDIENTE
7. Email a secretaría (no al docente todavía)
8. Secretaría accede a /secretaria/solicitudes/
9. Valida la procedencia de la solicitud
10a. Si procede → cambia estado a EN_REVISION → se asigna al docente → email al docente
10b. Si no procede → RECHAZADA → email al estudiante con motivo
11. Docente resuelve (igual que flujo 7.4 paso 9–10)
```

### 7.6 Flujo: Justificar inasistencia (Estudiante)

```
1. Estudiante accede a /solicitudes/justificacion/nueva/
2. Selecciona paralelo y fecha de la inasistencia (solo fechas con estado AUSENTE)
3. Escribe motivo
4. Adjunta certificado (PDF/imagen)
5. Envía solicitud → estado PENDIENTE
6. Inspector (o secretaría — pendiente P1) recibe
7. Revisa → Aprueba/Rechaza
8. Si aprueba → asistencia cambia de AUSENTE a JUSTIFICADO → recálculo de %
```

---

## 8. Decisiones de arquitectura — Sprint 3

| # | Decisión | Resolución | Razón |
|---|----------|-----------|-------|
| D25 | Log de auditoría de calificaciones | Modelo `LogCalificacion` separado de `RegistroAuditoria` | `RegistroAuditoria` es para acciones de seguridad (login/logout). `LogCalificacion` tiene campos específicos de calificaciones (valor_anterior, valor_nuevo) y requiere snapshots inmutables |
| D26 | Snapshots de texto en logs | `evaluacion_info` y `estudiante_info` como CharField, no FK | Inmutabilidad: si se elimina la evaluación o cambia el nombre del estudiante, el log conserva la información original |
| D27 | Validación de secretaría | Modelo `RegistroCalificacionParalelo` con estados | Separar el estado del registro (borrador/completo/validado) de las calificaciones individuales. Un paralelo tiene UN registro de calificaciones con UN estado |
| D28 | Escalamiento de recalificación | Campo `numero_solicitud` en `Solicitud` + lógica en servicio | 1ra solicitud → docente directo. 2da+ → secretaría primero. Cálculo automático basado en solicitudes previas del mismo estudiante para la misma evaluación |
| D29 | Archivos adjuntos | `FileField` con `upload_to="solicitudes/%Y/%m/"` | Simple, nativo de Django. Configurar `MEDIA_ROOT` y servir con nginx en producción |
| D30 | Promedio ponderado vs simple | Promedio ponderado usando campo `peso` de `Evaluacion` | Ya modelado en Sprint 0. Cada evaluación tiene su peso %. La suma debe ser 100% |
| D31 | Visibilidad de notas al estudiante | Solo cuando `RegistroCalificacionParalelo.estado == VALIDADO` | Evitar que el estudiante vea notas provisionales que pueden cambiar |
| D32 | Trazabilidad de solicitudes | Modelo `HistorialSolicitud` | Cada cambio de estado queda registrado con usuario, comentario y timestamp |
| D33 | Servicio de cálculo de promedios | Servicio de dominio puro (sin ORM) | Testeable, reutilizable, cumple DDD. Recibe lista de (nota, peso) y retorna Decimal |

---

## 9. Configuración técnica — Sprint 3

### 9.1 Nuevas URLs

```python
# apps/calificaciones/presentation/urls.py
urlpatterns = [
    path("paralelo/<int:paralelo_id>/registrar/", RegistrarCalificacionesView, name="registrar_calificaciones"),
    path("paralelo/<int:paralelo_id>/enviar-validacion/", EnviarValidacionView, name="enviar_validacion"),
    path("mi-libreta/", MiLibretaView, name="mi_libreta"),
    path("auditoria/", AuditoriaCalificacionesView, name="auditoria_calificaciones"),
]

# apps/solicitudes/presentation/urls.py
urlpatterns = [
    path("recalificacion/nueva/", NuevaSolicitudRecalificacionView, name="nueva_recalificacion"),
    path("justificacion/nueva/", NuevaSolicitudJustificacionView, name="nueva_justificacion"),
    path("mis-solicitudes/", MisSolicitudesView, name="mis_solicitudes"),
    path("<int:solicitud_id>/resolver/", ResolverSolicitudView, name="resolver_solicitud"),
    path("pendientes/", SolicitudesPendientesView, name="solicitudes_pendientes"),
]

# apps/secretaria/presentation/urls.py (o dentro de calificaciones)
urlpatterns = [
    path("calificaciones/pendientes/", CalificacionesPendientesValidacionView, name="calificaciones_pendientes"),
    path("calificaciones/<int:registro_id>/validar/", ValidarCalificacionesView, name="validar_calificaciones"),
    path("solicitudes/", SolicitudesSecretariaView, name="solicitudes_secretaria"),
]
```

### 9.2 Configuración de media files

```python
# config/settings/base.py — agregar
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

# Validación de archivos
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_UPLOAD_EXTENSIONS = [".pdf", ".jpg", ".jpeg", ".png"]
```

```python
# config/urls.py — agregar para desarrollo
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

### 9.3 Fixtures/Seeds para demo

Management command con:
- 6 evaluaciones por paralelo (4 parciales + proyecto + examen) con pesos sumando 100%.
- Calificaciones parciales para 5 estudiantes.
- 1 paralelo con registro validado, 1 en borrador.
- 2 solicitudes de recalificación (1 aprobada, 1 pendiente).
- Logs de auditoría de ejemplo.

---

## 10. Riesgos del Sprint 3

| # | Riesgo | Probabilidad | Impacto | Mitigación |
|---|--------|-------------|---------|-----------|
| R1 | Consultas pendientes P1–P5 no se resuelven a tiempo | Alta | Alto | Implementar con valores por defecto (documentados). Ajustar post-respuesta |
| R2 | Complejidad del flujo de recalificación multinivel | Media | Alto | Implementar flujo simple (1ra solicitud) primero. Escalamiento a secretaría como segunda iteración |
| R3 | Sprint de 26 puntos con 2 devs en 10 días | Media | Alto | HU18 y HU19 son las más complejas — priorizarlas si hay retraso. Buffer en día 10 |
| R4 | Configuración de media files para archivos adjuntos | Baja | Medio | Configurar `MEDIA_ROOT` el Día 1. Validar extensiones y tamaño en formulario |
| R5 | Cálculo de promedio ponderado con notas parciales (no todas cargadas) | Media | Medio | Calcular solo con notas existentes, mostrar "parcial" explícitamente. No dividir entre evaluaciones sin nota |
| R6 | Inmutabilidad de logs depende de disciplina del servicio (no enforced en DB) | Baja | Alto | No exponer endpoints de update/delete. Prohibir en servicio. Auditar en code review |
| R7 | Email de notificaciones puede saturar en flujos complejos | Baja | Bajo | Limitar a 1 email por cambio de estado. No enviar duplicados |

---

## 11. Métricas de éxito del Sprint 3

| # | Métrica | Criterio |
|---|---------|----------|
| M1 | HUs completadas | 7/7 (HU13–HU19) |
| M2 | Tests pasando | Suite completa verde + nuevos tests del sprint |
| M3 | Flujo E2E funcional — Calificaciones | Registrar notas → enviar validación → secretaría aprueba → estudiante ve libreta |
| M4 | Flujo E2E funcional — Recalificación | Estudiante reclama → docente resuelve → log auditoría → estudiante notificado |
| M5 | Cobertura dominio | ≥ 70% |
| M6 | PRs mergeados | Todos los feature branches mergeados a develop vía PR |
| M7 | Logs inmutables | Cada cambio de calificación tiene log con antes/después |
| M8 | Responsive | Todas las vistas nuevas responsive (mobile + desktop) |
