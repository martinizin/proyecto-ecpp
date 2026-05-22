# PRD — Sprint 4: Plataforma Web Académica ECPPP

| Campo | Valor |
|-------|-------|
| **Título** | Product Requirements Document — Sprint 4 |
| **Proyecto** | Plataforma Web Académica ECPPP |
| **Versión** | 0.5.0 |
| **Fecha** | Mayo 2026 |
| **Sprint** | S4 (Incremento 4) |
| **Rango de fechas** | 25/05/2026 – 06/06/2026 (2 semanas, ~10 días hábiles) |
| **Equipo** | 2 desarrolladores fullstack — Martín Jiménez, Junior Espín |
| **Metodología** | Scrum + Git Flow (`develop` → `feature/*` → PR) |
| **Estado** | Draft |

---

## 1. Resumen ejecutivo del Sprint 4

### 1.1 Objetivo del Sprint

Implementar tres pilares funcionales: (1) mejora del sistema de justificaciones con categorización de certificados y visualización segura de documentos, (2) dashboard de rendimiento académico para inspectores con métricas comparativas, y (3) asistente conversacional con IA (chatbot copilot) para consultas académicas de estudiantes y docentes. Este sprint construye sobre la gestión de calificaciones (Sprint 3), solicitudes con archivos adjuntos (Sprint 3) y la autenticación multirrol (Sprint 1).

### 1.2 Resumen de funcionalidades

| # | Funcionalidad | Descripción |
|---|---------------|-------------|
| 1 | Carga de certificados médicos/laborales | Categorización de justificaciones, multi-archivo, metadatos de certificados |
| 2 | Resolución de justificaciones por Inspector | UI dedicada con dashboard, filtros, bulk actions y deadline tracking |
| 3 | Asistente Copilot ECPP | Chatbot conversacional para consultas académicas (notas, asistencia, horarios) |
| 4 | Dashboard de rendimiento por curso | Métricas comparativas: promedios, asistencia, aprobación por paralelo con gráficos |
| 5 | Integración del motor IA | RAG con documentos institucionales, base de conocimiento administrable |
| 6 | Módulo de visualización de documentos | Visor seguro de PDFs e imágenes con control de acceso y watermark |

### 1.3 Pendientes ECPPP por consultar

> **IMPORTANTE:** Estas consultas deben resolverse el Día 1 del sprint antes de implementar. Afectan directamente el diseño.

| # | Consulta pendiente | Impacto en implementación | Valor por defecto si no se resuelve |
|---|-------------------|---------------------------|--------------------------------------|
| P1 | ¿Cuántos días hábiles tiene el estudiante para presentar justificación después de la inasistencia? | Define deadline de creación de solicitud y validación en formulario | 3 días hábiles desde la fecha de inasistencia |
| P2 | ¿El inspector tiene un plazo máximo para resolver justificaciones? | Define alertas y escalamiento en dashboard de inspector | 5 días hábiles desde la fecha de creación de la solicitud |
| P3 | ¿Qué información académica puede consultar el chatbot? (¿Solo del estudiante autenticado o datos públicos del curso?) | Define permisos del endpoint de IA y scope de respuestas | Solo datos del estudiante autenticado + info pública de materias/horarios |
| P4 | ¿Existe un catálogo institucional de tipos de certificados válidos? | Define si los tipos son fijos o configurables por admin | Tipos fijos: médico, laboral, calamidad doméstica |
| P5 | ¿Los documentos adjuntos pueden descargarse o solo visualizarse en línea? | Afecta política de seguridad del visor | Solo visualización en línea (no descarga directa por defecto) |

### 1.4 Definition of Done del Sprint 4

- [ ] Estudiante puede subir justificación con categoría (médico/laboral/calamidad), múltiples archivos y metadatos del certificado.
- [ ] Inspector tiene dashboard dedicado para gestionar justificaciones con filtros, búsqueda y acciones masivas.
- [ ] Inspector puede aprobar/rechazar justificaciones con preview de documentos adjuntos.
- [ ] Deadline de resolución configurable y visible en dashboard de inspector.
- [ ] Chatbot funcional: estudiante/docente puede consultar notas, asistencia, horarios en lenguaje natural.
- [ ] Conversaciones del chatbot persisten por sesión.
- [ ] Dashboard de rendimiento: inspector ve promedios, asistencia%, aprobación/reprobación por paralelo con gráficos.
- [ ] Filtros por período, materia y paralelo en dashboard de rendimiento.
- [ ] Admin puede gestionar documentos de base de conocimiento para el chatbot (RAG).
- [ ] Visor seguro de documentos: PDF inline (pdf.js), imágenes con zoom, watermark.
- [ ] Control de acceso en visor: solo roles autorizados pueden ver documentos.
- [ ] Log de acceso a documentos (auditoría).
- [ ] Tests con cobertura ≥ 70% en capa de dominio.
- [ ] Pipeline CI en verde.

---

## 2. Alcance del Sprint 4

### 2.1 Incluye

| Aspecto | Detalle |
|---------|---------|
| Justificaciones mejoradas | Categorización (médico, laboral, calamidad), multi-archivo, metadatos de certificado (institución, fecha, número) |
| Dashboard inspector | Lista filtrable de justificaciones pendientes, estadísticas, acciones masivas, deadline tracking |
| Chatbot copilot | Widget conversacional, endpoint de procesamiento NL, integración OpenAI, historial de sesión |
| Dashboard rendimiento | Gráficos Chart.js: promedios por paralelo, % asistencia, tasas aprobación, tendencias |
| Motor IA / RAG | Carga de documentos institucionales, vectorización, contexto académico para chatbot |
| Visor de documentos | PDF.js inline, visor de imágenes con zoom, watermark overlay, control de acceso por rol |

### 2.2 Excluye

| Aspecto | Razón |
|---------|-------|
| Reportes PDF/Excel exportables | Sprint 5 — se priorizó visualización interactiva |
| Notificaciones push (WebSocket/SSE) | Sprint 5 — se mantiene email como canal principal |
| Integración con sistema de pagos | Sprint 5 — fuera del scope académico inmediato |
| Analítica predictiva de deserción | Sprint 5 — requiere datos históricos y modelos ML más complejos |
| Speech-to-text en chatbot | Fuera de alcance — solo texto |
| Generación automática de documentos por IA | Fuera de alcance — el chatbot solo consulta, no genera certificados |

---

## 3. Backlog del Sprint 4

| ID | Nombre | Puntos | Responsable | Día(s) objetivo |
|----|--------|--------|-------------|-----------------|
| HU20 | Justificación de inasistencias — Carga de certificados médicos o laborales | 3 | Martín | Día 1–2 |
| HU21 | Resolución de justificaciones por Inspector | 3 | Junior | Día 2–3 |
| HU22 | Asistente Copilot ECPP | 5 | Martín | Día 3–6 |
| HU23 | Dashboard de rendimiento por curso | 3 | Junior | Día 4–5 |
| HU24 | Integración del motor IA | 3 | Martín | Día 6–8 |
| HU25 | Módulo de visualización de documentos | 3 | Junior | Día 6–8 |
| **Total** | | **20** | | |

---

## 4. Detalle por HU

### 4.1 HU20 — Justificación de inasistencias — Carga de certificados médicos o laborales

**Propósito:** Mejorar el formulario de justificación de inasistencia existente (Sprint 3) para soportar categorización de certificados, carga de múltiples archivos y metadatos del documento de respaldo.

**Reglas de negocio:**
- Tipos de certificado: `medico` (certificado médico), `laboral` (certificado de trabajo/permiso), `calamidad` (calamidad doméstica).
- Cada tipo tiene campos de metadatos específicos:
  - **Médico:** institución emisora, nombre del médico, fecha del certificado, número de certificado, días de reposo.
  - **Laboral:** empresa/institución, cargo, fecha del permiso, número de documento.
  - **Calamidad:** descripción del evento, fecha del evento, relación familiar (si aplica).
- Se permiten hasta 3 archivos adjuntos por solicitud (PDF/imagen, max 5MB cada uno).
- Validación: fecha del certificado no puede ser posterior a la fecha de la solicitud.
- Validación: la justificación debe crearse dentro de los 3 días hábiles posteriores a la inasistencia (configurable).
- El tipo de certificado determina qué campos son obligatorios en el formulario.

**Modelo — Metadatos de certificado:**

```python
# apps/solicitudes/infrastructure/models.py — nuevo modelo
class CertificadoJustificacion(models.Model):
    """Metadata for justification certificates attached to a solicitud."""

    class TipoCertificado(models.TextChoices):
        MEDICO = "medico", "Certificado Médico"
        LABORAL = "laboral", "Certificado Laboral"
        CALAMIDAD = "calamidad", "Calamidad Doméstica"

    solicitud = models.OneToOneField(
        "solicitudes.Solicitud", on_delete=models.CASCADE,
        related_name="certificado"
    )
    tipo = models.CharField(max_length=15, choices=TipoCertificado.choices)
    institucion_emisora = models.CharField(max_length=200, blank=True)
    fecha_certificado = models.DateField()
    numero_documento = models.CharField(max_length=100, blank=True)

    # Específicos médico
    nombre_medico = models.CharField(max_length=200, blank=True)
    dias_reposo = models.PositiveIntegerField(null=True, blank=True)

    # Específicos laboral
    cargo = models.CharField(max_length=200, blank=True)

    # Específicos calamidad
    descripcion_evento = models.TextField(blank=True)
    relacion_familiar = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Certificado de Justificación"
        verbose_name_plural = "Certificados de Justificación"

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.solicitud}"
```

**Modelo — Archivos adjuntos múltiples:**

```python
# apps/solicitudes/infrastructure/models.py — nuevo modelo
class ArchivoSolicitud(models.Model):
    """Multiple file attachments for a solicitud."""

    solicitud = models.ForeignKey(
        "solicitudes.Solicitud", on_delete=models.CASCADE,
        related_name="archivos"
    )
    archivo = models.FileField(upload_to="solicitudes/%Y/%m/")
    nombre_original = models.CharField(max_length=255)
    tipo_mime = models.CharField(max_length=100)
    tamanio_bytes = models.PositiveIntegerField()
    subido_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Archivo de Solicitud"
        verbose_name_plural = "Archivos de Solicitud"
        constraints = [
            models.CheckConstraint(
                check=models.Q(tamanio_bytes__lte=5 * 1024 * 1024),
                name="archivo_max_5mb",
            )
        ]

    def __str__(self):
        return self.nombre_original
```

**Servicio de dominio — Validación de certificados:**

