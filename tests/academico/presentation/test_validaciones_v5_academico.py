"""
Integration tests for V5 (conflictos de horario) — Paralelo Web layer.

Cubre los 4 entry points Django de paralelos (design §4 filas 1-4):
  - ParaleloForm.clean()          — Tasks 2.2 (create + edit-mode dedup self).
  - ParaleloCreateView.post()     — Task  2.3 (REORDER: conflict ANTES de service.crear).
  - ParaleloUpdateView (edit)     — Task  2.4 (conflictos_horario en contexto, R1.3 self-conflict).
  - ParaleloHorarioUpdateView     — Task  2.5 (JSON: {ok:false, errors, conflictos}).
  - ParaleloCreateLoteView        — Task  2.6 (per-asignatura conflict → horario_warnings).

Patrón: cada test crea su propio docente / periodo / tipo_licencia / asignatura
para no depender de la fixture global y mantener aislamiento.
"""

from __future__ import annotations

import datetime
import json
from datetime import time

import pytest
from django.test import Client
from django.urls import reverse

from apps.academico.infrastructure.models import (
    Asignatura,
    AsignaturaLicencia,
    BloqueHorario,
    Paralelo,
    Periodo,
    TipoLicencia,
)
from apps.usuarios.infrastructure.models import Usuario


# ---------------------------------------------------------------------------
# Helpers locales (mirroring V1 style)
# ---------------------------------------------------------------------------


def _make_tipo_licencia(codigo: str = "C") -> TipoLicencia:
    tl, _ = TipoLicencia.objects.get_or_create(
        codigo=codigo,
        defaults={
            "nombre": f"Licencia {codigo}",
            "duracion_meses": 6,
            "num_asignaturas": 10,
            "activo": True,
        },
    )
    return tl


def _make_periodo(tl: TipoLicencia, nombre: str = "Periodo V5 Test") -> Periodo:
    return Periodo.objects.create(
        nombre=nombre,
        tipo_licencia=tl,
        fecha_inicio=datetime.date(2026, 1, 1),
        fecha_fin=datetime.date(2026, 6, 30),
        activo=True,
    )


def _make_docente(suffix: str = "v5") -> Usuario:
    return Usuario.objects.create_user(
        username=f"docente_{suffix}",
        email=f"docente_{suffix}@test.com",
        password="testpass123",
        rol="docente",
    )


def _make_inspector(suffix: str = "v5") -> Usuario:
    return Usuario.objects.create_user(
        username=f"inspector_{suffix}",
        email=f"inspector_{suffix}@test.com",
        password="testpass123",
        rol="inspector",
        cedula=f"09{suffix[-7:].rjust(7, '0')[:7]}",
    )


def _make_asignatura(codigo: str, tl: TipoLicencia) -> Asignatura:
    a = Asignatura.objects.create(nombre=f"Asig {codigo}", codigo=codigo, descripcion="")
    AsignaturaLicencia.objects.create(asignatura=a, tipo_licencia=tl, horas_lectivas=20)
    return a


def _seed_paralelo_con_bloque(
    *,
    docente: Usuario,
    periodo: Periodo,
    tipo_licencia: TipoLicencia,
    asignatura: Asignatura,
    nombre: str,
    dia: str,
    hora_inicio: time,
    hora_fin: time,
) -> Paralelo:
    """Crea un Paralelo + un BloqueHorario asociado."""
    p = Paralelo.objects.create(
        asignatura=asignatura,
        periodo=periodo,
        tipo_licencia=tipo_licencia,
        docente=docente,
        nombre=nombre,
        capacidad_maxima=30,
    )
    BloqueHorario.objects.create(
        paralelo=p,
        dia_semana=dia,
        hora_inicio=hora_inicio,
        hora_fin=hora_fin,
    )
    return p


