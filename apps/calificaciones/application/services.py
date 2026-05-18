"""
Application services (use cases) for the Calificaciones bounded context.
"""

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.academico.infrastructure.models import Matricula, Paralelo
from apps.calificaciones.domain.exceptions import NotaFueraDeRangoError
from apps.calificaciones.domain.services import CalificacionValidationService
from apps.calificaciones.infrastructure.models import (
    Calificacion,
    Evaluacion,
    LogCalificacion,
    RegistroCalificacionParalelo,
)


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
                f"{calificacion.estudiante.get_full_name()} " f"({calificacion.estudiante.cedula})"
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
            .prefetch_related("registro_calificaciones")
            .order_by("asignatura__nombre", "nombre")
        )

    def obtener_o_crear_registro(self, paralelo_id: int):
        """Get or create the RegistroCalificacionParalelo for a paralelo."""
        registro, _ = RegistroCalificacionParalelo.objects.get_or_create(paralelo_id=paralelo_id)
        return registro

    def verificar_completitud(self, paralelo_id: int) -> bool:
        """Check if ALL evaluaciones have grades for ALL active students."""
        evaluaciones = Evaluacion.objects.filter(paralelo_id=paralelo_id)
        if not evaluaciones.exists():
            return False
        matriculas_activas = Matricula.objects.filter(
            paralelo_id=paralelo_id, estado=Matricula.Estado.ACTIVA
        ).count()
        if matriculas_activas == 0:
            return False
        total_esperado = evaluaciones.count() * matriculas_activas
        total_existente = Calificacion.objects.filter(evaluacion__paralelo_id=paralelo_id).count()
        return total_existente >= total_esperado

    def enviar_a_validacion(self, paralelo_id: int, usuario=None) -> dict:
        """Change state to COMPLETO if all grades are filled."""
        registro = self.obtener_o_crear_registro(paralelo_id)

        if registro.estado not in [
            RegistroCalificacionParalelo.Estado.BORRADOR,
            RegistroCalificacionParalelo.Estado.RECHAZADO,
        ]:
            return {
                "ok": False,
                "error": "Las calificaciones ya fueron enviadas a validación.",
            }

        if not self.verificar_completitud(paralelo_id):
            return {
                "ok": False,
                "error": "No se puede enviar: faltan calificaciones por registrar.",
            }

        total_peso = Evaluacion.objects.filter(paralelo_id=paralelo_id).aggregate(
            total=Sum("peso")
        )["total"]
        if total_peso != Decimal("100"):
            return {
                "ok": False,
                "error": (
                    f"Los pesos de las evaluaciones suman {total_peso}% " "(deben sumar 100%)."
                ),
            }

        registro.estado = RegistroCalificacionParalelo.Estado.COMPLETO
        registro.fecha_envio = timezone.now()
        registro.save(update_fields=["estado", "fecha_envio"])

        paralelo = registro.paralelo
        info_paralelo = f"{paralelo.asignatura} — Paralelo {paralelo.nombre}"

        # Log macro: envío de planilla
        LogCalificacion.objects.create(
            accion=LogCalificacion.TipoAccion.ENVIO_PLANILLA,
            realizado_por=usuario,
            evaluacion_info=info_paralelo,
            motivo=f"Planilla enviada a validación — {info_paralelo}",
        )

        # Notify secretaría (in-app + email)
        self._notificar_secretaria_envio(registro, usuario)

        return {"ok": True}

    def puede_editar(self, paralelo_id: int) -> bool:
        """Returns True if docente can still edit grades (BORRADOR or RECHAZADO)."""
        try:
            registro = RegistroCalificacionParalelo.objects.get(paralelo_id=paralelo_id)
            return registro.estado in [
                RegistroCalificacionParalelo.Estado.BORRADOR,
                RegistroCalificacionParalelo.Estado.RECHAZADO,
            ]
        except RegistroCalificacionParalelo.DoesNotExist:
            return True

    def obtener_planilla(self, paralelo_id: int) -> dict:
        evaluaciones = list(Evaluacion.objects.filter(paralelo_id=paralelo_id).order_by("tipo"))
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
                errores.append(
                    (
                        f"nota_{estudiante_id}_{evaluacion_id}",
                        f"Nota '{nota_str}' fuera de rango (0–20).",
                    )
                )
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

        return {"guardadas": guardadas, "errores": errores}

    def _notificar_secretaria_envio(self, registro, usuario):
        """Notify all secretaría users that a planilla was submitted."""
        import logging

        from apps.notificaciones.infrastructure.models import Notificacion
        from apps.shared.email_utils import enviar_email_html
        from apps.usuarios.infrastructure.models import Usuario

        logger = logging.getLogger(__name__)
        paralelo = registro.paralelo
        docente_nombre = usuario.get_full_name() if usuario else "Docente"
        info = f"{paralelo.asignatura} — Paralelo {paralelo.nombre}"

        titulo = f"Planilla enviada — {info}"
        mensaje = (
            f"El docente {docente_nombre} ha enviado la planilla de "
            f"calificaciones de {info} para su validación."
        )

        secretarias = Usuario.objects.filter(rol="secretaria", is_active=True)
        for sec in secretarias:
            Notificacion.objects.create(
                destinatario=sec,
                tipo=Notificacion.Tipo.ENVIO_PLANILLA,
                titulo=titulo,
                mensaje=mensaje,
                url="/calificaciones/pendientes-validacion/",
            )
            if sec.email:
                try:
                    enviar_email_html(
                        destinatario=sec.email,
                        asunto=f"[ECPP] {titulo}",
                        template="emails/notificacion_general.html",
                        contexto={"titulo": titulo, "mensaje": mensaje},
                    )
                except Exception:
                    logger.exception("Error enviando email a secretaría.")