```python
# apps/solicitudes/domain/services.py
from datetime import date, timedelta

class CertificadoValidationService:
    """Validates certificate metadata based on type."""

    CAMPOS_OBLIGATORIOS = {
        "medico": ["institucion_emisora", "nombre_medico", "fecha_certificado", "dias_reposo"],
        "laboral": ["institucion_emisora", "cargo", "fecha_certificado", "numero_documento"],
        "calamidad": ["descripcion_evento", "fecha_certificado"],
    }

    MAX_ARCHIVOS = 3
    MAX_TAMANIO = 5 * 1024 * 1024  # 5MB
    EXTENSIONES_VALIDAS = [".pdf", ".jpg", ".jpeg", ".png"]
    DIAS_LIMITE_JUSTIFICACION = 3

    @classmethod
    def validar_campos_obligatorios(cls, tipo: str, datos: dict) -> list[str]:
        """Returns list of missing required fields for the certificate type."""
        campos = cls.CAMPOS_OBLIGATORIOS.get(tipo, [])
        return [campo for campo in campos if not datos.get(campo)]

    @classmethod
    def validar_fecha_certificado(cls, fecha_certificado: date, fecha_solicitud: date) -> bool:
        """Certificate date cannot be after solicitud date."""
        return fecha_certificado <= fecha_solicitud

    @classmethod
    def validar_plazo_justificacion(cls, fecha_inasistencia: date, fecha_solicitud: date) -> bool:
        """Justification must be submitted within N business days of absence."""
        dias_habiles = 0
        current = fecha_inasistencia
        while current < fecha_solicitud:
            current += timedelta(days=1)
            if current.weekday() < 5:  # Monday-Friday
                dias_habiles += 1
        return dias_habiles <= cls.DIAS_LIMITE_JUSTIFICACION

    @classmethod
    def validar_archivo(cls, nombre: str, tamanio: int) -> list[str]:
        """Validate file extension and size."""
        errores = []
        ext = "." + nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""
        if ext not in cls.EXTENSIONES_VALIDAS:
            errores.append(f"Extensión '{ext}' no permitida. Válidas: {cls.EXTENSIONES_VALIDAS}")
        if tamanio > cls.MAX_TAMANIO:
            errores.append(f"Archivo excede el límite de 5MB ({tamanio / 1024 / 1024:.1f}MB)")
        return errores
```

**Servicio de aplicación:**

```python
# apps/solicitudes/application/services.py
class JustificacionCertificadoAppService:
    """Orchestrates justification submission with certificate metadata."""

    def __init__(self):
        self.validation_service = CertificadoValidationService()

    def crear_justificacion_con_certificado(
        self, estudiante, asistencia, tipo_certificado, metadatos, archivos, descripcion
    ):
        # Validate deadline
        if not self.validation_service.validar_plazo_justificacion(
            asistencia.fecha, date.today()
        ):
            raise PlazoJustificacionExpiradoError(asistencia.fecha)

        # Validate required fields
        campos_faltantes = self.validation_service.validar_campos_obligatorios(
            tipo_certificado, metadatos
        )
        if campos_faltantes:
            raise CamposObligatoriosFaltantesError(campos_faltantes)

        # Validate certificate date
        if not self.validation_service.validar_fecha_certificado(
            metadatos["fecha_certificado"], date.today()
        ):
            raise FechaCertificadoInvalidaError()

        # Validate files
        if len(archivos) > CertificadoValidationService.MAX_ARCHIVOS:
            raise MaximoArchivosExcedidoError(len(archivos))

        for archivo in archivos:
            errores = self.validation_service.validar_archivo(archivo.name, archivo.size)
            if errores:
                raise ArchivoInvalidoError(archivo.name, errores)

        # Create solicitud
        solicitud = Solicitud.objects.create(
            tipo=Solicitud.TipoSolicitud.JUSTIFICACION,
            estudiante=estudiante,
            asistencia=asistencia,
            descripcion=descripcion,
            estado=Solicitud.EstadoSolicitud.PENDIENTE,
        )

        # Create certificate metadata
        CertificadoJustificacion.objects.create(
            solicitud=solicitud,
            tipo=tipo_certificado,
            **metadatos,
        )

        # Create file attachments
        for archivo in archivos:
            ArchivoSolicitud.objects.create(
                solicitud=solicitud,
                archivo=archivo,
                nombre_original=archivo.name,
                tipo_mime=archivo.content_type,
                tamanio_bytes=archivo.size,
            )

        # Notify inspector
        NotificacionService.notificar_nueva_justificacion(solicitud)

        return solicitud
```

**Criterios de aceptación:**
- [ ] Modelo `CertificadoJustificacion` creado con migración.
- [ ] Modelo `ArchivoSolicitud` creado con migración (reemplaza uso directo de `archivo_adjunto` para nuevas solicitudes).
- [ ] Formulario de justificación muestra campos dinámicos según tipo de certificado (Alpine.js).
- [ ] Validación de campos obligatorios por tipo (médico requiere institución+médico+días, laboral requiere empresa+cargo, etc).
- [ ] Multi-upload: hasta 3 archivos por solicitud (PDF/imagen, max 5MB c/u).
- [ ] Validación de plazo: no permite justificación si pasaron más de 3 días hábiles.
- [ ] Fecha del certificado no posterior a fecha de solicitud.
- [ ] Servicio de dominio `CertificadoValidationService` con tests unitarios.
- [ ] Servicio de aplicación orquesta creación de solicitud + certificado + archivos.
- [ ] Tests: validaciones de campos por tipo, plazo, archivos.

**Branch:** `feature/HU20-certificados-justificacion`

---

### 4.2 HU21 — Resolución de justificaciones por Inspector

**Propósito:** Crear una interfaz dedicada para que el inspector gestione las justificaciones de inasistencia con herramientas de filtrado, acciones masivas, preview de documentos y tracking de deadlines.

**Reglas de negocio:**
- El inspector ve TODAS las justificaciones de TODOS los paralelos que supervisa.
- Deadline por defecto: 5 días hábiles desde la fecha de creación (configurable).
- Alertas visuales: solicitudes próximas a vencer (≤2 días), vencidas (>deadline).
- Acciones masivas: aprobar/rechazar múltiples solicitudes seleccionadas.
- Al aprobar: la asistencia cambia de `AUSENTE` a `JUSTIFICADO` (reutiliza lógica Sprint 3).
- Estadísticas en panel lateral: total pendientes, aprobadas hoy, rechazadas hoy, promedio de resolución.
- Filtros: por estado, tipo de certificado, paralelo, fecha de creación, fecha de vencimiento.

**Vista principal — Dashboard de justificaciones:**

```python
# apps/solicitudes/presentation/views.py
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, View
from django.db.models import Q, Count, Avg, F
from django.utils import timezone
from datetime import timedelta

class InspectorJustificacionesDashboardView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Dashboard for inspector to manage justification requests."""

    template_name = "solicitudes/inspector/dashboard.html"
    context_object_name = "solicitudes"
    paginate_by = 20

    def test_func(self):
        return self.request.user.rol == "inspector"

    def get_queryset(self):
        qs = Solicitud.objects.filter(
            tipo=Solicitud.TipoSolicitud.JUSTIFICACION
        ).select_related(
            "estudiante", "asistencia", "certificado"
        ).prefetch_related("archivos")

        # Filters
        estado = self.request.GET.get("estado")
        if estado:
            qs = qs.filter(estado=estado)

        tipo_cert = self.request.GET.get("tipo_certificado")
        if tipo_cert:
            qs = qs.filter(certificado__tipo=tipo_cert)

        paralelo = self.request.GET.get("paralelo")
        if paralelo:
            qs = qs.filter(asistencia__paralelo_id=paralelo)

        busqueda = self.request.GET.get("q")
        if busqueda:
            qs = qs.filter(
                Q(estudiante__first_name__icontains=busqueda) |
                Q(estudiante__last_name__icontains=busqueda) |
                Q(estudiante__cedula__icontains=busqueda)
            )

        return qs.order_by("-fecha_creacion")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoy = timezone.now().date()
        deadline_dias = ConfiguracionJustificacion.get_deadline_dias()

        all_justificaciones = Solicitud.objects.filter(
            tipo=Solicitud.TipoSolicitud.JUSTIFICACION
        )

        context["stats"] = {
            "pendientes": all_justificaciones.filter(
                estado=Solicitud.EstadoSolicitud.PENDIENTE
            ).count(),
            "aprobadas_hoy": all_justificaciones.filter(
                estado=Solicitud.EstadoSolicitud.APROBADA,
                fecha_resolucion__date=hoy,
            ).count(),
            "rechazadas_hoy": all_justificaciones.filter(
                estado=Solicitud.EstadoSolicitud.RECHAZADA,
                fecha_resolucion__date=hoy,
            ).count(),
            "vencidas": all_justificaciones.filter(
                estado=Solicitud.EstadoSolicitud.PENDIENTE,
                fecha_creacion__date__lte=hoy - timedelta(days=deadline_dias),
            ).count(),
        }
        context["deadline_dias"] = deadline_dias
        return context


class InspectorResolverJustificacionView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Resolve a single justification (approve/reject)."""

    def test_func(self):
        return self.request.user.rol == "inspector"

    def post(self, request, solicitud_id):
        solicitud = get_object_or_404(Solicitud, pk=solicitud_id)
        accion = request.POST.get("accion")  # "aprobar" or "rechazar"
        comentario = request.POST.get("comentario", "")

        service = FlujoAprobacionAppService()

        if accion == "aprobar":
            service.aprobar_justificacion(solicitud, request.user, comentario)
        elif accion == "rechazar":
            if not comentario:
                messages.error(request, "El comentario es obligatorio al rechazar.")
                return redirect("inspector_justificacion_detalle", pk=solicitud_id)
            service.rechazar_justificacion(solicitud, request.user, comentario)

        return redirect("inspector_justificaciones_dashboard")


class InspectorBulkActionView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Bulk approve/reject justifications."""

    def test_func(self):
        return self.request.user.rol == "inspector"

    def post(self, request):
        ids = request.POST.getlist("solicitud_ids")
        accion = request.POST.get("accion_masiva")
        comentario = request.POST.get("comentario_masivo", "Resolución masiva")

        service = FlujoAprobacionAppService()
        solicitudes = Solicitud.objects.filter(
            pk__in=ids,
            tipo=Solicitud.TipoSolicitud.JUSTIFICACION,
            estado=Solicitud.EstadoSolicitud.PENDIENTE,
        )

        for solicitud in solicitudes:
            if accion == "aprobar":
                service.aprobar_justificacion(solicitud, request.user, comentario)
            elif accion == "rechazar":
                service.rechazar_justificacion(solicitud, request.user, comentario)

        messages.success(request, f"{solicitudes.count()} solicitudes procesadas.")
        return redirect("inspector_justificaciones_dashboard")
```