# ---------------------------------------------------------------------------
# Task 2.3 — ParaleloCreateView: conflict ANTES de service.crear (REORDER)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestParaleloCreateViewConflictoDocente:
    """Locked decision 3: detectar_conflicto_docente corre ANTES de service.crear."""

    def test_post_con_conflicto_docente_no_crea_paralelo_y_renderiza_contexto(self):
        """R1.1: docente con bloque 08-10 lunes; POST quiere 09-11 lunes → rechazado.

        Asserts:
          - status_code == 200 (re-render, no redirect)
          - Paralelo NUEVO no fue creado (no rollback necesario)
          - context['conflictos_horario'] tiene 1 conflicto con datos del existente
          - form tiene non-field error con mensaje del docente
        """
        tl = _make_tipo_licencia("C")
        periodo = _make_periodo(tl)
        docente = _make_docente("create_conf")
        inspector = _make_inspector("create_conf")
        asig_existente = _make_asignatura("V5C-EX1", tl)
        asig_nueva = _make_asignatura("V5C-NEW", tl)

        # Estado previo: docente ya dicta lunes 08-10
        _seed_paralelo_con_bloque(
            docente=docente,
            periodo=periodo,
            tipo_licencia=tl,
            asignatura=asig_existente,
            nombre="A",
            dia="lunes",
            hora_inicio=time(8, 0),
            hora_fin=time(10, 0),
        )

        client = Client()
        client.force_login(inspector)

        post_data = {
            "periodo": periodo.pk,
            "tipo_licencia": tl.pk,
            "asignatura": asig_nueva.pk,
            "nombre": "B",
            "docente": docente.pk,
            "capacidad_maxima": 30,
            "bloques_count": "1",
            "bloque_dia_0": "lunes",
            "bloque_inicio_0": "09:00",
            "bloque_fin_0": "11:00",
        }
        response = client.post(reverse("academico:paralelo_create"), data=post_data)

        assert response.status_code == 200
        # El paralelo nuevo (asig_nueva) NO debe existir (chequeo antes de service.crear)
        assert not Paralelo.objects.filter(asignatura=asig_nueva).exists()

        ctx_conflictos = response.context.get("conflictos_horario")
        assert ctx_conflictos is not None
        assert len(ctx_conflictos) == 1
        c = ctx_conflictos[0]
        assert c.asignatura_codigo == "V5C-EX1"
        assert c.dia_semana == "lunes"
        assert c.hora_inicio == time(8, 0)

        # Mensaje de form (non-field)
        form = response.context["form"]
        assert form.errors
        all_errors = str(form.errors)
        assert "docente" in all_errors.lower() and "conflicto" in all_errors.lower()

    def test_post_back_to_back_es_aceptado(self):
        """R1.2: bloque 08-10 vs 10-12 mismo día NO es conflicto (half-open)."""
        tl = _make_tipo_licencia("C")
        periodo = _make_periodo(tl)
        docente = _make_docente("create_b2b")
        inspector = _make_inspector("create_b2b")
        asig_existente = _make_asignatura("V5C-B1", tl)
        asig_nueva = _make_asignatura("V5C-B2", tl)

        _seed_paralelo_con_bloque(
            docente=docente,
            periodo=periodo,
            tipo_licencia=tl,
            asignatura=asig_existente,
            nombre="A",
            dia="lunes",
            hora_inicio=time(8, 0),
            hora_fin=time(10, 0),
        )

        client = Client()
        client.force_login(inspector)
        post_data = {
            "periodo": periodo.pk,
            "tipo_licencia": tl.pk,
            "asignatura": asig_nueva.pk,
            "nombre": "B",
            "docente": docente.pk,
            "capacidad_maxima": 30,
            "bloques_count": "1",
            "bloque_dia_0": "lunes",
            "bloque_inicio_0": "10:00",
            "bloque_fin_0": "12:00",
        }
        response = client.post(reverse("academico:paralelo_create"), data=post_data)

        # Redirect a paralelo_list = éxito
        assert response.status_code == 302
        assert Paralelo.objects.filter(asignatura=asig_nueva).exists()


