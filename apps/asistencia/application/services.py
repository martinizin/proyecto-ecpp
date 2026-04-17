"""
Application services (use cases) for the Asistencia bounded context.

Orchestrates: save attendance → recalculate % → evaluate alerts.
"""

from datetime import date
from decimal import Decimal
from typing import List, Optional

from django.db import transaction
from django.db.models import Q

from collections import defaultdict

from apps.academico.infrastructure.models import Matricula, Paralelo, TipoLicencia
from apps.asistencia.domain.services import AsistenciaCalculoService
from apps.asistencia.infrastructure.models import Asistencia


class RegistroAsistenciaAppService:
    """
    Use case: Register daily attendance for a paralelo.
    Creates PRESENTE for checked students, AUSENTE for unchecked.
    Recalculates percentages and returns alert data.
    """

    def __init__(self):
        self.calculo_service = AsistenciaCalculoService()

    def obtener_estudiantes_matriculados(self, paralelo_id: int):
        """Get active enrolled students for a paralelo, ordered by last_name."""
        return (
            Matricula.objects.filter(
                paralelo_id=paralelo_id,
                estado=Matricula.Estado.ACTIVA,
            )
            .select_related("estudiante")
            .order_by("estudiante__last_name", "estudiante__first_name")
        )

    def asistencia_ya_registrada(self, paralelo_id: int, fecha: date) -> bool:
        """Check if attendance has already been taken for this paralelo on this date."""
        return Asistencia.objects.filter(
            paralelo_id=paralelo_id, fecha=fecha
        ).exists()

    def obtener_asistencia_existente(self, paralelo_id: int, fecha: date):
        """Get existing attendance records for editing."""
        return Asistencia.objects.filter(
            paralelo_id=paralelo_id, fecha=fecha
        ).select_related("estudiante")

    @transaction.atomic
    def registrar_asistencia(
        self,
        paralelo_id: int,
        fecha: date,
        estudiantes_presentes_ids: List[int],
        registrado_por_id: int,
    ) -> dict:
        """
        Register attendance for a paralelo on a given date.

        Args:
            paralelo_id: Paralelo ID.
            fecha: Date of attendance.
            estudiantes_presentes_ids: List of student IDs marked as present.
            registrado_por_id: User ID who registered.

        Returns:
            dict with 'registros_creados', 'alertas' (list of students at risk).
        """
        paralelo = Paralelo.objects.select_related("periodo").get(pk=paralelo_id)
        matriculas = self.obtener_estudiantes_matriculados(paralelo_id)

        # Delete existing records for this date (allows re-taking attendance)
        Asistencia.objects.filter(paralelo_id=paralelo_id, fecha=fecha).delete()

        # Create records
        registros = []
        for matricula in matriculas:
            estado = (
                Asistencia.Estado.PRESENTE
                if matricula.estudiante_id in estudiantes_presentes_ids
                else Asistencia.Estado.AUSENTE
            )
            registros.append(
                Asistencia(
                    estudiante_id=matricula.estudiante_id,
                    paralelo_id=paralelo_id,
                    fecha=fecha,
                    estado=estado,
                )
            )

        Asistencia.objects.bulk_create(registros)

        # Recalculate percentages and check alerts for absent students
        alertas = []
        estudiantes_ausentes_ids = [
            m.estudiante_id
            for m in matriculas
            if m.estudiante_id not in estudiantes_presentes_ids
        ]

        for estudiante_id in estudiantes_ausentes_ids:
            datos = self._calcular_datos_estudiante(estudiante_id, paralelo_id)
            inasistencia = self.calculo_service.calcular_porcentaje_inasistencia(
                datos["sesiones_asistidas"], datos["total_sesiones"]
            )
            riesgo = self.calculo_service.evaluar_riesgo(inasistencia)
            if riesgo == "rojo":
                alertas.append(
                    {
                        "estudiante_id": estudiante_id,
                        "porcentaje_inasistencia": inasistencia,
                        "paralelo": paralelo,
                    }
                )

        return {
            "registros_creados": len(registros),
            "alertas": alertas,
        }

    def _calcular_datos_estudiante(
        self, estudiante_id: int, paralelo_id: int
    ) -> dict:
        """Calculate attendance data for a single student in a paralelo."""
        total = Asistencia.objects.filter(
            estudiante_id=estudiante_id,
            paralelo_id=paralelo_id,
        ).count()

        asistidas = Asistencia.objects.filter(
            estudiante_id=estudiante_id,
            paralelo_id=paralelo_id,
        ).filter(
            Q(estado=Asistencia.Estado.PRESENTE)
            | Q(estado=Asistencia.Estado.JUSTIFICADO)
        ).count()

        return {
            "sesiones_asistidas": asistidas,
            "total_sesiones": total,
        }

    def obtener_historial(self, paralelo_id: int):
        """
        Get attendance history for a paralelo grouped by date.

        Returns:
            List of dicts: {'fecha': date, 'registros': queryset}
        """
        fechas = (
            Asistencia.objects.filter(paralelo_id=paralelo_id)
            .values_list("fecha", flat=True)
            .distinct()
            .order_by("-fecha")
        )

        historial = []
        for fecha in fechas:
            registros = (
                Asistencia.objects.filter(paralelo_id=paralelo_id, fecha=fecha)
                .select_related("estudiante")
                .order_by("estudiante__last_name", "estudiante__first_name")
            )
            presentes = registros.filter(
                Q(estado=Asistencia.Estado.PRESENTE)
                | Q(estado=Asistencia.Estado.JUSTIFICADO)
            ).count()
            total = registros.count()

            historial.append(
                {
                    "fecha": fecha,
                    "registros": registros,
                    "presentes": presentes,
                    "total": total,
                }
            )

        return historial

    def obtener_paralelos_docente(self, docente_id: int):
        """Get paralelos assigned to a docente in the active period."""
        return (
            Paralelo.objects.filter(
                docente_id=docente_id,
                periodo__activo=True,
            )
            .select_related("asignatura", "periodo", "tipo_licencia")
            .order_by("asignatura__codigo", "nombre")
        )

    def obtener_todos_paralelos_activos(self):
        """Get all paralelos in the active period (for inspector)."""
        return (
            Paralelo.objects.filter(periodo__activo=True)
            .select_related("asignatura", "periodo", "tipo_licencia", "docente")
            .order_by("asignatura__codigo", "nombre")
        )

    def obtener_datos_supervision(self, tipo_licencia_id: int = None) -> dict:
        """
        Build supervision panel data for the inspector.

        Returns dict with 'estudiantes' (sorted by inasistencia desc),
        'tipos_licencia' (for filter dropdown), and 'tipo_licencia_seleccionado'.
        """
        matriculas = Matricula.objects.filter(
            estado=Matricula.Estado.ACTIVA,
            paralelo__periodo__activo=True,
        ).select_related("estudiante", "paralelo__asignatura", "paralelo__tipo_licencia")

        if tipo_licencia_id:
            matriculas = matriculas.filter(paralelo__tipo_licencia_id=tipo_licencia_id)

        # Group matriculas by student
        estudiantes_map: dict = defaultdict(list)
        for matricula in matriculas:
            estudiantes_map[matricula.estudiante_id].append(matricula)

        estudiantes = []
        for estudiante_id, mats in estudiantes_map.items():
            estudiante = mats[0].estudiante

            # Calculate per-paralelo attendance data
            datos_list = []
            for mat in mats:
                datos = self._calcular_datos_estudiante(estudiante_id, mat.paralelo_id)
                datos_list.append(datos)

            inasistencia_general = self.calculo_service.calcular_inasistencia_general(datos_list)
            riesgo = self.calculo_service.evaluar_riesgo(inasistencia_general)

            # Collect distinct tipo_licencia names
            tipos = sorted(set(
                str(mat.paralelo.tipo_licencia)
                for mat in mats
                if mat.paralelo.tipo_licencia
            ))
            tipo_licencia_str = ", ".join(tipos) if tipos else "—"

            estudiantes.append({
                "estudiante": estudiante,
                "tipo_licencia": tipo_licencia_str,
                "inasistencia_general": inasistencia_general,
                "riesgo": riesgo,
            })

        # Sort by inasistencia descending (most at risk first)
        estudiantes.sort(key=lambda e: e["inasistencia_general"], reverse=True)

        tipos_licencia = TipoLicencia.objects.filter(activo=True).order_by("codigo")

        return {
            "estudiantes": estudiantes,
            "tipos_licencia": tipos_licencia,
            "tipo_licencia_seleccionado": tipo_licencia_id,
        }

    def obtener_datos_asistencia_estudiante(self, estudiante_id: int) -> dict:
        """
        Build attendance dashboard data for a student.

        Returns dict with 'asignaturas' (per-subject cards),
        'inasistencia_general', and 'riesgo_general'.
        """
        matriculas = (
            Matricula.objects.filter(
                estudiante_id=estudiante_id,
                estado=Matricula.Estado.ACTIVA,
                paralelo__periodo__activo=True,
            )
            .select_related("paralelo__asignatura", "paralelo__periodo", "paralelo__docente")
        )

        asignaturas = []
        for matricula in matriculas:
            paralelo = matricula.paralelo
            datos = self._calcular_datos_estudiante(estudiante_id, paralelo.id)
            porcentaje_inasistencia = self.calculo_service.calcular_porcentaje_inasistencia(
                datos["sesiones_asistidas"], datos["total_sesiones"]
            )
            riesgo = self.calculo_service.evaluar_riesgo(porcentaje_inasistencia)

            asignaturas.append(
                {
                    "paralelo": paralelo,
                    "sesiones_asistidas": datos["sesiones_asistidas"],
                    "total_sesiones": datos["total_sesiones"],
                    "porcentaje_inasistencia": porcentaje_inasistencia,
                    "riesgo": riesgo,
                }
            )

        inasistencia_general = self.calculo_service.calcular_inasistencia_general(asignaturas)
        riesgo_general = self.calculo_service.evaluar_riesgo(inasistencia_general)

        return {
            "asignaturas": asignaturas,
            "inasistencia_general": inasistencia_general,
            "riesgo_general": riesgo_general,
        }
