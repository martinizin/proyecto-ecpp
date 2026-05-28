"""Tests for InspectorJustificacionDetalleView (HU21 — T5).

Capability: ``inspector-resolucion-justificacion`` (R1, R2, R3 — detail
view + dual evidence rendering + MIME-aware preview).

Covers:
  * Access control (anonymous, non-inspector roles, inspector OK).
  * Queryset filter to ``TipoSolicitud.JUSTIFICACION`` (404 otherwise).
  * Dual evidence rendering: legacy ``archivo_adjunto`` + new
    ``ArchivoSolicitud`` reverse FK in the same template.
  * MIME-aware preview: PDFs as ``<iframe>``, images as ``<img>``,
    other MIME types as download links.
  * Historial table rendering and empty state.
  * Urgency badge classification reflected in the rendered HTML.
  * Form de resolución visibility according to ``estado``:
      - Pendiente / EnRevisión: form action visible.
      - Aprobada / Rechazada: form hidden, "ya fue resuelta" message.

NOTE on N+1: the view uses ``select_related`` + ``prefetch_related``
intentionally to avoid N+1 (see design #735). We do NOT enforce a
strict ``assertNumQueries`` cap here — T4 already protects the dashboard
budget; the detail view's query count depends on each test's setup
(legacy attachment vs N archivos, certificado presence, etc.).
"""

import datetime

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from apps.asistencia.infrastructure.models import Asistencia
from apps.solicitudes.infrastructure.models import (
    ArchivoSolicitud,
    CertificadoJustificacion,
    ConfiguracionJustificacion,
    HistorialSolicitud,
    Solicitud,
)
from apps.usuarios.infrastructure.models import Usuario
from tests.factories import (
    AsistenciaFactory,
    DocenteFactory,
    EstudianteFactory,
    InspectorFactory,
    ParaleloFactory,
    PeriodoFactory,
    SolicitudFactory,
    UsuarioFactory,
)


# -------------------------------------------------------------------- #
# Helpers
# -------------------------------------------------------------------- #


def _make_justificacion(
    *,
    estudiante=None,
    paralelo=None,
    estado=Solicitud.EstadoSolicitud.PENDIENTE,
    fecha_creacion=None,
    archivo_adjunto=None,
):
    """Create a ``Solicitud(tipo=JUSTIFICACION)`` with an Asistencia link."""
    if estudiante is None:
        estudiante = EstudianteFactory()
        estudiante.save()
    if paralelo is None:
        periodo = PeriodoFactory(activo=True)
        paralelo = ParaleloFactory(periodo=periodo)
    asistencia = AsistenciaFactory(
        estudiante=estudiante,
        paralelo=paralelo,
        estado=Asistencia.Estado.AUSENTE,
    )
    sol = SolicitudFactory(
        tipo=Solicitud.TipoSolicitud.JUSTIFICACION,
        estudiante=estudiante,
        asistencia=asistencia,
        estado=estado,
        descripcion="Justificación de prueba",
    )
    if archivo_adjunto is not None:
        sol.archivo_adjunto = archivo_adjunto
        sol.save()
    if fecha_creacion is not None:
        Solicitud.objects.filter(pk=sol.pk).update(fecha_creacion=fecha_creacion)
        sol.refresh_from_db()
    return sol


def _url(pk):
    return reverse("solicitudes:inspector_justificacion_detalle", args=[pk])


# -------------------------------------------------------------------- #
# R9 — Access control
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestAccesoControl:
    def test_anonymous_redirects_to_login(self, client):
        sol = _make_justificacion()
        resp = client.get(_url(sol.pk))
        assert resp.status_code == 302
        assert "/usuarios/login/" in resp.url

    @pytest.mark.parametrize(
        "factory_callable",
        [
            lambda: EstudianteFactory(),
            lambda: DocenteFactory(),
            lambda: UsuarioFactory(rol=Usuario.Rol.SECRETARIA),
        ],
        ids=["estudiante", "docente", "secretaria"],
    )
    def test_no_inspector_forbidden(self, client, factory_callable):
        sol = _make_justificacion()
        user = factory_callable()
        user.save()
        client.force_login(user)
        resp = client.get(_url(sol.pk))
        assert resp.status_code == 403

    def test_inspector_ok(self, client):
        sol = _make_justificacion()
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        resp = client.get(_url(sol.pk))
        assert resp.status_code == 200