**Modelo de configuración:**

```python
# apps/solicitudes/infrastructure/models.py
class ConfiguracionJustificacion(models.Model):
    """Singleton configuration for justification deadlines."""

    deadline_dias = models.PositiveIntegerField(
        default=5,
        help_text="Días hábiles para resolver una justificación"
    )
    alerta_dias = models.PositiveIntegerField(
        default=2,
        help_text="Días antes del deadline para mostrar alerta"
    )

    class Meta:
        verbose_name = "Configuración de Justificaciones"

    @classmethod
    def get_deadline_dias(cls):
        config, _ = cls.objects.get_or_create(pk=1)
        return config.deadline_dias

    @classmethod
    def get_alerta_dias(cls):
        config, _ = cls.objects.get_or_create(pk=1)
        return config.alerta_dias
```

**Criterios de aceptación:**
- [ ] Dashboard de inspector con lista de justificaciones paginada (20/página).
- [ ] Filtros: estado, tipo de certificado, paralelo, búsqueda por nombre/cédula.
- [ ] Panel de estadísticas: pendientes, aprobadas hoy, rechazadas hoy, vencidas.
- [ ] Indicadores de deadline: normal (verde), próximo a vencer (amarillo ≤2 días), vencido (rojo).
- [ ] Detalle de solicitud con preview de documentos adjuntos (integra HU25).
- [ ] Aprobación → asistencia cambia a `JUSTIFICADO`, email al estudiante.
- [ ] Rechazo → comentario obligatorio, email al estudiante.
- [ ] Acciones masivas: seleccionar múltiples + aprobar/rechazar.
- [ ] Modelo `ConfiguracionJustificacion` con deadline configurable desde Django Admin.
- [ ] `HistorialSolicitud` registra cada acción del inspector.
- [ ] Tests de vista, filtros, bulk actions.

**Branch:** `feature/HU21-resolucion-inspector`

---

### 4.3 HU22 — Asistente Copilot ECPP

**Propósito:** Implementar un chatbot conversacional integrado en la plataforma que permita a estudiantes y docentes consultar información académica (calificaciones, asistencia, horarios) mediante lenguaje natural.

**Reglas de negocio:**
- Accesible para roles: `estudiante`, `docente`.
- El chatbot responde SOLO con datos del usuario autenticado (estudiante ve sus notas, docente ve sus paralelos).
- No puede modificar datos — es de solo lectura/consulta.
- Historial de conversación persistido por sesión (máximo 50 mensajes por sesión).
- Sesiones expiran después de 24 horas de inactividad.
- Respuestas limitadas a 500 tokens.
- Rate limiting: máximo 30 mensajes por hora por usuario.

**Estructura de la app `copilot`:**

```
apps/copilot/
├── __init__.py
├── apps.py
├── domain/
│   ├── __init__.py
│   ├── value_objects.py
│   ├── services.py
│   └── exceptions.py
├── application/
│   ├── __init__.py
│   └── services.py
├── infrastructure/
│   ├── __init__.py
│   ├── models.py
│   ├── repositories.py
│   └── openai_client.py
└── presentation/
    ├── __init__.py
    ├── views.py
    ├── urls.py
    └── serializers.py
```

**Modelos — Conversación y mensajes:**

```python
# apps/copilot/infrastructure/models.py
import uuid
from django.db import models

class ConversacionCopilot(models.Model):
    """A chat session between a user and the copilot."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.CASCADE,
        related_name="conversaciones_copilot"
    )
    titulo = models.CharField(max_length=200, blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    ultima_actividad = models.DateTimeField(auto_now=True)
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Conversación Copilot"
        verbose_name_plural = "Conversaciones Copilot"
        ordering = ["-ultima_actividad"]
        indexes = [
            models.Index(fields=["usuario", "-ultima_actividad"]),
        ]

    def __str__(self):
        return f"{self.usuario} — {self.titulo or 'Sin título'}"


class MensajeCopilot(models.Model):
    """A single message in a copilot conversation."""

    class Rol(models.TextChoices):
        USER = "user", "Usuario"
        ASSISTANT = "assistant", "Asistente"
        SYSTEM = "system", "Sistema"

    conversacion = models.ForeignKey(
        ConversacionCopilot, on_delete=models.CASCADE,
        related_name="mensajes"
    )
    rol = models.CharField(max_length=10, choices=Rol.choices)
    contenido = models.TextField()
    tokens_usados = models.PositiveIntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Mensaje Copilot"
        verbose_name_plural = "Mensajes Copilot"
        ordering = ["timestamp"]

    def __str__(self):
        return f"[{self.rol}] {self.contenido[:50]}"
```

**Servicio de dominio — Procesamiento de consultas:**

```python
# apps/copilot/domain/services.py
from dataclasses import dataclass

@dataclass(frozen=True)
class ConsultaAcademica:
    """Value object representing a parsed academic query."""
    tipo: str  # "calificaciones", "asistencia", "horario", "general"
    entidad: str  # "materia", "paralelo", "periodo"
    parametros: dict

class QueryClassifierService:
    """Classifies natural language queries into academic data types."""

    KEYWORDS_CALIFICACIONES = ["nota", "calificación", "promedio", "parcial", "examen", "libreta"]
    KEYWORDS_ASISTENCIA = ["asistencia", "falta", "ausencia", "justificación", "inasistencia"]
    KEYWORDS_HORARIO = ["horario", "clase", "hora", "día", "aula", "salón"]

    @classmethod
    def clasificar(cls, query: str) -> str:
        """Classify query intent based on keywords."""
        query_lower = query.lower()
        if any(kw in query_lower for kw in cls.KEYWORDS_CALIFICACIONES):
            return "calificaciones"
        if any(kw in query_lower for kw in cls.KEYWORDS_ASISTENCIA):
            return "asistencia"
        if any(kw in query_lower for kw in cls.KEYWORDS_HORARIO):
            return "horario"
        return "general"
```

**Servicio de aplicación — Orquestación:**

```python
# apps/copilot/application/services.py
from django.utils import timezone
from datetime import timedelta

class CopilotAppService:
    """Orchestrates chat interactions with the copilot."""

    MAX_MENSAJES_POR_SESION = 50
    MAX_MENSAJES_POR_HORA = 30
    SESION_TIMEOUT_HORAS = 24
    MAX_TOKENS_RESPUESTA = 500

    def __init__(self, openai_client, context_service, academic_data_service):
        self.openai_client = openai_client
        self.context_service = context_service
        self.academic_data_service = academic_data_service

    def obtener_o_crear_conversacion(self, usuario):
        """Get active conversation or create a new one."""
        timeout = timezone.now() - timedelta(hours=self.SESION_TIMEOUT_HORAS)
        conversacion = ConversacionCopilot.objects.filter(
            usuario=usuario,
            activa=True,
            ultima_actividad__gte=timeout,
        ).first()

        if not conversacion:
            conversacion = ConversacionCopilot.objects.create(usuario=usuario)

        return conversacion

    def procesar_mensaje(self, usuario, contenido: str) -> str:
        """Process a user message and return assistant response."""
        # Rate limiting
        if self._excede_rate_limit(usuario):
            raise RateLimitExcedidoError()

        conversacion = self.obtener_o_crear_conversacion(usuario)

        # Check session message limit
        msg_count = conversacion.mensajes.count()
        if msg_count >= self.MAX_MENSAJES_POR_SESION:
            raise SesionLlenaError()

        # Save user message
        MensajeCopilot.objects.create(
            conversacion=conversacion,
            rol=MensajeCopilot.Rol.USER,
            contenido=contenido,
        )

        # Classify query and get relevant academic data
        tipo_consulta = QueryClassifierService.clasificar(contenido)
        datos_academicos = self.academic_data_service.obtener_datos(
            usuario=usuario,
            tipo=tipo_consulta,
        )

        # Build context with RAG documents
        contexto_rag = self.context_service.obtener_contexto_relevante(contenido)

        # Build messages for OpenAI
        historial = list(conversacion.mensajes.order_by("timestamp").values("rol", "contenido")[:20])
        system_prompt = self._construir_system_prompt(usuario, datos_academicos, contexto_rag)

        # Call OpenAI
        respuesta, tokens = self.openai_client.chat_completion(
            system_prompt=system_prompt,
            messages=historial,
            max_tokens=self.MAX_TOKENS_RESPUESTA,
        )

        # Save assistant response
        MensajeCopilot.objects.create(
            conversacion=conversacion,
            rol=MensajeCopilot.Rol.ASSISTANT,
            contenido=respuesta,
            tokens_usados=tokens,
        )

        return respuesta

    def _excede_rate_limit(self, usuario) -> bool:
        una_hora_atras = timezone.now() - timedelta(hours=1)
        count = MensajeCopilot.objects.filter(
            conversacion__usuario=usuario,
            rol=MensajeCopilot.Rol.USER,
            timestamp__gte=una_hora_atras,
        ).count()
        return count >= self.MAX_MENSAJES_POR_HORA

    def _construir_system_prompt(self, usuario, datos_academicos, contexto_rag):
        rol = usuario.rol
        return f"""Eres el asistente académico de la ECPPP (Escuela de Capacitación de Policía).
Rol del usuario: {rol}
Datos académicos del usuario:
{datos_academicos}

Contexto institucional:
{contexto_rag}

Reglas:
- Responde SOLO con información del usuario autenticado.
- NO puedes modificar datos, solo consultar.
- Responde en español, de forma concisa y amable.
- Si no tienes la información, indícalo claramente.
- No inventes datos.
"""
```

**Cliente OpenAI:**

```python
# apps/copilot/infrastructure/openai_client.py
from openai import OpenAI
from django.conf import settings

class OpenAIClient:
    """Wrapper for OpenAI API interactions."""

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.COPILOT_MODEL  # "gpt-4o-mini"

    def chat_completion(self, system_prompt: str, messages: list, max_tokens: int = 500):
        """Send chat completion request to OpenAI."""
        formatted_messages = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            formatted_messages.append({
                "role": msg["rol"],
                "content": msg["contenido"],
            })

        response = self.client.chat.completions.create(
            model=self.model,
            messages=formatted_messages,
            max_tokens=max_tokens,
            temperature=0.3,
        )

        content = response.choices[0].message.content
        tokens = response.usage.total_tokens
        return content, tokens
```

**Vista y endpoint:**

