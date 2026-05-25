"""Tests for InspectorResolucionAppService (HU21 T3).

Thin wrapper over SolicitudAppService.resolver_solicitud that adds:
  * idempotent skip on already-resolved solicitudes,
  * comentario validation for rechazar (singular and bulk),
  * BulkResultadoDTO with procesadas / omitidas / omitidas_ids,
  * per-row transaction.atomic so a single failure does not abort the batch,
  * all-or-nothing comentario validation (no writes if invalid).
"""

import pytest

from apps.asistencia.infrastructure.models import Asistencia
from apps.solicitudes.application.dtos import BulkResultadoDTO
from apps.solicitudes.application.services import (
    InspectorResolucionAppService,
)
from apps.solicitudes.infrastructure.models import HistorialSolicitud, Solicitud
from tests.factories import (
    AsistenciaFactory,
    EstudianteFactory,
    InspectorFactory,
    SolicitudFactory,
)


# -------------------------------------------------------------------- #
# Helpers
# -------------------------------------------------------------------- #


def _make_justificacion_pendiente():
    """Build a PENDIENTE justification with linked AUSENTE asistencia."""
    estudiante = EstudianteFactory()
    asistencia = AsistenciaFactory(estudiante=estudiante)
    solicitud = SolicitudFactory(
        tipo=Solicitud.TipoSolicitud.JUSTIFICACION,
        estudiante=estudiante,
        asistencia=asistencia,
        estado=Solicitud.EstadoSolicitud.PENDIENTE,
        descripcion="Necesito justificar.",
    )
    return solicitud, asistencia, estudiante


# -------------------------------------------------------------------- #
# Singular: aprobar_justificacion
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestAprobarJustificacion:
    def test_aprobar_pendiente_transiciona_a_aprobada(self):
        solicitud, asistencia, _ = _make_justificacion_pendiente()
        inspector = InspectorFactory()

        service = InspectorResolucionAppService()
        resultado = service.aprobar_justificacion(solicitud, inspector, comentario="OK")

        solicitud.refresh_from_db()
        asistencia.refresh_from_db()

        assert solicitud.estado == Solicitud.EstadoSolicitud.APROBADA
        assert asistencia.estado == Asistencia.Estado.JUSTIFICADO
        # Wrapper returns the (refreshed) solicitud
        assert resultado is not None
        assert getattr(resultado, "pk", None) == solicitud.pk

    def test_aprobar_crea_historial_y_resuelto_por(self):
        solicitud, _, _ = _make_justificacion_pendiente()
        inspector = InspectorFactory()
        historial_pre = HistorialSolicitud.objects.count()

        InspectorResolucionAppService().aprobar_justificacion(solicitud, inspector, comentario="")

        assert HistorialSolicitud.objects.count() == historial_pre + 1
        solicitud.refresh_from_db()
        assert solicitud.resuelto_por_id == inspector.pk

    def test_aprobar_idempotente_sobre_ya_aprobada(self):
        """Already APROBADA → no new history, no double notification."""
        solicitud, _, _ = _make_justificacion_pendiente()
        inspector = InspectorFactory()
        # Resolve first.
        service = InspectorResolucionAppService()
        service.aprobar_justificacion(solicitud, inspector, comentario="OK")
        solicitud.refresh_from_db()
        historial_after_first = HistorialSolicitud.objects.count()

        # Second call must be a no-op.
        service.aprobar_justificacion(solicitud, inspector, comentario="OK")

        assert HistorialSolicitud.objects.count() == historial_after_first
        solicitud.refresh_from_db()
        assert solicitud.estado == Solicitud.EstadoSolicitud.APROBADA


