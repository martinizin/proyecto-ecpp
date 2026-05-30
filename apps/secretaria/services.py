"""Application services for the Secretaría module — user and enrollment management."""

import string

from django.apps import apps as django_apps
from django.db import transaction
from django.utils.crypto import get_random_string

from apps.usuarios.domain.exceptions import UsuarioConDependenciasError
from apps.usuarios.infrastructure.email_service import send_credenciales_email
from apps.usuarios.infrastructure.models import Usuario


# CASCADE FK sources that BLOCK deletion of a Usuario. We enumerate them
# explicitly (instead of walking _meta.related_objects) to keep the policy
# decision documented and reviewable: secretaría must NOT silently destroy
# academic history (matrículas, calificaciones, asistencias) or workflow
# evidence (solicitudes). Audit-only relations (RegistroAuditoria, LogEntry,
# *_por SET_NULL fields) are intentionally absent — they survive deletion
# with a NULL pointer, which is the desired behavior.
_FK_SOURCES = {
    "matriculas":     ("academico.Matricula",       "estudiante"),
    "calificaciones": ("calificaciones.Calificacion", "estudiante"),
    "asistencias":    ("asistencia.Asistencia",     "estudiante"),
    "solicitudes":    ("solicitudes.Solicitud",     "estudiante"),
}


class GestionUsuariosService:
    """Service for user management by secretaría."""

    def listar_usuarios(self, search: str = None, rol_filter: str = None):
        """List users with optional search and role filter."""
        qs = Usuario.objects.all().order_by("-date_joined")
        if search:
            from django.db.models import Q

            qs = qs.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
                | Q(cedula__icontains=search)
            )
        if rol_filter:
            qs = qs.filter(rol=rol_filter)
        return qs

    @transaction.atomic
    def crear_usuario(self, email, first_name, last_name, rol, cedula, telefono="") -> tuple:
        """Create a new user with auto-generated temp password.

        Wrapped in `@transaction.atomic` (per design D5 / R8): if the
        credentials email cannot be sent, the entire creation rolls back —
        no orphan accounts whose email is already burned by the UNIQUE
        constraint. The exception propagates so the caller (view) can render
        a proper error and let the secretaría retry.

        Returns (usuario, temp_password).
        """
        temp_password = get_random_string(
            length=12,
            allowed_chars=string.ascii_letters + string.digits + "!@#$%&*",
        )

        usuario = Usuario(
            email=email,
            username=email,  # project convention: username = email
            first_name=first_name,
            last_name=last_name,
            rol=rol,
            cedula=cedula,
            telefono=telefono,
            is_active=True,
            debe_cambiar_password=True,
        )
        usuario.set_password(temp_password)
        usuario.save()

        # Side-effect MUST run inside the atomic block: any exception here
        # triggers the rollback above, ensuring no half-created user lingers.
        send_credenciales_email(usuario, temp_password)

        return usuario, temp_password

    def obtener_usuario(self, usuario_id):
        """Get a single user by ID."""
        return Usuario.objects.get(pk=usuario_id)

    @transaction.atomic
    def eliminar_usuario(self, usuario_id) -> None:
        """Hard-delete a user, guarding against CASCADE-FK data loss.

        Workflow (per design D5):
        1. Acquire a row-level lock with SELECT FOR UPDATE inside the atomic
           block — prevents a concurrent request from sneaking in a FK between
           the dependency check and the DELETE.
        2. Count dependencies across `_FK_SOURCES` (CASCADE relations only).
        3. If any are non-zero, raise `UsuarioConDependenciasError` with the
           full breakdown so the secretaría sees the complete picture.
        4. Otherwise, delete the row.
        """
        usuario = Usuario.objects.select_for_update().get(pk=usuario_id)
        dependencias = self._contar_dependencias(usuario_id)
        if dependencias:
            raise UsuarioConDependenciasError(dependencias)
        usuario.delete()

    @staticmethod
    def _contar_dependencias(usuario_id) -> dict:
        """Return a dict {source_name: count} for every non-zero CASCADE FK.

        Sources with zero rows are omitted so the resulting dict is empty when
        the user can be safely deleted — callers can do `if deps: raise(...)`.
        """
        counts = {}
        for nombre, (label, fk_field) in _FK_SOURCES.items():
            Model = django_apps.get_model(label)
            cantidad = Model.objects.filter(**{fk_field: usuario_id}).count()
            if cantidad:
                counts[nombre] = cantidad
        return counts