# ---------------------------------------------------------------------------
# Task 2.4 — ParaleloUpdateView (asignatura edit): conflicto + self-exclude
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestParaleloUpdateViewConflictoDocente:
    """ParaleloUpdateView (alias ParaleloAsignaturaEditView en design §4)."""

    def test_edit_que_genera_conflicto_con_otro_paralelo_es_rechazado(self):
        """Docente dicta P_OTRO lun 08-10 y P_TARGET vie 10-12; editar P_TARGET
        a lun 09-11 debe disparar conflicto con P_OTRO."""
        tl = _make_tipo_licencia("C")
        periodo = _make_periodo(tl)
        docente = _make_docente("edit_conf")
        inspector = _make_inspector("edit_conf")
        asig_otro = _make_asignatura("V5E-OTH", tl)
        asig_target = _make_asignatura("V5E-TGT", tl)

        _seed_paralelo_con_bloque(
            docente=docente,
            periodo=periodo,
            tipo_licencia=tl,
            asignatura=asig_otro,
            nombre="A",
            dia="lunes",
            hora_inicio=time(8, 0),
            hora_fin=time(10, 0),
        )
        target = _seed_paralelo_con_bloque(
            docente=docente,
            periodo=periodo,
            tipo_licencia=tl,
            asignatura=asig_target,
            nombre="B",
            dia="viernes",
            hora_inicio=time(10, 0),
            hora_fin=time(12, 0),
        )

        client = Client()
        client.force_login(inspector)
        post_data = {
            "docente": docente.pk,
            "bloque_dia_0": "lunes",
            "bloque_inicio_0": "09:00",
            "bloque_fin_0": "11:00",
        }
        response = client.post(
            reverse("academico:paralelo_update", kwargs={"pk": target.pk}),
            data=post_data,
        )

        assert response.status_code == 200
        ctx_conf = response.context.get("conflictos_horario")
        assert ctx_conf is not None
        assert len(ctx_conf) == 1
        assert ctx_conf[0].asignatura_codigo == "V5E-OTH"
        # El bloque original del target sigue intacto (no se borró)
        assert target.bloques_horario.filter(dia_semana="viernes").exists()

    def test_edit_self_conflict_es_permitido_R1_3(self):
        """R1.3: editar el mismo paralelo manteniendo / cambiando su propio
        horario NO debe disparar conflicto contra sí mismo."""
        tl = _make_tipo_licencia("C")
        periodo = _make_periodo(tl)
        docente = _make_docente("edit_self")
        inspector = _make_inspector("edit_self")
        asig = _make_asignatura("V5E-SELF", tl)

        target = _seed_paralelo_con_bloque(
            docente=docente,
            periodo=periodo,
            tipo_licencia=tl,
            asignatura=asig,
            nombre="A",
            dia="lunes",
            hora_inicio=time(8, 0),
            hora_fin=time(10, 0),
        )

        client = Client()
        client.force_login(inspector)
        post_data = {
            "docente": docente.pk,
            "bloque_dia_0": "lunes",
            "bloque_inicio_0": "09:00",
            "bloque_fin_0": "11:00",
        }
        response = client.post(
            reverse("academico:paralelo_update", kwargs={"pk": target.pk}),
            data=post_data,
        )

        # Redirect = éxito; conflictos_horario NO debe estar en contexto
        assert response.status_code == 302
        # Reemplazó bloques: ahora 09-11 lunes
        target.refresh_from_db()
        bloques = list(target.bloques_horario.all())
        assert len(bloques) == 1
        assert bloques[0].hora_inicio == time(9, 0)
        assert bloques[0].hora_fin == time(11, 0)