```python
# apps/copilot/presentation/views.py
from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
import json

class CopilotChatView(LoginRequiredMixin, UserPassesTestMixin, View):
    """API endpoint for copilot chat interactions."""

    def test_func(self):
        return self.request.user.rol in ["estudiante", "docente"]

    def post(self, request):
        try:
            body = json.loads(request.body)
            mensaje = body.get("mensaje", "").strip()

            if not mensaje:
                return JsonResponse({"error": "Mensaje vacío"}, status=400)

            if len(mensaje) > 1000:
                return JsonResponse({"error": "Mensaje demasiado largo (max 1000 caracteres)"}, status=400)

            service = CopilotAppService(
                openai_client=OpenAIClient(),
                context_service=ContextoRAGService(),
                academic_data_service=AcademicDataService(),
            )

            respuesta = service.procesar_mensaje(request.user, mensaje)

            return JsonResponse({
                "respuesta": respuesta,
                "timestamp": timezone.now().isoformat(),
            })

        except RateLimitExcedidoError:
            return JsonResponse(
                {"error": "Has excedido el límite de mensajes (30/hora). Intenta más tarde."},
                status=429,
            )
        except SesionLlenaError:
            return JsonResponse(
                {"error": "Sesión llena (50 mensajes). Inicia una nueva conversación."},
                status=400,
            )

    def get(self, request):
        """Get conversation history."""
        service = CopilotAppService(
            openai_client=OpenAIClient(),
            context_service=ContextoRAGService(),
            academic_data_service=AcademicDataService(),
        )
        conversacion = service.obtener_o_crear_conversacion(request.user)
        mensajes = conversacion.mensajes.order_by("timestamp").values(
            "rol", "contenido", "timestamp"
        )
        return JsonResponse({"mensajes": list(mensajes), "conversacion_id": str(conversacion.id)})


class CopilotNuevaConversacionView(LoginRequiredMixin, View):
    """Start a new conversation (close current)."""

    def post(self, request):
        ConversacionCopilot.objects.filter(
            usuario=request.user, activa=True
        ).update(activa=False)

        nueva = ConversacionCopilot.objects.create(usuario=request.user)
        return JsonResponse({"conversacion_id": str(nueva.id)})
```

**Criterios de aceptación:**
- [ ] App `copilot` creada con estructura DDD completa.
- [ ] Modelo `ConversacionCopilot` y `MensajeCopilot` con migraciones.
- [ ] Endpoint POST `/copilot/chat/` recibe mensaje y retorna respuesta de IA.
- [ ] Endpoint GET `/copilot/chat/` retorna historial de conversación activa.
- [ ] Endpoint POST `/copilot/nueva-conversacion/` cierra sesión actual y crea nueva.
- [ ] Rate limiting: máximo 30 mensajes/hora por usuario.
- [ ] Sesiones expiran tras 24h de inactividad.
- [ ] Máximo 50 mensajes por sesión.
- [ ] Clasificación de queries: calificaciones, asistencia, horario, general.
- [ ] Solo roles `estudiante` y `docente` pueden acceder.
- [ ] Widget de chat en template (Alpine.js) con animaciones de typing.
- [ ] Respuestas solo contienen datos del usuario autenticado.
- [ ] Tests: servicio de clasificación, rate limiting, session management.

**Branch:** `feature/HU22-copilot-chatbot`

---

### 4.4 HU23 — Dashboard de rendimiento por curso

**Propósito:** Proporcionar al inspector una vista comparativa del rendimiento académico por paralelo con métricas de calificaciones, asistencia y aprobación, visualizadas con gráficos interactivos.

**Reglas de negocio:**
- Accesible para rol `inspector` (y `secretaria` en modo lectura).
- Métricas por paralelo: promedio general de notas, % asistencia, tasa de aprobación, tasa de reprobación.
- Filtros: período académico, materia, paralelo específico.
- Gráficos: barras comparativas (promedios), líneas (tendencia por parcial), donut (aprobación/reprobación).
- Datos actualizados en tiempo real (recalculados al cargar la vista).

**Servicio de dominio — Cálculo de métricas:**

```python
# apps/academico/domain/services.py
from dataclasses import dataclass
from decimal import Decimal

@dataclass
class MetricasParalelo:
    """Aggregated metrics for a paralelo."""
    paralelo_id: int
    paralelo_nombre: str
    materia_nombre: str
    promedio_general: Decimal
    porcentaje_asistencia: Decimal
    tasa_aprobacion: Decimal
    tasa_reprobacion: Decimal
    total_estudiantes: int
    estudiantes_aprobados: int
    estudiantes_reprobados: int
    estudiantes_en_curso: int

class RendimientoAcademicoService:
    """Calculates academic performance metrics per paralelo."""

    @staticmethod
    def calcular_promedio_paralelo(calificaciones_paralelo: list) -> Decimal:
        """Average of all student final grades in a paralelo."""
        if not calificaciones_paralelo:
            return Decimal("0")
        total = sum(c.promedio for c in calificaciones_paralelo)
        return (total / len(calificaciones_paralelo)).quantize(Decimal("0.01"))

    @staticmethod
    def calcular_tasa_aprobacion(aprobados: int, total: int) -> Decimal:
        """Percentage of students with final grade >= 16."""
        if total == 0:
            return Decimal("0")
        return (Decimal(aprobados) / Decimal(total) * 100).quantize(Decimal("0.1"))

    @staticmethod
    def calcular_porcentaje_asistencia(presentes: int, total_clases: int) -> Decimal:
        """Overall attendance percentage for a paralelo."""
        if total_clases == 0:
            return Decimal("0")
        return (Decimal(presentes) / Decimal(total_clases) * 100).quantize(Decimal("0.1"))
```

**Servicio de aplicación:**

```python
# apps/academico/application/services.py
class DashboardRendimientoAppService:
    """Aggregates metrics for the performance dashboard."""

    def obtener_metricas_por_periodo(self, periodo_id, materia_id=None):
        """Get metrics for all paralelos in a period, optionally filtered by subject."""
        from apps.academico.infrastructure.models import Paralelo
        from apps.calificaciones.infrastructure.models import Calificacion, RegistroCalificacionParalelo
        from apps.asistencia.infrastructure.models import Asistencia

        paralelos = Paralelo.objects.filter(periodo_id=periodo_id)
        if materia_id:
            paralelos = paralelos.filter(materia_id=materia_id)

        metricas = []
        for paralelo in paralelos.select_related("materia"):
            # Calificaciones
            estudiantes = paralelo.matriculas.filter(activa=True).count()
            calificaciones = Calificacion.objects.filter(
                evaluacion__paralelo=paralelo
            )

            # Calculate per-student averages
            from django.db.models import Avg
            promedios_estudiantes = calificaciones.values(
                "estudiante"
            ).annotate(promedio=Avg("nota"))

            aprobados = promedios_estudiantes.filter(promedio__gte=16).count()
            reprobados = promedios_estudiantes.filter(promedio__lt=16).count()

            promedio_general = calificaciones.aggregate(
                avg=Avg("nota")
            )["avg"] or Decimal("0")

            # Asistencia
            total_registros = Asistencia.objects.filter(paralelo=paralelo).count()
            presentes = Asistencia.objects.filter(
                paralelo=paralelo,
                estado__in=["presente", "justificado"]
            ).count()

            porcentaje_asistencia = RendimientoAcademicoService.calcular_porcentaje_asistencia(
                presentes, total_registros
            )

            metricas.append(MetricasParalelo(
                paralelo_id=paralelo.id,
                paralelo_nombre=str(paralelo),
                materia_nombre=paralelo.materia.nombre,
                promedio_general=Decimal(str(promedio_general)).quantize(Decimal("0.01")),
                porcentaje_asistencia=porcentaje_asistencia,
                tasa_aprobacion=RendimientoAcademicoService.calcular_tasa_aprobacion(aprobados, estudiantes),
                tasa_reprobacion=RendimientoAcademicoService.calcular_tasa_aprobacion(reprobados, estudiantes),
                total_estudiantes=estudiantes,
                estudiantes_aprobados=aprobados,
                estudiantes_reprobados=reprobados,
                estudiantes_en_curso=estudiantes - aprobados - reprobados,
            ))

        return metricas

    def obtener_tendencia_parciales(self, paralelo_id):
        """Get grade trend across parciales for a paralelo."""
        from apps.calificaciones.infrastructure.models import Calificacion, Evaluacion
        from django.db.models import Avg

        evaluaciones = Evaluacion.objects.filter(
            paralelo_id=paralelo_id
        ).order_by("tipo")

        tendencia = []
        for evaluacion in evaluaciones:
            promedio = Calificacion.objects.filter(
                evaluacion=evaluacion
            ).aggregate(avg=Avg("nota"))["avg"]
            tendencia.append({
                "evaluacion": evaluacion.get_tipo_display(),
                "promedio": float(promedio) if promedio else None,
            })

        return tendencia
```

**Vista:**

```python
# apps/academico/presentation/views.py
class DashboardRendimientoView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Performance dashboard for inspector."""

    template_name = "academico/dashboard_rendimiento.html"

    def test_func(self):
        return self.request.user.rol in ["inspector", "secretaria"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = DashboardRendimientoAppService()

        periodo_id = self.request.GET.get("periodo")
        materia_id = self.request.GET.get("materia")

        if not periodo_id:
            from apps.academico.infrastructure.models import PeriodoAcademico
            periodo_activo = PeriodoAcademico.objects.filter(activo=True).first()
            periodo_id = periodo_activo.id if periodo_activo else None

        if periodo_id:
            context["metricas"] = service.obtener_metricas_por_periodo(periodo_id, materia_id)
        else:
            context["metricas"] = []

        context["periodos"] = PeriodoAcademico.objects.all()
        context["materias"] = Materia.objects.all()
        return context


class DashboardRendimientoAPIView(LoginRequiredMixin, View):
    """JSON API for chart data (consumed by Chart.js)."""

    def get(self, request):
        service = DashboardRendimientoAppService()
        periodo_id = request.GET.get("periodo")
        materia_id = request.GET.get("materia")
        paralelo_id = request.GET.get("paralelo")

        if paralelo_id:
            # Trend data for a specific paralelo
            tendencia = service.obtener_tendencia_parciales(paralelo_id)
            return JsonResponse({"tendencia": tendencia})

        if periodo_id:
            metricas = service.obtener_metricas_por_periodo(periodo_id, materia_id)
            data = {
                "labels": [m.paralelo_nombre for m in metricas],
                "promedios": [float(m.promedio_general) for m in metricas],
                "asistencia": [float(m.porcentaje_asistencia) for m in metricas],
                "aprobacion": [float(m.tasa_aprobacion) for m in metricas],
            }
            return JsonResponse(data)

        return JsonResponse({"error": "Período requerido"}, status=400)
```

