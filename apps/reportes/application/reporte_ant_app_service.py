"""
Application service: orchestrates ANT report generation (HU26).
"""

from datetime import datetime
from decimal import Decimal

from django.core.files.base import ContentFile

from apps.asistencia.domain.services import AsistenciaCalculoService
from apps.asistencia.infrastructure.models import Asistencia
from apps.calificaciones.domain.services import CalificacionValidationService
from apps.calificaciones.infrastructure.models import Calificacion
from apps.reportes.application.reporte_ant_generator_service import ReporteANTPDFBuilder
from apps.reportes.domain.entities import DatosEstudianteReporte
from apps.reportes.domain.exceptions import PeriodoSinEstudiantesError
from apps.reportes.domain.services import ReporteANTService
from apps.reportes.infrastructure.models import ReporteANT
from apps.academico.infrastructure.models import Matricula


class ReporteANTAppService:
    """
    Orchestrates ANT report generation:
    1. Collect student data from the period.
    2. Build the PDF with reportlab.
    3. Compute SHA-256 hash.
    4. Rebuild PDF including the hash in the footer.
    5. Persist the ReporteANT record.
    """

    def __init__(self, periodo, generado_por, firma_path=None, notas=""):
        self.periodo = periodo
        self.generado_por = generado_por
        self.firma_path = firma_path
        self.notas = notas
        self._calculo_asistencia = AsistenciaCalculoService()

    def generar(self) -> ReporteANT:
        estudiantes = self._recolectar_datos()
        if not estudiantes:
            raise PeriodoSinEstudiantesError(
                f"El período '{self.periodo.nombre}' no tiene estudiantes matriculados."
            )

        totales = ReporteANTService.consolidar_totales(estudiantes)

        builder = ReporteANTPDFBuilder(
            periodo_nombre=self.periodo.nombre,
            generado_por_nombre=self.generado_por.get_full_name(),
            generado_por_cedula=self.generado_por.cedula or "",
            firma_path=self.firma_path,
            notas=self.notas,
        )

        # First pass: build PDF to get hash
        pdf_sin_hash = builder.construir(estudiantes, totales)
        hash_integridad = ReporteANTService.computar_hash(pdf_sin_hash)

        # Second pass: embed hash in footer
        pdf_final = builder.construir(estudiantes, totales, hash_footer=hash_integridad)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reporte_ant_{self.periodo.id}_{timestamp}.pdf"

        reporte = ReporteANT.objects.create(
            periodo=self.periodo,
            generado_por=self.generado_por,
            total_estudiantes=totales.total,
            total_aprobados=totales.aprobados,
            total_reprobados=totales.reprobados,
            total_desertores=totales.desertores,
            total_en_curso=totales.en_curso,
            archivo_pdf=ContentFile(pdf_final, name=filename),
            hash_sha256=ReporteANTService.computar_hash(pdf_final),
            firma_responsable_imagen=self.firma_path or "",
            nombre_firmante=self.generado_por.get_full_name(),
            cedula_firmante=self.generado_por.cedula or "",
            cargo_firmante="Director Académico ECPPP",
            notas=self.notas,
        )
        return reporte

    def _recolectar_datos(self) -> list[DatosEstudianteReporte]:
        matriculas = (
            Matricula.objects.filter(
                paralelo__periodo=self.periodo,
                estado=Matricula.Estado.ACTIVA,
            )
            .select_related(
                "estudiante",
                "paralelo",
                "paralelo__asignatura",
            )
            .order_by("estudiante__last_name", "estudiante__first_name")
        )

        resultado = []
        for matricula in matriculas:
            estudiante = matricula.estudiante
            paralelo = matricula.paralelo

            porcentaje_asistencia, es_desertor = self._calcular_asistencia(
                estudiante.id, paralelo.id
            )
            promedio = self._calcular_promedio(estudiante, paralelo)
            estado = ReporteANTService.calcular_estado_estudiante(
                promedio_final=promedio,
                porcentaje_asistencia=porcentaje_asistencia,
                es_desertor=es_desertor,
            )

            resultado.append(
                DatosEstudianteReporte(
                    cedula=estudiante.cedula,
                    nombres_completos=estudiante.get_full_name(),
                    paralelo_codigo=paralelo.nombre,
                    materia_nombre=paralelo.asignatura.nombre,
                    porcentaje_asistencia=porcentaje_asistencia,
                    promedio_final=promedio,
                    estado=estado,
                )
            )
        return resultado

    def _calcular_asistencia(self, estudiante_id: int, paralelo_id: int) -> tuple[Decimal, bool]:
        """Returns (porcentaje_asistencia, es_desertor).

        A student is considered a desertor when the period has attendance records
        but the student has zero present/justified sessions.
        """
        from django.db.models import Q

        total = Asistencia.objects.filter(
            estudiante_id=estudiante_id, paralelo_id=paralelo_id
        ).count()
        asistidas = (
            Asistencia.objects.filter(
                estudiante_id=estudiante_id,
                paralelo_id=paralelo_id,
            )
            .filter(Q(estado=Asistencia.Estado.PRESENTE) | Q(estado=Asistencia.Estado.JUSTIFICADO))
            .count()
        )
        porcentaje = self._calculo_asistencia.calcular_porcentaje_asistencia(asistidas, total)
        es_desertor = total > 0 and asistidas == 0
        return porcentaje, es_desertor

    def _calcular_promedio(self, estudiante, paralelo) -> Decimal | None:
        evaluaciones = paralelo.evaluaciones.order_by("tipo")
        if not evaluaciones.exists():
            return None

        calificaciones_map = {
            cal.evaluacion_id: cal
            for cal in Calificacion.objects.filter(
                evaluacion__paralelo=paralelo,
                estudiante=estudiante,
            )
        }

        notas_con_pesos = []
        for ev in evaluaciones:
            cal = calificaciones_map.get(ev.id)
            if cal is not None:
                notas_con_pesos.append((cal.nota, ev.peso))

        if not notas_con_pesos:
            return None

        return CalificacionValidationService.calcular_promedio_ponderado(notas_con_pesos)