# -------------------------------------------------------------------- #
# Queryset filtering — only JUSTIFICACION
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestQuerysetFiltering:
    def test_no_justificacion_returns_404(self, client):
        # A solicitud with tipo=RECTIFICACION must not be reachable through
        # the inspector detail view (it filters on JUSTIFICACION only).
        estudiante = EstudianteFactory()
        estudiante.save()
        sol = SolicitudFactory(
            tipo=Solicitud.TipoSolicitud.RECTIFICACION,
            estudiante=estudiante,
            descripcion="No-justificacion solicitud",
        )
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)

        resp = client.get(_url(sol.pk))
        assert resp.status_code == 404

    def test_solicitud_inexistente_404(self, client):
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)
        resp = client.get(_url(99999))
        assert resp.status_code == 404


# -------------------------------------------------------------------- #
# R2 + R3 — Dual evidence rendering with MIME-aware preview
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestRenderEvidenciasDual:
    def test_renderiza_archivo_adjunto_legacy_cuando_existe(self, client):
        sol = _make_justificacion(
            archivo_adjunto=SimpleUploadedFile(
                "legacy.pdf",
                b"%PDF-1.4 fake content",
                content_type="application/pdf",
            ),
        )
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)

        resp = client.get(_url(sol.pk))
        assert resp.status_code == 200
        # Legacy attachment URL appears somewhere in the page.
        assert sol.archivo_adjunto.url.encode() in resp.content

    def test_renderiza_archivo_adjunto_legacy_pdf_como_iframe(self, client):
        """Regresion: legacy PDF debe seguir renderizando <iframe>, no <img>."""
        sol = _make_justificacion(
            archivo_adjunto=SimpleUploadedFile(
                "legacy.pdf",
                b"%PDF-1.4 fake content",
                content_type="application/pdf",
            ),
        )
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)

        resp = client.get(_url(sol.pk))
        assert resp.status_code == 200
        body = resp.content
        legacy_url = sol.archivo_adjunto.url.encode()
        # Must render iframe pointing to the legacy file.
        assert b"<iframe" in body
        assert legacy_url in body

    def test_renderiza_archivo_adjunto_legacy_imagen_como_img(self, client):
        """Bug QA: una imagen subida como archivo_adjunto legacy debe
        previsualizarse con <img>, no caer al fallback 'Descargar'.
        """
        sol = _make_justificacion(
            archivo_adjunto=SimpleUploadedFile(
                "cfg_general.png",
                b"\x89PNG\r\n\x1a\n fake png",
                content_type="image/png",
            ),
        )
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)

        resp = client.get(_url(sol.pk))
        assert resp.status_code == 200
        body = resp.content
        legacy_url = sol.archivo_adjunto.url.encode()
        # Image preview rendered, NOT the download-only fallback.
        assert b"<img" in body
        assert legacy_url in body
        # Defensive: do NOT show the descargar fallback for this case.
        assert b"Descargar " + sol.archivo_adjunto.name.encode() not in body

    def test_renderiza_archivos_nuevos_pdf_como_iframe(self, client):
        sol = _make_justificacion()
        archivo = ArchivoSolicitud.objects.create(
            solicitud=sol,
            archivo=SimpleUploadedFile(
                "evidencia.pdf",
                b"%PDF-1.4 fake content",
                content_type="application/pdf",
            ),
            nombre_original="evidencia.pdf",
            tipo_mime="application/pdf",
            tamanio_bytes=21,
        )
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)

        resp = client.get(_url(sol.pk))
        assert resp.status_code == 200
        body = resp.content
        assert b"<iframe" in body
        assert archivo.archivo.url.encode() in body

    def test_renderiza_archivos_nuevos_imagen_como_img(self, client):
        sol = _make_justificacion()
        archivo = ArchivoSolicitud.objects.create(
            solicitud=sol,
            archivo=SimpleUploadedFile(
                "evidencia.jpg",
                b"\xff\xd8\xff\xe0 fake jpeg",
                content_type="image/jpeg",
            ),
            nombre_original="evidencia.jpg",
            tipo_mime="image/jpeg",
            tamanio_bytes=15,
        )
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)

        resp = client.get(_url(sol.pk))
        assert resp.status_code == 200
        body = resp.content
        assert b"<img" in body
        assert archivo.archivo.url.encode() in body

    def test_renderiza_archivos_otros_como_link_descarga(self, client):
        sol = _make_justificacion()
        archivo = ArchivoSolicitud.objects.create(
            solicitud=sol,
            archivo=SimpleUploadedFile(
                "evidencia.pdf",  # extension valid for FileExtensionValidator
                b"binary content",
                content_type="application/octet-stream",
            ),
            nombre_original="evidencia.bin",
            tipo_mime="application/octet-stream",
            tamanio_bytes=14,
        )
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)

        resp = client.get(_url(sol.pk))
        assert resp.status_code == 200
        body = resp.content
        # Neither iframe nor img — falls through to a download link.
        url_bytes = archivo.archivo.url.encode()
        assert url_bytes in body
        # Specifically: anchor tag pointing at the file URL.
        assert b'href="' + url_bytes in body

    def test_renderiza_legacy_y_nuevos_simultaneamente(self, client):
        sol = _make_justificacion(
            archivo_adjunto=SimpleUploadedFile(
                "legacy.pdf",
                b"%PDF-1.4 legacy",
                content_type="application/pdf",
            ),
        )
        nuevo = ArchivoSolicitud.objects.create(
            solicitud=sol,
            archivo=SimpleUploadedFile(
                "nuevo.pdf",
                b"%PDF-1.4 new",
                content_type="application/pdf",
            ),
            nombre_original="nuevo.pdf",
            tipo_mime="application/pdf",
            tamanio_bytes=13,
        )
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)

        resp = client.get(_url(sol.pk))
        assert resp.status_code == 200
        body = resp.content
        assert sol.archivo_adjunto.url.encode() in body
        assert nuevo.archivo.url.encode() in body

    def test_sin_evidencias_muestra_mensaje(self, client):
        sol = _make_justificacion()
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)

        resp = client.get(_url(sol.pk))
        assert resp.status_code == 200
        assert b"Sin evidencias adjuntas" in resp.content


