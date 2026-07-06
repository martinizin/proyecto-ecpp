"""Template tags for the Academico bounded context."""

from datetime import date

from django import template
from django.db.models import Q

from apps.academico.infrastructure.models import Periodo

register = template.Library()


@register.simple_tag
def cierre_periodo_disponible():
    """
    HU28: the closing dashboard only exists once a period has actually
    closed — its fecha_fin passed or it was deactivated (has a snapshot).
    """
    return Periodo.objects.filter(Q(fecha_fin__lt=date.today()) | Q(cierre__isnull=False)).exists()
