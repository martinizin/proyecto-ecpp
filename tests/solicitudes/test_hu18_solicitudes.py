"""
Tests for HU18 — Solicitudes de recalificación y justificación de inasistencia.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.calificaciones.infrastructure.models import RegistroCalificacionParalelo
from apps.notificaciones.infrastructure.models import Notificacion
from apps.solicitudes.application.services import SolicitudAppService
from apps.solicitudes.infrastructure.models import Solicitud
from tests.factories import (
    AsistenciaFactory,
    CalificacionFactory,
    DocenteFactory,
    EstudianteFactory,
    EvaluacionFactory,
    InspectorFactory,
    MatriculaFactory,
    ParaleloFactory,
    PeriodoFactory,
    RegistroCalificacionParaleloFactory,
    SolicitudFactory,
)


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE TESTS
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestObtenerCalificacionesReclamables:
    def _setup_validada(self):
        """Helper: calificacion with VALIDADO registro, active period, active matricula."""
        periodo = PeriodoFactory(activo=True)
        paralelo = ParaleloFactory(periodo=periodo)
        estudiante = EstudianteFactory()
        estudiante.save()
        MatriculaFactory(estudiante=estudiante, paralelo=paralelo)
        RegistroCalificacionParaleloFactory(
            paralelo=paralelo, estado=RegistroCalificacionParalelo.Estado.VALIDADO
        )
        evaluacion = EvaluacionFactory(paralelo=paralelo)
        calificacion = CalificacionFactory(evaluacion=evaluacion, estudiante=estudiante)
        return estudiante, calificacion

    def test_obtener_calificaciones_reclamables_solo_validadas(self):
        estudiante, calificacion = self._setup_validada()
        service = SolicitudAppService()
        qs = service.obtener_calificaciones_reclamables(estudiante)
        assert calificacion in qs

    def test_obtener_calificaciones_reclamables_excluye_no_validadas(self):
        periodo = PeriodoFactory(activo=True)
        paralelo = ParaleloFactory(periodo=periodo)
        estudiante = EstudianteFactory()
        estudiante.save()
        MatriculaFactory(estudiante=estudiante, paralelo=paralelo)
        # BORRADOR — should be excluded
        RegistroCalificacionParaleloFactory(
            paralelo=paralelo, estado=RegistroCalificacionParalelo.Estado.BORRADOR
        )
        evaluacion = EvaluacionFactory(paralelo=paralelo)
        CalificacionFactory(evaluacion=evaluacion, estudiante=estudiante)

        service = SolicitudAppService()
        qs = service.obtener_calificaciones_reclamables(estudiante)
        assert qs.count() == 0


@pytest.mark.django_db
class TestCrearRecalificacion:
    def _setup(self):
        periodo = PeriodoFactory(activo=True)
        paralelo = ParaleloFactory(periodo=periodo)
        estudiante = EstudianteFactory()
        estudiante.save()
        MatriculaFactory(estudiante=estudiante, paralelo=paralelo)
        RegistroCalificacionParaleloFactory(
            paralelo=paralelo, estado=RegistroCalificacionParalelo.Estado.VALIDADO
        )
        evaluacion = EvaluacionFactory(paralelo=paralelo)
        calificacion = CalificacionFactory(evaluacion=evaluacion, estudiante=estudiante)
        return estudiante, calificacion

    def test_crear_recalificacion_exitosa(self):
        estudiante, calificacion = self._setup()
        service = SolicitudAppService()
        result = service.crear_recalificacion(estudiante, calificacion.pk, "Nota incorrecta")
        assert result["ok"] is True
        sol = result["solicitud"]
        assert sol.tipo == Solicitud.TipoSolicitud.RECTIFICACION
        assert sol.numero_solicitud == 1
        assert sol.requiere_secretaria is False
        # Notificacion created for docente
        assert Notificacion.objects.filter(
            destinatario=calificacion.evaluacion.paralelo.docente
        ).exists()

    def test_crear_recalificacion_segunda_requiere_secretaria(self):
        estudiante, calificacion = self._setup()
        service = SolicitudAppService()
        service.crear_recalificacion(estudiante, calificacion.pk, "Primera vez")
        result = service.crear_recalificacion(estudiante, calificacion.pk, "Segunda vez")
        assert result["ok"] is True
        assert result["solicitud"].numero_solicitud == 2
        assert result["solicitud"].requiere_secretaria is True

    def test_crear_recalificacion_sin_descripcion(self):
        """Post-QA simplification: descripcion (motivo) is now optional."""
        estudiante, calificacion = self._setup()
        service = SolicitudAppService()
        result = service.crear_recalificacion(estudiante, calificacion.pk, "")
        assert result["ok"] is True
        assert result["solicitud"].descripcion == ""

    def test_crear_recalificacion_calificacion_invalida(self):
        estudiante = EstudianteFactory()
        estudiante.save()
        service = SolicitudAppService()
        result = service.crear_recalificacion(estudiante, 99999, "Motivo")
        assert result["ok"] is False
        assert "no encontrada" in result["error"].lower()

    def test_crear_recalificacion_periodo_inactivo(self):
        periodo = PeriodoFactory(activo=False)
        paralelo = ParaleloFactory(periodo=periodo)
        estudiante = EstudianteFactory()
        estudiante.save()
        MatriculaFactory(estudiante=estudiante, paralelo=paralelo)
        RegistroCalificacionParaleloFactory(
            paralelo=paralelo, estado=RegistroCalificacionParalelo.Estado.VALIDADO
        )
        evaluacion = EvaluacionFactory(paralelo=paralelo)
        calificacion = CalificacionFactory(evaluacion=evaluacion, estudiante=estudiante)

        service = SolicitudAppService()
        result = service.crear_recalificacion(estudiante, calificacion.pk, "Motivo")
        assert result["ok"] is False
        assert "período activo" in result["error"].lower()


@pytest.mark.django_db
class TestJustificacion:
    def _setup(self):
        periodo = PeriodoFactory(activo=True)
        paralelo = ParaleloFactory(periodo=periodo)
        estudiante = EstudianteFactory()
        estudiante.save()
        MatriculaFactory(estudiante=estudiante, paralelo=paralelo)
        asistencia = AsistenciaFactory(estudiante=estudiante, paralelo=paralelo)
        return estudiante, asistencia

    def test_obtener_inasistencias_justificables(self):
        estudiante, asistencia = self._setup()
        service = SolicitudAppService()
        qs = service.obtener_inasistencias_justificables(estudiante)
        assert asistencia in qs

    def test_crear_justificacion_exitosa(self):
        estudiante, asistencia = self._setup()
        service = SolicitudAppService()
        result = service.crear_justificacion(estudiante, asistencia.pk, "Estuve enfermo")
        assert result["ok"] is True
        assert result["solicitud"].tipo == Solicitud.TipoSolicitud.JUSTIFICACION

    def test_crear_justificacion_duplicada_pendiente(self):
        estudiante, asistencia = self._setup()
        service = SolicitudAppService()
        service.crear_justificacion(estudiante, asistencia.pk, "Primera")
        result = service.crear_justificacion(estudiante, asistencia.pk, "Segunda")
        assert result["ok"] is False
        assert "pendiente" in result["error"].lower()

    def test_crear_justificacion_permite_si_previa_rechazada(self):
        estudiante, asistencia = self._setup()
        # Create a rejected one
        SolicitudFactory(
            tipo=Solicitud.TipoSolicitud.JUSTIFICACION,
            estudiante=estudiante,
            asistencia=asistencia,
            estado=Solicitud.EstadoSolicitud.RECHAZADA,
        )
        service = SolicitudAppService()
        result = service.crear_justificacion(estudiante, asistencia.pk, "Reintento")
        assert result["ok"] is True


@pytest.mark.django_db
class TestObtenerMisSolicitudes:
    def test_obtener_mis_solicitudes_filtro_tipo(self):
        estudiante = EstudianteFactory()
        estudiante.save()
        SolicitudFactory(estudiante=estudiante, tipo=Solicitud.TipoSolicitud.RECTIFICACION)
        SolicitudFactory(estudiante=estudiante, tipo=Solicitud.TipoSolicitud.JUSTIFICACION)
        service = SolicitudAppService()
        qs = service.obtener_mis_solicitudes(
            estudiante, tipo=Solicitud.TipoSolicitud.RECTIFICACION
        )
        assert qs.count() == 1
        assert qs.first().tipo == Solicitud.TipoSolicitud.RECTIFICACION


@pytest.mark.django_db
class TestValidarArchivo:
    def test_validar_archivo_tamano_excedido(self):
        error = SolicitudAppService._validar_archivo(
            SimpleUploadedFile("doc.pdf", b"x" * (6 * 1024 * 1024), content_type="application/pdf")
        )
        assert error is not None
        assert "5 MB" in error

    def test_validar_archivo_extension_invalida(self):
        error = SolicitudAppService._validar_archivo(
            SimpleUploadedFile("virus.exe", b"data", content_type="application/octet-stream")
        )
        assert error is not None
        assert "PDF" in error or "png" in error.lower() or "permiten" in error.lower()


# ══════════════════════════════════════════════════════════════════════════════
# VIEW TESTS
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestCrearRecalificacionView:
    def _setup(self, client):
        periodo = PeriodoFactory(activo=True)
        paralelo = ParaleloFactory(periodo=periodo)
        estudiante = EstudianteFactory()
        estudiante.save()
        MatriculaFactory(estudiante=estudiante, paralelo=paralelo)
        RegistroCalificacionParaleloFactory(
            paralelo=paralelo, estado=RegistroCalificacionParalelo.Estado.VALIDADO
        )
        evaluacion = EvaluacionFactory(paralelo=paralelo)
        calificacion = CalificacionFactory(evaluacion=evaluacion, estudiante=estudiante)
        client.force_login(estudiante)
        return estudiante, calificacion

    def test_crear_recalificacion_get_estudiante(self, client):
        self._setup(client)
        url = reverse("solicitudes:crear_recalificacion")
        response = client.get(url)
        assert response.status_code == 200

    def test_crear_recalificacion_get_docente_prohibido(self, client):
        docente = DocenteFactory()
        docente.save()
        client.force_login(docente)
        url = reverse("solicitudes:crear_recalificacion")
        response = client.get(url)
        assert response.status_code == 403

    def test_crear_recalificacion_post_exitoso(self, client):
        estudiante, calificacion = self._setup(client)
        url = reverse("solicitudes:crear_recalificacion")
        response = client.post(
            url,
            {
                "calificacion": calificacion.pk,
                "descripcion": "Error en nota",
            },
        )
        assert response.status_code == 302
        assert Solicitud.objects.filter(estudiante=estudiante).exists()

    def test_asignaturas_map_en_contexto(self, client):
        """GET expone asignaturas_map agrupado por asignatura para los cascading selects."""
        estudiante, calificacion = self._setup(client)
        url = reverse("solicitudes:crear_recalificacion")
        response = client.get(url)

        assert response.status_code == 200
        assert "asignaturas_map" in response.context

        mapa = response.context["asignaturas_map"]
        assert isinstance(mapa, dict)
        assert all(
            isinstance(k, str) for k in mapa.keys()
        ), "keys deben ser str (json_script-safe)"

        # La asignatura del setup debe estar
        asignatura = calificacion.evaluacion.paralelo.asignatura
        entry = mapa[str(asignatura.pk)]
        assert entry["nombre"] == asignatura.nombre
        assert entry["codigo"] == asignatura.codigo

        # La evaluación debe estar dentro de su asignatura
        evaluaciones = entry["evaluaciones"]
        assert len(evaluaciones) == 1
        ev = evaluaciones[0]
        assert ev["id"] == calificacion.pk
        assert ev["tipo_label"] == calificacion.evaluacion.get_tipo_display()
        assert ev["nota"] == str(calificacion.nota)

    def test_asignaturas_map_agrupa_por_asignatura(self, client):
        """Múltiples calificaciones de la misma asignatura quedan bajo una sola key."""
        estudiante, cal1 = self._setup(client)
        # Agregar segunda evaluación al MISMO paralelo (misma asignatura)
        paralelo = cal1.evaluacion.paralelo
        ev2 = EvaluacionFactory(paralelo=paralelo, tipo="parcial2_10h")
        cal2 = CalificacionFactory(evaluacion=ev2, estudiante=estudiante)

        url = reverse("solicitudes:crear_recalificacion")
        response = client.get(url)
        mapa = response.context["asignaturas_map"]

        asignatura_key = str(paralelo.asignatura.pk)
        assert asignatura_key in mapa
        ids = [ev["id"] for ev in mapa[asignatura_key]["evaluaciones"]]
        assert cal1.pk in ids
        assert cal2.pk in ids


@pytest.mark.django_db
class TestCrearJustificacionView:
    def _setup(self, client):
        periodo = PeriodoFactory(activo=True)
        paralelo = ParaleloFactory(periodo=periodo)
        estudiante = EstudianteFactory()
        estudiante.save()
        MatriculaFactory(estudiante=estudiante, paralelo=paralelo)
        asistencia = AsistenciaFactory(estudiante=estudiante, paralelo=paralelo)
        client.force_login(estudiante)
        return estudiante, asistencia

    def test_crear_justificacion_get_estudiante(self, client):
        self._setup(client)
        url = reverse("solicitudes:crear_justificacion")
        response = client.get(url)
        assert response.status_code == 200

    def test_crear_justificacion_post_exitoso(self, client):
        estudiante, asistencia = self._setup(client)
        url = reverse("solicitudes:crear_justificacion")
        response = client.post(
            url,
            {
                "asistencia": asistencia.pk,
                "descripcion": "Estuve enfermo",
            },
        )
        assert response.status_code == 302
        assert Solicitud.objects.filter(
            estudiante=estudiante, tipo=Solicitud.TipoSolicitud.JUSTIFICACION
        ).exists()


@pytest.mark.django_db
class TestMisSolicitudesView:
    def _login_estudiante(self, client):
        estudiante = EstudianteFactory()
        estudiante.save()
        client.force_login(estudiante)
        return estudiante

    def test_mis_solicitudes_get(self, client):
        estudiante = self._login_estudiante(client)
        SolicitudFactory(estudiante=estudiante)
        url = reverse("solicitudes:mis_solicitudes")
        response = client.get(url)
        assert response.status_code == 200

    def test_mis_solicitudes_filtro_tipo(self, client):
        estudiante = self._login_estudiante(client)
        SolicitudFactory(estudiante=estudiante, tipo=Solicitud.TipoSolicitud.RECTIFICACION)
        SolicitudFactory(estudiante=estudiante, tipo=Solicitud.TipoSolicitud.JUSTIFICACION)
        url = reverse("solicitudes:mis_solicitudes")
        response = client.get(url, {"tipo": "rectificacion"})
        assert response.status_code == 200


@pytest.mark.django_db
class TestDashboardEstudiante:
    def test_dashboard_estudiante_muestra_cards_solicitudes(self, client):
        estudiante = EstudianteFactory()
        estudiante.save()
        client.force_login(estudiante)
        url = reverse("usuarios:dashboard")
        response = client.get(url)
        assert response.status_code == 200
        content = response.content.decode()
        assert (
            "solicitudes" in content.lower()
            or "recalificacion" in content.lower()
            or reverse("solicitudes:mis_solicitudes") in content
        )


# ══════════════════════════════════════════════════════════════════════════════
# NEW TESTS — Recalificación desde COMPLETO + Notificaciones justificación
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestRecalificacionDesdeCompleto:
    """Reclamable grades should include COMPLETO (planilla enviada, no validada aún)."""

    def test_calificaciones_reclamables_incluye_completo(self):
        periodo = PeriodoFactory(activo=True)
        paralelo = ParaleloFactory(periodo=periodo)
        estudiante = EstudianteFactory()
        estudiante.save()
        MatriculaFactory(estudiante=estudiante, paralelo=paralelo)
        RegistroCalificacionParaleloFactory(
            paralelo=paralelo, estado=RegistroCalificacionParalelo.Estado.COMPLETO
        )
        evaluacion = EvaluacionFactory(paralelo=paralelo)
        calificacion = CalificacionFactory(evaluacion=evaluacion, estudiante=estudiante)

        qs = SolicitudAppService.obtener_calificaciones_reclamables(estudiante)
        assert calificacion in qs

    def test_crear_recalificacion_con_estado_completo(self):
        periodo = PeriodoFactory(activo=True)
        paralelo = ParaleloFactory(periodo=periodo)
        estudiante = EstudianteFactory()
        estudiante.save()
        MatriculaFactory(estudiante=estudiante, paralelo=paralelo)
        RegistroCalificacionParaleloFactory(
            paralelo=paralelo, estado=RegistroCalificacionParalelo.Estado.COMPLETO
        )
        evaluacion = EvaluacionFactory(paralelo=paralelo)
        calificacion = CalificacionFactory(evaluacion=evaluacion, estudiante=estudiante)

        result = SolicitudAppService.crear_recalificacion(
            estudiante, calificacion.pk, "Nota incorrecta"
        )
        assert result["ok"] is True

    def test_crear_recalificacion_rechaza_borrador(self):
        periodo = PeriodoFactory(activo=True)
        paralelo = ParaleloFactory(periodo=periodo)
        estudiante = EstudianteFactory()
        estudiante.save()
        MatriculaFactory(estudiante=estudiante, paralelo=paralelo)
        RegistroCalificacionParaleloFactory(
            paralelo=paralelo, estado=RegistroCalificacionParalelo.Estado.BORRADOR
        )
        evaluacion = EvaluacionFactory(paralelo=paralelo)
        calificacion = CalificacionFactory(evaluacion=evaluacion, estudiante=estudiante)

        result = SolicitudAppService.crear_recalificacion(estudiante, calificacion.pk, "Motivo")
        assert result["ok"] is False
        assert "planilla ya fue enviada" in result["error"].lower()


@pytest.mark.django_db
class TestNotificacionInspectorJustificacion:
    """Inspector should be notified (in-app + email) when a justification is created."""

    def test_crear_justificacion_notifica_inspector(self):
        periodo = PeriodoFactory(activo=True)
        paralelo = ParaleloFactory(periodo=periodo)
        estudiante = EstudianteFactory()
        estudiante.save()
        MatriculaFactory(estudiante=estudiante, paralelo=paralelo)
        asistencia = AsistenciaFactory(estudiante=estudiante, paralelo=paralelo)

        inspector = InspectorFactory()
        inspector.save()

        result = SolicitudAppService.crear_justificacion(
            estudiante, asistencia.pk, "Estuve enfermo"
        )
        assert result["ok"] is True

        # Inspector receives in-app notification
        notif = Notificacion.objects.filter(
            destinatario=inspector,
            tipo=Notificacion.Tipo.SOLICITUD_JUSTIFICACION,
        )
        assert notif.exists()
        assert "justificación" in notif.first().titulo.lower()

    def test_crear_justificacion_sin_inspector_no_falla(self):
        """If no inspectors exist, justification creation still succeeds."""
        periodo = PeriodoFactory(activo=True)
        paralelo = ParaleloFactory(periodo=periodo)
        estudiante = EstudianteFactory()
        estudiante.save()
        MatriculaFactory(estudiante=estudiante, paralelo=paralelo)
        asistencia = AsistenciaFactory(estudiante=estudiante, paralelo=paralelo)

        result = SolicitudAppService.crear_justificacion(
            estudiante, asistencia.pk, "Motivo válido"
        )
        assert result["ok"] is True