# -------------------------------------------------------------------- #
# Historial rendering
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestRenderHistorial:
    def test_renderiza_historial_cuando_hay_filas(self, client):
        sol = _make_justificacion()
        actor = InspectorFactory()
        actor.save()
        HistorialSolicitud.objects.create(
            solicitud=sol,
            estado_anterior=Solicitud.EstadoSolicitud.PENDIENTE,
            estado_nuevo=Solicitud.EstadoSolicitud.EN_REVISION,
            cambiado_por=actor,
            comentario="Comentario único de historial",
        )
        client.force_login(actor)

        resp = client.get(_url(sol.pk))
        assert resp.status_code == 200
        assert b"Comentario \xc3\xbanico de historial" in resp.content

    def test_sin_historial_muestra_mensaje(self, client):
        sol = _make_justificacion()
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)

        resp = client.get(_url(sol.pk))
        assert resp.status_code == 200
        assert b"Sin historial" in resp.content


# -------------------------------------------------------------------- #
# Urgency badge
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestBadgeUrgencia:
    def test_urgencia_se_renderiza_con_clase_correcta(self, client):
        # Force config defaults so the math is deterministic.
        ConfiguracionJustificacion.objects.filter(pk=1).delete()
        ConfiguracionJustificacion.get_singleton()  # deadline=5, alerta=2

        # 30 days ago => vencido.
        sol = _make_justificacion(
            estado=Solicitud.EstadoSolicitud.PENDIENTE,
            fecha_creacion=timezone.now() - datetime.timedelta(days=30),
        )
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)

        resp = client.get(_url(sol.pk))
        assert resp.status_code == 200
        # The shared partial renders ``badge-rojo`` (and ``bg-red-*``)
        # for the ``vencido`` urgency.
        assert b"badge-rojo" in resp.content or b"bg-red" in resp.content


