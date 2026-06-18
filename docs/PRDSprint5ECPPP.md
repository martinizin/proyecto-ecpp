# PRD — Sprint 5: Plataforma Web Académica ECPPP

| Campo | Valor |
|-------|-------|
| **Título** | Product Requirements Document — Sprint 5 |
| **Proyecto** | Plataforma Web Académica ECPPP |
| **Versión** | 0.6.0 |
| **Fecha** | Junio 2026 |
| **Sprint** | S5 (Incremento 5 — Cierre de proyecto) |
| **Rango de fechas** | 22/06/2026 – 03/07/2026 (2 semanas, ~10 días hábiles) |
| **Equipo** | 2 desarrolladores fullstack — Martín Jiménez, Junior Espín |
| **Metodología** | Scrum + Git Flow (`develop` → `feature/*` → PR) |
| **Estado** | Draft |

---

## 1. Resumen ejecutivo del Sprint 5

### 1.1 Objetivo del Sprint

Cerrar el ciclo de vida del proyecto ECPPP: (1) generar los reportes normativos exigidos por la **Resolución 005-DIR-2022** de la ANT y la exportación masiva de listados en PDF/Excel, (2) consolidar el dashboard institucional de cierre de período con tasas de aprobación y deserción, (3) producir la documentación técnica final (arquitectura, base de datos, manual de usuario), (4) desplegar la plataforma en un **VPS institucional** con PostgreSQL, Redis, Nginx, Gunicorn, SSL, backups automatizados y endurecimiento de seguridad, y (5) absorber tres observaciones del cliente (cierre de sesión por inactividad, notas 3–5 por parcial, y nuevo rol **Director Académico** de solo lectura). Este sprint construye sobre la gestión de calificaciones (S3), justificaciones/dashboards (S4) y libera el producto a producción.

### 1.2 Resumen de funcionalidades

| # | Funcionalidad | Descripción |
|---|---------------|-------------|
| 1 | Reportes ANT — Resolución 005-DIR-2022 | Generación de reportes normativos trazables con firma de responsable y hash de integridad |
| 2 | Exportación masiva PDF/Excel | Descarga estructurada de libretas de calificaciones y listados de asistencia filtrables |
| 3 | Dashboard de cierre de período | Resumen final institucional con tasa de aprobación, reprobación y deserción por período académico |
| 4 | Documentación técnica final | Manuales de arquitectura, modelo de datos y usuario final (3 entregables) |
| 5 | Despliegue en VPS + Backups | Setup completo de infraestructura (Gunicorn, Nginx, PostgreSQL, Redis, SSL, backups automáticos, hardening) |
| 6 | Cierre de sesión por inactividad | Auto-logout con pop-up Alpine.js al expirar el tiempo máximo de inactividad |
| 7 | Notas 3–5 por parcial | El docente registra entre 3 y 5 sub-notas dentro de cada parcial antes de consolidar la nota final |
| 8 | Rol Director Académico | Nuevo rol con acceso de solo lectura (mismos módulos que inspector) para monitoreo y trazabilidad |

### 1.3 Pendientes ECPPP por consultar

> **IMPORTANTE:** Estas consultas deben resolverse el Día 1 del sprint antes de implementar. Afectan directamente el diseño y los entregables normativos.

| # | Consulta pendiente | Impacto en implementación | Valor por defecto si no se resuelve |
|---|-------------------|---------------------------|--------------------------------------|
| P1 | ¿Cuál es el formato exacto del reporte ANT (campos obligatorios, periodicidad, firma electrónica o escaneada)? | Define el layout del PDF/Excel y los campos del modelo `ReporteANT` | Reporte PDF con: datos del estudiante, paralelo, calificaciones por parcial, asistencia %, estado final. Firmado con rúbrica del responsable + hash SHA-256 |
| P2 | ¿Los reportes ANT se generan por paralelo, por período, o por estudiante individual? | Define el alcance del endpoint de generación | Por período académico completo (un reporte consolidado por período activo) |
| P3 | ¿Se necesita un usuario específico con rol "ANT" para descargar reportes, o cualquier usuario con permisos puede hacerlo? | Define control de acceso al endpoint | Rol `secretaria` y `director_academico` pueden generar/descargar |
| P4 | ¿Cuál es el tiempo máximo de inactividad permitido antes de cerrar la sesión? | Define el timeout configurable | 20 minutos (alineado con buenas prácticas de seguridad para sistemas académicos) |
| P5 | ¿Las 3–5 notas del parcial son promediables o el docente debe elegir una como definitiva? | Define el algoritmo de consolidación | Promedio aritmético de las sub-notas registradas, con la posibilidad de sobrescribir manualmente la nota final del parcial |
| P6 | ¿El "Director Académico" hereda los permisos de inspector EXACTAMENTE o solo un subconjunto? | Define matriz de permisos del nuevo rol | Mismos módulos que inspector pero con `view_only=True` en todas las acciones; no puede aprobar/rechazar solicitudes ni modificar calificaciones |
| P7 | ¿El VPS destino es Ubuntu 22.04 LTS o 24.04 LTS? ¿Tiene acceso root? | Define comandos exactos del deploy | Ubuntu 22.04 LTS con acceso root vía SSH (suposición más común para infraestructura institucional) |
| P8 | ¿El dominio institucional está disponible y los DNS ya apuntan al VPS? | Define pasos de SSL y Nginx server block | Asumimos dominio `ecppp.edu.ec` con DNS propagado antes del Día 8 |

### 1.4 Definition of Done del Sprint 5

