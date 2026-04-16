"""
Unit tests for Academico domain layer.
Pure Python — NO database required.
Tests: PeriodoService, AsignaturaService, ParaleloService.
Refs: SCN-PER-05→08, SCN-CAT-08→10
"""

from datetime import date

import pytest

from apps.academico.domain.exceptions import (
    AsignaturaCodigoDuplicadoError,
    CupoExcedidoError,
    DocenteInvalidoError,
    EstadoMatriculaInvalidoError,
    MatriculaDuplicadaError,
    ParaleloDuplicadoError,
    PeriodoActivoExistenteError,
    PeriodoInactivoError,
    PeriodoSolapadoError,
)
from apps.academico.domain.services import (
    AsignaturaService,
    MatriculaService,
    ParaleloService,
    PeriodoService,
)


# =============================================================================
# PeriodoService Tests
# =============================================================================


class TestPeriodoService:
    """Tests for academic period domain rules."""

    def setup_method(self):
        self.service = PeriodoService()

    def test_validar_fechas_correctas(self):
        """fecha_inicio < fecha_fin should pass."""
        self.service.validar_fechas(
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 7, 31),
        )

    def test_validar_fechas_iguales(self):
        """fecha_inicio == fecha_fin should raise."""
        with pytest.raises(PeriodoSolapadoError, match="anterior"):
            self.service.validar_fechas(
                fecha_inicio=date(2026, 3, 1),
                fecha_fin=date(2026, 3, 1),
            )

    def test_validar_fechas_invertidas(self):
        """fecha_inicio > fecha_fin should raise."""
        with pytest.raises(PeriodoSolapadoError, match="anterior"):
            self.service.validar_fechas(
                fecha_inicio=date(2026, 7, 31),
                fecha_fin=date(2026, 3, 1),
            )

    def test_activacion_sin_periodo_activo(self):
        """No active period → activate directly."""
        result = self.service.verificar_activacion(
            periodo_activo_actual=None,
            confirmar_desactivacion=False,
        )
        assert result is True

    def test_activacion_con_confirmacion(self):
        """Active period exists + user confirmed → proceed."""
        result = self.service.verificar_activacion(
            periodo_activo_actual="2025-B",
            confirmar_desactivacion=True,
        )
        assert result is True

    def test_activacion_sin_confirmacion_raise(self):
        """Active period exists + no confirmation → raise."""
        with pytest.raises(PeriodoActivoExistenteError, match="2025-B"):
            self.service.verificar_activacion(
                periodo_activo_actual="2025-B",
                confirmar_desactivacion=False,
            )

    def test_activacion_sin_confirmacion_mensaje_pregunta(self):
        """Error message should ask for confirmation."""
        with pytest.raises(PeriodoActivoExistenteError, match="desactivarlo"):
            self.service.verificar_activacion(
                periodo_activo_actual="2025-B",
                confirmar_desactivacion=False,
            )


# =============================================================================
# AsignaturaService Tests
# =============================================================================


class TestAsignaturaService:
    """Tests for subject domain validation."""

    def setup_method(self):
        self.service = AsignaturaService()

    def test_validar_datos_correctos(self):
        """Valid data should pass."""
        self.service.validar_datos(
            codigo="LEG-001",
            horas_lectivas=40,
            tipos_licencia_ids=[1, 2],
            codigo_exists=False,
        )

    def test_codigo_duplicado(self):
        with pytest.raises(AsignaturaCodigoDuplicadoError, match="LEG-001"):
            self.service.validar_datos(
                codigo="LEG-001",
                horas_lectivas=40,
                tipos_licencia_ids=[1],
                codigo_exists=True,
            )

    @pytest.mark.parametrize("horas", [0, -1, -100])
    def test_horas_lectivas_invalidas(self, horas):
        with pytest.raises(ValueError, match="mayores a 0"):
            self.service.validar_datos(
                codigo="LEG-001",
                horas_lectivas=horas,
                tipos_licencia_ids=[1],
                codigo_exists=False,
            )

    def test_sin_tipos_licencia(self):
        with pytest.raises(ValueError, match="al menos un tipo"):
            self.service.validar_datos(
                codigo="LEG-001",
                horas_lectivas=40,
                tipos_licencia_ids=[],
                codigo_exists=False,
            )


# =============================================================================
# ParaleloService Tests
# =============================================================================