**Criterios de aceptación:**
- [ ] Vista dashboard accesible para inspector y secretaría (lectura).
- [ ] Tabla resumen con métricas por paralelo: promedio, %asistencia, %aprobación.
- [ ] Gráfico de barras comparativo de promedios por paralelo (Chart.js).
- [ ] Gráfico de línea con tendencia por parcial para un paralelo seleccionado.
- [ ] Gráfico donut: distribución aprobados/reprobados/en curso.
- [ ] Filtros funcionales: período, materia, paralelo.
- [ ] Endpoint JSON `/academico/dashboard/api/` para alimentar gráficos (Chart.js fetch).
- [ ] Servicio de dominio `RendimientoAcademicoService` con cálculos puros.
- [ ] Servicio de aplicación con queries optimizadas (select_related, aggregate).
- [ ] Template responsive con cards de resumen + gráficos.
- [ ] Tests: cálculos de métricas, endpoint API.

**Branch:** `feature/HU23-dashboard-rendimiento`

---

### 4.5 HU24 — Integración del motor IA

**Propósito:** Configurar el contexto académico institucional para el asistente conversacional mediante RAG (Retrieval-Augmented Generation), permitiendo al admin gestionar documentos de base de conocimiento.

**Reglas de negocio:**
- Admin puede subir documentos institucionales: reglamento, malla curricular, políticas de asistencia, normativa de calificaciones.
- Los documentos se procesan (chunking) y se almacenan como embeddings vectoriales.
- Al recibir una consulta, se buscan los chunks más relevantes y se incluyen como contexto.
- Máximo 3 documentos de contexto por consulta (para no exceder tokens).
- Formatos soportados para documentos: PDF, TXT, DOCX.
- Admin puede activar/desactivar documentos sin eliminarlos.

**Modelos — Base de conocimiento:**

```python
# apps/copilot/infrastructure/models.py
class DocumentoConocimiento(models.Model):
    """Institutional document used as RAG context for the copilot."""

    class Categoria(models.TextChoices):
        REGLAMENTO = "reglamento", "Reglamento Institucional"
        MALLA = "malla", "Malla Curricular"
        POLITICA_ASISTENCIA = "politica_asistencia", "Política de Asistencia"
        POLITICA_CALIFICACIONES = "politica_calificaciones", "Política de Calificaciones"
        GENERAL = "general", "Información General"

    titulo = models.CharField(max_length=300)
    descripcion = models.TextField(blank=True)
    categoria = models.CharField(max_length=30, choices=Categoria.choices)
    archivo = models.FileField(upload_to="conocimiento/%Y/%m/")
    activo = models.BooleanField(default=True)
    subido_por = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.SET_NULL, null=True,
        related_name="documentos_conocimiento"
    )
    fecha_subida = models.DateTimeField(auto_now_add=True)
    fecha_procesado = models.DateTimeField(null=True, blank=True)
    procesado = models.BooleanField(default=False)
    total_chunks = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Documento de Conocimiento"
        verbose_name_plural = "Documentos de Conocimiento"
        ordering = ["-fecha_subida"]

    def __str__(self):
        return f"{self.titulo} ({self.get_categoria_display()})"


class ChunkDocumento(models.Model):
    """A text chunk from a processed document with its embedding."""

    documento = models.ForeignKey(
        DocumentoConocimiento, on_delete=models.CASCADE,
        related_name="chunks"
    )
    contenido = models.TextField()
    indice = models.PositiveIntegerField()  # chunk order in document
    embedding = models.JSONField(null=True, blank=True)  # vector as list[float]
    tokens = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Chunk de Documento"
        verbose_name_plural = "Chunks de Documentos"
        ordering = ["documento", "indice"]
        unique_together = [("documento", "indice")]

    def __str__(self):
        return f"{self.documento.titulo} — Chunk {self.indice}"
```

**Servicio de procesamiento de documentos:**

```python
# apps/copilot/application/services.py
class DocumentoProcesamientoService:
    """Processes uploaded documents into chunks with embeddings."""

    CHUNK_SIZE = 500  # tokens
    CHUNK_OVERLAP = 50  # tokens overlap between chunks

    def __init__(self, openai_client):
        self.openai_client = openai_client

    def procesar_documento(self, documento: DocumentoConocimiento):
        """Extract text, chunk it, and generate embeddings."""
        # Extract text based on file type
        texto = self._extraer_texto(documento.archivo)

        # Split into chunks
        chunks = self._dividir_en_chunks(texto)

        # Generate embeddings and save chunks
        for i, chunk_texto in enumerate(chunks):
            embedding = self.openai_client.generar_embedding(chunk_texto)
            ChunkDocumento.objects.create(
                documento=documento,
                contenido=chunk_texto,
                indice=i,
                embedding=embedding,
                tokens=self._contar_tokens(chunk_texto),
            )

        documento.procesado = True
        documento.fecha_procesado = timezone.now()
        documento.total_chunks = len(chunks)
        documento.save()

    def _extraer_texto(self, archivo) -> str:
        """Extract text from PDF, TXT, or DOCX."""
        nombre = archivo.name.lower()
        if nombre.endswith(".pdf"):
            return self._extraer_pdf(archivo)
        elif nombre.endswith(".txt"):
            return archivo.read().decode("utf-8")
        elif nombre.endswith(".docx"):
            return self._extraer_docx(archivo)
        raise FormatoNoSoportadoError(nombre)

    def _extraer_pdf(self, archivo) -> str:
        import PyPDF2
        reader = PyPDF2.PdfReader(archivo)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    def _extraer_docx(self, archivo) -> str:
        import docx
        doc = docx.Document(archivo)
        return "\n".join(para.text for para in doc.paragraphs)

    def _dividir_en_chunks(self, texto: str) -> list[str]:
        """Split text into overlapping chunks by approximate token count."""
        palabras = texto.split()
        chunks = []
        i = 0
        while i < len(palabras):
            chunk = " ".join(palabras[i:i + self.CHUNK_SIZE])
            chunks.append(chunk)
            i += self.CHUNK_SIZE - self.CHUNK_OVERLAP
        return chunks

    def _contar_tokens(self, texto: str) -> int:
        """Approximate token count (words * 1.3)."""
        return int(len(texto.split()) * 1.3)


class ContextoRAGService:
    """Retrieves relevant document chunks for a query."""

    MAX_CHUNKS_POR_CONSULTA = 3

    def __init__(self):
        self.openai_client = OpenAIClient()

    def obtener_contexto_relevante(self, query: str) -> str:
        """Find most relevant chunks for a query using cosine similarity."""
        query_embedding = self.openai_client.generar_embedding(query)

        # Get all active chunks
        chunks = ChunkDocumento.objects.filter(
            documento__activo=True,
            documento__procesado=True,
            embedding__isnull=False,
        )

        # Calculate similarity and rank
        scored_chunks = []
        for chunk in chunks:
            similarity = self._cosine_similarity(query_embedding, chunk.embedding)
            scored_chunks.append((similarity, chunk))

        # Sort by similarity descending, take top N
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        top_chunks = scored_chunks[:self.MAX_CHUNKS_POR_CONSULTA]

        # Combine context
        contexto = "\n\n---\n\n".join(
            f"[{chunk.documento.titulo}]\n{chunk.contenido}"
            for _, chunk in top_chunks
        )
        return contexto

    @staticmethod
    def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        mag_a = math.sqrt(sum(a * a for a in vec_a))
        mag_b = math.sqrt(sum(b * b for b in vec_b))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)
```

**Cliente OpenAI — Embeddings:**

```python
# apps/copilot/infrastructure/openai_client.py (extender)
class OpenAIClient:
    # ... (chat_completion from HU22)

    def generar_embedding(self, texto: str) -> list[float]:
        """Generate embedding vector for text."""
        response = self.client.embeddings.create(
            model=settings.COPILOT_EMBEDDING_MODEL,  # "text-embedding-3-small"
            input=texto,
        )
        return response.data[0].embedding
```

**Vista admin para gestión de documentos:**

```python
# apps/copilot/presentation/views.py
class GestionDocumentosConocimientoView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Admin view to manage knowledge base documents."""

    template_name = "copilot/admin/documentos.html"
    context_object_name = "documentos"

    def test_func(self):
        return self.request.user.is_staff or self.request.user.rol == "inspector"

    def get_queryset(self):
        return DocumentoConocimiento.objects.all()


class SubirDocumentoConocimientoView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Upload and process a new knowledge base document."""

    def test_func(self):
        return self.request.user.is_staff

    def post(self, request):
        titulo = request.POST.get("titulo")
        categoria = request.POST.get("categoria")
        descripcion = request.POST.get("descripcion", "")
        archivo = request.FILES.get("archivo")

        if not all([titulo, categoria, archivo]):
            messages.error(request, "Título, categoría y archivo son obligatorios.")
            return redirect("gestion_documentos_conocimiento")

        documento = DocumentoConocimiento.objects.create(
            titulo=titulo,
            descripcion=descripcion,
            categoria=categoria,
            archivo=archivo,
            subido_por=request.user,
        )

        # Process asynchronously (or synchronously for MVP)
        service = DocumentoProcesamientoService(OpenAIClient())
        try:
            service.procesar_documento(documento)
            messages.success(request, f"Documento '{titulo}' procesado ({documento.total_chunks} chunks).")
        except Exception as e:
            messages.error(request, f"Error al procesar documento: {e}")

        return redirect("gestion_documentos_conocimiento")


class ToggleDocumentoActivoView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Toggle active state of a knowledge document."""

    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, documento_id):
        doc = get_object_or_404(DocumentoConocimiento, pk=documento_id)
        doc.activo = not doc.activo
        doc.save()
        estado = "activado" if doc.activo else "desactivado"
        messages.success(request, f"Documento '{doc.titulo}' {estado}.")
        return redirect("gestion_documentos_conocimiento")
```

**Criterios de aceptación:**
- [ ] Modelos `DocumentoConocimiento` y `ChunkDocumento` con migraciones.
- [ ] Admin puede subir documentos (PDF, TXT, DOCX) desde interfaz web.
- [ ] Documentos se procesan: extracción de texto → chunking → embedding.
- [ ] Admin puede activar/desactivar documentos (toggle sin eliminar).
- [ ] Admin puede ver lista de documentos con estado (procesado/pendiente, activo/inactivo).
- [ ] Servicio `ContextoRAGService` busca chunks relevantes por similitud coseno.
- [ ] Máximo 3 chunks de contexto por consulta.
- [ ] Integración con `CopilotAppService` (HU22): el contexto RAG se inyecta en el system prompt.
- [ ] Extracción de texto funciona para PDF (PyPDF2), TXT y DOCX (python-docx).
- [ ] Tests: procesamiento de chunks, similitud coseno, toggle activo.

