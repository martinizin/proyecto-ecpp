"""Tests for domain helpers `dias_habiles_transcurridos` and
`clasificar_urgencia` in `apps.solicitudes.domain.services`.

Pure-Python helpers — no Django, no DB. These tests anchor the semantics
agreed in the HU21 spec (`solicitudes-domain-helpers` capability):

* `dias_habiles_transcurridos(fecha_inicio, fecha_referencia)`:
  counts weekdays (Mon-Fri) AFTER `fecha_inicio` UP TO AND INCLUDING
  `fecha_referencia`. Saturday/Sunday never count. Same date -> 0.
  Future fecha_inicio -> 0.

* `clasificar_urgencia(fecha_creacion, deadline_dias, alerta_dias, today=None)`:
  computes `elapsed = dias_habiles_transcurridos(fecha_creacion, today)` and
  `remaining = deadline_dias - elapsed`. Returns:
    - "vencido" when remaining <= 0
    - "alerta"  when 0 < remaining <= alerta_dias
    - "normal"  otherwise
  Raises ValueError when alerta_dias >= deadline_dias.
"""

from __future__ import annotations

import ast
import importlib
import inspect
from datetime import date

import pytest

from apps.solicitudes.domain import services as urgencia_module
from apps.solicitudes.domain.services import (
    clasificar_urgencia,
    dias_habiles_transcurridos,
)


# ---------------------------------------------------------------------------
# dias_habiles_transcurridos
# ---------------------------------------------------------------------------
class TestDiasHabilesTranscurridos:
    def test_same_day_returns_zero(self):
        d = date(2026, 5, 25)  # Monday
        assert dias_habiles_transcurridos(d, d) == 0

    def test_monday_to_friday_same_week_returns_four(self):
        # Spec scenario: Monday -> Friday same week -> 4 (Tue, Wed, Thu, Fri)
        monday = date(2026, 5, 25)
        friday = date(2026, 5, 29)
        assert dias_habiles_transcurridos(monday, friday) == 4

    def test_one_weekday_forward_returns_one(self):
        # Monday -> Tuesday -> 1
        assert dias_habiles_transcurridos(date(2026, 5, 25), date(2026, 5, 26)) == 1

    def test_friday_to_monday_skips_weekend_returns_one(self):
        # Spec scenario: Friday -> next Monday -> 1
        friday = date(2026, 5, 29)
        next_monday = date(2026, 6, 1)
        assert dias_habiles_transcurridos(friday, next_monday) == 1

    def test_saturday_to_tuesday_returns_two(self):
        # Sat (fecha_inicio) does not count; Mon + Tue = 2
        saturday = date(2026, 5, 30)
        tuesday = date(2026, 6, 2)
        assert dias_habiles_transcurridos(saturday, tuesday) == 2

    def test_ten_calendar_days_two_weekends_returns_six(self):
        # Mon 2026-05-25 -> Thu 2026-06-04 = 10 calendar days.
        # Weekdays after start through end: Tue 26, Wed 27, Thu 28, Fri 29,
        # (Sat 30, Sun 31 excluded), Mon Jun 1, Tue 2, Wed 3, Thu 4 -> wait
        # that's 8 weekdays. Let's pick a clearer scenario.
        # Use Mon May 25 -> Mon Jun 8 (14 calendar days, 2 full weekends):
        # Tue 26, Wed 27, Thu 28, Fri 29, Mon Jun 1, Tue 2, Wed 3, Thu 4,
        # Fri 5, Mon 8 = 10 weekdays. So span 10 calendar days =>
        # Mon May 25 -> Thu Jun 4: Tue 26, Wed 27, Thu 28, Fri 29, Mon Jun 1,
        # Tue 2, Wed 3, Thu 4 = 8. Adjust the assertion accordingly.
        start = date(2026, 5, 25)  # Monday
        end = date(2026, 6, 4)  # Thursday (10 calendar days later)
        assert dias_habiles_transcurridos(start, end) == 8

    def test_future_fecha_inicio_returns_zero(self):
        # fecha_referencia is BEFORE fecha_inicio -> 0
        assert dias_habiles_transcurridos(date(2026, 6, 1), date(2026, 5, 25)) == 0


