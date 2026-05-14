"""
Application services (use cases) for the Calificaciones bounded context.
"""

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Sum

from apps.academico.infrastructure.models import Matricula, Paralelo
from apps.calificaciones.domain.exceptions import NotaFueraDeRangoError
from apps.calificaciones.domain.services import CalificacionValidationService
from apps.calificaciones.infrastructure.models import Calificacion, Evaluacion, LogCalificacion


class AuditoriaCalificacionService:
    """Registra logs inmutables de cambios en calificaciones.

    Nunca llamar update/delete sobre LogCalificacion.
    """

    @staticmethod
    def registrar_cambio(
        calificacion: Calificacion,
        accion: str,
        valor_anterior,
        valor_nuevo,
        usuario,
        ip: str = None,
        motivo: str = "",
    ) -> None:
        LogCalificacion.objects.create(
            calificacion=calificacion,
            evaluacion_info=str(calificacion.evaluacion),
            estudiante_info=(
                f"{calificacion.estudiante.get_full_name()} "
                f"({calificacion.estudiante.cedula})"
            ),
            accion=accion,
            valor_anterior=valor_anterior,
            valor_nuevo=valor_nuevo,
            realizado_por=usuario,
            ip=ip,
            motivo=motivo,
        )


class RegistroCalificacionAppService:

    def obtener_paralelos_docente(self, docente_id: int):
        return (
            Paralelo.objects.filter(docente_id=docente_id)
            .select_related("asignatura", "periodo", "tipo_licencia")
            .order_by("asignatura__nombre", "nombre")
        )

    def obtener_planilla(self, paralelo_id: int) -> dict:
        evaluaciones = list(
            Evaluacion.objects.filter(paralelo_id=paralelo_id).order_by("tipo")
        )
        matriculas = (
            Matricula.objects.filter(paralelo_id=paralelo_id, estado=Matricula.Estado.ACTIVA)
            .select_related("estudiante")
            .order_by("estudiante__last_name", "estudiante__first_name")
        )

        calificaciones_qs = Calificacion.objects.filter(evaluacion__paralelo_id=paralelo_id)
        lookup = {(c.estudiante_id, c.evaluacion_id): c for c in calificaciones_qs}

        filas = []
        for matricula in matriculas:
            notas_con_pesos = []
            celdas = []
            for ev in evaluaciones:
                cal = lookup.get((matricula.estudiante_id, ev.id))
                celdas.append((ev, cal))
                if cal is not None:
                    notas_con_pesos.append((cal.nota, ev.peso))

            promedio = (
                CalificacionValidationService.calcular_promedio_ponderado(notas_con_pesos)
                if notas_con_pesos
                else None
            )
            filas.append({"matricula": matricula, "celdas": celdas, "promedio": promedio})

        return {"evaluaciones": evaluaciones, "filas": filas}

    @transaction.atomic
    def guardar_calificaciones(
        self, paralelo_id: int, notas_data: dict, usuario, ip: str = None
    ) -> dict:
        evaluaciones_ids = set(
            Evaluacion.objects.filter(paralelo_id=paralelo_id).values_list("id", flat=True)
        )
        errores = []
        guardadas = 0

        for (estudiante_id, evaluacion_id), nota_str in notas_data.items():
            if not nota_str or nota_str.strip() == "":
                continue
            if evaluacion_id not in evaluaciones_ids:
                continue

            try:
                nota_vo = CalificacionValidationService.validar_nota(nota_str)
            except (NotaFueraDeRangoError, InvalidOperation):
                errores.append((
                    f"nota_{estudiante_id}_{evaluacion_id}",
                    f"Nota '{nota_str}' fuera de rango (0–20).",
                ))
                continue

            valor_anterior = (
                Calificacion.objects.filter(
                    evaluacion_id=evaluacion_id,
                    estudiante_id=estudiante_id,
                )
                .values_list("nota", flat=True)
                .first()
            )

            cal, created = Calificacion.objects.update_or_create(
                evaluacion_id=evaluacion_id,
                estudiante_id=estudiante_id,
                defaults={"nota": nota_vo.valor},
            )

            if created or valor_anterior != nota_vo.valor:
                guardadas += 1
                accion = (
                    LogCalificacion.TipoAccion.CREACION
                    if created
                    else LogCalificacion.TipoAccion.MODIFICACION
                )
                AuditoriaCalificacionService.registrar_cambio(
                    calificacion=cal,
                    accion=accion,
                    valor_anterior=valor_anterior,
                    valor_nuevo=nota_vo.valor,
                    usuario=usuario,
                    ip=ip,
                )

        return {"guardadas": guardadas, "errores": errores}