**Branch:** `feature/HU24-motor-ia-rag`

---

### 4.6 HU25 — Módulo de visualización de documentos

**Propósito:** Implementar un visor seguro para certificados y evidencias adjuntas que permita visualizar PDFs e imágenes sin descarga directa, con watermark, control de acceso y auditoría.

**Reglas de negocio:**
- PDFs se renderizan inline usando pdf.js (no descarga directa).
- Imágenes se muestran con visor personalizado con zoom (scroll wheel + botones).
- Watermark superpuesto: nombre de usuario + fecha/hora de visualización.
- Control de acceso: solo roles autorizados pueden ver documentos:
  - Inspector: ve todos los documentos de justificaciones.
  - Secretaría: ve documentos de recalificaciones y justificaciones.
  - Docente: ve documentos de solicitudes de recalificación de sus paralelos.
  - Estudiante: ve solo SUS propios documentos adjuntos.
- Cada acceso queda registrado en log de auditoría.
- URLs de documentos son temporales (signed URLs con expiración de 30 minutos).

**Modelo — Log de acceso a documentos:**

```python
# apps/solicitudes/infrastructure/models.py
class LogAccesoDocumento(models.Model):
    """Audit log for document access."""

    archivo = models.ForeignKey(
        ArchivoSolicitud, on_delete=models.SET_NULL, null=True,
        related_name="accesos"
    )
    archivo_nombre = models.CharField(max_length=255)  # snapshot
    usuario = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.SET_NULL, null=True,
        related_name="accesos_documentos"
    )
    usuario_info = models.CharField(max_length=200)  # snapshot
    ip = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    accion = models.CharField(
        max_length=20,
        choices=[("visualizar", "Visualizar"), ("intentar", "Intento denegado")],
    )

    class Meta:
        verbose_name = "Log de Acceso a Documento"
        verbose_name_plural = "Logs de Acceso a Documentos"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["archivo", "timestamp"]),
            models.Index(fields=["usuario", "timestamp"]),
        ]
```

**Servicio de dominio — Control de acceso:**

```python
# apps/solicitudes/domain/services.py
class DocumentoAccessControlService:
    """Determines if a user can access a specific document."""

    @staticmethod
    def puede_ver_documento(usuario, archivo: "ArchivoSolicitud") -> bool:
        """Check if user has permission to view this document."""
        solicitud = archivo.solicitud
        rol = usuario.rol

        if rol == "inspector":
            # Inspector can see all justification documents
            return solicitud.tipo == Solicitud.TipoSolicitud.JUSTIFICACION

        if rol == "secretaria":
            # Secretaría can see all documents
            return True

        if rol == "docente":
            # Docente can see recalificación documents from their paralelos
            if solicitud.tipo == Solicitud.TipoSolicitud.RECTIFICACION:
                if solicitud.calificacion:
                    return solicitud.calificacion.evaluacion.paralelo.docente == usuario
            return False

        if rol == "estudiante":
            # Estudiante can only see their own documents
            return solicitud.estudiante == usuario

        return False
```

**Servicio de URLs firmadas:**

```python
# apps/solicitudes/application/services.py
import hashlib
import time
from django.conf import settings
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired

class DocumentoURLService:
    """Generates and validates signed URLs for document access."""

    EXPIRACION_SEGUNDOS = 1800  # 30 minutes

    @classmethod
    def generar_url_firmada(cls, archivo_id: int, usuario_id: int) -> str:
        """Generate a time-limited signed URL for document access."""
        signer = TimestampSigner()
        token = signer.sign(f"{archivo_id}:{usuario_id}")
        return f"/documentos/ver/{archivo_id}/?token={token}"

    @classmethod
    def validar_token(cls, archivo_id: int, usuario_id: int, token: str) -> bool:
        """Validate a signed URL token."""
        signer = TimestampSigner()
        try:
            value = signer.unsign(token, max_age=cls.EXPIRACION_SEGUNDOS)
            expected = f"{archivo_id}:{usuario_id}"
            return value == expected
        except (BadSignature, SignatureExpired):
            return False
```

**Vista del visor:**

```python
# apps/solicitudes/presentation/views.py
class DocumentoViewerView(LoginRequiredMixin, View):
    """Secure document viewer with access control and audit logging."""

    def get(self, request, archivo_id):
        archivo = get_object_or_404(ArchivoSolicitud, pk=archivo_id)
        token = request.GET.get("token")

        # Validate signed URL
        if not DocumentoURLService.validar_token(archivo_id, request.user.id, token):
            LogAccesoDocumento.objects.create(
                archivo=archivo,
                archivo_nombre=archivo.nombre_original,
                usuario=request.user,
                usuario_info=f"{request.user.get_full_name()} ({request.user.cedula})",
                ip=self._get_client_ip(request),
                accion="intentar",
            )
            return HttpResponseForbidden("Enlace expirado o inválido.")

        # Check access control
        access_service = DocumentoAccessControlService()
        if not access_service.puede_ver_documento(request.user, archivo):
            LogAccesoDocumento.objects.create(
                archivo=archivo,
                archivo_nombre=archivo.nombre_original,
                usuario=request.user,
                usuario_info=f"{request.user.get_full_name()} ({request.user.cedula})",
                ip=self._get_client_ip(request),
                accion="intentar",
            )
            return HttpResponseForbidden("No tiene permisos para ver este documento.")

        # Log successful access
        LogAccesoDocumento.objects.create(
            archivo=archivo,
            archivo_nombre=archivo.nombre_original,
            usuario=request.user,
            usuario_info=f"{request.user.get_full_name()} ({request.user.cedula})",
            ip=self._get_client_ip(request),
            accion="visualizar",
        )

        # Render viewer template
        es_pdf = archivo.tipo_mime == "application/pdf"
        context = {
            "archivo": archivo,
            "es_pdf": es_pdf,
            "watermark_texto": f"{request.user.get_full_name()} — {timezone.now().strftime('%d/%m/%Y %H:%M')}",
            "archivo_url": archivo.archivo.url,
        }
        return render(request, "solicitudes/visor_documento.html", context)

    def _get_client_ip(self, request):
        x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        return x_forwarded.split(",")[0] if x_forwarded else request.META.get("REMOTE_ADDR")


class GenerarURLDocumentoView(LoginRequiredMixin, View):
    """Generate a signed URL for viewing a document."""

    def get(self, request, archivo_id):
        archivo = get_object_or_404(ArchivoSolicitud, pk=archivo_id)

        # Pre-check access
        if not DocumentoAccessControlService.puede_ver_documento(request.user, archivo):
            return JsonResponse({"error": "Sin permisos"}, status=403)

        url = DocumentoURLService.generar_url_firmada(archivo_id, request.user.id)
        return JsonResponse({"url": url, "expira_en": DocumentoURLService.EXPIRACION_SEGUNDOS})
```

**Criterios de aceptación:**
- [ ] Modelo `LogAccesoDocumento` creado con migración.
- [ ] PDF se renderiza inline con pdf.js (sin botón de descarga nativo).
- [ ] Imágenes se muestran con visor personalizado: zoom in/out, ajustar a pantalla.
- [ ] Watermark overlay visible: nombre del usuario + fecha/hora de acceso.
- [ ] Control de acceso por rol implementado y testeado:
  - Inspector → justificaciones.
  - Secretaría → todo.
  - Docente → recalificaciones de sus paralelos.
  - Estudiante → solo propios.
- [ ] URLs firmadas con expiración de 30 minutos (Django TimestampSigner).
- [ ] Log de auditoría registra cada acceso exitoso e intento denegado.
- [ ] Servicio `DocumentoAccessControlService` con tests unitarios por cada rol.
- [ ] Servicio `DocumentoURLService` con tests de generación y validación de tokens.
- [ ] Template del visor responsive.
- [ ] Content-Disposition: inline (no attachment) en headers de respuesta.

**Branch:** `feature/HU25-visor-documentos`

---

## 5. Modelo de datos — Cambios del Sprint 4

### 5.1 Nuevos modelos

| Modelo | App | Ubicación |
|--------|-----|-----------|
| `CertificadoJustificacion` | `solicitudes` | `apps/solicitudes/infrastructure/models.py` |
| `ArchivoSolicitud` | `solicitudes` | `apps/solicitudes/infrastructure/models.py` |
| `ConfiguracionJustificacion` | `solicitudes` | `apps/solicitudes/infrastructure/models.py` |
| `LogAccesoDocumento` | `solicitudes` | `apps/solicitudes/infrastructure/models.py` |
| `ConversacionCopilot` | `copilot` | `apps/copilot/infrastructure/models.py` |
| `MensajeCopilot` | `copilot` | `apps/copilot/infrastructure/models.py` |
| `DocumentoConocimiento` | `copilot` | `apps/copilot/infrastructure/models.py` |
| `ChunkDocumento` | `copilot` | `apps/copilot/infrastructure/models.py` |

### 5.2 Modificaciones a modelos existentes

| Modelo | Cambio | Razón |
|--------|--------|-------|
| `Solicitud` | Campo `archivo_adjunto` se mantiene por retrocompatibilidad, pero nuevas solicitudes usan `ArchivoSolicitud` (multi-archivo) | Migración gradual sin romper datos existentes |

### 5.3 Nuevos value objects de dominio

| Value Object | App | Ubicación |
|-------------|-----|-----------|
| `ConsultaAcademica` | `copilot` | `apps/copilot/domain/value_objects.py` |
| `MetricasParalelo` | `academico` | `apps/academico/domain/value_objects.py` |

### 5.4 Nuevos servicios de dominio

| Servicio | App | Ubicación |
|----------|-----|-----------|
| `CertificadoValidationService` | `solicitudes` | `apps/solicitudes/domain/services.py` |
| `DocumentoAccessControlService` | `solicitudes` | `apps/solicitudes/domain/services.py` |
| `QueryClassifierService` | `copilot` | `apps/copilot/domain/services.py` |
| `RendimientoAcademicoService` | `academico` | `apps/academico/domain/services.py` |

### 5.5 Nuevos servicios de aplicación

| Servicio | App | Ubicación |
|----------|-----|-----------|
| `JustificacionCertificadoAppService` | `solicitudes` | `apps/solicitudes/application/services.py` |
| `DocumentoURLService` | `solicitudes` | `apps/solicitudes/application/services.py` |
| `CopilotAppService` | `copilot` | `apps/copilot/application/services.py` |
| `DocumentoProcesamientoService` | `copilot` | `apps/copilot/application/services.py` |
| `ContextoRAGService` | `copilot` | `apps/copilot/application/services.py` |
| `AcademicDataService` | `copilot` | `apps/copilot/application/services.py` |
| `DashboardRendimientoAppService` | `academico` | `apps/academico/application/services.py` |