# ---------------------------------------------------------------------------
# Task 2.5 — ParaleloHorarioUpdateView (JSON): contrato {ok, errors, conflictos}
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestParaleloHorarioUpdateViewConflictoDocenteJSON:
    """JSON-only endpoint. Design §5.3 fija el shape exacto."""

    def test_json_post_con_conflicto_docente_retorna_payload_estructurado(self):
        tl = _make_tipo_licencia("C")
        periodo = _make_periodo(tl)
        docente = _make_docente("json_conf")
        inspector = _make_inspector("json_conf")
        asig_otro = _make_asignatura("V5J-OTH", tl)
        asig_target = _make_asignatura("V5J-TGT", tl)

        _seed_paralelo_con_bloque(
            docente=docente,
            periodo=periodo,
            tipo_licencia=tl,
            asignatura=asig_otro,
            nombre="A",
            dia="lunes",
            hora_inicio=time(8, 0),
            hora_fin=time(10, 0),
        )
        target = _seed_paralelo_con_bloque(
            docente=docente,
            periodo=periodo,
            tipo_licencia=tl,
            asignatura=asig_target,
            nombre="B",
            dia="viernes",
            hora_inicio=time(14, 0),
            hora_fin=time(16, 0),
        )

        client = Client()
        client.force_login(inspector)
        payload = {
            "bloques": [
                {"dia": "lunes", "inicio": "09:00", "fin": "11:00"},
            ]
        }
        response = client.post(
            reverse("academico:paralelo_horario_update", kwargs={"pk": target.pk}),
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 400
        body = response.json()
        assert body["ok"] is False
        assert isinstance(body["errors"], list) and len(body["errors"]) >= 1
        assert "conflictos" in body
        assert isinstance(body["conflictos"], list) and len(body["conflictos"]) == 1
        c = body["conflictos"][0]
        # `time` debe venir como isoformat string
        assert c["asignatura_codigo"] == "V5J-OTH"
        assert c["dia_semana"] == "lunes"
        assert c["hora_inicio"] == "08:00:00"
        assert c["hora_fin"] == "10:00:00"
        assert c["dia_semana_label"] == "Lunes"


# ---------------------------------------------------------------------------
# Task 2.6 — ParaleloCreateLoteView: conflicto por asignatura → warning,
# el lote sigue (no aborta)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestParaleloCreateLoteViewConflictoDocente:
    def test_lote_con_una_asignatura_en_conflicto_skip_bloque_pero_no_aborta(self):
        """2 asignaturas en el lote; el docente ya tiene lunes 08-10.
        Asignatura A pide lunes 09-11 (conflicto → bloque skip + warning).
        Asignatura B pide viernes 10-12 (ok → bloque creado).
        Ambos paralelos se crean; solo el bloque conflictivo se omite.
        """
        tl = _make_tipo_licencia("C")
        periodo = _make_periodo(tl)
        docente = _make_docente("lote_conf")
        inspector = _make_inspector("lote_conf")

        asig_pre = _make_asignatura("V5L-PRE", tl)
        asig_a = _make_asignatura("V5L-A", tl)
        asig_b = _make_asignatura("V5L-B", tl)

        # Pre-existente: docente ocupado lunes 08-10
        _seed_paralelo_con_bloque(
            docente=docente,
            periodo=periodo,
            tipo_licencia=tl,
            asignatura=asig_pre,
            nombre="PRE",
            dia="lunes",
            hora_inicio=time(8, 0),
            hora_fin=time(10, 0),
        )

        client = Client()
        client.force_login(inspector)
        post_data = {
            "periodo": periodo.pk,
            "tipo_licencia": tl.pk,
            "asignaturas": [asig_a.pk, asig_b.pk],
            "nombre": "L1",
            "docente": docente.pk,
            "capacidad_maxima": 30,
            # Bloque para A: CONFLICTO
            f"horario_{asig_a.pk}_count": "1",
            f"horario_{asig_a.pk}_dia_0": "lunes",
            f"horario_{asig_a.pk}_inicio_0": "09:00",
            f"horario_{asig_a.pk}_fin_0": "11:00",
            # Bloque para B: OK
            f"horario_{asig_b.pk}_count": "1",
            f"horario_{asig_b.pk}_dia_0": "viernes",
            f"horario_{asig_b.pk}_inicio_0": "10:00",
            f"horario_{asig_b.pk}_fin_0": "12:00",
        }
        response = client.post(
            reverse("academico:paralelo_create_lote"), data=post_data, follow=True
        )

        assert response.status_code == 200

        # Ambos paralelos creados
        p_a = Paralelo.objects.filter(asignatura=asig_a, nombre="L1").first()
        p_b = Paralelo.objects.filter(asignatura=asig_b, nombre="L1").first()
        assert p_a is not None
        assert p_b is not None

        # Bloque de A NO debe existir (conflicto skip)
        assert p_a.bloques_horario.count() == 0
        # Bloque de B sí
        assert p_b.bloques_horario.count() == 1

        # Algún message warning sobre el conflicto
        messages_text = " ".join(str(m) for m in response.context["messages"])
        assert "conflicto" in messages_text.lower() or "Conflicto" in messages_text


# ---------------------------------------------------------------------------
# Task 3.8 — Smoke tests: full request cycle renders partial markup
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSmokePartialRenderParalelo:
    """Smoke tests del ciclo completo de request en los 4 entry points web de
    Paralelo + 1 JSON (ParaleloHorarioUpdateView). Verifican que el partial
    `conflicto_horario_error.html` se renderiza con sus strings clave."""

    def _seed_setup(self, suffix: str):
        tl = _make_tipo_licencia("C")
        periodo = _make_periodo(tl)
        docente = _make_docente(suffix)
        inspector = _make_inspector(suffix)
        return tl, periodo, docente, inspector

    def test_smoke_paralelo_create_render_partial(self):
        """ParaleloCreateView: POST con conflicto debe renderizar partial."""
        tl, periodo, docente, inspector = self._seed_setup("smk_create")
        asig_pre = _make_asignatura("SMKC-PRE", tl)
        asig_new = _make_asignatura("SMKC-NEW", tl)

        _seed_paralelo_con_bloque(
            docente=docente,
            periodo=periodo,
            tipo_licencia=tl,
            asignatura=asig_pre,
            nombre="A",
            dia="lunes",
            hora_inicio=time(8, 0),
            hora_fin=time(10, 0),
        )

        client = Client()
        client.force_login(inspector)
        response = client.post(
            reverse("academico:paralelo_create"),
            data={
                "periodo": periodo.pk,
                "tipo_licencia": tl.pk,
                "asignatura": asig_new.pk,
                "nombre": "B",
                "docente": docente.pk,
                "capacidad_maxima": 30,
                "bloques_count": "1",
                "bloque_dia_0": "lunes",
                "bloque_inicio_0": "09:00",
                "bloque_fin_0": "11:00",
            },
        )

        assert response.status_code == 200
        from django.test.utils import setup_test_environment  # noqa: F401

        content = response.content.decode("utf-8")
        assert 'role="alert"' in content
        assert "aria-live" in content
        assert "Conflicto de horario detectado" in content
        assert "SMKC-PRE" in content
        assert "Lunes" in content
        assert "08:00" in content
        assert "10:00" in content

    def test_smoke_paralelo_update_render_partial(self):
        """ParaleloUpdateView (asignatura edit): POST conflicto renderiza partial."""
        tl, periodo, docente, inspector = self._seed_setup("smk_update")
        asig_otro = _make_asignatura("SMKU-OTH", tl)
        asig_target = _make_asignatura("SMKU-TGT", tl)

        _seed_paralelo_con_bloque(
            docente=docente,
            periodo=periodo,
            tipo_licencia=tl,
            asignatura=asig_otro,
            nombre="A",
            dia="lunes",
            hora_inicio=time(8, 0),
            hora_fin=time(10, 0),
        )
        target = _seed_paralelo_con_bloque(
            docente=docente,
            periodo=periodo,
            tipo_licencia=tl,
            asignatura=asig_target,
            nombre="B",
            dia="viernes",
            hora_inicio=time(14, 0),
            hora_fin=time(16, 0),
        )

        client = Client()
        client.force_login(inspector)
        response = client.post(
            reverse("academico:paralelo_update", kwargs={"pk": target.pk}),
            data={
                "docente": docente.pk,
                "bloque_dia_0": "lunes",
                "bloque_inicio_0": "09:00",
                "bloque_fin_0": "11:00",
            },
        )

        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert 'role="alert"' in content
        assert "Conflicto de horario detectado" in content
        assert "SMKU-OTH" in content
        assert "Lunes" in content

    def test_smoke_paralelo_horario_update_json_shape(self):
        """ParaleloHorarioUpdateView: contrato JSON estructurado (sin partial)."""
        tl, periodo, docente, inspector = self._seed_setup("smk_json")
        asig_otro = _make_asignatura("SMKJ-OTH", tl)
        asig_target = _make_asignatura("SMKJ-TGT", tl)

        _seed_paralelo_con_bloque(
            docente=docente,
            periodo=periodo,
            tipo_licencia=tl,
            asignatura=asig_otro,
            nombre="A",
            dia="lunes",
            hora_inicio=time(8, 0),
            hora_fin=time(10, 0),
        )
        target = _seed_paralelo_con_bloque(
            docente=docente,
            periodo=periodo,
            tipo_licencia=tl,
            asignatura=asig_target,
            nombre="B",
            dia="viernes",
            hora_inicio=time(14, 0),
            hora_fin=time(16, 0),
        )

        client = Client()
        client.force_login(inspector)
        response = client.post(
            reverse("academico:paralelo_horario_update", kwargs={"pk": target.pk}),
            data=json.dumps({"bloques": [{"dia": "lunes", "inicio": "09:00", "fin": "11:00"}]}),
            content_type="application/json",
        )

        assert response.status_code == 400
        body = response.json()
        assert body["ok"] is False
        assert isinstance(body.get("conflictos"), list) and len(body["conflictos"]) == 1
        c = body["conflictos"][0]
        assert c["asignatura_codigo"] == "SMKJ-OTH"
        assert c["dia_semana"] == "lunes"
        assert c["hora_inicio"] == "08:00:00"

    def test_smoke_paralelo_create_lote_warning_message(self):
        """ParaleloCreateLoteView: collect-all → redirect con warning message
        (no renderiza partial porque redirige; cubre el wire defensivo del
        template para casos futuros)."""
        tl, periodo, docente, inspector = self._seed_setup("smk_lote")
        asig_pre = _make_asignatura("SMKL-PRE", tl)
        asig_a = _make_asignatura("SMKL-A", tl)

        _seed_paralelo_con_bloque(
            docente=docente,
            periodo=periodo,
            tipo_licencia=tl,
            asignatura=asig_pre,
            nombre="PRE",
            dia="lunes",
            hora_inicio=time(8, 0),
            hora_fin=time(10, 0),
        )

        client = Client()
        client.force_login(inspector)
        response = client.post(
            reverse("academico:paralelo_create_lote"),
            data={
                "periodo": periodo.pk,
                "tipo_licencia": tl.pk,
                "asignaturas": [asig_a.pk],
                "nombre": "L1",
                "docente": docente.pk,
                "capacidad_maxima": 30,
                f"horario_{asig_a.pk}_count": "1",
                f"horario_{asig_a.pk}_dia_0": "lunes",
                f"horario_{asig_a.pk}_inicio_0": "09:00",
                f"horario_{asig_a.pk}_fin_0": "11:00",
            },
            follow=True,
        )

        assert response.status_code == 200
        messages_text = " ".join(str(m) for m in response.context["messages"])
        assert "conflicto" in messages_text.lower()