# ---------------------------------------------------------------------------
# Gestión de evaluaciones (CRUD)
# ---------------------------------------------------------------------------

class GestionEvaluacionesAppService:

    TIPOS_ORDENADOS = [
        "parcial1", "parcial2_10h", "parcial3", "parcial4_10h", "examen_final"
    ]

    def obtener_evaluaciones(self, paralelo_id: int) -> dict:
        evaluaciones = list(
            Evaluacion.objects.filter(paralelo_id=paralelo_id).order_by("tipo")
        )
        tipos_usados = {ev.tipo for ev in evaluaciones}
        tipos_disponibles = [
            (v, label)
            for v, label in Evaluacion.TipoEvaluacion.choices
            if v not in tipos_usados
        ]
        total_peso = sum(ev.peso for ev in evaluaciones)
        return {
            "evaluaciones": evaluaciones,
            "tipos_disponibles": tipos_disponibles,
            "total_peso": total_peso,
            "pesos_completos": total_peso == Decimal("100"),
        }

    @transaction.atomic
    def crear_evaluacion(self, paralelo_id: int, tipo: str, peso_str: str) -> dict:
        errores = []

        if not tipo or tipo not in dict(Evaluacion.TipoEvaluacion.choices):
            errores.append("Tipo de evaluación inválido.")
            return {"ok": False, "errores": errores}

        if Evaluacion.objects.filter(paralelo_id=paralelo_id, tipo=tipo).exists():
            errores.append(f"Ya existe una evaluación de tipo '{tipo}' en este paralelo.")
            return {"ok": False, "errores": errores}

        try:
            peso = Decimal(str(peso_str))
            if peso <= 0 or peso > 100:
                raise ValueError
        except (InvalidOperation, ValueError):
            errores.append("El peso debe ser un número entre 1 y 100.")
            return {"ok": False, "errores": errores}

        total_actual = Evaluacion.objects.filter(paralelo_id=paralelo_id).aggregate(
            total=Sum("peso")
        )["total"] or Decimal("0")

        if total_actual + peso > Decimal("100"):
            errores.append(
                f"El peso {peso}% supera el 100% total. Disponible: {100 - total_actual}%."
            )
            return {"ok": False, "errores": errores}

        ev = Evaluacion.objects.create(paralelo_id=paralelo_id, tipo=tipo, peso=peso)
        return {"ok": True, "evaluacion": ev}

    @transaction.atomic
    def actualizar_evaluacion(self, evaluacion_id: int, peso_str: str) -> dict:
        errores = []

        try:
            ev = Evaluacion.objects.get(pk=evaluacion_id)
        except Evaluacion.DoesNotExist:
            return {"ok": False, "errores": ["Evaluación no encontrada."]}

        try:
            peso = Decimal(str(peso_str))
            if peso <= 0 or peso > 100:
                raise ValueError
        except (InvalidOperation, ValueError):
            errores.append("El peso debe ser un número entre 1 y 100.")
            return {"ok": False, "errores": errores}

        total_sin_esta = (
            Evaluacion.objects.filter(paralelo_id=ev.paralelo_id)
            .exclude(pk=evaluacion_id)
            .aggregate(total=Sum("peso"))["total"]
            or Decimal("0")
        )

        if total_sin_esta + peso > Decimal("100"):
            errores.append(
                f"El peso {peso}% supera el 100% total. Disponible: {100 - total_sin_esta}%."
            )
            return {"ok": False, "errores": errores}

        ev.peso = peso
        ev.save(update_fields=["peso"])
        return {"ok": True, "evaluacion": ev}

    @transaction.atomic
    def eliminar_evaluacion(self, evaluacion_id: int) -> dict:
        try:
            ev = Evaluacion.objects.get(pk=evaluacion_id)
        except Evaluacion.DoesNotExist:
            return {"ok": False, "error": "Evaluación no encontrada."}

        if Calificacion.objects.filter(evaluacion_id=evaluacion_id).exists():
            return {
                "ok": False,
                "error": (
                    f"No se puede eliminar '{ev.get_tipo_display()}' porque ya tiene "
                    "calificaciones registradas."
                ),
            }

        paralelo_id = ev.paralelo_id
        ev.delete()
        return {"ok": True, "paralelo_id": paralelo_id}