class GestionMatriculasService:
    """Service for enrollment management by secretaría."""

    def __init__(self):
        from apps.academico.domain.services import MatriculaService

        self.domain_service = MatriculaService()

    def listar_matriculas(self, paralelo_filter=None, estado_filter=None, search=None):
        """List enrollments with optional filters."""
        from apps.academico.infrastructure.models import Matricula

        qs = Matricula.objects.select_related(
            "estudiante",
            "paralelo__asignatura",
            "paralelo__periodo",
            "paralelo__tipo_licencia",
            "matriculado_por",
        ).order_by("-fecha_matricula")

        if paralelo_filter:
            qs = qs.filter(paralelo_id=paralelo_filter)
        if estado_filter:
            qs = qs.filter(estado=estado_filter)
        if search:
            from django.db.models import Q

            qs = qs.filter(
                Q(estudiante__first_name__icontains=search)
                | Q(estudiante__last_name__icontains=search)
                | Q(estudiante__cedula__icontains=search)
            )
        return qs

    def obtener_paralelos_activos(self):
        """Get all paralelos in active period for the dropdown."""
        from apps.academico.infrastructure.models import Paralelo

        return (
            Paralelo.objects.filter(periodo__activo=True)
            .select_related("asignatura", "periodo", "tipo_licencia", "docente")
            .order_by("asignatura__codigo", "nombre")
        )

    def obtener_estudiantes_disponibles(self):
        """Get all active students for the dropdown."""
        from apps.usuarios.infrastructure.models import Usuario

        return Usuario.objects.filter(rol="estudiante", is_active=True).order_by(
            "last_name", "first_name"
        )

    def crear_matricula(self, estudiante_id, paralelo_id, registrado_por_id):
        """
        Create enrollment with domain validations.
        Raises domain exceptions on failure.
        """
        from apps.academico.infrastructure.models import Matricula, Paralelo

        paralelo = Paralelo.objects.select_related("periodo", "asignatura").get(pk=paralelo_id)

        # Domain validations
        self.domain_service.validar_periodo_activo(paralelo.periodo.activo)

        existe = Matricula.objects.filter(
            estudiante_id=estudiante_id, paralelo_id=paralelo_id
        ).exists()
        self.domain_service.validar_no_duplicada(existe)

        # Check same asignatura in same periodo (any paralelo)
        ya_inscrito_asignatura = (
            Matricula.objects.filter(
                estudiante_id=estudiante_id,
                paralelo__asignatura_id=paralelo.asignatura_id,
                paralelo__periodo_id=paralelo.periodo_id,
                estado=Matricula.Estado.ACTIVA,
            )
            .select_related("paralelo")
            .first()
        )
        self.domain_service.validar_asignatura_no_duplicada(
            ya_inscrito=ya_inscrito_asignatura is not None,
            asignatura_nombre=paralelo.asignatura.nombre,
            paralelo_existente=(
                ya_inscrito_asignatura.paralelo.nombre if ya_inscrito_asignatura else ""
            ),
        )

        activas = Matricula.objects.filter(
            paralelo_id=paralelo_id, estado=Matricula.Estado.ACTIVA
        ).count()
        self.domain_service.validar_cupo(activas, paralelo.capacidad_maxima)

        # V5: schedule conflict against student's ACTIVA matrículas in same period.
        # Loads paralelo bloques as plain tuples; raises typed exception on conflict.
        from apps.academico.domain.exceptions import ConflictoHorarioEstudianteError
        from apps.academico.domain.services import HorarioConflictoService
        from apps.academico.infrastructure.models import BloqueHorario

        bloques_paralelo = [
            (b.dia_semana, b.hora_inicio, b.hora_fin)
            for b in BloqueHorario.objects.filter(paralelo_id=paralelo_id)
        ]
        if bloques_paralelo:
            conflictos = HorarioConflictoService.detectar_conflicto_estudiante(
                estudiante_id=estudiante_id,
                periodo_id=paralelo.periodo_id,
                bloques_propuestos=bloques_paralelo,
            )
            if conflictos:
                raise ConflictoHorarioEstudianteError(conflictos)

        matricula = Matricula.objects.create(
            estudiante_id=estudiante_id,
            paralelo_id=paralelo_id,
            estado=Matricula.Estado.ACTIVA,
            matriculado_por_id=registrado_por_id,
        )
        return matricula

    def cambiar_estado(self, matricula_id, nuevo_estado, rol):
        """Change enrollment state with domain validation."""
        from apps.academico.infrastructure.models import Matricula

        matricula = Matricula.objects.select_related("paralelo").get(pk=matricula_id)

        # Validate transition
        self.domain_service.validar_transicion_estado(
            estado_actual=matricula.estado,
            nuevo_estado=nuevo_estado,
            rol=rol,
        )

        # If reactivating, check capacity
        if nuevo_estado == Matricula.Estado.ACTIVA:
            activas = (
                Matricula.objects.filter(
                    paralelo=matricula.paralelo,
                    estado=Matricula.Estado.ACTIVA,
                )
                .exclude(pk=matricula.pk)
                .count()
            )
            self.domain_service.validar_cupo(activas, matricula.paralelo.capacidad_maxima)

        matricula.estado = nuevo_estado
        matricula.save(update_fields=["estado"])
        return matricula

    def obtener_matricula(self, matricula_id):
        """Get a single enrollment by ID."""
        from apps.academico.infrastructure.models import Matricula

        return Matricula.objects.select_related(
            "estudiante", "paralelo__asignatura", "paralelo__periodo"
        ).get(pk=matricula_id)

    def cambiar_paralelo(self, matricula_id, nuevo_paralelo_id):
        """
        Change the paralelo of an active enrollment.
        Validates: enrollment is active, no duplicate, capacity not exceeded.
        """
        from apps.academico.infrastructure.models import Matricula, Paralelo

        matricula = Matricula.objects.select_related("paralelo__periodo").get(pk=matricula_id)

        # Only active enrollments can change paralelo
        if matricula.estado != Matricula.Estado.ACTIVA:
            from apps.academico.domain.exceptions import EstadoMatriculaInvalidoError

            raise EstadoMatriculaInvalidoError(
                "Solo se puede cambiar el paralelo de matrículas activas."
            )

        nuevo_paralelo = Paralelo.objects.select_related("periodo").get(pk=nuevo_paralelo_id)

        # Cannot move to same paralelo
        if matricula.paralelo_id == nuevo_paralelo.pk:
            from apps.academico.domain.exceptions import MatriculaDuplicadaError

            raise MatriculaDuplicadaError("El estudiante ya se encuentra en este paralelo.")

        # Check no duplicate in target paralelo
        existe = Matricula.objects.filter(
            estudiante_id=matricula.estudiante_id, paralelo_id=nuevo_paralelo_id
        ).exists()
        self.domain_service.validar_no_duplicada(existe)

        # Check capacity in target paralelo
        activas = Matricula.objects.filter(
            paralelo_id=nuevo_paralelo_id, estado=Matricula.Estado.ACTIVA
        ).count()
        self.domain_service.validar_cupo(activas, nuevo_paralelo.capacidad_maxima)

        matricula.paralelo = nuevo_paralelo
        matricula.save(update_fields=["paralelo_id"])
        return matricula

    def obtener_periodos_activos(self):
        """Get all active periods (one per tipo_licencia)."""
        from apps.academico.infrastructure.models import Periodo

        return (
            Periodo.objects.filter(activo=True)
            .select_related("tipo_licencia")
            .order_by("tipo_licencia__codigo")
        )

    def obtener_paralelos_por_periodo(self, periodo_id):
        """Get all paralelos for a specific period."""
        from apps.academico.infrastructure.models import Paralelo

        return (
            Paralelo.objects.filter(periodo_id=periodo_id)
            .select_related("asignatura", "periodo", "tipo_licencia", "docente")
            .order_by("asignatura__codigo", "nombre")
        )

    def matricular_en_lote(self, estudiante_id, paralelo_ids, registrado_por_id):
        """
        Enroll a student in multiple paralelos at once.
        Skips paralelos where enrollment already exists or capacity is full.
        Returns (created_count, skipped_details).
        """
        from django.db import transaction
        from apps.academico.domain.services import HorarioConflictoService
        from apps.academico.infrastructure.models import BloqueHorario, Matricula, Paralelo

        paralelos = Paralelo.objects.filter(pk__in=paralelo_ids).select_related(
            "periodo", "asignatura"
        )

        creados = 0
        omitidos = []

        with transaction.atomic():
            for paralelo in paralelos:
                # Validate active period
                if not paralelo.periodo.activo:
                    omitidos.append(f"{paralelo.asignatura.codigo}: período inactivo")
                    continue

                # Check duplicate
                if Matricula.objects.filter(
                    estudiante_id=estudiante_id, paralelo_id=paralelo.pk
                ).exists():
                    omitidos.append(f"{paralelo.asignatura.codigo}: ya matriculado")
                    continue

                # Check same asignatura in same periodo (any paralelo)
                mat_asignatura = Matricula.objects.filter(
                    estudiante_id=estudiante_id,
                    paralelo__asignatura_id=paralelo.asignatura_id,
                    paralelo__periodo_id=paralelo.periodo_id,
                    estado=Matricula.Estado.ACTIVA,
                ).exists()
                if mat_asignatura:
                    omitidos.append(
                        f"{paralelo.asignatura.codigo}: ya inscrito en "
                        f"esta asignatura en otro paralelo"
                    )
                    continue

                # Check capacity
                activas = Matricula.objects.filter(
                    paralelo=paralelo, estado=Matricula.Estado.ACTIVA
                ).count()
                if activas >= paralelo.capacidad_maxima:
                    omitidos.append(f"{paralelo.asignatura.codigo}: sin cupo")
                    continue

                # V5: schedule conflict check (collect-all — design §4.1 + task 2.8).
                bloques_paralelo = [
                    (b.dia_semana, b.hora_inicio, b.hora_fin)
                    for b in BloqueHorario.objects.filter(paralelo_id=paralelo.pk)
                ]
                if bloques_paralelo:
                    conflictos = HorarioConflictoService.detectar_conflicto_estudiante(
                        estudiante_id=estudiante_id,
                        periodo_id=paralelo.periodo_id,
                        bloques_propuestos=bloques_paralelo,
                    )
                    if conflictos:
                        first = conflictos[0]
                        omitidos.append(
                            f"{paralelo.asignatura.codigo}: conflicto de horario con "
                            f"{first.asignatura_codigo} ({first.paralelo_nombre}) "
                            f"el {first.dia_semana_label} "
                            f"{first.hora_inicio:%H:%M}-{first.hora_fin:%H:%M}"
                        )
                        continue

                Matricula.objects.create(
                    estudiante_id=estudiante_id,
                    paralelo=paralelo,
                    estado=Matricula.Estado.ACTIVA,
                    matriculado_por_id=registrado_por_id,
                )
                creados += 1

        return creados, omitidos