# ---------------------------------------------------------------------------
# Gestión de evaluaciones (CRUD)
# ---------------------------------------------------------------------------


class GestionEvaluacionesAppService:

    TIPOS_ORDENADOS = ["parcial1", "parcial2_10h", "parcial3", "parcial4_10h", "examen_final"]

    def obtener_evaluaciones(self, paralelo_id: int) -> dict:
        evaluaciones = list(Evaluacion.objects.filter(paralelo_id=paralelo_id).order_by("tipo"))
        tipos_usados = {ev.tipo for ev in evaluaciones}
        tipos_disponibles = [
            (v, label) for v, label in Evaluacion.TipoEvaluacion.choices if v not in tipos_usados
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

        total_sin_esta = Evaluacion.objects.filter(paralelo_id=ev.paralelo_id).exclude(
            pk=evaluacion_id
        ).aggregate(total=Sum("peso"))["total"] or Decimal("0")

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


# ---------------------------------------------------------------------------
# Validación de calificaciones por secretaría (HU16)
# ---------------------------------------------------------------------------


class ValidacionCalificacionAppService:
    """Use cases for secretaría grade validation."""

    def obtener_pendientes(self):
        """Returns registros with estado COMPLETO (pending validation)."""
        return (
            RegistroCalificacionParalelo.objects.filter(
                estado=RegistroCalificacionParalelo.Estado.COMPLETO
            )
            .select_related(
                "paralelo__asignatura",
                "paralelo__periodo",
                "paralelo__tipo_licencia",
                "paralelo__docente",
            )
            .order_by("-fecha_envio")
        )

    def obtener_detalle_validacion(self, paralelo_id: int) -> dict:
        """Returns planilla data + registro for a paralelo pending validation."""
        try:
            registro = RegistroCalificacionParalelo.objects.select_related(
                "paralelo__asignatura",
                "paralelo__periodo",
                "paralelo__tipo_licencia",
                "paralelo__docente",
            ).get(paralelo_id=paralelo_id)
        except RegistroCalificacionParalelo.DoesNotExist:
            return None

        if registro.estado != RegistroCalificacionParalelo.Estado.COMPLETO:
            return None

        planilla_service = RegistroCalificacionAppService()
        planilla = planilla_service.obtener_planilla(paralelo_id)
        return {"registro": registro, "paralelo": registro.paralelo, **planilla}

    def aprobar(self, paralelo_id: int, usuario) -> dict:
        """Approve grades: set estado=VALIDADO."""
        try:
            registro = RegistroCalificacionParalelo.objects.get(paralelo_id=paralelo_id)
        except RegistroCalificacionParalelo.DoesNotExist:
            return {"ok": False, "error": "Registro no encontrado."}

        if registro.estado != RegistroCalificacionParalelo.Estado.COMPLETO:
            return {
                "ok": False,
                "error": "Solo se pueden aprobar calificaciones en estado Completo.",
            }

        registro.estado = RegistroCalificacionParalelo.Estado.VALIDADO
        registro.fecha_validacion = timezone.now()
        registro.validado_por = usuario
        registro.save(update_fields=["estado", "fecha_validacion", "validado_por"])

        paralelo = registro.paralelo
        info_paralelo = f"{paralelo.asignatura} — Paralelo {paralelo.nombre}"

        # Log macro: aprobación de planilla
        LogCalificacion.objects.create(
            accion=LogCalificacion.TipoAccion.APROBACION_PLANILLA,
            realizado_por=usuario,
            evaluacion_info=info_paralelo,
            motivo=f"Planilla aprobada — {info_paralelo}",
        )

        # Notify docente (in-app + email)
        self._notificar_docente_resultado(registro, usuario, aprobado=True)

        return {"ok": True}

    def rechazar(self, paralelo_id: int, usuario, observaciones: str) -> dict:
        """Reject grades: set estado=RECHAZADO with observaciones."""
        if not observaciones or not observaciones.strip():
            return {"ok": False, "error": "Debe indicar las observaciones para el docente."}

        try:
            registro = RegistroCalificacionParalelo.objects.get(paralelo_id=paralelo_id)
        except RegistroCalificacionParalelo.DoesNotExist:
            return {"ok": False, "error": "Registro no encontrado."}

        if registro.estado != RegistroCalificacionParalelo.Estado.COMPLETO:
            return {
                "ok": False,
                "error": "Solo se pueden rechazar calificaciones en estado Completo.",
            }

        registro.estado = RegistroCalificacionParalelo.Estado.RECHAZADO
        registro.observaciones_secretaria = observaciones.strip()
        registro.save(update_fields=["estado", "observaciones_secretaria"])

        paralelo = registro.paralelo
        info_paralelo = f"{paralelo.asignatura} — Paralelo {paralelo.nombre}"

        # Log macro: rechazo de planilla
        LogCalificacion.objects.create(
            accion=LogCalificacion.TipoAccion.RECHAZO_PLANILLA,
            realizado_por=usuario,
            evaluacion_info=info_paralelo,
            motivo=f"Planilla rechazada — {info_paralelo}. {observaciones.strip()}",
        )

        # Notify docente (in-app + email)
        self._notificar_docente_resultado(
            registro, usuario, aprobado=False, observaciones=observaciones.strip()
        )

        return {"ok": True}

    def _notificar_docente_resultado(self, registro, usuario, aprobado=True, observaciones=""):
        """Notify docente that their planilla was approved/rejected."""
        import logging

        from apps.notificaciones.infrastructure.models import Notificacion
        from apps.shared.email_utils import enviar_email_html

        logger = logging.getLogger(__name__)
        paralelo = registro.paralelo
        docente = paralelo.docente
        if not docente:
            return

        info = f"{paralelo.asignatura} — Paralelo {paralelo.nombre}"

        if aprobado:
            titulo = f"Planilla aprobada — {info}"
            mensaje = (
                f"Su planilla de calificaciones de {info} ha sido aprobada "
                f"por secretaría. Las notas ya son visibles para los estudiantes."
            )
            tipo_notif = Notificacion.Tipo.APROBACION_PLANILLA
        else:
            titulo = f"Planilla rechazada — {info}"
            mensaje = (
                f"Su planilla de calificaciones de {info} ha sido rechazada "
                f"por secretaría.\n\nObservaciones: {observaciones}\n\n"
                f"Por favor corrija y reenvíe."
            )
            tipo_notif = Notificacion.Tipo.RECHAZO_PLANILLA

        Notificacion.objects.create(
            destinatario=docente,
            tipo=tipo_notif,
            titulo=titulo,
            mensaje=mensaje,
            url="/calificaciones/paralelos/",
        )

        if docente.email:
            try:
                enviar_email_html(
                    destinatario=docente.email,
                    asunto=f"[ECPP] {titulo}",
                    template="emails/notificacion_general.html",
                    contexto={"titulo": titulo, "mensaje": mensaje},
                )
            except Exception:
                logger.exception("Error enviando email a docente.")


class LibretaCalificacionesAppService:
    """Read-only service: builds the student's grade report (libreta).

    Shows all subjects (paralelos) where the student has an active enrollment
    in any active period. Grades are only visible when the paralelo's
    RegistroCalificacionParalelo is in VALIDADO state.
    """

    @staticmethod
    def obtener_libreta(estudiante):
        """Return the full grade report for a student.

        Returns:
            dict with keys:
            - materias: list of dicts per paralelo
            - promedio_general: Decimal or None
            - total_materias: int
            - materias_con_promedio: int
        """
        materias = []

        # Active enrollments in active periods
        matriculas = (
            Matricula.objects.filter(
                estudiante=estudiante,
                estado=Matricula.Estado.ACTIVA,
                paralelo__periodo__activo=True,
            )
            .select_related(
                "paralelo__asignatura",
                "paralelo__periodo",
                "paralelo__docente",
            )
            .order_by("paralelo__asignatura__codigo")
        )

        for matricula in matriculas:
            paralelo = matricula.paralelo
            materia = LibretaCalificacionesAppService._construir_materia(paralelo, estudiante)
            materias.append(materia)

        # Promedio general: average of per-subject promedios
        promedios_validos = [m["promedio"] for m in materias if m["promedio"] is not None]
        promedio_general = None
        if promedios_validos:
            promedio_general = (sum(promedios_validos) / len(promedios_validos)).quantize(
                Decimal("0.01")
            )

        return {
            "materias": materias,
            "promedio_general": promedio_general,
            "total_materias": len(materias),
            "materias_con_promedio": len(promedios_validos),
        }

    @staticmethod
    def _construir_materia(paralelo, estudiante):
        """Build a single subject card data dict."""
        # Check if grades are published (COMPLETO or VALIDADO)
        try:
            registro = paralelo.registro_calificaciones
            notas_visibles = registro.estado in [
                RegistroCalificacionParalelo.Estado.COMPLETO,
                RegistroCalificacionParalelo.Estado.VALIDADO,
            ]
        except RegistroCalificacionParalelo.DoesNotExist:
            notas_visibles = False

        evaluaciones = paralelo.evaluaciones.order_by("tipo")
        calificaciones_map = {}
        if notas_visibles:
            calificaciones_map = {
                cal.evaluacion_id: cal
                for cal in Calificacion.objects.filter(
                    evaluacion__paralelo=paralelo,
                    estudiante=estudiante,
                )
            }

        filas_evaluaciones = []
        notas_con_pesos = []

        for ev in evaluaciones:
            cal = calificaciones_map.get(ev.id)
            nota = cal.nota if cal else None
            filas_evaluaciones.append(
                {
                    "tipo": ev.get_tipo_display(),
                    "peso": ev.peso,
                    "nota": nota,
                }
            )
            if nota is not None:
                notas_con_pesos.append((nota, ev.peso))

        # Calculate promedio only if there are grades
        promedio = None
        if notas_con_pesos:
            promedio = CalificacionValidationService.calcular_promedio_ponderado(notas_con_pesos)

        # Determine status
        if not notas_visibles:
            estado = "pendiente"
        elif not evaluaciones.exists():
            estado = "sin_evaluaciones"
        elif len(notas_con_pesos) < evaluaciones.count():
            estado = "en_curso"
        else:
            estado = CalificacionValidationService.estado_aprobacion(promedio)

        return {
            "paralelo": paralelo,
            "evaluaciones": filas_evaluaciones,
            "promedio": promedio,
            "estado": estado,
            "notas_visibles": notas_visibles,
        }


class SupervisionCalificacionesAppService:
    """Inspector view: lista de estudiantes con promedios generales."""

    @staticmethod
    def obtener_datos_supervision(tipo_licencia_id=None):
        """Return all active students with their overall GPA for supervision.

        Returns:
            dict with keys:
            - estudiantes: list of dicts (estudiante, promedio_general, total_materias, riesgo)
            - tipos_licencia: queryset for filter dropdown
        """
        from apps.academico.infrastructure.models import TipoLicencia

        # Get all students with active enrollments in active periods
        filtro = {
            "estado": Matricula.Estado.ACTIVA,
            "paralelo__periodo__activo": True,
        }
        if tipo_licencia_id:
            filtro["paralelo__tipo_licencia_id"] = tipo_licencia_id

        estudiante_ids = (
            Matricula.objects.filter(**filtro).values_list("estudiante_id", flat=True).distinct()
        )

        from apps.usuarios.infrastructure.models import Usuario

        estudiantes_qs = Usuario.objects.filter(id__in=estudiante_ids, rol="estudiante").order_by(
            "last_name", "first_name"
        )

        resultados = []
        for est in estudiantes_qs:
            libreta = LibretaCalificacionesAppService.obtener_libreta(est)
            promedio = libreta["promedio_general"]

            # Determine risk level
            if promedio is None:
                riesgo = "sin_datos"
            elif promedio < Decimal("14"):
                riesgo = "rojo"
            elif promedio < Decimal("16"):
                riesgo = "amarillo"
            else:
                riesgo = "verde"

            resultados.append(
                {
                    "estudiante": est,
                    "promedio_general": promedio,
                    "total_materias": libreta["total_materias"],
                    "materias_con_promedio": libreta["materias_con_promedio"],
                    "riesgo": riesgo,
                }
            )

        tipos_licencia = TipoLicencia.objects.order_by("codigo")

        return {
            "estudiantes": resultados,
            "tipos_licencia": tipos_licencia,
            "total_estudiantes": len(resultados),
            "en_riesgo": sum(1 for e in resultados if e["riesgo"] == "rojo"),
        }