### 5.6 Migraciones necesarias

1. Crear app `copilot` con `startapp` y registrar en `INSTALLED_APPS`.
2. Crear modelo `CertificadoJustificacion` en app `solicitudes`.
3. Crear modelo `ArchivoSolicitud` en app `solicitudes`.
4. Crear modelo `ConfiguracionJustificacion` en app `solicitudes`.
5. Crear modelo `LogAccesoDocumento` en app `solicitudes`.
6. Crear modelos `ConversacionCopilot` y `MensajeCopilot` en app `copilot`.
7. Crear modelos `DocumentoConocimiento` y `ChunkDocumento` en app `copilot`.

---

## 6. Distribución de trabajo — 10 días (Git Flow)

> **Convención:** `develop` → `feature/HU0X-nombre` → PR → merge a `develop`.
> Ambos devs son fullstack. Trabajo en paralelo con PRs cruzados.

### Semana 1 — Justificaciones + inicio Copilot

#### Día 1 (Lunes 25/05) — Fundamentos justificaciones + app copilot

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Martín** | HU20: Modelos `CertificadoJustificacion` + `ArchivoSolicitud`, migraciones, servicio de dominio `CertificadoValidationService`, tests unitarios | `feature/HU20-certificados-justificacion` | Modelos + servicio + tests, PR abierto |
| **Junior** | HU21: Modelo `ConfiguracionJustificacion`, `LogAccesoDocumento`, migración. Crear estructura base de vista inspector dashboard | `feature/HU21-resolucion-inspector` | Modelos + scaffold vista, PR abierto |

#### Día 2 (Martes 26/05) — Formularios justificación + dashboard inspector

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Martín** | HU20: Formulario multi-archivo con campos dinámicos (Alpine.js por tipo certificado), validaciones frontend + backend, servicio de aplicación | `feature/HU20-certificados-justificacion` | Formulario funcional con validación |
| **Junior** | HU21: Vista ListView con filtros (estado, tipo, paralelo, búsqueda), panel estadísticas, paginación, template responsive | `feature/HU21-resolucion-inspector` | Dashboard con filtros funcional |

#### Día 3 (Miércoles 27/05) — Cierre justificaciones + inicio chatbot

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Martín** | HU20: Tests completos (validación plazo, campos por tipo, archivos). Merge PR. Inicio HU22: crear app `copilot`, modelos `ConversacionCopilot` + `MensajeCopilot`, migraciones | `feature/HU20-...` → `feature/HU22-copilot-chatbot` | PR HU20 merged, app copilot creada |
| **Junior** | HU21: Bulk actions, detalle solicitud con preview, deadline indicators (verde/amarillo/rojo), acciones aprobar/rechazar con email. Merge PR | `feature/HU21-resolucion-inspector` | PR HU21 merged, dashboard completo |

#### Día 4 (Jueves 28/05) — Chatbot core + dashboard rendimiento

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Martín** | HU22: `OpenAIClient`, `QueryClassifierService`, `CopilotAppService` (procesar_mensaje, rate limiting, session management), endpoint POST/GET | `feature/HU22-copilot-chatbot` | Backend chatbot funcional |
| **Junior** | HU23: Servicio de dominio `RendimientoAcademicoService`, servicio de aplicación `DashboardRendimientoAppService`, endpoint API JSON | `feature/HU23-dashboard-rendimiento` | Servicios + API funcionando |

#### Día 5 (Viernes 29/05) — Widget chat + gráficos

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Martín** | HU22: Widget de chat Alpine.js (template component), animación typing, nueva conversación, historial en sidebar | `feature/HU22-copilot-chatbot` | Widget UI funcional |
| **Junior** | HU23: Template con Chart.js (barras promedios, línea tendencia, donut aprobación), filtros período/materia, cards resumen. Tests | `feature/HU23-dashboard-rendimiento` | Dashboard con gráficos, PR abierto |

### Semana 2 — Motor IA + visor documentos + integración

#### Día 6 (Lunes 01/06) — RAG + visor

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Martín** | HU24: Modelos `DocumentoConocimiento` + `ChunkDocumento`, migraciones, `DocumentoProcesamientoService` (extracción PDF/TXT/DOCX, chunking) | `feature/HU24-motor-ia-rag` | Modelos + procesamiento, PR abierto |
| **Junior** | HU25: Servicio `DocumentoAccessControlService`, `DocumentoURLService` (signed URLs), vista `DocumentoViewerView`. Merge PR HU23 | `feature/HU25-visor-documentos` | Servicios acceso + URLs, PR HU23 merged |

#### Día 7 (Martes 02/06) — Embeddings + visor frontend

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Martín** | HU24: Generación de embeddings vía OpenAI, `ContextoRAGService` (búsqueda por similitud coseno), integración con `CopilotAppService` | `feature/HU24-motor-ia-rag` | RAG funcional E2E |
| **Junior** | HU25: Template visor con pdf.js (renderizado inline), visor de imágenes (zoom Alpine.js), watermark overlay CSS, headers Content-Disposition | `feature/HU25-visor-documentos` | Visor funcional PDF + imágenes |

#### Día 8 (Miércoles 03/06) — Admin RAG + auditoría visor

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Martín** | HU24: Vista admin gestión documentos (upload, lista, toggle activo), tests completos. Merge PR HU22 | `feature/HU24-motor-ia-rag` | Admin funcional, PR HU22 merged |
| **Junior** | HU25: `LogAccesoDocumento` integrado, vista de auditoría de accesos (inspector), integración con HU21 (preview en dashboard). Tests completos | `feature/HU25-visor-documentos` | Auditoría + integración, PR abierto |

#### Día 9 (Jueves 04/06) — Integración + testing

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Martín** | Merge PR HU24. Integración final copilot: testing E2E (pregunta → clasificación → RAG → respuesta), fix bugs | `develop` | PR HU24 merged, copilot E2E funcional |
| **Junior** | Merge PR HU25. Testing E2E visor: cada rol ve solo lo permitido, watermark visible, URLs expiran correctamente | `develop` | PR HU25 merged, visor E2E funcional |

#### Día 10 (Viernes 05/06) — Cierre sprint

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Martín** | Fix bugs finales, data fixtures para demo (conversaciones, documentos conocimiento), testing suite completa | `develop` | Suite verde, fixtures |
| **Junior** | Fix bugs finales, testing cross-feature (justificación → visor → inspector), documentación cierre sprint | `develop` | Suite verde, documentación |

### Tareas no técnicas (en paralelo durante el sprint)

| Tarea | Responsable | Día |
|-------|-------------|-----|
| Resolver consultas pendientes P1–P5 con la ECPPP | Junior | Día 1 |
| Obtener API key OpenAI y configurar en `.env` | Martín | Día 1 |
| Solicitar documentos institucionales para RAG (reglamento, malla) | Junior | Día 1 |
| Configurar dependencias nuevas (openai, PyPDF2, python-docx, pdfjs) | Martín | Día 1 |
| Code review cruzado de cada PR (mínimo 1 approval antes de merge) | Ambos | Continuo |
| Testing manual de flujos completos | Ambos | Día 9–10 |
| Crear data fixtures/seeds para demo | Martín | Día 10 |

---

## 7. Flujos de usuario completos

### 7.1 Flujo: Justificar inasistencia con certificado (Estudiante)

```
1. Estudiante accede a /solicitudes/justificacion/nueva/
2. Selecciona paralelo y fecha de inasistencia (solo AUSENTE)
3. Selecciona tipo de certificado: médico / laboral / calamidad
4. Formulario muestra campos dinámicos según tipo:
   - Médico: institución, médico, fecha cert, nro, días reposo
   - Laboral: empresa, cargo, fecha permiso, nro documento
   - Calamidad: descripción evento, fecha, relación familiar
5. Completa campos obligatorios del tipo seleccionado
6. Adjunta hasta 3 archivos (PDF/imagen, max 5MB c/u)
7. Escribe descripción/motivo
8. Sistema valida:
   a. Plazo: ≤3 días hábiles desde la inasistencia
   b. Campos obligatorios por tipo
   c. Fecha certificado ≤ fecha solicitud
   d. Archivos: extensión + tamaño
9. Envía → estado PENDIENTE
10. Inspector recibe notificación email
```

### 7.2 Flujo: Inspector resuelve justificaciones

```
1. Inspector accede a /solicitudes/inspector/dashboard/
2. Ve panel de estadísticas: pendientes (12), aprobadas hoy (5), rechazadas (2), vencidas (1)
3. Ve lista filtrable de solicitudes con indicadores de deadline:
   - Verde: dentro de plazo
   - Amarillo: ≤2 días para vencer
   - Rojo: vencida
4. Puede filtrar por: estado, tipo certificado, paralelo, búsqueda
5. Click en solicitud → vista detalle:
   - Datos del estudiante
   - Metadata del certificado
   - Preview de documentos (visor seguro HU25)
   - Historial de la solicitud
6a. Aprueba → asistencia cambia AUSENTE→JUSTIFICADO → email estudiante
6b. Rechaza → escribe comentario obligatorio → email estudiante
7. Alternativa: selecciona múltiples + acción masiva aprobar/rechazar
```

### 7.3 Flujo: Estudiante/Docente usa Copilot

```
1. Usuario ve widget de chat (flotante, esquina inferior derecha)
2. Click → se abre panel de conversación
3. Escribe pregunta: "¿Cuál es mi promedio en Matemáticas?"
4. Sistema:
   a. Clasifica query → "calificaciones"
   b. Obtiene datos académicos del usuario (sus notas de Matemáticas)
   c. Busca contexto RAG relevante (reglas de aprobación)
   d. Envía a OpenAI con system prompt + historial + datos + contexto
   e. Recibe respuesta
5. Respuesta aparece en el chat con animación de typing
6. Usuario puede seguir conversando (historial se mantiene)
7. Si excede 30 msg/hora → mensaje de rate limit
8. Si sesión tiene 50+ mensajes → sugerir nueva conversación
9. Puede hacer click en "Nueva conversación" para reiniciar
```

### 7.4 Flujo: Inspector consulta dashboard de rendimiento

```
1. Inspector accede a /academico/dashboard-rendimiento/
2. Ve selector de período (default: período activo) y materia (opcional)
3. Ve cards resumen: total paralelos, promedio general, % asistencia global
4. Ve gráfico de barras: promedio por paralelo (comparativo)
5. Ve gráfico donut: distribución aprobados/reprobados/en curso
6. Selecciona un paralelo → se carga gráfico de línea (tendencia por parcial)
7. Puede cambiar filtros → gráficos se actualizan (fetch API → Chart.js update)
```