class TestParaleloService:
    """Tests for parallel domain validation."""

    def setup_method(self):
        self.service = ParaleloService()

    def test_validar_datos_correctos(self):
        """Valid data should pass."""
        self.service.validar_datos(
            docente_rol="docente",
            periodo_activo=True,
            combinacion_exists=False,
        )

    def test_docente_rol_invalido(self):
        with pytest.raises(DocenteInvalidoError, match="docente"):
            self.service.validar_docente(docente_rol="estudiante")

    def test_docente_rol_inspector_invalido(self):
        with pytest.raises(DocenteInvalidoError, match="docente"):
            self.service.validar_docente(docente_rol="inspector")

    def test_docente_rol_valido(self):
        self.service.validar_docente(docente_rol="docente")

    def test_periodo_inactivo(self):
        with pytest.raises(PeriodoInactivoError, match="activo"):
            self.service.validar_periodo_activo(periodo_activo=False)

    def test_periodo_activo_valido(self):
        self.service.validar_periodo_activo(periodo_activo=True)

    def test_combinacion_duplicada(self):
        with pytest.raises(ParaleloDuplicadoError, match="misma combinación"):
            self.service.validar_unicidad(combinacion_exists=True)

    def test_combinacion_unica(self):
        self.service.validar_unicidad(combinacion_exists=False)

    def test_validar_datos_docente_invalido_prioridad(self):
        """validar_datos checks docente first."""
        with pytest.raises(DocenteInvalidoError):
            self.service.validar_datos(
                docente_rol="estudiante",
                periodo_activo=False,
                combinacion_exists=True,
            )

    def test_validar_datos_periodo_inactivo_prioridad(self):
        """After docente passes, periodo check is next."""
        with pytest.raises(PeriodoInactivoError):
            self.service.validar_datos(
                docente_rol="docente",
                periodo_activo=False,
                combinacion_exists=True,
            )

    def test_validar_datos_duplicado_ultimo(self):
        """Uniqueness is checked last."""
        with pytest.raises(ParaleloDuplicadoError):
            self.service.validar_datos(
                docente_rol="docente",
                periodo_activo=True,
                combinacion_exists=True,
            )


# =============================================================================
# MatriculaService Tests
# =============================================================================


class TestMatriculaService:
    """Tests for enrollment domain rules."""

    def setup_method(self):
        self.service = MatriculaService()

    # --- Cupo ---

    def test_validar_cupo_ok(self):
        self.service.validar_cupo(activas_en_paralelo=29, capacidad_maxima=30)

    def test_validar_cupo_excedido(self):
        with pytest.raises(CupoExcedidoError, match="capacidad máxima"):
            self.service.validar_cupo(activas_en_paralelo=30, capacidad_maxima=30)

    def test_validar_cupo_excedido_over(self):
        with pytest.raises(CupoExcedidoError):
            self.service.validar_cupo(activas_en_paralelo=35, capacidad_maxima=30)

    # --- Duplicada ---

    def test_validar_no_duplicada_ok(self):
        self.service.validar_no_duplicada(matricula_existente=False)

    def test_validar_no_duplicada_raises(self):
        with pytest.raises(MatriculaDuplicadaError, match="ya tiene"):
            self.service.validar_no_duplicada(matricula_existente=True)

    # --- Periodo activo ---

    def test_validar_periodo_activo_ok(self):
        self.service.validar_periodo_activo(periodo_activo=True)

    def test_validar_periodo_inactivo_raises(self):
        with pytest.raises(PeriodoInactivoError, match="período activo"):
            self.service.validar_periodo_activo(periodo_activo=False)

    # --- Transiciones de estado: secretaria ---

    def test_secretaria_activa_a_retirada(self):
        self.service.validar_transicion_estado("activa", "retirada", "secretaria")

    def test_secretaria_retirada_a_activa(self):
        self.service.validar_transicion_estado("retirada", "activa", "secretaria")

    def test_secretaria_no_puede_suspender(self):
        with pytest.raises(EstadoMatriculaInvalidoError):
            self.service.validar_transicion_estado("activa", "suspendida", "secretaria")

    def test_secretaria_no_puede_cambiar_suspendida(self):
        with pytest.raises(EstadoMatriculaInvalidoError):
            self.service.validar_transicion_estado("suspendida", "activa", "secretaria")

    # --- Transiciones de estado: inspector ---

    def test_inspector_activa_a_suspendida(self):
        self.service.validar_transicion_estado("activa", "suspendida", "inspector")

    def test_inspector_suspendida_a_activa(self):
        self.service.validar_transicion_estado("suspendida", "activa", "inspector")

    def test_inspector_no_puede_retirar(self):
        with pytest.raises(EstadoMatriculaInvalidoError):
            self.service.validar_transicion_estado("activa", "retirada", "inspector")

    def test_inspector_no_puede_cambiar_retirada(self):
        with pytest.raises(EstadoMatriculaInvalidoError):
            self.service.validar_transicion_estado("retirada", "activa", "inspector")

    # --- Mismo estado = no-op ---

    def test_mismo_estado_no_raises(self):
        self.service.validar_transicion_estado("activa", "activa", "secretaria")
        self.service.validar_transicion_estado("suspendida", "suspendida", "inspector")

    # --- Rol inválido ---

    def test_rol_invalido_raises(self):
        with pytest.raises(EstadoMatriculaInvalidoError, match="permisos"):
            self.service.validar_transicion_estado("activa", "retirada", "docente")
