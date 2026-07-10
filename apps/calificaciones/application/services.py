"""
Application services (use cases) for the Calificaciones bounded context.
"""

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.academico.infrastructure.models import Matricula, Paralelo
from apps.calificaciones.domain.exceptions import (
    NotaFueraDeRangoError,
    SubNotasFueraDeRangoError,
)
from apps.calificaciones.domain.services import (
    CalificacionValidationService,
    SubNotaValidationService,
)
from apps.calificaciones.infrastructure.models import (
    Calificacion,
    ConfiguracionSubNotas,
    Evaluacion,
    LogCalificacion,
    RegistroCalificacionParalelo,
    SubNotaConfig,
    SubNotaParcial,
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

    def hay_calificaciones_registradas(self, paralelo_id: int) -> bool:
        """Check if at least one grade has been entered for this paralelo."""
        return Calificacion.objects.filter(evaluacion__paralelo_id=paralelo_id).exists()

    def enviar_a_validacion(self, paralelo_id: int, usuario=None) -> dict:
        """Change state to COMPLETO if at least one grade is registered."""
        registro = self.obtener_o_crear_registro(paralelo_id)

        if registro.estado not in [
            RegistroCalificacionParalelo.Estado.BORRADOR,
            RegistroCalificacionParalelo.Estado.RECHAZADO,
        ]:
            return {
                "ok": False,
                "error": "Las calificaciones ya fueron enviadas a validación.",
            }

        if not self.hay_calificaciones_registradas(paralelo_id):
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
# Sub-notas por parcial (HU32)
# ---------------------------------------------------------------------------


class SubNotaParcialAppService:
    """Use cases for sub-grade configuration and registration within parciales."""

    def __init__(self):
        self.registro_service = RegistroCalificacionAppService()

    def obtener_configuracion(self, evaluacion_id: int):
        """Return the ordered SubNotaConfig items for an evaluacion, or None."""
        config = (
            ConfiguracionSubNotas.objects.filter(evaluacion_id=evaluacion_id)
            .prefetch_related("items")
            .first()
        )
        if config is None:
            return None
        return list(config.items.all())

    def obtener_sub_notas(self, evaluacion_id: int, matricula_id: int):
        """Return the ordered sub-grades of a student for an evaluacion."""
        return list(
            SubNotaParcial.objects.filter(
                evaluacion_id=evaluacion_id, matricula_id=matricula_id
            ).order_by("orden")
        )

    @transaction.atomic
    def configurar_sub_notas(
        self, evaluacion_id: int, nombres: list[str], pesos: list[str] = None
    ) -> dict:
        """Define (or replace) the 3-5 sub-grade names (and optional weights) for a parcial.

        Si se proveen pesos, cada sub-nota tiene un peso porcentual y los
        pesos deben sumar 100. Sin pesos, la nota final es el promedio simple.
        """
        try:
            evaluacion = Evaluacion.objects.get(pk=evaluacion_id)
        except Evaluacion.DoesNotExist:
            return {"ok": False, "error": "Evaluación no encontrada."}

        if not evaluacion.es_parcial:
            return {
                "ok": False,
                "error": "Solo los parciales admiten sub-notas.",
            }

        if not self.registro_service.puede_editar(evaluacion.paralelo_id):
            return {
                "ok": False,
                "error": (
                    "La planilla ya fue enviada a validación; "
                    "las sub-notas no pueden modificarse."
                ),
            }

        nombres_limpios = [n.strip() for n in nombres if n and n.strip()]
        if len(nombres_limpios) != len(nombres):
            return {"ok": False, "error": "Los nombres de las sub-notas no pueden estar vacíos."}

        try:
            SubNotaValidationService.validar_cantidad(len(nombres_limpios))
        except SubNotasFueraDeRangoError as exc:
            return {"ok": False, "error": str(exc)}

        pesos_decimales = None
        if pesos:
            if len(pesos) != len(nombres_limpios):
                return {
                    "ok": False,
                    "error": "Cada sub-nota debe tener su peso porcentual.",
                }
            try:
                pesos_decimales = [Decimal(str(p).strip()) for p in pesos]
            except InvalidOperation:
                return {"ok": False, "error": "Los pesos deben ser números válidos."}
            if not SubNotaValidationService.validar_pesos_sub_notas(pesos_decimales):
                suma = sum(pesos_decimales)
                return {
                    "ok": False,
                    "error": (
                        "Los pesos deben ser mayores a 0 y sumar exactamente "
                        f"100% (actualmente suman {suma}%)."
                    ),
                }

        # Reemplazar configuración previa; las sub-notas registradas con la
        # estructura anterior dejan de ser válidas y se eliminan.
        ConfiguracionSubNotas.objects.filter(evaluacion=evaluacion).delete()
        sub_notas_eliminadas, _ = SubNotaParcial.objects.filter(evaluacion=evaluacion).delete()

        config = ConfiguracionSubNotas.objects.create(evaluacion=evaluacion)
        for orden, nombre in enumerate(nombres_limpios, start=1):
            SubNotaConfig.objects.create(
                configuracion=config,
                nombre=nombre,
                orden=orden,
                peso=pesos_decimales[orden - 1] if pesos_decimales else None,
            )

        return {
            "ok": True,
            "config": config,
            "sub_notas_eliminadas": sub_notas_eliminadas,
        }

    @transaction.atomic
    def registrar_sub_notas(
        self,
        evaluacion_id: int,
        matricula_id: int,
        notas: list[str],
        usuario=None,
        ip: str = None,
        override_str: str = "",
        justificacion: str = "",
    ) -> dict:
        """Register the sub-grades of a student and consolidate the parcial grade.

        La nota final del parcial es el promedio aritmético de las sub-notas,
        salvo que el docente registre un override manual (con justificación
        obligatoria si difiere del promedio).
        """
        try:
            evaluacion = Evaluacion.objects.get(pk=evaluacion_id)
        except Evaluacion.DoesNotExist:
            return {"ok": False, "error": "Evaluación no encontrada."}

        if not evaluacion.es_parcial:
            return {"ok": False, "error": "Solo los parciales admiten sub-notas."}

        try:
            matricula = Matricula.objects.select_related("estudiante").get(
                pk=matricula_id,
                paralelo_id=evaluacion.paralelo_id,
                estado=Matricula.Estado.ACTIVA,
            )
        except Matricula.DoesNotExist:
            return {"ok": False, "error": "Matrícula no encontrada en este paralelo."}

        if not self.registro_service.puede_editar(evaluacion.paralelo_id):
            return {
                "ok": False,
                "error": (
                    "La planilla ya fue enviada a validación; "
                    "las sub-notas no pueden modificarse."
                ),
            }

        items_config = self.obtener_configuracion(evaluacion_id)
        if not items_config:
            return {
                "ok": False,
                "error": "Primero configure las sub-notas de este parcial.",
            }

        if len(notas) != len(items_config):
            return {
                "ok": False,
                "error": (
                    f"Se esperaban {len(items_config)} sub-notas " f"y se recibieron {len(notas)}."
                ),
            }

        if any(not str(n or "").strip() for n in notas):
            return {
                "ok": False,
                "error": (
                    f"Debe completar las {len(items_config)} sub-notas "
                    "del parcial antes de guardar."
                ),
            }

        valores = []
        for item, nota_str in zip(items_config, notas):
            try:
                nota_vo = CalificacionValidationService.validar_nota(nota_str)
            except (NotaFueraDeRangoError, InvalidOperation):
                return {
                    "ok": False,
                    "error": f"La nota de '{item.nombre}' está fuera de rango (0–20).",
                }
            valores.append(nota_vo.valor)

        pesos = [item.peso for item in items_config]
        if all(p is not None for p in pesos):
            promedio = SubNotaValidationService.calcular_nota_final_ponderada(valores, pesos)
        else:
            promedio = SubNotaValidationService.calcular_nota_final_sub_notas(valores)

        override = None
        justificacion = justificacion.strip()
        if override_str and str(override_str).strip():
            try:
                override = CalificacionValidationService.validar_nota(override_str).valor
            except (NotaFueraDeRangoError, InvalidOperation):
                return {
                    "ok": False,
                    "error": "La nota de override está fuera de rango (0–20).",
                }
            if (
                SubNotaValidationService.requiere_justificacion_override(promedio, override)
                and not justificacion
            ):
                return {
                    "ok": False,
                    "error": (
                        "La justificación es obligatoria cuando la nota final "
                        "difiere del promedio de las sub-notas."
                    ),
                }

        nota_final = override if override is not None else promedio

        SubNotaParcial.objects.filter(evaluacion=evaluacion, matricula=matricula).delete()
        for item, valor in zip(items_config, valores):
            SubNotaParcial.objects.create(
                evaluacion=evaluacion,
                matricula=matricula,
                nombre=item.nombre,
                nota=valor,
                orden=item.orden,
                peso=item.peso,
                nota_final_parcial_override=override,
                justificacion_override=justificacion if override is not None else "",
            )

        valor_anterior = (
            Calificacion.objects.filter(evaluacion=evaluacion, estudiante=matricula.estudiante)
            .values_list("nota", flat=True)
            .first()
        )
        calificacion, created = Calificacion.objects.update_or_create(
            evaluacion=evaluacion,
            estudiante=matricula.estudiante,
            defaults={"nota": nota_final},
        )

        if created or valor_anterior != nota_final:
            motivo = f"Nota consolidada desde {len(valores)} sub-notas (promedio {promedio})."
            if override is not None and override != promedio:
                motivo += f" Override manual: {override}. Justificación: {justificacion}"
            AuditoriaCalificacionService.registrar_cambio(
                calificacion=calificacion,
                accion=(
                    LogCalificacion.TipoAccion.CREACION
                    if created
                    else LogCalificacion.TipoAccion.MODIFICACION
                ),
                valor_anterior=valor_anterior,
                valor_nuevo=nota_final,
                usuario=usuario,
                ip=ip,
                motivo=motivo,
            )

        return {
            "ok": True,
            "promedio": promedio,
            "nota_final": nota_final,
            "calificacion": calificacion,
        }


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
        sub_notas_map = {}
        if notas_visibles:
            calificaciones_map = {
                cal.evaluacion_id: cal
                for cal in Calificacion.objects.filter(
                    evaluacion__paralelo=paralelo,
                    estudiante=estudiante,
                )
            }
            sub_notas = SubNotaParcial.objects.filter(
                evaluacion__paralelo=paralelo,
                matricula__estudiante=estudiante,
                matricula__paralelo=paralelo,
            ).order_by("evaluacion_id", "orden")
            for sub in sub_notas:
                sub_notas_map.setdefault(sub.evaluacion_id, []).append(sub)

        filas_evaluaciones = []
        notas_con_pesos = []

        for ev in evaluaciones:
            cal = calificaciones_map.get(ev.id)
            nota = cal.nota if cal else None
            subs_ev = sub_notas_map.get(ev.id, [])
            filas_evaluaciones.append(
                {
                    "tipo": ev.get_tipo_display(),
                    "peso": ev.peso,
                    "nota": nota,
                    "sub_notas": [
                        {"nombre": s.nombre, "peso": s.peso, "nota": s.nota} for s in subs_ev
                    ],
                    "override": (subs_ev[0].nota_final_parcial_override if subs_ev else None),
                    "justificacion_override": (
                        subs_ev[0].justificacion_override if subs_ev else ""
                    ),
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


# ---------------------------------------------------------------------------
# Reporte de Auditoría (HU27b follow-up 2026-06-24)
# ---------------------------------------------------------------------------


class ExportarAuditoriaService:
    """Genera archivos Excel/PDF del Reporte de Auditoría.

    Queryea ``LogCalificacion`` (NO ``Calificacion``) con los mismos filtros
    que la página ``/calificaciones/auditoria/``. Genera un "Reporte de
    Auditoría" (no "Reporte de Calificaciones") — el bug era que el
    botón inline de la página apuntaba a los endpoints de
    calificaciones/asistencia que generan el archivo equivocado.

    Filtros soportados (todos opcionales, vienen de ``?fecha_inicio=...``,
    ``?fecha_fin=...``, ``?accion=...``, ``?docente=...``,
    ``?estudiante=...``):
    - ``fecha_inicio`` (YYYY-MM-DD) → ``timestamp__date__gte=fecha_inicio``
    - ``fecha_fin`` (YYYY-MM-DD) → ``timestamp__date__lte=fecha_fin``
    - ``accion`` → match exacto en ``LogCalificacion.TipoAccion.choices``
    - ``docente`` (int) → ``realizado_por_id=docente`` (ignora si no es int)
    - ``estudiante`` (str) → ``estudiante_info__icontains=estudiante``
    """

    def __init__(self, filtros: dict):
        self.filtros = filtros or {}

    def exportar_excel(self):
        """Genera un .xlsx con los logs filtrados."""
        from io import BytesIO

        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter

        wb = Workbook()
        ws = wb.active
        ws.title = "Auditoría"

        header_fill = PatternFill("solid", fgColor="1E3A8A")  # azul oscuro (mismo que reportes)
        header_font = Font(bold=True, color="FFFFFF")
        header_align = Alignment(horizontal="center", vertical="center")
        bold = Font(bold=True)

        # Header block: 3 filas (título + filtros + generado) + 1 spacer
        header_lines = self._header_block_rows()
        for i, line in enumerate(header_lines, start=1):
            cell = ws.cell(row=i, column=1, value=line)
            cell.font = bold
            ws.merge_cells(start_row=i, end_row=i, start_column=1, end_column=12)

        # Spacer row
        ws.cell(row=len(header_lines) + 1, column=1, value="")

        # Column headers
        column_headers = [
            "Fecha y hora",
            "Acción",
            "Materia",
            "Paralelo",
            "Evaluación",
            "Estudiante",
            "Cédula",
            "Valor anterior",
            "Valor nuevo",
            "Realizado por",
            "IP",
            "Motivo",
        ]
        header_row_idx = len(header_lines) + 2
        for col_idx, header in enumerate(column_headers, start=1):
            cell = ws.cell(row=header_row_idx, column=col_idx, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_align

        # Data rows
        logs = self._query_logs()
        for i, log in enumerate(logs, start=header_row_idx + 1):
            paralelo = log.calificacion.evaluacion.paralelo if log.calificacion else None
            ws.cell(
                row=i,
                column=1,
                value=log.timestamp.replace(tzinfo=None) if log.timestamp else "",
            )
            ws.cell(row=i, column=2, value=log.get_accion_display())
            ws.cell(
                row=i,
                column=3,
                value=paralelo.asignatura.nombre if paralelo and paralelo.asignatura else "",
            )
            ws.cell(
                row=i,
                column=4,
                value=str(paralelo) if paralelo else "",
            )
            ws.cell(row=i, column=5, value=log.evaluacion_info or "")
            ws.cell(row=i, column=6, value=log.estudiante_info or "")
            # Cédula: extraemos del snapshot "Nombre (cédula)" si tiene el formato
            estudiante_info = log.estudiante_info or ""
            cedula = ""
            open_paren = estudiante_info.rfind("(")
            if open_paren >= 0 and estudiante_info.endswith(")"):
                cedula = estudiante_info[open_paren + 1 : -1]  # noqa: E203
            ws.cell(row=i, column=7, value=cedula)
            ws.cell(
                row=i,
                column=8,
                value=float(log.valor_anterior) if log.valor_anterior is not None else "",
            )
            ws.cell(
                row=i,
                column=9,
                value=float(log.valor_nuevo) if log.valor_nuevo is not None else "",
            )
            realizado_por = log.realizado_por
            if realizado_por:
                realizado_por_str = realizado_por.get_full_name() or realizado_por.username
            else:
                realizado_por_str = ""
            ws.cell(row=i, column=10, value=realizado_por_str)
            ws.cell(row=i, column=11, value=log.ip or "")
            ws.cell(row=i, column=12, value=log.motivo or "")

        # Auto-size columns
        for col_idx, header in enumerate(column_headers, start=1):
            max_length = len(header)
            column_letter = get_column_letter(col_idx)
            for row in ws.iter_rows(min_col=col_idx, max_col=col_idx, values_only=True):
                for cell_value in row:
                    if cell_value is not None:
                        cell_str = str(cell_value)
                        if len(cell_str) > max_length:
                            max_length = len(cell_str)
            ws.column_dimensions[column_letter].width = min(max_length + 2, 50)

        # Freeze pane below the column headers
        ws.freeze_panes = ws.cell(row=header_row_idx + 1, column=1)

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer

    def exportar_pdf(self):
        """Genera un .pdf con los logs filtrados."""
        from io import BytesIO

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=1.5 * cm,
            rightMargin=1.5 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )
        styles = getSampleStyleSheet()
        elements = []

        # Header block
        for line in self._header_block_rows():
            elements.append(Paragraph(line, styles["Heading4"]))
        elements.append(Spacer(1, 0.5 * cm))

        # Data table
        logs = list(self._query_logs())
        headers = [
            "Fecha",
            "Acción",
            "Materia",
            "Paralelo",
            "Evaluación",
            "Estudiante",
            "Ant.",
            "Nuevo",
            "Realizado por",
            "Motivo",
        ]
        data = [headers]
        cell_style = ParagraphStyle("cell", parent=styles["Normal"], fontSize=7, leading=9)
        for log in logs:
            paralelo = log.calificacion.evaluacion.paralelo if log.calificacion else None
            row = [
                Paragraph(
                    log.timestamp.strftime("%Y-%m-%d %H:%M") if log.timestamp else "",
                    cell_style,
                ),
                Paragraph(log.get_accion_display(), cell_style),
                Paragraph(
                    paralelo.asignatura.nombre if paralelo and paralelo.asignatura else "",
                    cell_style,
                ),
                Paragraph(str(paralelo) if paralelo else "", cell_style),
                Paragraph(log.evaluacion_info or "", cell_style),
                Paragraph(log.estudiante_info or "", cell_style),
                str(log.valor_anterior) if log.valor_anterior is not None else "",
                str(log.valor_nuevo) if log.valor_nuevo is not None else "",
                Paragraph(
                    (log.realizado_por.get_full_name() if log.realizado_por else ""),
                    cell_style,
                ),
                Paragraph(log.motivo or "", cell_style),
            ]
            data.append(row)
        if len(data) == 1:
            # Sin resultados (R10): tabla vacía con mensaje
            data.append(["Sin resultados para los filtros aplicados"] + [""] * 9)
        table = Table(data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 8),
                    ("FONTSIZE", (0, 1), (-1, -1), 7),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        elements.append(table)
        doc.build(elements)
        buffer.seek(0)
        return buffer

    def _query_logs(self):
        """Query ``LogCalificacion`` aplicando los filtros del service."""
        from apps.calificaciones.infrastructure.models import LogCalificacion

        qs = LogCalificacion.objects.select_related(
            "calificacion__evaluacion__paralelo__asignatura",
            "calificacion__evaluacion__paralelo__periodo",
            "realizado_por",
        ).order_by("-timestamp")

        fecha_inicio = self.filtros.get("fecha_inicio")
        if fecha_inicio:
            qs = qs.filter(timestamp__date__gte=fecha_inicio)
        fecha_fin = self.filtros.get("fecha_fin")
        if fecha_fin:
            qs = qs.filter(timestamp__date__lte=fecha_fin)
        accion = self.filtros.get("accion")
        if accion:
            qs = qs.filter(accion=accion)
        docente = self.filtros.get("docente")
        if docente:
            try:
                docente_id = int(docente)
            except (TypeError, ValueError):
                docente_id = None
            if docente_id:
                qs = qs.filter(realizado_por_id=docente_id)
        estudiante = self.filtros.get("estudiante")
        if estudiante:
            qs = qs.filter(estudiante_info__icontains=estudiante)
        return qs

    def _header_block_rows(self):
        """Filas del header block: título + rango de fechas + generación."""
        from django.utils import timezone

        rows = [
            "ECPPP — Reporte de Auditoría",
        ]
        fecha_inicio = self.filtros.get("fecha_inicio") or ""
        fecha_fin = self.filtros.get("fecha_fin") or ""
        if fecha_inicio or fecha_fin:
            rows.append(f"Rango: {fecha_inicio or 'sin límite'} → {fecha_fin or 'sin límite'}")
        else:
            rows.append("Rango: todos los registros")
        accion = self.filtros.get("accion")
        if accion:
            rows.append(f"Filtro acción: {accion}")
        rows.append(f"Generado: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return rows

    def _filename(self, formato: str) -> str:
        """Filename: ``auditoria_[rango]_<YYYYMMDD>_<HHMMSS>.<ext>``."""
        from django.utils import timezone

        ext = "xlsx" if formato == "excel" else "pdf"
        parts = ["auditoria"]
        fecha_inicio = self.filtros.get("fecha_inicio") or ""
        fecha_fin = self.filtros.get("fecha_fin") or ""
        if fecha_inicio or fecha_fin:
            parts.append(
                f"{(fecha_inicio or 'inicio').replace('-', '')}_"
                f"{(fecha_fin or 'hoy').replace('-', '')}"
            )
        parts.append(timezone.now().strftime("%Y%m%d_%H%M%S"))
        return "_".join(parts) + f".{ext}"