# -------------------------------------------------------------------- #
# Form de resolución — visibility according to estado
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestFormResolverVisibility:
    def test_form_resolver_visible_si_pendiente(self, client):
        sol = _make_justificacion(estado=Solicitud.EstadoSolicitud.PENDIENTE)
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)

        resp = client.get(_url(sol.pk))
        assert resp.status_code == 200
        # The form skeleton points at the resolver endpoint for this solicitud.
        resolver_url = reverse("solicitudes:inspector_justificacion_resolver", args=[sol.pk])
        assert resolver_url.encode() in resp.content

    def test_form_resolver_oculto_si_ya_resuelta(self, client):
        sol = _make_justificacion(estado=Solicitud.EstadoSolicitud.APROBADA)
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)

        resp = client.get(_url(sol.pk))
        assert resp.status_code == 200
        # "Ya fue resuelta" message must render.
        assert b"ya fue resuelta" in resp.content.lower()
        # The form action MUST NOT point at the resolver endpoint when
        # the solicitud is already resolved.
        resolver_url = reverse("solicitudes:inspector_justificacion_resolver", args=[sol.pk])
        # No <form ... action="<resolver_url>"> in the rendered HTML.
        assert (b'action="' + resolver_url.encode() + b'"') not in resp.content


# -------------------------------------------------------------------- #
# Certificado block (defensive rendering)
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestCertificadoBlock:
    def test_renderiza_tipo_certificado_si_existe(self, client):
        sol = _make_justificacion()
        CertificadoJustificacion.objects.create(
            solicitud=sol,
            tipo="medico",
            institucion_emisora="Hospital Eugenio Espejo",
            fecha_certificado=datetime.date(2026, 4, 1),
        )
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)

        resp = client.get(_url(sol.pk))
        assert resp.status_code == 200
        assert b"Hospital Eugenio Espejo" in resp.content


# -------------------------------------------------------------------- #
# Post-archive fix — urgencia condicional al estado en el header del detalle
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestUrgenciaHeaderSegunEstado:
    """El badge de urgencia en el header del detalle solo aparece si la
    solicitud sigue PENDIENTE / EN_REVISION. Para resueltas, ni el badge
    ni la línea de 'N días hábiles transcurridos' deben renderizarse.
    """

    def _login_inspector(self, client):
        inspector = InspectorFactory()
        inspector.save()
        client.force_login(inspector)

    def test_detalle_pendiente_muestra_badge_urgencia(self, client):
        ConfiguracionJustificacion.objects.filter(pk=1).delete()
        ConfiguracionJustificacion.get_singleton()
        sol = _make_justificacion(
            estado=Solicitud.EstadoSolicitud.PENDIENTE,
            fecha_creacion=timezone.now() - datetime.timedelta(days=30),
        )
        self._login_inspector(client)

        resp = client.get(_url(sol.pk))
        assert resp.status_code == 200
        # Pendiente vieja -> 'Vencido' debe aparecer en el header.
        assert b"Vencido" in resp.content
        assert resp.context["solicitud"].urgencia == "vencido"

    @pytest.mark.parametrize(
        "estado",
        [
            Solicitud.EstadoSolicitud.APROBADA,
            Solicitud.EstadoSolicitud.RECHAZADA,
        ],
    )
    def test_detalle_resuelta_no_muestra_badge_urgencia(self, client, estado):
        ConfiguracionJustificacion.objects.filter(pk=1).delete()
        ConfiguracionJustificacion.get_singleton()
        sol = _make_justificacion(
            estado=estado,
            fecha_creacion=timezone.now() - datetime.timedelta(days=30),
        )
        self._login_inspector(client)

        resp = client.get(_url(sol.pk))
        assert resp.status_code == 200
        body = resp.content
        # Ninguna de las 3 etiquetas del partial _urgency_badge.html.
        assert b"Vencido" not in body
        assert b"Por vencer" not in body
        assert b"Al d\xc3\xada" not in body
        assert resp.context["solicitud"].urgencia is None