# ---------------------------------------------------------------------------
# clasificar_urgencia
# ---------------------------------------------------------------------------
class TestClasificarUrgencia:
    DEADLINE = 5
    ALERTA = 2

    def test_zero_elapsed_returns_normal(self):
        # elapsed=0, remaining=5, > alerta=2 -> normal
        d = date(2026, 5, 25)
        assert clasificar_urgencia(d, self.DEADLINE, self.ALERTA, today=d) == "normal"

    def test_one_elapsed_returns_normal(self):
        # Mon -> Tue, elapsed=1, remaining=4 -> normal
        result = clasificar_urgencia(
            date(2026, 5, 25), self.DEADLINE, self.ALERTA, today=date(2026, 5, 26)
        )
        assert result == "normal"

    def test_two_elapsed_returns_normal(self):
        # elapsed=2, remaining=3, > alerta=2 -> normal (boundary just above alerta)
        result = clasificar_urgencia(
            date(2026, 5, 25), self.DEADLINE, self.ALERTA, today=date(2026, 5, 27)
        )
        assert result == "normal"

    def test_three_elapsed_returns_alerta_boundary(self):
        # Spec scenario: 3 business days elapsed, remaining=2, == alerta -> "alerta"
        result = clasificar_urgencia(
            date(2026, 5, 25), self.DEADLINE, self.ALERTA, today=date(2026, 5, 28)
        )
        assert result == "alerta"

    def test_four_elapsed_returns_alerta(self):
        # elapsed=4 (Mon->Fri), remaining=1 (<= alerta) -> alerta
        result = clasificar_urgencia(
            date(2026, 5, 25), self.DEADLINE, self.ALERTA, today=date(2026, 5, 29)
        )
        assert result == "alerta"

    def test_five_elapsed_returns_vencido_boundary(self):
        # elapsed=5 (Mon->next Mon = 5 weekdays: Tue,Wed,Thu,Fri,Mon),
        # remaining=0 -> "vencido" (boundary inclusive on vencido per spec:
        # remaining <= 0)
        result = clasificar_urgencia(
            date(2026, 5, 25), self.DEADLINE, self.ALERTA, today=date(2026, 6, 1)
        )
        assert result == "vencido"

    def test_seven_elapsed_returns_vencido(self):
        # elapsed=7 (Mon -> Wed +9 cal days), remaining=-2 -> vencido
        result = clasificar_urgencia(
            date(2026, 5, 25), self.DEADLINE, self.ALERTA, today=date(2026, 6, 3)
        )
        assert result == "vencido"

    def test_today_defaults_to_date_today(self):
        # When today=None, helper should call date.today(). We can't easily
        # mock builtins.date here without freezegun, but we verify by passing
        # fecha_creacion == today (None defaults) -> elapsed=0 -> normal.
        today = date.today()
        assert clasificar_urgencia(today, self.DEADLINE, self.ALERTA, today=None) == "normal"

    def test_alerta_dias_equals_deadline_raises_value_error(self):
        with pytest.raises(ValueError):
            clasificar_urgencia(
                date(2026, 5, 25), deadline_dias=5, alerta_dias=5, today=date(2026, 5, 25)
            )

    def test_alerta_dias_greater_than_deadline_raises_value_error(self):
        with pytest.raises(ValueError):
            clasificar_urgencia(
                date(2026, 5, 25), deadline_dias=3, alerta_dias=5, today=date(2026, 5, 25)
            )


# ---------------------------------------------------------------------------
# Pure-Python import audit — helpers must not import Django
# ---------------------------------------------------------------------------
class TestImportAudit:
    def test_services_module_does_not_import_django(self):
        """Static AST audit: no `import django...` or `from django...` in
        the domain services module."""
        source_file = inspect.getsourcefile(urgencia_module)
        assert source_file is not None
        with open(source_file, "r", encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), filename=source_file)

        offenders: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "django" or alias.name.startswith("django."):
                        offenders.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module and (node.module == "django" or node.module.startswith("django.")):
                    offenders.append(node.module)
        assert offenders == [], f"domain/services.py imports Django: {offenders}"

    def test_reimporting_module_does_not_pull_django(self):
        """Runtime check: re-importing the module does not register any
        `django.*` symbol via this module's globals."""
        mod = importlib.reload(urgencia_module)
        django_refs = [
            name
            for name, value in vars(mod).items()
            if getattr(value, "__module__", "").startswith("django")
        ]
        assert django_refs == [], f"domain/services.py exposes django symbols: {django_refs}"