### 7.5 Flujo: Admin gestiona base de conocimiento

```
1. Admin accede a /copilot/admin/documentos/
2. Ve lista de documentos: título, categoría, estado (procesado/pendiente), activo/inactivo
3. Click "Subir documento":
   a. Ingresa título y categoría
   b. Selecciona archivo (PDF/TXT/DOCX)
   c. Sistema procesa: extrae texto → divide en chunks → genera embeddings
   d. Muestra resultado: "Documento procesado (24 chunks)"
4. Puede toggle activo/inactivo (sin eliminar)
5. Documentos activos se usan como contexto RAG en el chatbot
```

### 7.6 Flujo: Visualizar documento con visor seguro

```
1. Usuario (inspector/secretaría/docente/estudiante) está en detalle de solicitud
2. Ve lista de archivos adjuntos con miniatura
3. Click en archivo → sistema genera URL firmada (30 min expiración)
4. Se abre visor:
   - Si PDF: renderiza con pdf.js (paginado, sin botón descarga)
   - Si imagen: visor con zoom (scroll wheel + botones +/-)
5. Watermark visible: "Juan Pérez — 25/05/2026 14:30"
6. Log de auditoría registra: quién, cuándo, qué, desde qué IP
7. Si URL expiró → muestra error "Enlace expirado" → debe generar nueva URL
8. Si rol no tiene permiso → muestra error "Sin permisos" + log de intento
```

---

## 8. Decisiones de arquitectura — Sprint 4

| # | Decisión | Resolución | Razón |
|---|----------|-----------|-------|
| D34 | Multi-archivo en solicitudes | Modelo separado `ArchivoSolicitud` (FK a Solicitud) en vez de campo FileField | Permite múltiples archivos por solicitud sin cambiar el modelo existente. El campo `archivo_adjunto` original se mantiene por retrocompatibilidad |
| D35 | Metadatos de certificado | Modelo separado `CertificadoJustificacion` (OneToOne con Solicitud) | Evita agregar 10+ campos nullable a `Solicitud`. Campos varían por tipo. Separación de responsabilidades |
| D36 | Chatbot como app separada `copilot` | Nueva app Django con estructura DDD completa | Dominio completamente distinto (IA/NLP), no tiene acoplamiento fuerte con apps existentes. Facilita testing aislado |
| D37 | Almacenamiento de embeddings | Campo JSONField en `ChunkDocumento` (lista de floats) | Simple para MVP. Sin dependencia de vector DB externa (pgvector/Pinecone). Suficiente para <1000 chunks. Migrar a pgvector si escala |
| D38 | Rate limiting del chatbot | Basado en conteo de mensajes en DB (no Redis) | Simplicidad: no requiere infraestructura adicional. 30 msg/hora verificado con query COUNT. Suficiente para la escala de la ECPPP |
| D39 | Signed URLs para documentos | Django TimestampSigner con expiración de 30min | Nativo de Django, no requiere dependencias. Seguro contra URL sharing. Expiración configurable |
| D40 | Visor PDF | pdf.js (Mozilla) embebido via CDN | Renderiza PDF en canvas (no usa viewer nativo del browser). Permite desactivar descarga. Open source, mantenido |
| D41 | Gráficos del dashboard | Chart.js v4 via CDN | Ligero (~60KB), no requiere build step. Compatible con Alpine.js. Suficiente para los tipos de gráficos requeridos |
| D42 | Procesamiento de documentos RAG | Síncrono en MVP (procesa al subir) | Simplicidad: no requiere Celery/queue. Los documentos son pocos (<50) y pequeños (<10 páginas). Migrar a async si hay timeout |
| D43 | Cosine similarity en Python | Cálculo en memoria vs DB | Con <1000 chunks el cálculo en Python es suficientemente rápido (<100ms). Si escala, migrar a pgvector con índice HNSW |
| D44 | Watermark en visor | CSS overlay (position absolute + opacity) | No modifica el archivo original. Se genera dinámicamente con datos del usuario. Fácil de implementar sin procesamiento server-side |
| D45 | Modelo de configuración singleton | `ConfiguracionJustificacion` con `get_or_create(pk=1)` | Pattern simple para configuración global. Editable desde Django Admin sin hardcodear valores |

---

## 9. Configuración técnica — Sprint 4

### 9.1 Nuevas URLs

```python
# apps/copilot/presentation/urls.py
urlpatterns = [
    path("chat/", CopilotChatView.as_view(), name="copilot_chat"),
    path("nueva-conversacion/", CopilotNuevaConversacionView.as_view(), name="copilot_nueva_conversacion"),
    path("admin/documentos/", GestionDocumentosConocimientoView.as_view(), name="gestion_documentos_conocimiento"),
    path("admin/documentos/subir/", SubirDocumentoConocimientoView.as_view(), name="subir_documento_conocimiento"),
    path("admin/documentos/<int:documento_id>/toggle/", ToggleDocumentoActivoView.as_view(), name="toggle_documento_activo"),
]

# apps/solicitudes/presentation/urls.py — nuevas rutas
urlpatterns += [
    path("inspector/dashboard/", InspectorJustificacionesDashboardView.as_view(), name="inspector_justificaciones_dashboard"),
    path("inspector/<int:solicitud_id>/resolver/", InspectorResolverJustificacionView.as_view(), name="inspector_resolver_justificacion"),
    path("inspector/<int:solicitud_id>/detalle/", InspectorJustificacionDetalleView.as_view(), name="inspector_justificacion_detalle"),
    path("inspector/bulk-action/", InspectorBulkActionView.as_view(), name="inspector_bulk_action"),
]

# apps/solicitudes/presentation/urls.py — visor documentos
urlpatterns += [
    path("documentos/<int:archivo_id>/url/", GenerarURLDocumentoView.as_view(), name="generar_url_documento"),
    path("documentos/ver/<int:archivo_id>/", DocumentoViewerView.as_view(), name="visor_documento"),
]

# apps/academico/presentation/urls.py — dashboard rendimiento
urlpatterns += [
    path("dashboard-rendimiento/", DashboardRendimientoView.as_view(), name="dashboard_rendimiento"),
    path("dashboard-rendimiento/api/", DashboardRendimientoAPIView.as_view(), name="dashboard_rendimiento_api"),
]
```

### 9.2 Dependencias nuevas

```txt
# requirements/base.txt — agregar
openai>=1.30.0          # OpenAI API client (chat + embeddings)
PyPDF2>=3.0.0           # PDF text extraction
python-docx>=1.1.0      # DOCX text extraction
```

```txt
# Frontend (CDN en templates, no npm)
# pdf.js v4.x — Mozilla PDF viewer
# Chart.js v4.x — Charting library
# (Alpine.js ya está instalado)
```

```python
# config/settings/base.py — agregar
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")
COPILOT_MODEL = env("COPILOT_MODEL", default="gpt-4o-mini")
COPILOT_EMBEDDING_MODEL = env("COPILOT_EMBEDDING_MODEL", default="text-embedding-3-small")

# App registration
INSTALLED_APPS += ["apps.copilot"]
```

```env
# .env — agregar
OPENAI_API_KEY=sk-...
COPILOT_MODEL=gpt-4o-mini
COPILOT_EMBEDDING_MODEL=text-embedding-3-small
```

### 9.3 Fixtures/Seeds para demo

Management command `python manage.py seed_sprint4` con:
- 3 solicitudes de justificación con certificados (1 médico, 1 laboral, 1 calamidad) y archivos adjuntos.
- 2 solicitudes resueltas (1 aprobada, 1 rechazada) con historial.
- 1 conversación de copilot con 5 mensajes (demo).
- 3 documentos de conocimiento procesados (reglamento dummy, política asistencia, malla).
- Datos de calificaciones suficientes para que el dashboard muestre gráficos.
- Configuración de justificación (5 días deadline).

---

## 10. Riesgos del Sprint 4

| # | Riesgo | Probabilidad | Impacto | Mitigación |
|---|--------|-------------|---------|-----------|
| R1 | API key OpenAI no disponible o con rate limits | Media | Alto | Tener mock/stub del client para desarrollo sin API real. Tests usan mock. Cuenta con billing configurada |
| R2 | Costos de API OpenAI se disparan en testing | Media | Medio | Usar `gpt-4o-mini` (más barato). Rate limit en app (30 msg/hora). Monitorear usage en dashboard OpenAI |
| R3 | Procesamiento de documentos RAG timeout en archivos grandes | Baja | Medio | Limitar tamaño de documentos (10MB). Chunks de 500 tokens. Procesamiento síncrono OK para pocos docs |
| R4 | Consultas pendientes P1–P5 no se resuelven a tiempo | Alta | Alto | Implementar con valores por defecto documentados. Ajustar post-respuesta |
| R5 | pdf.js no renderiza ciertos PDFs correctamente | Baja | Bajo | Fallback: enlace de descarga con watermark. Testear con PDFs reales de la ECPPP |
| R6 | Similitud coseno en Python es lenta con muchos chunks | Baja | Medio | Con <1000 chunks es suficiente. Si escala: migrar a pgvector o FAISS. Cachear embeddings de queries frecuentes |
| R7 | Complejidad del chatbot (5 pts) puede exceder estimación | Media | Alto | Priorizar: backend funcional primero (Día 3–4), UI después (Día 5). RAG (HU24) como mejora, no blocker |
| R8 | Multi-file upload con validación es complejo en frontend | Baja | Medio | Alpine.js drag&drop + validación client-side previa. Backend siempre valida server-side |

---

## 11. Métricas de éxito del Sprint 4

| # | Métrica | Criterio |
|---|---------|----------|
| M1 | HUs completadas | 6/6 (HU20–HU25) |
| M2 | Tests pasando | Suite completa verde + nuevos tests del sprint |
| M3 | Flujo E2E — Justificación mejorada | Estudiante sube certificado categorizado → inspector ve y resuelve con visor |
| M4 | Flujo E2E — Chatbot | Usuario pregunta → clasificación → RAG → respuesta coherente |
| M5 | Flujo E2E — Dashboard rendimiento | Inspector ve gráficos con datos reales, filtra por período/materia |
| M6 | Cobertura dominio | ≥ 70% en servicios de dominio nuevos |
| M7 | PRs mergeados | Todos los feature branches mergeados a develop vía PR |
| M8 | Seguridad visor | URLs firmadas expiran, roles sin permiso son bloqueados, accesos logueados |
| M9 | Rate limiting chatbot | 30+ mensajes/hora devuelve 429, sesión de 50+ mensajes pide nueva conversación |
| M10 | Responsive | Todas las vistas nuevas responsive (mobile + desktop) |
