"""Tests for ConfiguracionJustificacion singleton model + admin gate (HU21 T2).

Strict TDD: this file is written BEFORE the production code. It MUST fail
on first run with ImportError because `ConfiguracionJustificacion` does
not yet exist.
"""

import pytest
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory

from apps.solicitudes.admin import ConfiguracionJustificacionAdmin
from apps.solicitudes.infrastructure.models import ConfiguracionJustificacion


pytestmark = pytest.mark.django_db


class TestConfiguracionJustificacionDefaults:
    def test_get_singleton_creates_pk_1_on_empty_table(self):
        assert not ConfiguracionJustificacion.objects.exists()
        obj, created = ConfiguracionJustificacion.get_singleton()
        assert created is True
        assert obj.pk == 1
        assert obj.deadline_dias == 5
        assert obj.alerta_dias == 2

    def test_get_deadline_dias_returns_5_by_default(self):
        assert ConfiguracionJustificacion.get_deadline_dias() == 5

    def test_get_alerta_dias_returns_2_by_default(self):
        assert ConfiguracionJustificacion.get_alerta_dias() == 2

    def test_get_deadline_dias_returns_int(self):
        value = ConfiguracionJustificacion.get_deadline_dias()
        assert isinstance(value, int)

    def test_get_alerta_dias_returns_int(self):
        value = ConfiguracionJustificacion.get_alerta_dias()
        assert isinstance(value, int)


class TestConfiguracionJustificacionIdempotency:
    def test_get_singleton_twice_returns_same_row(self):
        first, created_first = ConfiguracionJustificacion.get_singleton()
        second, created_second = ConfiguracionJustificacion.get_singleton()
        assert created_first is True
        assert created_second is False
        assert first.pk == second.pk == 1

    def test_modified_value_persists_across_calls(self):
        obj, _ = ConfiguracionJustificacion.get_singleton()
        obj.deadline_dias = 10
        obj.save()
        assert ConfiguracionJustificacion.get_deadline_dias() == 10
        assert ConfiguracionJustificacion.get_alerta_dias() == 2


class TestConfiguracionJustificacionSingletonInvariant:
    def test_save_forces_pk_1_even_when_pk_set_to_2(self):
        """Whether enforced by save() override or by always returning pk=1,
        the system MUST NOT have two rows in the table."""
        # Pre-populate the singleton
        ConfiguracionJustificacion.get_singleton()
        # Attempt to create another row with a different pk
        rogue = ConfiguracionJustificacion(pk=2, deadline_dias=99, alerta_dias=50)
        rogue.save()
        # Only one row may exist; get_singleton() must still resolve to pk=1
        obj, _ = ConfiguracionJustificacion.get_singleton()
        assert obj.pk == 1
        assert ConfiguracionJustificacion.objects.count() == 1

    def test_delete_is_blocked(self):
        obj, _ = ConfiguracionJustificacion.get_singleton()
        obj.delete()
        # Singleton must survive delete() attempts
        assert ConfiguracionJustificacion.objects.filter(pk=1).exists()


class TestConfiguracionJustificacionStr:
    def test_str_is_human_readable_spanish(self):
        obj, _ = ConfiguracionJustificacion.get_singleton()
        text = str(obj)
        # Must mention configuration and current numbers in Spanish
        assert "Configuración" in text
        assert "5" in text
        assert "2" in text


class TestConfiguracionJustificacionFieldNaming:
    def test_field_names_follow_spanish_convention(self):
        field_names = {f.name for f in ConfiguracionJustificacion._meta.get_fields()}
        assert "deadline_dias" in field_names
        assert "alerta_dias" in field_names
        assert "actualizado_en" in field_names


class TestConfiguracionJustificacionAdminGate:
    def setup_method(self):
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.admin = ConfiguracionJustificacionAdmin(ConfiguracionJustificacion, self.site)

    def test_has_add_permission_true_when_empty(self):
        assert not ConfiguracionJustificacion.objects.exists()
        request = self.factory.get("/admin/")
        assert self.admin.has_add_permission(request) is True

    def test_has_add_permission_false_when_row_exists(self):
        ConfiguracionJustificacion.get_singleton()
        request = self.factory.get("/admin/")
        assert self.admin.has_add_permission(request) is False

    def test_has_delete_permission_always_false(self):
        ConfiguracionJustificacion.get_singleton()
        request = self.factory.get("/admin/")
        obj, _ = ConfiguracionJustificacion.get_singleton()
        assert self.admin.has_delete_permission(request) is False
        assert self.admin.has_delete_permission(request, obj) is False