# -------------------------------------------------------------------- #
# Singular: rechazar_justificacion
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestRechazarJustificacion:
    def test_rechazar_happy_path(self):
        solicitud, asistencia, _ = _make_justificacion_pendiente()
        inspector = InspectorFactory()

        InspectorResolucionAppService().rechazar_justificacion(
            solicitud, inspector, comentario="Documentos incompletos"
        )

        solicitud.refresh_from_db()
        asistencia.refresh_from_db()

        assert solicitud.estado == Solicitud.EstadoSolicitud.RECHAZADA
        assert "Documentos incompletos" in solicitud.respuesta
        # Asistencia stays AUSENTE on rechazo
        assert asistencia.estado == Asistencia.Estado.AUSENTE

    def test_rechazar_comentario_vacio_levanta_value_error(self):
        solicitud, _, _ = _make_justificacion_pendiente()
        inspector = InspectorFactory()
        historial_pre = HistorialSolicitud.objects.count()

        with pytest.raises(ValueError):
            InspectorResolucionAppService().rechazar_justificacion(
                solicitud, inspector, comentario=""
            )

        # No state change, no history row.
        solicitud.refresh_from_db()
        assert solicitud.estado == Solicitud.EstadoSolicitud.PENDIENTE
        assert HistorialSolicitud.objects.count() == historial_pre

    def test_rechazar_comentario_solo_espacios_levanta_value_error(self):
        solicitud, _, _ = _make_justificacion_pendiente()
        inspector = InspectorFactory()
        historial_pre = HistorialSolicitud.objects.count()

        with pytest.raises(ValueError):
            InspectorResolucionAppService().rechazar_justificacion(
                solicitud, inspector, comentario="   "
            )

        solicitud.refresh_from_db()
        assert solicitud.estado == Solicitud.EstadoSolicitud.PENDIENTE
        assert HistorialSolicitud.objects.count() == historial_pre

    def test_rechazar_idempotente_sobre_ya_resuelta(self):
        solicitud, _, _ = _make_justificacion_pendiente()
        inspector = InspectorFactory()
        service = InspectorResolucionAppService()
        service.aprobar_justificacion(solicitud, inspector, comentario="OK")
        solicitud.refresh_from_db()
        historial_after_aprobar = HistorialSolicitud.objects.count()

        # Now try to reject an already-APROBADA one.
        service.rechazar_justificacion(solicitud, inspector, comentario="cambio")

        solicitud.refresh_from_db()
        assert solicitud.estado == Solicitud.EstadoSolicitud.APROBADA
        assert HistorialSolicitud.objects.count() == historial_after_aprobar