- [ ] Inspector/Secretaría puede generar el reporte ANT consolidado por período, descargable en PDF con firma del responsable y hash de integridad.
- [ ] El reporte ANT es **idempotente**: regenerar el mismo reporte produce el mismo hash (mismos datos → mismo resultado).
- [ ] Docente/Inspector/Secretaría pueden exportar listados de calificaciones y asistencia a PDF y Excel, con filtros por período, materia, paralelo.
- [ ] Dashboard de cierre de período accesible para inspector/director académico: muestra tasas de aprobación, reprobación, deserción y promedios por período completo.
- [ ] Manual de arquitectura (audiencia: devs/soporte), manual de base de datos (audiencia: DBA/soporte) y manual de usuario (audiencia: usuarios finales) entregados en `docs/manuales/`.
- [ ] Aplicación desplegada y operativa en VPS con HTTPS válido (Let's Encrypt).
- [ ] Backups automatizados de PostgreSQL y `media/` con retención de 30 días verificables.
- [ ] Sesión expira tras N minutos de inactividad (configurable) con pop-up Alpine.js que avisa al usuario y redirige al login.
- [ ] Docente puede registrar entre 3 y 5 notas por parcial; la nota final del parcial se calcula como promedio (o se permite override manual).
- [ ] Nuevo rol `director_academico` con acceso de solo lectura a los mismos módulos que inspector.
- [ ] Tests con cobertura ≥ 70% en capa de dominio.
- [ ] Pipeline CI en verde.
- [ ] Smoke test E2E post-deploy desde URL pública.

---

## 2. Alcance del Sprint 5

### 2.1 Incluye

| Aspecto | Detalle |
|---------|---------|
| Reporte ANT | Generación de PDF normativo con datos del estudiante, calificaciones, asistencia, estado final. Hash de integridad (SHA-256) + firma del responsable. Tabla `ReporteANT` con snapshot inmutable. |
| Exportación PDF/Excel | Descarga masiva de libretas (estudiante, paralelo, período completo) y listados de asistencia. Usa `reportlab` (PDF) y `openpyxl` (Excel). Filtros combinables. |
| Dashboard cierre de período | Vista resumen final con tarjetas KPI, gráficos de torta (aprobación/reprobación/deserción), tabla de paralelos con promedios y estados. |
| Manuales técnicos | 3 documentos Markdown/PDF: arquitectura (DDD, decisiones, diagramas), modelo de datos (ER, migraciones, semillas), manual de usuario (guía paso a paso por rol). |
| Despliegue VPS | Hardening del servidor (firewall, SSH, fail2ban), instalación de PostgreSQL, Redis, Python, Nginx, Gunicorn (systemd), SSL con Let's Encrypt, backups con `cron` + `pg_dump`, monitoreo básico. |
| Timeout de sesión | Middleware que rastrea `last_activity` en sesión; job de cleanup o middleware on-request; pop-up Alpine.js + redirect a login cuando expira. |
| Notas 3–5 por parcial | Modelo `SubNotaParcial` (FK a `Evaluacion` y `Matricula`); UI para que el docente registre sub-notas; promedio automático configurable y override manual. |
| Rol Director Académico | Nuevo `rol` en `Usuario`, con matriz de permisos `view_only` que reusa los mixins/vistas existentes de inspector. |

### 2.2 Excluye

| Aspecto | Razón |
|---------|-------|
| Firma electrónica avanzada (token criptográfico) para reportes ANT | El cliente confirmó que la firma es escaneada (imagen PNG subida por admin) más hash de integridad. Firma digital avanzada con certificado queda fuera de alcance |
| Migración a un cluster Kubernetes / multi-VPS | El despliegue es single-VPS por requerimiento institucional. Escalabilidad horizontal queda como deuda técnica documentada |
| Notificaciones push/WebSocket | Sprint anterior ya excluido. Se mantiene email |
| Integración con sistema de pagos | Fuera del alcance académico |
| Analytics predictivo con ML | El dashboard muestra datos agregados del período, no predicciones |
| App móvil nativa | La plataforma es web responsive; app móvil queda como roadmap post-proyecto |
| Carga de calificaciones desde Excel/CSV | Excluido para evitar complejidad de validación. La carga es manual por docente |

---

## 3. Backlog del Sprint 5

| ID | Nombre | Puntos | Responsable | Día(s) objetivo |
|----|--------|--------|-------------|-----------------|
| HU26 | Reportes ANT — Resolución 005-DIR-2022 | 5 | Junior | Día 1–3 |
| HU27 | Exportación masiva PDF/Excel | 5 | Martín | Día 1–4 |
| HU28 | Dashboard de cierre de período | 3 | Junior | Día 3–5 |
| HU29 | Documentación técnica final (3 manuales) | 3 | Martín | Día 4–7 |
| HU30 | Despliegue en VPS + Backups automatizados | 5 | Martín | Día 5–8 |
| HU31 | Cierre de sesión por inactividad | 2 | Martín | Día 2–3 |
| HU32 | Notas 3–5 por parcial (Sub-notas) | 3 | Junior | Día 4–6 |
| HU33 | Rol Director Académico (solo lectura) | 2 | Junior | Día 6–7 |
| **Total** | | **28** | | |

---

## 4. Detalle por HU

### 4.1 HU26 — Reportes consolidados para la ANT (Resolución 005-DIR-2022)

**Propósito:** Generar los reportes normativos exigidos por la Resolución 005-DIR-2022 de la ANT, con datos institucionales, calificaciones, asistencia y estado final por estudiante, incluyendo firma del responsable y hash de integridad para garantizar trazabilidad.

**Reglas de negocio:**
- Un reporte se genera por **período académico completo** y contiene TODOS los estudiantes matriculados.
- Datos incluidos por estudiante: cédula, nombres, paralelo, materia, calificaciones por parcial, promedio final, % asistencia, estado (Aprobado/Reprobado/En curso/Desertor).
- Encabezado institucional: nombre ECPPP, período, fecha de generación, número de resolución.
- Firma del responsable: imagen PNG almacenada en `media/firmas/` (subida por admin), más nombre y cédula del firmante.
- Hash de integridad: SHA-256 sobre el contenido completo del PDF (excluyendo metadata del PDF) — permite verificar que el documento no fue alterado.
- Cada generación queda registrada en `ReporteANT` con: timestamp, usuario que generó, hash, path del PDF, número de estudiantes.
- El reporte es **regenerable**: si la secretaría detecta un error en datos, puede regenerar (se crea nuevo registro, los anteriores quedan como histórico).
- Formato: PDF (normativo), Excel opcional (datos tabulares para cruce).

**Modelo — Reporte ANT:**

```python
# apps/reportes/infrastructure/models.py — nuevo modelo
class ReporteANT(models.Model):
    """Regulatory report for ANT (Resolución 005-DIR-2022). Immutable snapshot."""

    periodo = models.ForeignKey(
        "academico.PeriodoAcademico", on_delete=models.PROTECT,
        related_name="reportes_ant"
    )
    numero_resolucion = models.CharField(
        max_length=50, default="005-DIR-2022"
    )
    generado_por = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.PROTECT,
        related_name="reportes_ant_generados",
        limit_choices_to={"rol__in": ["secretaria", "director_academico", "inspector"]},
    )
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    total_estudiantes = models.PositiveIntegerField()
    total_aprobados = models.PositiveIntegerField()
    total_reprobados = models.PositiveIntegerField()
    total_desertores = models.PositiveIntegerField()
    total_en_curso = models.PositiveIntegerField()
    archivo_pdf = models.FileField(upload_to="reportes/ant/%Y/%m/")
    archivo_excel = models.FileField(upload_to="reportes/ant/%Y/%m/", null=True, blank=True)
    hash_sha256 = models.CharField(max_length=64)  # hex digest
    firma_responsable_imagen = models.CharField(
        max_length=300, blank=True,
        help_text="Path relativo a la imagen de firma del responsable (PNG)."
    )
    nombre_firmante = models.CharField(max_length=200)
    cedula_firmante = models.CharField(max_length=20)
    cargo_firmante = models.CharField(max_length=100, default="Director Académico ECPPP")
    notas = models.TextField(blank=True, help_text="Observaciones o notas institucionales")

    class Meta:
        verbose_name = "Reporte ANT"
        verbose_name_plural = "Reportes ANT"
        ordering = ["-fecha_generacion"]
        indexes = [
            models.Index(fields=["periodo", "-fecha_generacion"]),
        ]

    def __str__(self):
        return f"Reporte ANT {self.periodo} — {self.fecha_generacion:%Y-%m-%d %H:%M}"
```

**Servicio de dominio — Cálculo del reporte:**

```python
# apps/reportes/domain/services.py
import hashlib
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class DatosEstudianteReporte:
    """Snapshot of a student's data for the ANT report."""
    cedula: str
    nombres_completos: str
    paralelo_codigo: str
    materia_nombre: str
    promedio_final: Decimal | None
    porcentaje_asistencia: Decimal
    estado: str  # "aprobado" | "reprobado" | "en_curso" | "desertor"
    calificaciones_por_parcial: dict[str, Decimal]


class ReporteANTService:
    """Builds ANT report data and computes integrity hash."""

    @staticmethod
    def calcular_estado_estudiante(
        promedio_final: Decimal | None,
        porcentaje_asistencia: Decimal,
        es_desertor: bool,
    ) -> str:
        """Determines final state for the report."""
        if es_desertor:
            return "desertor"
        if promedio_final is None:
            return "en_curso"
        if promedio_final >= Decimal("16") and porcentaje_asistencia >= Decimal("70"):
            return "aprobado"
        return "reprobado"

    @staticmethod
    def computar_hash_contenido(contenido_pdf_bytes: bytes) -> str:
        """SHA-256 hash of the report's content (excludes PDF metadata)."""
        return hashlib.sha256(contenido_pdf_bytes).hexdigest()

    @staticmethod
    def consolidar_datos(estudiantes_data: list[DatosEstudianteReporte]) -> dict:
        """Aggregates totals for the report header."""
        return {
            "total": len(estudiantes_data),
            "aprobados": sum(1 for e in estudiantes_data if e.estado == "aprobado"),
            "reprobados": sum(1 for e in estudiantes_data if e.estado == "reprobado"),
            "desertores": sum(1 for e in estudiantes_data if e.estado == "desertor"),
            "en_curso": sum(1 for e in estudiantes_data if e.estado == "en_curso"),
        }
```

**Servicio de aplicación — Generación del PDF:**

```python
# apps/reportes/application/services.py
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

class ReporteANTGeneratorService:
    """Orchestrates the generation of the ANT regulatory PDF report."""

    def __init__(self, periodo, generado_por, firma_path=None, notas=""):
        self.periodo = periodo
        self.generado_por = generado_por
        self.firma_path = firma_path
        self.notas = notas

    def generar(self) -> ReporteANT:
        # 1. Recolectar datos
        datos_estudiantes = self._recolectar_datos_estudiantes()
        totales = ReporteANTService.consolidar_datos(datos_estudiantes)

        # 2. Construir PDF en memoria
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=landscape(A4),
            leftMargin=2 * cm, rightMargin=2 * cm,
            topMargin=2 * cm, bottomMargin=2 * cm,
        )
        elements = self._construir_elementos_pdf(datos_estudiantes, totales)
        doc.build(elements)

        # 3. Calcular hash ANTES de guardar (para incluirlo en el PDF)
        contenido = buffer.getvalue()
        hash_integridad = ReporteANTService.computar_hash_contenido(contenido)

        # 4. Reconstruir PDF con hash incluido en el pie
        buffer2 = BytesIO()
        doc2 = SimpleDocTemplate(buffer2, pagesize=landscape(A4), ...)
        elements2 = self._construir_elementos_pdf(
            datos_estudiantes, totales, hash_integridad
        )
        doc2.build(elements2)
        contenido_final = buffer2.getvalue()

        # 5. Persistir
        filename = f"reporte_ant_{self.periodo.codigo}_{datetime.now():%Y%m%d_%H%M}.pdf"
        reporte = ReporteANT.objects.create(
            periodo=self.periodo,
            generado_por=self.generado_por,
            total_estudiantes=totales["total"],
            total_aprobados=totales["aprobados"],
            total_reprobados=totales["reprobados"],
            total_desertores=totales["desertores"],
            total_en_curso=totales["en_curso"],
            archivo_pdf=ContentFile(contenido_final, name=filename),
            hash_sha256=ReporteANTService.computar_hash_contenido(contenido_final),
            firma_responsable_imagen=self.firma_path or "",
            nombre_firmante=self.generado_por.get_full_name(),
            cedula_firmante=self.generado_por.cedula,
            notas=self.notas,
        )
        return reporte

    def _recolectar_datos_estudiantes(self) -> list[DatosEstudianteReporte]:
        """Collects all students in the period with their final grades and attendance."""
        from apps.academico.infrastructure.models import Matricula
        from apps.calificaciones.application.services import LibretaCalificacionesAppService
        from apps.asistencia.application.services import ResumenAsistenciaService

        matriculas = Matricula.objects.filter(
            paralelo__periodo=self.periodo, activa=True
        ).select_related("estudiante", "paralelo", "paralelo__materia")

        datos = []
        for matricula in matriculas:
            libreta = LibretaCalificacionesAppService().obtener_libreta(matricula.estudiante)
            promedio = libreta.get_promedio_por_paralelo(matricula.paralelo_id)
            asistencia = ResumenAsistenciaService().obtener_resumen(
                matricula.estudiante, matricula.paralelo
            )
            es_desertor = ResumenAsistenciaService().es_desertor(
                matricula.estudiante, matricula.paralelo
            )

            estado = ReporteANTService.calcular_estado_estudiante(
                promedio, asistencia.porcentaje, es_desertor
            )

            datos.append(DatosEstudianteReporte(
                cedula=matricula.estudiante.cedula,
                nombres_completos=matricula.estudiante.get_full_name(),
                paralelo_codigo=matricula.paralelo.codigo,
                materia_nombre=matricula.paralelo.materia.nombre,
                promedio_final=promedio,
                porcentaje_asistencia=asistencia.porcentaje,
                estado=estado,
                calificaciones_por_parcial=libreta.get_notas_por_evaluacion(matricula.paralelo_id),
            ))
        return datos

    def _construir_elementos_pdf(self, datos, totales, hash_footer=None):
        """Builds the reportlab elements (header, table, footer with hash and signature)."""
        styles = getSampleStyleSheet()
        elements = []

        # Encabezado
        elements.append(Paragraph("ESCUELA DE CAPACITACIÓN DE POLICÍA PROFESIONAL", styles["Title"]))
        elements.append(Paragraph("REPORTE NORMATIVO — RESOLUCIÓN 005-DIR-2022 (ANT)", styles["Heading2"]))
        elements.append(Paragraph(f"Período académico: {self.periodo.nombre} ({self.periodo.codigo})", styles["Normal"]))
        elements.append(Paragraph(f"Fecha de generación: {datetime.now():%d/%m/%Y %H:%M}", styles["Normal"]))
        elements.append(Spacer(1, 0.5 * cm))

        # Resumen
        elements.append(Paragraph(
            f"<b>Total estudiantes:</b> {totales['total']} &nbsp;&nbsp; "
            f"<b>Aprobados:</b> {totales['aprobados']} &nbsp;&nbsp; "
            f"<b>Reprobados:</b> {totales['reprobados']} &nbsp;&nbsp; "
            f"<b>En curso:</b> {totales['en_curso']} &nbsp;&nbsp; "
            f"<b>Desertores:</b> {totales['desertores']}",
            styles["Normal"]
        ))
        elements.append(Spacer(1, 0.5 * cm))

        # Tabla de datos
        header = ["Cédula", "Nombres", "Paralelo", "Materia", "Promedio", "Asist. %", "Estado"]
        rows = [header]
        for d in datos:
            rows.append([
                d.cedula,
                d.nombres_completos,
                d.paralelo_codigo,
                d.materia_nombre[:40],
                f"{d.promedio_final:.2f}" if d.promedio_final else "—",
                f"{d.porcentaje_asistencia:.1f}%",
                d.estado.upper(),
            ])

        table = Table(rows, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 1 * cm))

        # Firma
        if self.firma_path:
            elements.append(Image(self.firma_path, width=4 * cm, height=1.5 * cm))
        elements.append(Paragraph(
            f"___________________________________<br/>"
            f"<b>{self.generado_por.get_full_name()}</b><br/>"
            f"C.C. {self.generado_por.cedula}<br/>"
            f"Director Académico ECPPP",
            styles["Normal"]
        ))
        elements.append(Spacer(1, 0.5 * cm))

        # Hash de integridad
        if hash_footer:
            elements.append(Paragraph(
                f"<font size=7 color='grey'>Hash SHA-256 (verificación de integridad):<br/>"
                f"{hash_footer}</font>",
                styles["Normal"]
            ))

        if self.notas:
            elements.append(Spacer(1, 0.5 * cm))
            elements.append(Paragraph(f"<b>Notas:</b> {self.notas}", styles["Normal"]))

        return elements
```

**Vista de generación y descarga:**

```python
# apps/reportes/presentation/views.py
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views import View
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

class ReporteANTListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """List of generated ANT reports."""
    template_name = "reportes/ant/listado.html"
    context_object_name = "reportes"
    paginate_by = 20

    def test_func(self):
        return self.request.user.rol in ["inspector", "secretaria", "director_academico"]

    def get_queryset(self):
        return ReporteANT.objects.all().order_by("-fecha_generacion")


class ReporteANTGenerarView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Generate a new ANT report for a period."""

    def test_func(self):
        return self.request.user.rol in ["secretaria", "director_academico"]

    def post(self, request):
        periodo_id = request.POST.get("periodo_id")
        notas = request.POST.get("notas", "")
        firma_path = request.POST.get("firma_path", "")

        periodo = get_object_or_404(PeriodoAcademico, pk=periodo_id)

        service = ReporteANTGeneratorService(
            periodo=periodo,
            generado_por=request.user,
            firma_path=firma_path or None,
            notas=notas,
        )
        reporte = service.generar()
        messages.success(request, f"Reporte ANT generado ({reporte.total_estudiantes} estudiantes).")
        return redirect("reporte_ant_listado")


class ReporteANTDescargarView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Download the generated PDF."""

    def test_func(self):
        return self.request.user.rol in ["inspector", "secretaria", "director_academico"]

    def get(self, request, reporte_id):
        reporte = get_object_or_404(ReporteANT, pk=reporte_id)
        if not reporte.archivo_pdf:
            raise Http404("Archivo no disponible")
        return FileResponse(
            reporte.archivo_pdf.open("rb"),
            as_attachment=True,
            filename=os.path.basename(reporte.archivo_pdf.name),
        )


class ReporteANTVerificarHashView(LoginRequiredMixin, View):
    """Verify the integrity hash of a stored PDF."""

    def get(self, request, reporte_id):
        reporte = get_object_or_404(ReporteANT, pk=reporte_id)
        contenido = reporte.archivo_pdf.read()
        hash_actual = ReporteANTService.computar_hash_contenido(contenido)
        coincide = hash_actual == reporte.hash_sha256
        return JsonResponse({
            "hash_almacenado": reporte.hash_sha256,
            "hash_actual": hash_actual,
            "integridad_valida": coincide,
        })
```

**Criterios de aceptación:**
- [ ] Modelo `ReporteANT` con migración.
- [ ] App `reportes` con estructura DDD completa.
- [ ] Endpoint POST `/reportes/ant/generar/` accesible para `secretaria` y `director_academico`.
- [ ] Reporte PDF generado con encabezado institucional, tabla de estudiantes, totales, firma y hash.
- [ ] Hash SHA-256 calculado y almacenado; el endpoint `/reportes/ant/<id>/verificar-hash/` retorna si el PDF actual coincide con el hash guardado.
- [ ] Reporte regenerable (no se sobreescriben los anteriores, se crea un nuevo registro).
- [ ] Listado de reportes generados accesible para inspector/secretaría/director académico.
- [ ] Descarga segura del PDF con `FileResponse`.
- [ ] Servicio `ReporteANTService` con tests unitarios (cálculo de estado, hash).
- [ ] Tests de generación de PDF (verificar que el archivo se crea y no está vacío).

**Branch:** `feature/HU26-reportes-ant`

---

### 4.2 HU27 — Exportación masiva PDF/Excel

**Propósito:** Permitir la descarga masiva de listados de calificaciones (libretas) y asistencia en formatos PDF y Excel, con filtros combinables para análisis y reportes externos.

**Reglas de negocio:**
- Filtros aplicables: período académico, materia, paralelo, estado de registro (borrador/completo/validado), estudiante individual.
- **Libreta de calificaciones (PDF/Excel):** un archivo por estudiante o un consolidado por paralelo.
- **Listado de asistencia (PDF/Excel):** consolidado por paralelo con % de asistencia por estudiante.
- Archivos generados on-demand (no se persisten en DB, se descargan directamente).
- El header del archivo incluye: nombre ECPPP, período, filtros aplicados, fecha de generación, usuario que generó.
- Excel: una hoja por paralelo (formato `.xlsx` con `openpyxl`).
- PDF: tabla con `reportlab`, encabezado en cada página.
- Rate limit: máximo 10 exportaciones por minuto por usuario (para no saturar el servidor).
- Solo roles `docente`, `inspector`, `secretaria`, `director_academico` pueden exportar.

**Servicio de aplicación — Exportación:**

```python
# apps/reportes/application/services.py
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors

class ExportacionCalificacionesService:
    """Exports grade reports to PDF and Excel."""

    def __init__(self, filtros: dict, usuario):
        self.filtros = filtros  # {periodo_id, materia_id, paralelo_id, estudiante_id, estado}
        self.usuario = usuario
        self.periodo = get_object_or_404(PeriodoAcademico, pk=filtros["periodo_id"])

    def exportar_excel_calificaciones(self) -> BytesIO:
        """Generates an Excel file with grades, one sheet per paralelo."""
        wb = Workbook()
        wb.remove(wb.active)  # remove default sheet

        paralelos = self._filtrar_paralelos()
        for paralelo in paralelos:
            ws = wb.create_sheet(title=paralelo.codigo[:31])
            self._llenar_hoja_calificaciones(ws, paralelo)

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer

    def _llenar_hoja_calificaciones(self, ws, paralelo):
        """Fills an Excel sheet with grades for a paralelo."""
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill("solid", fgColor="1E3A8A")

        # Header
        ws.append([f"ECPPP — {self.periodo.nombre}"])
        ws.append([f"Paralelo: {paralelo.codigo} — {paralelo.materia.nombre}"])
        ws.append([f"Generado: {timezone.now():%d/%m/%Y %H:%M} por {self.usuario.get_full_name()}"])
        ws.append([])

        # Column headers
        evaluaciones = paralelo.evaluaciones.order_by("orden")
        header_row = ["Cédula", "Nombres"] + [e.nombre for e in evaluaciones] + ["Promedio", "Estado"]
        ws.append(header_row)
        for col_idx in range(1, len(header_row) + 1):
            cell = ws.cell(row=ws.max_row, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")

        # Data
        matriculas = paralelo.matriculas.filter(activa=True).select_related("estudiante")
        for matricula in matriculas:
            row = [matricula.estudiante.cedula, matricula.estudiante.get_full_name()]
            notas = []
            for ev in evaluaciones:
                calif = Calificacion.objects.filter(
                    evaluacion=ev, estudiante=matricula.estudiante
                ).first()
                nota = float(calif.nota) if calif else None
                row.append(nota if nota is not None else "—")
                if nota is not None:
                    notas.append((Decimal(str(nota)), ev.peso))
            promedio = PromedioCalculoService.calcular_promedio_ponderado(notas) if notas else None
            estado = CalificacionValidationService.estado_aprobacion(promedio) if promedio else "en_curso"
            row.append(float(promedio) if promedio else "—")
            row.append(estado.upper())
            ws.append(row)

        # Auto-size columns
        for col in ws.columns:
            max_length = max((len(str(c.value)) for c in col if c.value is not None), default=10)
            ws.column_dimensions[col[0].column_letter].width = min(max_length + 2, 50)

    def exportar_pdf_calificaciones(self) -> BytesIO:
        """Generates a PDF with grades (consolidated, landscape A4)."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
        elements = []
        # ... similar structure to ANT report but per paralelo
        # (omitted for brevity — follows same reportlab pattern)
        doc.build(elements)
        buffer.seek(0)
        return buffer


class ExportacionAsistenciaService:
    """Exports attendance reports to PDF and Excel."""

    def exportar_excel_asistencia(self) -> BytesIO:
        """Generates an Excel file with attendance percentages per paralelo."""
        # Similar structure to grades export but with attendance data
        # ...
        pass
```

**Vistas y URLs:**

```python
# apps/reportes/presentation/views.py
class ExportarCalificacionesView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Export grades to PDF or Excel."""

    def test_func(self):
        return self.request.user.rol in ["docente", "inspector", "secretaria", "director_academico"]

    def get(self, request):
        formato = request.GET.get("formato", "excel")  # "excel" | "pdf"
        filtros = {
            "periodo_id": request.GET.get("periodo"),
            "materia_id": request.GET.get("materia"),
            "paralelo_id": request.GET.get("paralelo"),
            "estudiante_id": request.GET.get("estudiante"),
            "estado": request.GET.get("estado"),
        }

        service = ExportacionCalificacionesService(filtros, request.user)
        if formato == "excel":
            buffer = service.exportar_excel_calificaciones()
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"calificaciones_{timezone.now():%Y%m%d_%H%M}.xlsx"
        else:
            buffer = service.exportar_pdf_calificaciones()
            content_type = "application/pdf"
            filename = f"calificaciones_{timezone.now():%Y%m%d_%H%M}.pdf"

        response = HttpResponse(buffer.read(), content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class ExportarAsistenciaView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Export attendance to PDF or Excel."""
    # Similar structure
    pass
```

**Rate limiting:**

```python
# apps/reportes/application/services.py
from django.core.cache import cache
from django.utils import timezone

class ExportacionRateLimiter:
    """Limits exports to 10/minute per user."""

    MAX_POR_MINUTO = 10
    WINDOW_SEGUNDOS = 60

    @classmethod
    def check(cls, usuario_id: int) -> bool:
        key = f"export_rate_{usuario_id}_{timezone.now().strftime('%Y%m%d%H%M')}"
        count = cache.get(key, 0)
        if count >= cls.MAX_POR_MINUTO:
            return False
        cache.set(key, count + 1, timeout=cls.WINDOW_SEGUNDOS)
        return True
```

**Criterios de aceptación:**
- [ ] Endpoint GET `/reportes/calificaciones/exportar/?formato=excel|pdf&periodo=X&paralelo=Y` accesible para docente/inspector/secretaría/director académico.
- [ ] Endpoint similar `/reportes/asistencia/exportar/` para asistencia.
- [ ] Excel generado con `openpyxl`: una hoja por paralelo, columnas por evaluación, promedio y estado.
- [ ] PDF generado con `reportlab`: tabla landscape A4, encabezado en cada página.
- [ ] Filtros combinables: período, materia, paralelo, estado.
- [ ] Rate limiting: 10 exportaciones/minuto (retorna HTTP 429 si excede).
- [ ] Header del archivo con metadatos: ECPPP, período, filtros, fecha, usuario.
- [ ] Tests: generación de Excel, generación de PDF, rate limiting, filtros.

**Branch:** `feature/HU27-exportacion-pdf-excel`

---

### 4.3 HU28 — Dashboard de cierre de período

**Propósito:** Vista resumen final del período académico con tasas consolidadas de aprobación, reprobación, deserción y promedio general, accesible para inspector y director académico como herramienta de cierre institucional.

**Reglas de negocio:**
- Accesible para roles `inspector` y `director_academico` (solo lectura para el director).
- Muestra datos del período seleccionado (default: período activo más reciente cerrado).
- KPIs principales: total estudiantes, total paralelos, % aprobación, % reprobación, % deserción, promedio general institucional.
- Gráfico de torta: distribución de estados finales (Aprobado/Reprobado/En curso/Desertor).
- Tabla por paralelo: código, materia, docente, # estudiantes, promedio, % aprobación, % asistencia, estado.
- Gráfico de barras: comparativa de promedios por materia.
- Botón "Generar reporte ANT" (integra con HU26) si el usuario tiene permisos.
- Vista de solo lectura: no hay acciones de modificación, solo consulta y exportación.

**Servicio de dominio — Cálculo de cierre:**

```python
# apps/academico/domain/services.py
from dataclasses import dataclass
from decimal import Decimal

@dataclass
class CierrePeriodoMetricas:
    """Consolidated metrics for a period's closing dashboard."""
    periodo_id: int
    periodo_nombre: str
    total_estudiantes: int
    total_paralelos: int
    promedio_general_institucional: Decimal
    tasa_aprobacion: Decimal  # 0-100
    tasa_reprobacion: Decimal
    tasa_desercion: Decimal
    tasa_en_curso: Decimal
    total_aprobados: int
    total_reprobados: int
    total_desertores: int
    total_en_curso: int
    paralelos: list  # list of MetricasParalelo (from S4)


class CierrePeriodoService:
    """Computes the final period metrics for the closing dashboard."""

    @staticmethod
    def calcular_metricas_cierre(periodo) -> CierrePeriodoMetricas:
        """Aggregates all period-level metrics."""
        # Reuse services from HU23 (RendimientoAcademicoService) and HU26 (ReporteANTService)
        # ...
        pass
```

**Servicio de aplicación:**

```python
# apps/academico/application/services.py
class CierrePeriodoAppService:
    """Orchestrates the closing dashboard data."""

    def obtener_dashboard_cierre(self, periodo_id: int) -> dict:
        periodo = get_object_or_404(PeriodoAcademico, pk=periodo_id)
        metricas = CierrePeriodoService.calcular_metricas_cierre(periodo)

        # Gráfico de torta: distribución de estados
        data_torta = {
            "labels": ["Aprobados", "Reprobados", "En curso", "Desertores"],
            "values": [
                metricas.total_aprobados,
                metricas.total_reprobados,
                metricas.total_en_curso,
                metricas.total_desertores,
            ],
        }

        # Gráfico de barras: promedio por materia
        promedios_por_materia = (
            Calificacion.objects
            .filter(evaluacion__paralelo__periodo=periodo)
            .values("evaluacion__paralelo__materia__nombre")
            .annotate(promedio=Avg("nota"))
        )
        data_barras = {
            "labels": [m["evaluacion__paralelo__materia__nombre"] for m in promedios_por_materia],
            "values": [float(m["promedio"]) for m in promedios_por_materia],
        }

        return {
            "metricas": metricas,
            "data_torta": data_torta,
            "data_barras": data_barras,
        }
```

**Vista:**

```python
# apps/academico/presentation/views.py
class CierrePeriodoDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Closing period dashboard for inspector and director académico."""

    template_name = "academico/cierre_periodo.html"

    def test_func(self):
        return self.request.user.rol in ["inspector", "director_academico"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        periodo_id = self.request.GET.get("periodo")

        if not periodo_id:
            periodo_activo = PeriodoAcademico.objects.filter(estado="cerrado").order_by("-fecha_fin").first()
            if not periodo_activo:
                periodo_activo = PeriodoAcademico.objects.filter(activo=True).first()
            periodo_id = periodo_activo.id if periodo_activo else None

        if periodo_id:
            service = CierrePeriodoAppService()
            context["dashboard_data"] = service.obtener_dashboard_cierre(periodo_id)
            context["periodo_seleccionado"] = get_object_or_404(PeriodoAcademico, pk=periodo_id)

        context["periodos"] = PeriodoAcademico.objects.all().order_by("-fecha_inicio")
        return context
```

**Template — Cards de resumen:**

```html
<!-- templates/academico/cierre_periodo.html -->
<div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
    <div class="card bg-green-50 border-l-4 border-green-500 p-4">
        <h3 class="text-sm text-gray-600">Tasa de Aprobación</h3>
        <p class="text-3xl font-bold text-green-700" x-text="`${metricas.tasa_aprobacion}%`"></p>
    </div>
    <div class="card bg-red-50 border-l-4 border-red-500 p-4">
        <h3 class="text-sm text-gray-600">Tasa de Reprobación</h3>
        <p class="text-3xl font-bold text-red-700" x-text="`${metricas.tasa_reprobacion}%`"></p>
    </div>
    <div class="card bg-yellow-50 border-l-4 border-yellow-500 p-4">
        <h3 class="text-sm text-gray-600">Tasa de Deserción</h3>
        <p class="text-3xl font-bold text-yellow-700" x-text="`${metricas.tasa_desercion}%`"></p>
    </div>
    <div class="card bg-blue-50 border-l-4 border-blue-500 p-4">
        <h3 class="text-sm text-gray-600">Promedio General</h3>
        <p class="text-3xl font-bold text-blue-700" x-text="`${metricas.promedio_general_institucional}`"></p>
    </div>
</div>

<!-- Charts -->
<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
    <canvas id="chart-estados" x-data="chartEstados($store.dashboard.data_torta)"></canvas>
    <canvas id="chart-materias" x-data="chartMaterias($store.dashboard.data_barras)"></canvas>
</div>
```

**Criterios de aceptación:**
- [ ] Vista `/academico/cierre-periodo/` accesible para inspector y director académico.
- [ ] 4 cards KPI: tasa aprobación, reprobación, deserción, promedio general.
- [ ] Gráfico de torta: distribución de estados finales.
- [ ] Gráfico de barras: promedio por materia.
- [ ] Tabla por paralelo con métricas detalladas.
- [ ] Filtro por período académico (default: último período cerrado o activo).
- [ ] Director académico solo ve la vista en modo lectura (sin botones de acción).
- [ ] Botón "Generar reporte ANT" visible solo para roles con permiso (integra HU26).
- [ ] Servicio `CierrePeriodoService` con tests unitarios.
- [ ] Tests de vista y datos.

**Branch:** `feature/HU28-dashboard-cierre-periodo`

---

### 4.4 HU29 — Documentación técnica final

**Propósito:** Producir la documentación técnica completa del proyecto para tres audiencias distintas: desarrolladores/soporte, DBA/soporte, y usuarios finales. Es el entregable de cierre de proyecto y debe reflejar el estado real del sistema desplegado.

**Reglas de negocio:**
- **3 manuales independientes**, cada uno con su propio archivo Markdown (y exportación PDF opcional):
  1. **Manual de Arquitectura** — para devs/soporte técnico
  2. **Manual de Base de Datos** — para DBA/soporte
  3. **Manual de Usuario** — para usuarios finales (estudiantes, docentes, inspectores, secretaría, director académico)
- Cada manual debe estar versionado y fechado.
- Los manuales deben basarse en el **código real** del proyecto, no en suposiciones.
- El manual de usuario incluye capturas de pantalla de las vistas principales.
- Los manuales están en `docs/manuales/` y se incluyen en el repositorio.

**Estructura de cada manual:**

#### 4.4.1 Manual de Arquitectura (`docs/manuales/ARQUITECTURA.md`)

**Contenido:**
1. Visión general del sistema
2. Stack tecnológico (Django, PostgreSQL, Redis, Alpine.js, etc.)
3. Patrón de arquitectura: **DDD con Django Apps** (Domain → Application → Infrastructure → Presentation)
4. Estructura del proyecto (árbol de directorios)
5. Apps del sistema y su responsabilidad
6. Decisiones de arquitectura (ADR resumidos — referencia a `docs/ADR-ECPPP.md`)
7. Modelo de datos (ER diagram + descripción de entidades)
8. Flujos principales (diagramas de secuencia ASCII)
9. Seguridad: autenticación, autorización, control de acceso
10. Performance: caching, rate limiting, optimización de queries
11. Deployment (referencia a HU30)
12. Convenciones de código (PEP 8, Black, flake8, naming, commits)

#### 4.4.2 Manual de Base de Datos (`docs/manuales/BASE_DE_DATOS.md`)

**Contenido:**
1. Stack: PostgreSQL 15+
2. Diagrama ER (imagen + descripción)
3. Tabla por tabla: nombre, propósito, columnas, tipos, índices, constraints
4. Migraciones: cómo aplicarlas, cómo revertir, convenciones de naming
5. Seeds: management commands disponibles (`seed_sprint3`, `seed_sprint4`)
6. Backups: estrategia, comandos, restauración
7. Performance: índices recomendados, queries optimizadas, vacuum
8. Acceso: configuración de conexión, pool de conexiones (pgbouncer)
9. Troubleshooting: problemas comunes y soluciones

#### 4.4.3 Manual de Usuario (`docs/manuales/MANUAL_USUARIO.md`)

**Contenido por rol:**
- **Estudiante:** login, ver libreta, solicitar recalificación, justificar inasistencia, usar copilot
- **Docente:** login, registrar calificaciones (con 3–5 sub-notas), responder solicitudes, consultar paralelos
- **Inspector:** dashboard de justificaciones, dashboard de rendimiento, dashboard de cierre, ver logs de auditoría
- **Secretaría:** validar calificaciones, validar solicitudes escaladas, generar reportes ANT
- **Director Académico:** todos los dashboards en modo lectura, descarga de reportes

**Estructura de cada sección:**
- Objetivo
- Captura de pantalla (anotada)
- Paso a paso numerado
- Errores comunes
- Dónde pedir ayuda

**Criterios de aceptación:**
- [ ] Archivo `docs/manuales/ARQUITECTURA.md` creado (≥ 500 líneas, refleja el sistema real).
- [ ] Archivo `docs/manuales/BASE_DE_DATOS.md` creado (≥ 400 líneas, con diagrama ER en Mermaid).
- [ ] Archivo `docs/manuales/MANUAL_USUARIO.md` creado (≥ 600 líneas, con capturas de pantalla).
- [ ] Los manuales referencian archivos del código real (ej. `apps/calificaciones/domain/services.py:42`).
- [ ] Cada manual tiene fecha de última actualización y versión.
- [ ] Los manuales están enlazados desde el `README.md` principal.
- [ ] Capturas de pantalla de: login, dashboard estudiante, planilla docente, dashboard inspector, dashboard cierre, generación reporte ANT.

**Branch:** `feature/HU29-documentacion-final`

---

### 4.5 HU30 — Despliegue en VPS y Backups automatizados

**Propósito:** Realizar el despliegue completo de la plataforma ECPPP en un **VPS institucional** con todos los servicios necesarios (PostgreSQL, Redis, Nginx, Gunicorn), configurar SSL con Let's Encrypt, automatizar backups y aplicar hardening de seguridad. Esta HU es la **operación de cierre del proyecto** y requiere una guía paso a paso detallada.

#### 4.5.1 Arquitectura del despliegue

```
                    Internet
                       │
                       ▼
            ┌─────────────────────┐
            │  DNS (ecppp.edu.ec) │
            └──────────┬──────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │   Nginx (puerto 443)│  ← SSL termination, static files
            │   Nginx (puerto 80) │  ← redirect to HTTPS
            └──────────┬──────────┘
                       │ proxy_pass
                       ▼
            ┌─────────────────────┐
            │  Gunicorn (systemd) │  ← WSGI server (3 workers)
            │  unix socket        │
            └──────────┬──────────┘
                       │
              ┌────────┴────────┐
              ▼                 ▼
    ┌──────────────────┐  ┌──────────────┐
    │  Django App      │  │  Redis       │  ← cache, session
    │  (Python 3.11)   │  │  (puerto     │
    └────────┬─────────┘  │   6379 local)│
             │            └──────────────┘
             ▼
    ┌──────────────────┐
    │  PostgreSQL 15   │  ← DB principal
    │  (puerto 5432    │
    │   solo localhost)│
    └──────────────────┘

    Backups (cron):
    - pg_dump cada 6h → /var/backups/ecppp/db/
    - media/ cada 12h → /var/backups/ecppp/media/
    - Retención: 30 días
```

#### 4.5.2 Requisitos del VPS

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 4 GB | 8 GB |
| Disco | 80 GB SSD | 160 GB SSD |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
| Ancho de banda | 1 TB/mes | 2 TB/mes |
| IP | 1 IPv4 pública | 1 IPv4 + 1 IPv6 |

#### 4.5.3 Guía paso a paso del despliegue

> **Nota:** Todos los comandos asumen acceso SSH con usuario `deploy` y sudo. Adaptar paths/usuarios según la infraestructura institucional.

##### Paso 1 — Hardening inicial del servidor

```bash
# Conectar como root
ssh root@<IP_VPS>

# Actualizar sistema
apt update && apt upgrade -y

# Crear usuario deploy (no root)
adduser deploy
usermod -aG sudo deploy

# Configurar SSH key para deploy
mkdir -p /home/deploy/.ssh
# Pegar la clave pública del desarrollador
nano /home/deploy/.ssh/authorized_keys
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys
chown -R deploy:deploy /home/deploy/.ssh

# Deshabilitar login por password (solo key)
nano /etc/ssh/sshd_config
# PasswordAuthentication no
# PermitRootLogin no
systemctl restart sshd

# Configurar firewall (UFW)
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp   # HTTP (para Let's Encrypt)
ufw allow 443/tcp  # HTTPS
ufw enable
ufw status

# Instalar fail2ban
apt install -y fail2ban
systemctl enable fail2ban
systemctl start fail2ban
cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
# Configurar (opcional) en /etc/fail2ban/jail.local
```

##### Paso 2 — Instalar PostgreSQL 15

```bash
# Instalar PostgreSQL
apt install -y postgresql postgresql-contrib libpq-dev

# Verificar versión
sudo -u postgres psql -c "SELECT version();"

# Crear base de datos y usuario para ECPPP
sudo -u postgres psql <<EOF
CREATE USER ecppp_user WITH PASSWORD 'CAMBIAR_PASSWORD_SEGURO';
CREATE DATABASE ecppp_db OWNER ecppp_user ENCODING 'UTF8';
GRANT ALL PRIVILEGES ON DATABASE ecppp_db TO ecppp_user;
\c ecppp_db
GRANT ALL ON SCHEMA public TO ecppp_user;
EOF

# Configurar PostgreSQL para conexiones locales
nano /etc/postgresql/15/main/postgresql.conf
# listen_addresses = 'localhost'  # solo local
# max_connections = 200
# shared_buffers = 256MB  # 25% de RAM
# effective_cache_size = 768MB  # 75% de RAM
# work_mem = 4MB
# maintenance_work_mem = 128MB

nano /etc/postgresql/15/main/pg_hba.conf
# local   ecppp_db   ecppp_user   md5
# host    ecppp_db   ecppp_user   127.0.0.1/32   md5

systemctl restart postgresql
```

##### Paso 3 — Instalar Redis

```bash
apt install -y redis-server
nano /etc/redis/redis.conf
# bind 127.0.0.1
# requirepass CAMBIAR_PASSWORD_REDIS
# maxmemory 256mb
# maxmemory-policy allkeys-lru
systemctl restart redis
redis-cli -a CAMBIAR_PASSWORD_REDIS ping  # debe responder PONG
```

##### Paso 4 — Instalar Python y dependencias del sistema

```bash
apt install -y python3.11 python3.11-venv python3-pip \
               build-essential libssl-dev libffi-dev \
               nginx certbot python3-certbot-nginx \
               git curl

# Verificar
python3.11 --version
nginx -v
certbot --version
```

##### Paso 5 — Clonar repositorio y preparar entorno

```bash
# Como usuario deploy
su - deploy

# Clonar repo
git clone git@github.com:ecppp/proyecto-ecpp.git /home/deploy/proyecto-ecpp
cd /home/deploy/proyecto-ecpp

# Crear entorno virtual
python3.11 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements/production.txt
pip install gunicorn psycopg2-binary redis

# Crear directorios necesarios
mkdir -p logs media staticfiles backups

# Configurar .env
cp .env.example .env
nano .env
```

**Contenido de `.env` (producción):**

```env
# Django
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=GENERAR_CON secrets.token_urlsafe(50)
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=ecppp.edu.ec,www.ecppp.edu.ec,<IP_VPS>

# Database
DATABASE_URL=postgres://ecppp_user:PASSWORD@localhost:5432/ecppp_db

# Redis
REDIS_URL=redis://:PASSWORD_REDIS@127.0.0.1:6379/0

# Email (SMTP institucional)
EMAIL_HOST=smtp.ecppp.edu.ec
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=no-reply@ecppp.edu.ec
EMAIL_HOST_PASSWORD=EMAIL_PASSWORD
DEFAULT_FROM_EMAIL=no-reply@ecppp.edu.ec

# OpenAI (para copilot)
OPENAI_API_KEY=sk-...

# Session timeout (HU31)
SESSION_COOKIE_AGE=1200  # 20 minutos
SESSION_SAVE_EVERY_REQUEST=False  # usa last_activity explícito
```

**`config/settings/production.py` — ajustes clave:**

```python
from .base import *
import os

DEBUG = False
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Database
DATABASES = {
    "default": env.db("DATABASE_URL"),
}
DATABASES["default"]["CONN_MAX_AGE"] = 600  # connection pooling

# Cache (Redis)
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "ecppp",
    }
}

# Static files
STATIC_ROOT = BASE_DIR / "staticfiles"
STATIC_URL = "/static/"
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "logs" / "django.log",
        },
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": True,
        },
    },
}
```

##### Paso 6 — Migrar base de datos y collectstatic

```bash
# Migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Recolectar static files
python manage.py collectstatic --noinput

# (Opcional) Cargar datos de demo para instituciones nuevas
python manage.py seed_sprint4
```

##### Paso 7 — Configurar Gunicorn (systemd)

```bash
# Crear archivo de socket
sudo nano /etc/systemd/system/gunicorn.socket
```

```ini
[Unit]
Description=gunicorn socket for ecppp

[Socket]
ListenStream=/run/gunicorn.sock
SocketUser=www-data

[Install]
WantedBy=sockets.target
```

```bash
# Crear servicio
sudo nano /etc/systemd/system/gunicorn.service
```

```ini
[Unit]
Description=gunicorn daemon for ecppp
Requires=gunicorn.socket
After=network.target

[Service]
Type=notify
User=deploy
Group=deploy
WorkingDirectory=/home/deploy/proyecto-ecpp
EnvironmentFile=/home/deploy/proyecto-ecpp/.env
ExecStart=/home/deploy/proyecto-ecpp/venv/bin/gunicorn \
    --access-logfile /home/deploy/proyecto-ecpp/logs/access.log \
    --error-logfile /home/deploy/proyecto-ecpp/logs/error.log \
    --workers 3 \
    --worker-class sync \
    --timeout 60 \
    --bind unix:/run/gunicorn.sock \
    config.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

```bash
# Activar
sudo systemctl daemon-reload
sudo systemctl start gunicorn.socket
sudo systemctl enable gunicorn.socket
sudo systemctl status gunicorn.socket

# Verificar
curl --unix-socket /run/gunicorn.sock http://localhost/  # debe responder
```

##### Paso 8 — Configurar Nginx

```bash
sudo nano /etc/nginx/sites-available/ecppp
```

```nginx
upstream gunicorn_ecppp {
    server unix:/run/gunicorn.sock fail_timeout=0;
}

server {
    listen 80;
    server_name ecppp.edu.ec www.ecppp.edu.ec;

    # Redirect to HTTPS (after certbot is configured)
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name ecppp.edu.ec www.ecppp.edu.ec;

    client_max_body_size 20M;  # permite uploads hasta 20MB

    ssl_certificate /etc/letsencrypt/live/ecppp.edu.ec/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ecppp.edu.ec/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Logs
    access_log /var/log/nginx/ecppp_access.log;
    error_log /var/log/nginx/ecppp_error.log;

    # Static files
    location /static/ {
        alias /home/deploy/proyecto-ecpp/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /home/deploy/proyecto-ecpp/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    # Django app
    location / {
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_pass http://gunicorn_ecppp;
    }
}
```

```bash
# Activar sitio
sudo ln -s /etc/nginx/sites-available/ecppp /etc/nginx/sites-enabled/
sudo nginx -t  # verificar sintaxis
sudo systemctl restart nginx
```

##### Paso 9 — Configurar SSL con Let's Encrypt

```bash
# Obtener certificado (asume DNS ya propagado)
sudo certbot --nginx -d ecppp.edu.ec -d www.ecppp.edu.ec \
    --non-interactive --agree-tos -m admin@ecppp.edu.ec

# Verificar renovación automática
sudo certbot renew --dry-run
```

##### Paso 10 — Configurar backups automatizados

```bash
# Crear directorios de backup
sudo mkdir -p /var/backups/ecppp/{db,media}
sudo chown deploy:deploy /var/backups/ecppp

# Script de backup de DB
nano /home/deploy/proyecto-ecpp/scripts/backup_db.sh
```

```bash
#!/bin/bash
# Backup de PostgreSQL
set -e
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/var/backups/ecppp/db
BACKUP_FILE="$BACKUP_DIR/ecppp_db_$TIMESTAMP.sql.gz"

# Extraer password del .env
source /home/deploy/proyecto-ecpp/.env
DB_PASSWORD=$(echo $DATABASE_URL | sed -E 's|.*://[^:]+:([^@]+)@.*|\1|')

PGPASSWORD="$DB_PASSWORD" pg_dump -U ecppp_user -h localhost ecppp_db | gzip > "$BACKUP_FILE"

# Eliminar backups con más de 30 días
find "$BACKUP_DIR" -type f -name "*.sql.gz" -mtime +30 -delete

echo "Backup DB completado: $BACKUP_FILE"
```

```bash
# Script de backup de media
nano /home/deploy/proyecto-ecpp/scripts/backup_media.sh
```

```bash
#!/bin/bash
# Backup de archivos media
set -e
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/var/backups/ecppp/media
MEDIA_DIR=/home/deploy/proyecto-ecpp/media
BACKUP_FILE="$BACKUP_DIR/media_$TIMESTAMP.tar.gz"

tar -czf "$BACKUP_FILE" -C "$(dirname $MEDIA_DIR)" "$(basename $MEDIA_DIR)"

# Eliminar backups con más de 30 días
find "$BACKUP_DIR" -type f -name "*.tar.gz" -mtime +30 -delete

echo "Backup media completado: $BACKUP_FILE"
```

```bash
# Hacer ejecutables
chmod +x /home/deploy/proyecto-ecpp/scripts/backup_*.sh

# Configurar cron
crontab -e
```

```cron
# Backup DB cada 6 horas
0 */6 * * * /home/deploy/proyecto-ecpp/scripts/backup_db.sh >> /home/deploy/proyecto-ecpp/logs/backup.log 2>&1

# Backup media cada 12 horas
0 */12 * * * /home/deploy/proyecto-ecpp/scripts/backup_media.sh >> /home/deploy/proyecto-ecpp/logs/backup.log 2>&1

# Renovar certificados Let's Encrypt (diario)
0 3 * * * certbot renew --quiet
```

##### Paso 11 — Monitoreo y mantenimiento

```bash
# Health check endpoint (agregar a urls.py)
# /health/ → retorna 200 si la app está OK

# Monitoreo básico con cron + health check
# Cada 5 min verifica que la app responda, reinicia si falla
crontab -e
```

```cron
*/5 * * * * curl -sf https://ecppp.edu.ec/health/ || systemctl restart gunicorn
```

##### Paso 12 — Script de deploy para futuras actualizaciones

```bash
nano /home/deploy/proyecto-ecpp/scripts/deploy.sh
```

```bash
#!/bin/bash
# Deploy script para futuras actualizaciones
set -e
cd /home/deploy/proyecto-ecpp

echo "→ Pulling latest code..."
git pull origin main

echo "→ Activating venv..."
source venv/bin/activate

echo "→ Installing new dependencies..."
pip install -r requirements/production.txt

echo "→ Running migrations..."
python manage.py migrate --noinput

echo "→ Collecting static files..."
python manage.py collectstatic --noinput

echo "→ Restarting Gunicorn..."
sudo systemctl restart gunicorn

echo "→ Reloading Nginx..."
sudo systemctl reload nginx

echo "✓ Deploy completado."
```

```bash
chmod +x /home/deploy/proyecto-ecpp/scripts/deploy.sh
```

#### 4.5.4 Checklist post-deploy

- [ ] `https://ecppp.edu.ec` carga correctamente.
- [ ] Login funciona con HTTPS.
- [ ] Archivos estáticos se sirven correctamente.
- [ ] Uploads de archivos (media) funcionan.
- [ ] Health check `/health/` retorna 200.
- [ ] Logs de Nginx y Gunicorn se están generando.
- [ ] Primer backup de DB se creó correctamente.
- [ ] Cron de backups está activo (`crontab -l`).
- [ ] SSL válido (calificación A+ en [SSL Labs](https://www.ssllabs.com/ssltest/)).
- [ ] Fail2ban activo (`fail2ban-client status`).
- [ ] Firewall UFW activo (`ufw status`).
- [ ] Test de smoke E2E: login → ver libreta → generar reporte ANT → exportar Excel.

**Branch:** `feature/HU30-deploy-vps` (con sub-rama de staging previa si la ECPPP lo requiere)

---

### 4.6 HU31 — Cierre de sesión por inactividad

**Propósito:** Cerrar la sesión del usuario automáticamente cuando supere el tiempo máximo de inactividad (configurable, default 20 minutos), mostrando un pop-up con Alpine.js que le notifique y lo redirija al login.

**Reglas de negocio:**
- Timeout configurable vía `SESSION_COOKIE_AGE` (default 20 minutos = 1200 segundos).
- El timeout se reinicia con CUALQUIER actividad del usuario (request AJAX, navegación, etc.).
- Al detectar inactividad en frontend (Alpine.js setInterval):
  - Mostrar pop-up de aviso a los **18 minutos** (2 minutos antes del cierre).
  - Pop-up tiene un countdown de 2 minutos + 2 botones: "Continuar sesión" / "Cerrar sesión".
  - Si el usuario no hace nada → a los 20 minutos: redirect a `/login/?session=expired`.
- Backend: middleware que valida `last_activity` en sesión con cada request.
- Aplican a TODOS los roles autenticados.
- Compatible con la lógica de "recordar sesión" de Django si está activa.

**Middleware:**

```python
# apps/usuarios/middleware.py
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils import timezone
from django.conf import settings
from django.urls import reverse

class SessionTimeoutMiddleware:
    """Logs out users who have been inactive for SESSION_COOKIE_AGE seconds."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.timeout_segundos = getattr(settings, "SESSION_TIMEOUT_SECONDS", 1200)
        self.aviso_segundos = getattr(settings, "SESSION_WARNING_SECONDS", 120)

    def __call__(self, request):
        if request.user.is_authenticated:
            last_activity = request.session.get("last_activity")
            ahora = timezone.now()

            if last_activity:
                inactivo = (ahora - timezone.datetime.fromisoformat(last_activity)).total_seconds()
                if inactivo > self.timeout_segundos:
                    logout(request)
                    return redirect(f"{reverse('login')}?session=expired")
                # Si está en zona de aviso (últimos N segundos)
                if inactivo > (self.timeout_segundos - self.aviso_segundos):
                    request.session["session_warning"] = True
            # Actualizar last_activity
            request.session["last_activity"] = ahora.isoformat()

        return self.get_response(request)
```

**Template — Pop-up Alpine.js:**

```html
<!-- templates/base.html — incluir antes de </body> -->
<div x-data="sessionTimeout()" x-init="init()">
    <!-- Pop-up de aviso -->
    <div x-show="warning" x-cloak
         class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
        <div class="bg-white rounded-lg shadow-2xl p-6 max-w-md w-full">
            <h3 class="text-xl font-bold text-red-600 mb-2">⚠️ Sesión por expirar</h3>
            <p class="text-gray-700 mb-4">
                Tu sesión expirará en <strong x-text="countdown"></strong> segundos por inactividad.
            </p>
            <p class="text-sm text-gray-600 mb-4">
                Si no realizas ninguna acción, serás redirigido al inicio de sesión.
            </p>
            <div class="flex gap-2 justify-end">
                <button @click="logout()"
                        class="px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300">
                    Cerrar sesión
                </button>
                <button @click="extend()"
                        class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                    Continuar sesión
                </button>
            </div>
        </div>
    </div>
</div>

<script>
function sessionTimeout() {
    return {
        warning: false,
        countdown: 120,  // 2 minutos
        timer: null,
        warningTimer: null,
        init() {
            // Verificar si el backend ya marcó warning
            const warningFlag = document.body.dataset.sessionWarning === 'true';
            if (warningFlag) {
                this.showWarning();
            }
            // Set timer para verificar periódicamente
            this.timer = setInterval(() => this.checkActivity(), 30000);  // cada 30s
            // Reset timer en cualquier interacción
            ['click', 'keypress', 'mousemove'].forEach(event => {
                document.addEventListener(event, () => this.resetCountdown(), { passive: true });
            });
        },
        showWarning() {
            this.warning = true;
            this.countdown = 120;
            this.countdownTimer = setInterval(() => {
                this.countdown--;
                if (this.countdown <= 0) {
                    clearInterval(this.countdownTimer);
                    this.logout();
                }
            }, 1000);
        },
        checkActivity() {
            // Hacer un ping al backend para verificar
            fetch('/api/session/check/', { credentials: 'same-origin' })
                .then(r => r.json())
                .then(data => {
                    if (data.warning && !this.warning) {
                        this.showWarning();
                    } else if (!data.warning && this.warning) {
                        this.extend();
                    }
                });
        },
        extend() {
            // Hacer un request para extender la sesión
            fetch('/api/session/extend/', { method: 'POST', credentials: 'same-origin' });
            this.warning = false;
            clearInterval(this.countdownTimer);
        },
        logout() {
            window.location.href = '/logout/';
        },
        resetCountdown() {
            if (!this.warning) {
                fetch('/api/session/touch/', { method: 'POST', credentials: 'same-origin' });
            }
        }
    }
}
</script>
```

**Endpoints de sesión:**

```python
# apps/usuarios/presentation/views.py
from django.http import JsonResponse
from django.utils import timezone
from django.conf import settings
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

@login_required
def session_check(request):
    """Returns whether session is about to expire."""
    last_activity = request.session.get("last_activity")
    if not last_activity:
        return JsonResponse({"warning": False, "expired": True})
    inactivo = (timezone.now() - timezone.datetime.fromisoformat(last_activity)).total_seconds()
    timeout = getattr(settings, "SESSION_TIMEOUT_SECONDS", 1200)
    warning_threshold = timeout - getattr(settings, "SESSION_WARNING_SECONDS", 120)
    return JsonResponse({
        "warning": inactivo >= warning_threshold,
        "expired": inactivo >= timeout,
        "remaining": max(0, timeout - int(inactivo)),
    })

@login_required
@require_POST
def session_extend(request):
    """Extends the session by updating last_activity."""
    request.session["last_activity"] = timezone.now().isoformat()
    return JsonResponse({"status": "ok"})

@login_required
@require_POST
def session_touch(request):
    """Touches the session on any user activity (lightweight endpoint)."""
    request.session["last_activity"] = timezone.now().isoformat()
    return JsonResponse({"status": "ok"})
```

**Criterios de aceptación:**
- [ ] Middleware `SessionTimeoutMiddleware` configurado en `MIDDLEWARE`.
- [ ] Variables de configuración: `SESSION_TIMEOUT_SECONDS=1200`, `SESSION_WARNING_SECONDS=120`.
- [ ] Pop-up Alpine.js aparece a los 18 minutos de inactividad con countdown.
- [ ] Pop-up tiene botones "Continuar sesión" y "Cerrar sesión".
- [ ] Si el usuario no hace nada en 2 minutos → redirect a `/login/?session=expired`.
- [ ] Cualquier actividad del usuario (click, keypress, mousemove) reinicia el contador.
- [ ] Endpoints `/api/session/check/`, `/api/session/extend/`, `/api/session/touch/` implementados.
- [ ] Login detecta parámetro `?session=expired` y muestra mensaje "Su sesión ha expirado por inactividad".
- [ ] Tests: middleware (sesión expirada, sesión válida), endpoints.

**Branch:** `feature/HU31-session-timeout`

---

### 4.7 HU32 — Notas 3–5 por parcial (Sub-notas dentro de cada parcial)

**Propósito:** Permitir al docente registrar entre 3 y 5 sub-notas dentro de cada parcial antes de consolidar la nota final del parcial. La nota final del parcial se calcula como promedio aritmético de las sub-notas, con la posibilidad de override manual.

**Reglas de negocio:**
- Cada `Evaluacion` de tipo `parcial1`, `parcial2_10h`, `parcial3`, `parcial4_10h` permite entre 3 y 5 sub-notas.
- Las sub-notas son definidas/configuradas por el docente al inicio del registro (nombres personalizables: "Tarea 1", "Exposición", "Quiz", etc.).
- La nota final del parcial se calcula como **promedio aritmético** de las sub-notas.
- El docente puede hacer **override manual** de la nota final (justificación obligatoria si difiere del promedio).
- Las sub-notas son editables mientras el registro del paralelo esté en `BORRADOR` (Sprint 3).
- Una vez enviado a validación (`COMPLETO`), las sub-notas se vuelven inmutables.
- El estudiante ve las sub-notas en su libreta, no solo la nota final.

**Modelo — Sub-nota:**

```python
# apps/calificaciones/infrastructure/models.py — extender
class SubNotaParcial(models.Model):
    """A sub-grade within a parcial. Each parcial allows 3-5 sub-grades."""

    evaluacion = models.ForeignKey(
        "calificaciones.Evaluacion", on_delete=models.CASCADE,
        related_name="sub_notas"
    )
    matricula = models.ForeignKey(
        "academico.Matricula", on_delete=models.CASCADE,
        related_name="sub_notas"
    )
    nombre = models.CharField(
        max_length=100,
        help_text="Nombre de la sub-nota (ej. 'Tarea 1', 'Exposición')"
    )
    nota = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("20"))]
    )
    orden = models.PositiveSmallIntegerField()
    nota_final_parcial_override = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Si difiere del promedio, override manual del docente"
    )
    justificacion_override = models.TextField(
        blank=True,
        help_text="Obligatoria si nota_final_parcial_override difiere del promedio"
    )

    class Meta:
        verbose_name = "Sub-Nota de Parcial"
        verbose_name_plural = "Sub-Notas de Parciales"
        ordering = ["evaluacion", "orden"]
        unique_together = [("evaluacion", "matricula", "orden")]
        constraints = [
            models.CheckConstraint(
                check=models.Q(nota__gte=0) & models.Q(nota__lte=20),
                name="sub_nota_rango_0_20"
            ),
        ]

    def __str__(self):
        return f"{self.matricula.estudiante} — {self.evaluacion} — {self.nombre}: {self.nota}"
```

**Servicio de dominio — Validación de cantidad de sub-notas:**

```python
# apps/calificaciones/domain/services.py
class SubNotaValidationService:
    """Validates sub-grades for parciales."""

    MIN_SUB_NOTAS = 3
    MAX_SUB_NOTAS = 5

    @classmethod
    def validar_cantidad(cls, cantidad: int) -> None:
        if not (cls.MIN_SUB_NOTAS <= cantidad <= cls.MAX_SUB_NOTAS):
            raise SubNotasFueraDeRangoError(cantidad, cls.MIN_SUB_NOTAS, cls.MAX_SUB_NOTAS)

    @staticmethod
    def calcular_nota_final_sub_notas(sub_notas: list[SubNotaParcial]) -> Decimal:
        """Average of sub-grades, rounded to 2 decimals."""
        if not sub_notas:
            return Decimal("0")
        total = sum(sn.nota for sn in sub_notas)
        return (total / len(sub_notas)).quantize(Decimal("0.01"))

    @staticmethod
    def requiere_justificacion_override(promedio: Decimal, override: Decimal) -> bool:
        """Override requires justification if it differs from the average."""
        return promedio != override
```

**Servicio de aplicación — Registro de sub-notas:**

```python
# apps/calificaciones/application/services.py
class SubNotaParcialAppService:
    """Orchestrates sub-grade registration for parciales."""

    def configurar_sub_notas_para_evaluacion(
        self, evaluacion: Evaluacion, nombres: list[str]
    ) -> None:
        """Configures the sub-grades for an evaluacion (3-5)."""
        SubNotaValidationService.validar_cantidad(len(nombres))
        # Eliminar configuración previa si existía
        ConfiguracionSubNotas.objects.filter(evaluacion=evaluacion).delete()
        config = ConfiguracionSubNotas.objects.create(evaluacion=evaluacion)
        for i, nombre in enumerate(nombres, start=1):
            SubNotaConfig.objects.create(
                configuracion=config, nombre=nombre, orden=i
            )

    def registrar_sub_notas(
        self, evaluacion: Evaluacion, matricula: Matricula, notas_data: list[dict]
    ) -> SubNotaParcial:
        """Registers sub-grades for a student in an evaluacion."""
        SubNotaValidationService.validar_cantidad(len(notas_data))

        # Eliminar sub-notas previas (si está en BORRADOR)
        SubNotaParcial.objects.filter(evaluacion=evaluacion, matricula=matricula).delete()

        sub_notas = []
        for i, nd in enumerate(notas_data, start=1):
            sub_nota = SubNotaParcial.objects.create(
                evaluacion=evaluacion,
                matricula=matricula,
                nombre=nd["nombre"],
                nota=Decimal(str(nd["nota"])),
                orden=i,
            )
            sub_notas.append(sub_nota)

        # Calcular nota final del parcial
        promedio = SubNotaValidationService.calcular_nota_final_sub_notas(sub_notas)
        Calificacion.objects.update_or_create(
            evaluacion=evaluacion,
            estudiante=matricula.estudiante,
            defaults={"nota": promedio},
        )

        return sub_notas
```

**Vista de UI — Planilla con sub-notas (Alpine.js):**

```html
<!-- template para docente: planilla con sub-notas expandibles -->
<div x-data="{ expanded: {} }">
    <table class="w-full">
        <thead>
            <tr>
                <th>Estudiante</th>
                <template x-for="ev in evaluaciones" :key="ev.id">
                    <th>
                        <button @click="expanded[ev.id] = !expanded[ev.id]">
                            <span x-text="ev.nombre"></span>
                            <span x-text="expanded[ev.id] ? '▼' : '▶'"></span>
                        </button>
                    </th>
                </template>
                <th>Promedio Final</th>
            </tr>
        </thead>
        <tbody>
            <template x-for="matricula in matriculas" :key="matricula.id">
                <tr>
                    <td x-text="matricula.estudiante.nombre"></td>
                    <template x-for="ev in evaluaciones" :key="ev.id">
                        <td>
                            <!-- Si está expandido, mostrar sub-notas -->
                            <div x-show="expanded[ev.id]" x-transition>
                                <template x-for="i in ev.cantidad_sub_notas" :key="i">
                                    <input type="number"
                                           x-model="subNotas[matricula.id][ev.id][i].nota"
                                           min="0" max="20" step="0.01"
                                           class="w-16 border rounded px-1">
                                </template>
                                <div class="text-xs text-gray-500 mt-1">
                                    Promedio: <span x-text="calcularPromedio(matricula.id, ev.id)"></span>
                                </div>
                            </div>
                            <!-- Si no, mostrar solo la nota final -->
                            <div x-show="!expanded[ev.id]">
                                <span x-text="getNotaFinal(matricula.id, ev.id)"></span>
                            </div>
                        </td>
                    </template>
                </tr>
            </template>
        </tbody>
    </table>
</div>
```

**Criterios de aceptación:**
- [ ] Modelo `SubNotaParcial` con migración.
- [ ] Docente puede configurar entre 3 y 5 sub-notas por parcial (con nombres personalizables).
- [ ] Docente registra notas por sub-nota; la nota final del parcial se calcula como promedio.
- [ ] Override manual de la nota final con justificación obligatoria si difiere del promedio.
- [ ] Estudiante ve las sub-notas en su libreta, no solo la nota final del parcial.
- [ ] Sub-notas editables solo en estado `BORRADOR` (bloqueadas en `COMPLETO` y `VALIDADO`).
- [ ] Validación: exactamente 3–5 sub-notas por parcial; nota en rango 0–20.
- [ ] Servicio `SubNotaValidationService` con tests unitarios.
- [ ] UI con Alpine.js: expandir/colapsar sub-notas por celda.

**Branch:** `feature/HU32-sub-notas-parcial`

---

### 4.8 HU33 — Rol Director Académico (solo lectura)

**Propósito:** Crear un nuevo rol `director_academico` que tenga acceso a los mismos módulos que el inspector, pero en modo de **solo lectura** (visualización y trazabilidad), para que pueda monitorear y supervisar los procesos académicos sin poder modificarlos.

**Reglas de negocio:**
- Nuevo valor en `Usuario.Rol`: `director_academico`.
- Permisos de solo lectura en TODOS los módulos:
  - Dashboard de justificaciones (solo ver, no aprobar/rechazar).
  - Dashboard de rendimiento (solo ver).
  - Dashboard de cierre de período (solo ver).
  - Reportes ANT (puede generar y descargar).
  - Logs de auditoría (solo ver).
  - Visor de documentos (solo ver, igual que inspector).
  - Libreta de calificaciones (puede ver las de cualquier estudiante).
  - Lista de paralelos, estudiantes, docentes (solo ver).
- El director académico NO puede:
  - Aprobar/rechazar justificaciones.
  - Validar calificaciones como secretaría.
  - Subir documentos de conocimiento RAG.
  - Crear/modificar/eliminar usuarios.
  - Cambiar configuración del sistema.
- Vistas existentes: el director pasa los mismos `UserPassesTestMixin` que el inspector.
- Botones de acción (Aprobar, Rechazar, Editar, Eliminar) se ocultan condicionalmente con `{% if user.rol != "director_academico" %}` en templates.

**Modificaciones al modelo `Usuario`:**

```python
# apps/usuarios/infrastructure/models.py
class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        ESTUDIANTE = "estudiante", "Estudiante"
        DOCENTE = "docente", "Docente"
        INSPECTOR = "inspector", "Inspector"
        SECRETARIA = "secretaria", "Secretaría"
        DIRECTOR_ACADEMICO = "director_academico", "Director Académico"
        ADMIN = "admin", "Administrador"

    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.ESTUDIANTE)
```

**Helper para permisos:**

```python
# apps/usuarios/permissions.py
class DirectorAcademicoPermissionMixin(UserPassesTestMixin):
    """Mixin that allows inspector or director_academico access (read-only enforced in template)."""

    def test_func(self):
        return self.request.user.rol in ["inspector", "director_academico"]


class ReadOnlyIfDirectorMixin:
    """Template context mixin to flag view as read-only for director."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["es_solo_lectura"] = self.request.user.rol == "director_academico"
        return context
```

**Uso en vistas existentes:**

```python
# Modificar las vistas del inspector para aceptar también director_academico
class InspectorJustificacionesDashboardView(LoginRequiredMixin, DirectorAcademicoPermissionMixin, ListView):
    template_name = "solicitudes/inspector/dashboard.html"
    # ... resto igual
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["es_solo_lectura"] = self.request.user.rol == "director_academico"
        return context
```

**Template — Ocultar acciones al director:**

```html
<!-- templates/solicitudes/inspector/dashboard.html -->
{% if not es_solo_lectura %}
    <button @click="aprobar(solicitud.id)" class="btn btn-success">Aprobar</button>
    <button @click="rechazar(solicitud.id)" class="btn btn-danger">Rechazar</button>
{% else %}
    <span class="text-gray-500 italic">Solo lectura</span>
{% endif %}
```

**Migración de datos:**

```python
# Migration: agregar 'director_academico' a choices de Usuario.rol
# Django genera la migración automáticamente con makemigrations
# No requiere data migration (es solo agregar choice)
```

**Criterios de aceptación:**
- [ ] Nuevo valor `director_academico` agregado a `Usuario.Rol` con migración.
- [ ] Mixin `DirectorAcademicoPermissionMixin` creado y aplicado a vistas de inspector.
- [ ] Todas las vistas que el inspector accede ahora también son accesibles para director académico.
- [ ] Botones de acción (Aprobar, Rechazar, Editar, Eliminar, Subir) se ocultan cuando `es_solo_lectura=True`.
- [ ] Director académico puede generar y descargar reportes ANT.
- [ ] Director académico puede ver logs de auditoría pero no eliminarlos.
- [ ] Tests: login con director académico, acceso a dashboards, intento de acción bloqueado.
- [ ] Documentación en manual de usuario sobre el rol.

**Branch:** `feature/HU33-rol-director-academico`

---

## 5. Modelo de datos — Cambios del Sprint 5

### 5.1 Nuevos modelos

| Modelo | App | Ubicación |
|--------|-----|-----------|
| `ReporteANT` | `reportes` (nueva) | `apps/reportes/infrastructure/models.py` |
| `SubNotaParcial` | `calificaciones` | `apps/calificaciones/infrastructure/models.py` |
| `ConfiguracionSubNotas` | `calificaciones` | `apps/calificaciones/infrastructure/models.py` |
| `SubNotaConfig` | `calificaciones` | `apps/calificaciones/infrastructure/models.py` |

### 5.2 Modificaciones a modelos existentes

| Modelo | Cambio | Razón |
|--------|--------|-------|
| `Usuario.rol` | Agregar choice `director_academico` | Nuevo rol requerido por cliente (HU33) |
| `Evaluacion` | Agregar campo `cantidad_sub_notas` (default 3) | Configuración de sub-notas por evaluación (HU32) |
| `Calificacion` | Mantener campo `nota` como nota final del parcial (consolidada) | La nota final se calcula desde sub-notas |

### 5.3 Nuevos value objects de dominio

| Value Object | App | Ubicación |
|-------------|-----|-----------|
| `DatosEstudianteReporte` | `reportes` | `apps/reportes/domain/value_objects.py` |
| `CierrePeriodoMetricas` | `academico` | `apps/academico/domain/value_objects.py` |

### 5.4 Nuevos servicios de dominio

| Servicio | App | Ubicación |
|----------|-----|-----------|
| `ReporteANTService` | `reportes` | `apps/reportes/domain/services.py` |
| `CierrePeriodoService` | `academico` | `apps/academico/domain/services.py` |
| `SubNotaValidationService` | `calificaciones` | `apps/calificaciones/domain/services.py` |

### 5.5 Nuevos servicios de aplicación

| Servicio | App | Ubicación |
|----------|-----|-----------|
| `ReporteANTGeneratorService` | `reportes` | `apps/reportes/application/services.py` |
| `ExportacionCalificacionesService` | `reportes` | `apps/reportes/application/services.py` |
| `ExportacionAsistenciaService` | `reportes` | `apps/reportes/application/services.py` |
| `ExportacionRateLimiter` | `reportes` | `apps/reportes/application/services.py` |
| `CierrePeriodoAppService` | `academico` | `apps/academico/application/services.py` |
| `SubNotaParcialAppService` | `calificaciones` | `apps/calificaciones/application/services.py` |
| `SessionTimeoutMiddleware` | `usuarios` | `apps/usuarios/middleware.py` |

### 5.6 Migraciones necesarias

1. Crear app `reportes` con `startapp` y registrar en `INSTALLED_APPS`.
2. Crear modelo `ReporteANT` en app `reportes`.
3. Agregar choice `director_academico` a `Usuario.rol`.
4. Crear modelos `SubNotaParcial`, `ConfiguracionSubNotas`, `SubNotaConfig` en app `calificaciones`.
5. Agregar campo `cantidad_sub_notas` a `Evaluacion`.

### 5.7 Nuevas dependencias

```txt
# requirements/production.txt — agregar
reportlab>=4.0.0      # Generación de PDF
openpyxl>=3.1.0       # Generación de Excel
Pillow>=10.0.0        # Manejo de imágenes (firmas PNG)
gunicorn>=21.0.0      # WSGI server
psycopg2-binary>=2.9.0 # PostgreSQL adapter
redis>=5.0.0          # Cache backend
django-redis>=5.4.0   # Django cache backend para Redis
```

---

## 6. Distribución de trabajo — 10 días (Git Flow)

> **Convención:** `develop` → `feature/HU0X-nombre` → PR → merge a `develop`.
> Ambos devs son fullstack. Trabajo en paralelo con PRs cruzados.

### Semana 1 — Reportes + fixes de cliente

#### Día 1 (Lunes 22/06) — Setup + inicio reportes

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Martín** | HU27: Crear app `reportes`, dependencias `reportlab` + `openpyxl`, servicio `ExportacionCalificacionesService` (Excel) | `feature/HU27-exportacion-pdf-excel` | App creada + export Excel funcional |
| **Junior** | HU26: Crear modelo `ReporteANT`, servicio de dominio `ReporteANTService`, tests unitarios de cálculo de estado y hash | `feature/HU26-reportes-ant` | Modelo + servicio + tests, PR abierto |

#### Día 2 (Martes 23/06) — Exportación + reporte ANT PDF

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Martín** | HU27: Export PDF de calificaciones, exportación de asistencia (Excel + PDF), filtros, rate limiter | `feature/HU27-exportacion-pdf-excel` | Export funcional E2E |
| **Junior** | HU26: `ReporteANTGeneratorService` (PDF con reportlab), vista de generación, listado de reportes generados | `feature/HU26-reportes-ant` | PDF ANT funcional, PR abierto |

#### Día 3 (Miércoles 24/06) — Cierre reportes + session timeout

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Martín** | HU31: `SessionTimeoutMiddleware`, endpoints `/api/session/*`, pop-up Alpine.js con countdown, mensaje de sesión expirada en login | `feature/HU31-session-timeout` | Session timeout funcional |
| **Junior** | HU26: Endpoint de verificación de hash, descarga del PDF, tests E2E. Merge PR HU26 | `feature/HU26-reportes-ant` | PR merged, reporte ANT completo |

#### Día 4 (Jueves 25/06) — Inicio dashboard cierre + inicio sub-notas

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Martín** | HU27: Tests completos, rate limiting verificado, merge PR HU27. Inicio HU29: estructura de los 3 manuales | `feature/HU27-...` → `feature/HU29-documentacion-final` | PR merged, manuales en progreso |
| **Junior** | HU28: Servicio `CierrePeriodoService`, servicio de aplicación, vista del dashboard con cards KPI y gráficos | `feature/HU28-dashboard-cierre-periodo` | Dashboard funcional |

#### Día 5 (Viernes 26/06) — Cierre dashboard + sub-notas

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Martín** | HU29: Manual de Arquitectura (≥500 líneas), Manual de Base de Datos (≥400 líneas con ER en Mermaid) | `feature/HU29-documentacion-final` | 2 manuales entregados |
| **Junior** | HU28: Tabla por paralelo en dashboard, filtro por período, botón "Generar reporte ANT". Tests. Merge PR | `feature/HU28-dashboard-cierre-periodo` | PR merged, dashboard completo |

### Semana 2 — Sub-notas + rol director + deploy

#### Día 6 (Lunes 29/06) — Sub-notas + deploy staging

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Martín** | HU30: Configurar VPS staging (mismo setup que producción pero en subdominio), deploy de la rama actual a staging para testing | `feature/HU30-deploy-vps` | Staging operativo |
| **Junior** | HU32: Modelos `SubNotaParcial`, `ConfiguracionSubNotas`, migraciones, servicio de validación, vista de configuración | `feature/HU32-sub-notas-parcial` | Modelos + servicio, PR abierto |

#### Día 7 (Martes 30/06) — Sub-notas UI + manual usuario

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Martín** | HU29: Manual de Usuario (≥600 líneas con capturas), README actualizado, validación de los 3 manuales | `feature/HU29-documentacion-final` | 3 manuales completos, PR merged |
| **Junior** | HU32: UI de planilla con sub-notas expandibles (Alpine.js), override manual, validación de cantidad. Integración con planilla existente | `feature/HU32-sub-notas-parcial` | UI funcional, PR abierto |

#### Día 8 (Miércoles 01/07) — Director académico + deploy producción

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Martín** | HU30: Deploy a producción. Ejecutar checklist post-deploy completo. Configurar backups, monitorear logs | `feature/HU30-deploy-vps` | Producción operativa |
| **Junior** | HU33: Agregar `director_academico` a choices, mixin de permisos, ocultar botones de acción, migración, tests. Merge PR HU32 | `feature/HU33-rol-director-academico` | PRs merged, director funcional |

#### Día 9 (Jueves 02/07) — Integración + smoke tests

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Martín** | HU30: Smoke test E2E en producción: login → flujo completo → generar reporte ANT → exportar Excel. Verificar HTTPS, backups, fail2ban | `feature/HU30-deploy-vps` | Smoke E2E OK, PR merged |
| **Junior** | HU33: Tests E2E del director académico en todos los módulos. Actualizar manual de usuario con sección del nuevo rol | `feature/HU33-rol-director-academico` | Director validado, PR merged |

#### Día 10 (Viernes 03/07) — Cierre sprint

| Dev | Tarea | Branch | Entregable |
|-----|-------|--------|------------|
| **Martín** | Documentación de deploy en `docs/DEPLOY.md`. Verificación final de backups, monitoreo, SSL | `develop` | Deploy docs, suite verde |
| **Junior** | Documentación de cierre sprint. Verificación cross-feature, bugfixes, suite completa | `develop` | Suite verde, documentación final |

### Tareas no técnicas (en paralelo durante el sprint)

| Tarea | Responsable | Día |
|-------|-------------|-----|
| Resolver consultas pendientes P1–P8 con la ECPPP | Junior | Día 1 |
| Confirmar acceso al VPS, DNS, dominio, certificados | Martín | Día 1 |
| Solicitar firma escaneada del director académico (PNG) | Junior | Día 2 |
| Configurar credenciales SMTP institucionales | Martín | Día 2 |
| Code review cruzado de cada PR (mínimo 1 approval antes de merge) | Ambos | Continuo |
| Testing manual de flujos completos en staging | Ambos | Día 6–8 |
| Testing manual en producción post-deploy | Ambos | Día 8–9 |
| Comunicación con cliente de cierre de proyecto | Ambos | Día 10 |

---

## 7. Flujos de usuario completos

### 7.1 Flujo: Generar y descargar reporte ANT

```
1. Secretaría accede a /reportes/ant/
2. Ve listado de reportes generados anteriormente
3. Click "Generar nuevo reporte"
4. Selecciona período académico
5. (Opcional) Ingresa notas/observaciones institucionales
6. Click "Generar"
7. Sistema:
   a. Recolecta todos los estudiantes matriculados en el período
   b. Para cada estudiante: calcula promedio final, % asistencia, estado
   c. Genera PDF con encabezado, tabla, totales, firma
   d. Calcula hash SHA-256 del PDF
   e. Persiste ReporteANT con todos los metadatos
8. Redirige al listado con mensaje "Reporte generado (N estudiantes)"
9. Secretaría hace click en el reporte → descarga el PDF
10. (Opcional) Click en "Verificar integridad" → sistema confirma que el hash coincide
```

### 7.2 Flujo: Exportar calificaciones a Excel

```
1. Inspector accede a /reportes/calificaciones/exportar/
2. Selecciona filtros: período, materia, paralelo (opcional)
3. Selecciona formato: Excel o PDF
4. Click "Exportar"
5. Sistema genera el archivo on-demand
6. Browser descarga el archivo con nombre descriptivo
7. Inspector abre el Excel y ve una hoja por paralelo con:
   - Datos del estudiante
   - Nota por evaluación
   - Promedio ponderado
   - Estado (Aprobado/Reprobado/En curso)
```

### 7.3 Flujo: Sesión expirada por inactividad

```
1. Usuario autenticado deja la pestaña inactiva
2. A los 18 minutos: aparece pop-up Alpine.js
   "Tu sesión expirará en 2:00 minutos"
3. Pop-up tiene countdown regresivo
4a. Usuario hace click en "Continuar sesión"
    → se envía POST a /api/session/extend/
    → pop-up se cierra, sesión reiniciada
4b. Usuario hace click en "Cerrar sesión"
    → redirect a /logout/ → /login/
4c. Usuario no hace nada durante 2 minutos
    → countdown llega a 0
    → redirect automático a /logout/ → /login/?session=expired
5. En /login/: el sistema detecta ?session=expired y muestra mensaje
   "Su sesión ha expirado por inactividad. Por favor ingrese nuevamente."
```

### 7.4 Flujo: Docente registra sub-notas por parcial

```
1. Docente accede a planilla de calificaciones de un paralelo
2. Para cada parcial (columna), ve un indicador "▼" para expandir
3. Click en "▼" → se expande mostrando 3 inputs de sub-notas (configurado previamente)
4. Docente ingresa las notas de cada sub-nota (0-20)
5. Sistema calcula automáticamente el promedio y lo muestra
6. (Opcional) Si docente quiere hacer override:
   - Marca checkbox "Override manual"
   - Ingresa nota diferente
   - Escribe justificación obligatoria
7. Click "Guardar" → se persiste la nota final del parcial
8. El estudiante ve en su libreta: sub-notas individuales + promedio/override
```

### 7.5 Flujo: Director académico monitorea (solo lectura)

```
1. Director académico hace login
2. Ve dashboard con tarjetas de navegación a los módulos de inspector
3. Click en "Justificaciones" → ve dashboard con todas las solicitudes
   - Puede ver detalles, pero los botones Aprobar/Rechazar están OCULTOS
4. Click en "Rendimiento" → ve dashboard con gráficos (igual que inspector)
5. Click en "Cierre de período" → ve dashboard de cierre con KPIs
6. Click en "Reportes ANT" → puede ver reportes generados y DESCARGARLOS
7. Click en "Auditoría" → ve logs de calificaciones
8. NO ve botones de: Crear/Editar/Eliminar en ninguna vista
```

---

## 8. Decisiones de arquitectura — Sprint 5

| # | Decisión | Resolución | Razón |
|---|----------|-----------|-------|
| D46 | Generación de PDF normativo | `reportlab` (Python, programático) | Permite control total del layout, headers repetidos, embebido de imágenes (firmas), hash controlado. Alternativa `weasyprint` requiere Cairo/Pango (más complejo en VPS) |
| D47 | Generación de Excel | `openpyxl` (escritura programática) | Estándar de facto en Python, soporta estilos (colores, fonts), multi-hoja, fórmulas. Suficiente para los reportes requeridos |
| D48 | Hash de integridad de reporte ANT | SHA-256 sobre contenido del PDF | Estándar de la industria, 64 caracteres hexadecimales, colisión prácticamente imposible. Verificable independientemente con cualquier herramienta |
| D49 | Persistencia de reportes ANT | Modelo `ReporteANT` con archivo en FileField | Histórico de reportes generados, permite auditoría, regeneración sin perder los anteriores |
| D50 | Exportaciones masivas | Generadas on-demand, no persistidas | Reduce uso de disco, evita archivos obsoletos. El cliente puede regenerar con datos actualizados |
| D51 | Rate limiting de exportaciones | Cache backend (Redis) con counter por minuto | Simple, no requiere Celery/queue. Suficiente para evitar abuso. 10/min es generoso para uso legítimo |
| D52 | Timeout de sesión | Middleware + frontend Alpine.js con countdown | Defensa en profundidad: el frontend avisa al usuario, el backend es la fuente de verdad. Si usuario desactiva JS, el backend cierra la sesión igual |
| D53 | Sub-notas por parcial | Modelo `SubNotaParcial` separado, no JSONField | Permite queries, reportes, migración incremental. JSONField sería más compacto pero menos consultable |
| D54 | Sub-notas: rango 3-5 | Validación en `SubNotaValidationService` y constraints a nivel de modelo | Rango confirmado por cliente. Validación en dominio para evitar bypass |
| D55 | Sub-notas: promedio vs override | Promedio por defecto + override manual con justificación | El docente tiene flexibilidad pero queda documentado por qué se desvía. El log de auditoría registra el override |
| D56 | Rol Director Académico | Mismo mixin que inspector + flag `es_solo_lectura` en template | Reutiliza vistas existentes. El flag controla visibilidad de botones de acción. No requiere reescribir vistas |
| D57 | Deploy single-VPS | Gunicorn + Nginx + PostgreSQL + Redis en una sola máquina | Requerimiento institucional. Suficiente para la escala de la ECPPP (≤500 estudiantes). Escalabilidad horizontal como deuda técnica documentada |
| D58 | Gunicorn workers | 3 workers sync, 1 thread cada uno | Fórmula: `(2 * CPU) + 1`. Para VPS de 2-4 vCPU. Workers sync son suficientes para apps Django IO-bound |
| D59 | Backups | `pg_dump` + `tar` con cron, retención 30 días | Simple, robusto, verificable. Para entorno institucional es suficiente. Para producción crítica se recomienda backup offsite (no incluido) |
| D60 | SSL | Let's Encrypt con certbot | Gratuito, automático, integrado con Nginx. Renovación automática vía cron |
| D61 | Hardening | UFW + fail2ban + SSH key-only + HSTS | Estándar para servidores públicos. Protección contra los ataques más comunes (brute force, MITM) |
| D62 | Documentación | 3 archivos Markdown separados en `docs/manuales/` | Permite versionar independientemente, facilita la búsqueda, y cada manual tiene audiencia clara |
| D63 | Configuración de producción | Archivo `production.py` separado, variables en `.env` | Separación de entornos. `.env` no se commitea. `python-decouple` o `django-environ` para gestionar variables |

---

## 9. Configuración técnica — Sprint 5

### 9.1 Nuevas URLs

```python
# apps/reportes/presentation/urls.py
urlpatterns = [
    # Reportes ANT
    path("ant/", ReporteANTListView.as_view(), name="reporte_ant_listado"),
    path("ant/generar/", ReporteANTGenerarView.as_view(), name="reporte_ant_generar"),
    path("ant/<int:reporte_id>/descargar/", ReporteANTDescargarView.as_view(), name="reporte_ant_descargar"),
    path("ant/<int:reporte_id>/verificar-hash/", ReporteANTVerificarHashView.as_view(), name="reporte_ant_verificar_hash"),

    # Exportaciones
    path("calificaciones/exportar/", ExportarCalificacionesView.as_view(), name="exportar_calificaciones"),
    path("asistencia/exportar/", ExportarAsistenciaView.as_view(), name="exportar_asistencia"),
]

# apps/usuarios/presentation/urls.py — endpoints de sesión
urlpatterns += [
    path("api/session/check/", session_check, name="session_check"),
    path("api/session/extend/", session_extend, name="session_extend"),
    path("api/session/touch/", session_touch, name="session_touch"),
]

# apps/academico/presentation/urls.py — dashboard cierre
urlpatterns += [
    path("cierre-periodo/", CierrePeriodoDashboardView.as_view(), name="cierre_periodo_dashboard"),
]
```

### 9.2 Configuración de settings

```python
# config/settings/base.py — agregar
SESSION_TIMEOUT_SECONDS = 1200  # 20 minutos
SESSION_WARNING_SECONDS = 120   # 2 minutos de aviso

# Middleware
MIDDLEWARE += ["apps.usuarios.middleware.SessionTimeoutMiddleware"]

# Apps
INSTALLED_APPS += ["apps.reportes"]
```

### 9.3 Estructura de archivos del proyecto

```
proyecto-ecpp/
├── apps/
│   ├── reportes/                    # NUEVA
│   │   ├── domain/
│   │   │   ├── services.py
│   │   │   └── value_objects.py
│   │   ├── application/
│   │   │   └── services.py
│   │   ├── infrastructure/
│   │   │   └── models.py
│   │   └── presentation/
│   │       ├── views.py
│   │       └── urls.py
│   ├── calificaciones/
│   │   ├── domain/services.py       # EXTENDIDO (SubNotaValidationService)
│   │   ├── application/services.py  # EXTENDIDO (SubNotaParcialAppService)
│   │   └── infrastructure/models.py # EXTENDIDO (SubNotaParcial, etc.)
│   ├── academico/
│   │   ├── domain/services.py       # EXTENDIDO (CierrePeriodoService)
│   │   ├── application/services.py  # EXTENDIDO (CierrePeriodoAppService)
│   │   └── presentation/views.py    # EXTENDIDO
│   ├── usuarios/
│   │   ├── infrastructure/models.py # MODIFICADO (rol director_academico)
│   │   ├── middleware.py            # NUEVO (SessionTimeoutMiddleware)
│   │   ├── permissions.py           # NUEVO (DirectorAcademicoPermissionMixin)
│   │   └── presentation/views.py    # EXTENDIDO (endpoints session)
│   └── ...
├── docs/
│   ├── manuales/                    # NUEVO
│   │   ├── ARQUITECTURA.md
│   │   ├── BASE_DE_DATOS.md
│   │   └── MANUAL_USUARIO.md
│   ├── DEPLOY.md                    # NUEVO
│   ├── PRDSprint05.md               # NUEVO (este archivo)
│   └── ...
├── scripts/                         # NUEVO
│   ├── backup_db.sh
│   ├── backup_media.sh
│   └── deploy.sh
├── .env.example
├── requirements/
│   ├── base.txt
│   └── production.txt               # NUEVO
└── ...
```

---

## 10. Riesgos del Sprint 5

| # | Riesgo | Probabilidad | Impacto | Mitigación |
|---|--------|-------------|---------|-----------|
| R1 | Consultas pendientes P1–P8 no se resuelven a tiempo | Alta | Alto | Implementar con valores por defecto documentados. Ajustar post-respuesta del cliente |
| R2 | VPS no disponible o con configuración distinta a la asumida | Media | Alto | Día 1 confirmar acceso y especificaciones. Tener plan B (Docker compose o plataforma PaaS alternativa) |
| R3 | DNS no propagado al momento del deploy | Media | Alto | Verificar propagación con `dig` el Día 1. Si no, usar subdominio temporal o IP con advertencia en navegador |
| R4 | Backups no funcionan o no se pueden restaurar | Baja | Crítico | Hacer prueba de restore en staging antes de producción. Documentar procedimiento de restore en `docs/DEPLOY.md` |
| R5 | Reporte ANT no cumple con el formato exacto de la resolución | Media | Alto | Día 1 obtener muestra del formato anterior (si existe) o confirmar campos con el cliente. Implementación flexible que permita ajustes |
| R6 | Performance de exportaciones masivas con muchos datos | Media | Medio | Limitar a 500 registros por archivo (si excede, generar múltiples archivos). Mostrar mensaje al usuario |
| R7 | Sub-notas: docente no entiende el flujo de override | Baja | Medio | Manual de usuario con capturas paso a paso. Tooltip en UI explicando override |
| R8 | Rol director académico: vistas no ocultan TODAS las acciones | Media | Alto | Code review exhaustivo de TODAS las plantillas de inspector. Test E2E con login de director y verificar que no hay acciones disponibles |
| R9 | Documentación desactualizada respecto al código real | Media | Medio | Generar documentación al final, basada en el código mergeado. Code review de los manuales verifica referencias reales |
| R10 | Fallo en deploy de producción (downtime) | Baja | Crítico | Deploy a staging primero, smoke test E2E, después producción en horario de menor tráfico. Tener rollback plan (tag de versión anterior en git) |

---

## 11. Métricas de éxito del Sprint 5

| # | Métrica | Criterio |
|---|---------|----------|
| M1 | HUs completadas | 8/8 (HU26–HU33) |
| M2 | Tests pasando | Suite completa verde + nuevos tests del sprint |
| M3 | Reporte ANT funcional | Secretaría genera reporte → PDF descargable → hash verificable |
| M4 | Exportaciones PDF/Excel | Inspector/docente/secretaría/director descargan archivos correctos con filtros funcionales |
| M5 | Dashboard cierre | Inspector y director ven KPIs correctos del último período cerrado |
| M6 | Documentación completa | 3 manuales en `docs/manuales/` con contenido ≥ 500/400/600 líneas respectivamente |
| M7 | Deploy producción | App accesible vía HTTPS, smoke test E2E OK, sin errores en logs |
| M8 | Backups automatizados | 1er backup se crea correctamente, cron activo, restore verificado en staging |
| M9 | Hardening aplicado | UFW activo, fail2ban activo, SSH key-only, HSTS configurado, SSL Labs A o A+ |
| M10 | Session timeout | Sesión expira a los 20 min, pop-up aparece a los 18 min, redirect funciona, login muestra mensaje |
| M11 | Sub-notas 3-5 | Docente configura 3-5 sub-notas por parcial, override funciona, estudiante ve sub-notas en libreta |
| M12 | Director académico | Login funciona, accede a todos los módulos de inspector, ningún botón de acción visible |
| M13 | Cobertura dominio | ≥ 70% en servicios de dominio nuevos |
| M14 | PRs mergeados | Todos los feature branches mergeados a develop vía PR |

---

## 12. Cierre de proyecto

### 12.1 Entregables finales

| # | Entregable | Ubicación | Estado |
|---|------------|-----------|--------|
| 1 | Código fuente completo | `proyecto-ecpp/` | ✅ |
| 2 | Reportes normativos ANT | `apps/reportes/` | Sprint 5 |
| 3 | Exportación masiva | `apps/reportes/` | Sprint 5 |
| 4 | Dashboard de cierre | `apps/academico/` | Sprint 5 |
| 5 | Documentación técnica | `docs/manuales/` | Sprint 5 |
| 6 | Plataforma en producción | VPS institucional | Sprint 5 |
| 7 | Backups automatizados | `/var/backups/ecppp/` | Sprint 5 |
| 8 | Manuales de usuario | `docs/manuales/MANUAL_USUARIO.md` | Sprint 5 |

### 12.2 Deuda técnica documentada (post-proyecto)

| # | Ítem | Prioridad | Roadmap |
|---|------|-----------|---------|
| 1 | Firma electrónica avanzada para reportes ANT (certificado X.509) | Media | Post-proyecto |
| 2 | Multi-VPS / escalabilidad horizontal con load balancer | Baja | Cuando >1000 estudiantes activos |
| 3 | App móvil nativa (iOS/Android) | Baja | Q4 2026 |
| 4 | Notificaciones push en tiempo real (WebSocket) | Media | Cuando se justifique |
| 5 | Integración con sistema de pagos institucional | Media | Cuando se implemente |
| 6 | Analítica predictiva con ML (alertas tempranas de deserción) | Baja | 2027 |

### 12.3 Criterios de cierre

- [ ] Todos los HUs del Sprint 5 mergeados a `main`.
- [ ] Producción operativa y monitoreada durante 1 semana sin errores críticos.
- [ ] Cliente realiza smoke test de aceptación y firma conformidad.
- [ ] Manuales entregados y revisados con el cliente.
- [ ] Credenciales y accesos entregados formalmente al equipo de soporte institucional.
- [ ] Sesión de cierre con el cliente: demo end-to-end, Q&A, transferencia de conocimiento.

---

**Fin del PRD — Sprint 5**