# -------------------------------------------------------------------- #
# Bulk
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestProcesarBulkResolucion:
    def test_bulk_aprobar_happy_path(self):
        inspector = InspectorFactory()
        solicitudes = [
            _make_justificacion_pendiente()[0],
            _make_justificacion_pendiente()[0],
            _make_justificacion_pendiente()[0],
        ]
        ids = [s.pk for s in solicitudes]
        historial_pre = HistorialSolicitud.objects.count()

        resultado = InspectorResolucionAppService().procesar_bulk_resolucion(
            ids=ids, inspector=inspector, accion="aprobar", comentario=""
        )

        assert isinstance(resultado, BulkResultadoDTO)
        assert resultado.procesadas == 3
        assert resultado.omitidas == 0
        assert resultado.omitidas_ids == []
        for s in solicitudes:
            s.refresh_from_db()
            assert s.estado == Solicitud.EstadoSolicitud.APROBADA
        assert HistorialSolicitud.objects.count() == historial_pre + 3

    def test_bulk_rechazar_con_comentario_happy_path(self):
        inspector = InspectorFactory()
        solicitudes = [
            _make_justificacion_pendiente()[0],
            _make_justificacion_pendiente()[0],
        ]
        ids = [s.pk for s in solicitudes]

        resultado = InspectorResolucionAppService().procesar_bulk_resolucion(
            ids=ids,
            inspector=inspector,
            accion="rechazar",
            comentario="Lote rechazado",
        )

        assert resultado.procesadas == 2
        assert resultado.omitidas == 0
        for s in solicitudes:
            s.refresh_from_db()
            assert s.estado == Solicitud.EstadoSolicitud.RECHAZADA
            assert "Lote rechazado" in s.respuesta

    def test_bulk_rechazar_comentario_vacio_all_or_nothing(self):
        """Empty comentario on bulk rechazar → raises and writes ZERO rows."""
        inspector = InspectorFactory()
        solicitudes = [
            _make_justificacion_pendiente()[0],
            _make_justificacion_pendiente()[0],
            _make_justificacion_pendiente()[0],
        ]
        ids = [s.pk for s in solicitudes]
        historial_pre = HistorialSolicitud.objects.count()

        with pytest.raises(ValueError):
            InspectorResolucionAppService().procesar_bulk_resolucion(
                ids=ids, inspector=inspector, accion="rechazar", comentario=""
            )

        # ZERO state changes anywhere.
        for s in solicitudes:
            s.refresh_from_db()
            assert s.estado == Solicitud.EstadoSolicitud.PENDIENTE
        assert HistorialSolicitud.objects.count() == historial_pre

    def test_bulk_rechazar_comentario_solo_espacios_all_or_nothing(self):
        inspector = InspectorFactory()
        solicitudes = [
            _make_justificacion_pendiente()[0],
            _make_justificacion_pendiente()[0],
        ]
        ids = [s.pk for s in solicitudes]
        historial_pre = HistorialSolicitud.objects.count()

        with pytest.raises(ValueError):
            InspectorResolucionAppService().procesar_bulk_resolucion(
                ids=ids, inspector=inspector, accion="rechazar", comentario="   "
            )

        for s in solicitudes:
            s.refresh_from_db()
            assert s.estado == Solicitud.EstadoSolicitud.PENDIENTE
        assert HistorialSolicitud.objects.count() == historial_pre

    def test_bulk_aprobar_omite_ya_resueltas(self):
        """3 pendientes + 2 ya APROBADA → procesadas=3, omitidas=2."""
        inspector = InspectorFactory()
        pendientes = [
            _make_justificacion_pendiente()[0],
            _make_justificacion_pendiente()[0],
            _make_justificacion_pendiente()[0],
        ]
        # Pre-resolve 2 (use the service so flow is consistent).
        ya_resueltas = [
            _make_justificacion_pendiente()[0],
            _make_justificacion_pendiente()[0],
        ]
        service = InspectorResolucionAppService()
        for s in ya_resueltas:
            service.aprobar_justificacion(s, inspector, comentario="")
            s.refresh_from_db()
        ids = [s.pk for s in pendientes + ya_resueltas]

        resultado = service.procesar_bulk_resolucion(
            ids=ids, inspector=inspector, accion="aprobar", comentario=""
        )

        assert resultado.procesadas == 3
        assert resultado.omitidas == 2
        assert set(resultado.omitidas_ids) == {s.pk for s in ya_resueltas}
        for s in pendientes:
            s.refresh_from_db()
            assert s.estado == Solicitud.EstadoSolicitud.APROBADA

    def test_bulk_empty_ids_no_op(self):
        inspector = InspectorFactory()
        historial_pre = HistorialSolicitud.objects.count()

        resultado = InspectorResolucionAppService().procesar_bulk_resolucion(
            ids=[], inspector=inspector, accion="aprobar", comentario=""
        )

        assert isinstance(resultado, BulkResultadoDTO)
        assert resultado.procesadas == 0
        assert resultado.omitidas == 0
        assert resultado.omitidas_ids == []
        assert HistorialSolicitud.objects.count() == historial_pre

    def test_bulk_inspector_persistido_en_resuelto_por(self):
        """Service writes inspector into resuelto_por for every processed row."""
        inspector = InspectorFactory()
        solicitudes = [
            _make_justificacion_pendiente()[0],
            _make_justificacion_pendiente()[0],
        ]
        ids = [s.pk for s in solicitudes]

        InspectorResolucionAppService().procesar_bulk_resolucion(
            ids=ids, inspector=inspector, accion="aprobar", comentario=""
        )

        for s in solicitudes:
            s.refresh_from_db()
            assert s.resuelto_por_id == inspector.pk

    def test_bulk_fila_que_falla_no_aborta_el_lote(self, monkeypatch):
        """Per-row atomicity: forcing one row to fail must not abort the rest."""
        inspector = InspectorFactory()
        s_ok_1 = _make_justificacion_pendiente()[0]
        s_failing = _make_justificacion_pendiente()[0]
        s_ok_2 = _make_justificacion_pendiente()[0]
        ids = [s_ok_1.pk, s_failing.pk, s_ok_2.pk]

        from apps.solicitudes.application import services as services_module

        original = services_module.SolicitudAppService.resolver_solicitud

        def fake_resolver(*args, **kwargs):
            sid = kwargs.get("solicitud_id", args[0] if args else None)
            if sid == s_failing.pk:
                raise RuntimeError("Boom on this row")
            return original(*args, **kwargs)

        monkeypatch.setattr(
            services_module.SolicitudAppService,
            "resolver_solicitud",
            staticmethod(fake_resolver),
        )

        resultado = InspectorResolucionAppService().procesar_bulk_resolucion(
            ids=ids, inspector=inspector, accion="aprobar", comentario=""
        )

        # The two healthy rows must have been processed.
        s_ok_1.refresh_from_db()
        s_ok_2.refresh_from_db()
        s_failing.refresh_from_db()
        assert s_ok_1.estado == Solicitud.EstadoSolicitud.APROBADA
        assert s_ok_2.estado == Solicitud.EstadoSolicitud.APROBADA
        # The failing row stayed PENDIENTE and counts as omitida.
        assert s_failing.estado == Solicitud.EstadoSolicitud.PENDIENTE
        assert resultado.procesadas == 2
        assert s_failing.pk in resultado.omitidas_ids
        assert resultado.omitidas == len(resultado.omitidas_ids)
