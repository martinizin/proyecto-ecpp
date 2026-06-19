"""
Presentation layer for HU26 — ANT report generation and download.
"""

import os

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView

from apps.academico.infrastructure.models import Periodo
from apps.reportes.application.reporte_ant_app_service import ReporteANTAppService
from apps.reportes.domain.exceptions import PeriodoSinEstudiantesError
from apps.reportes.domain.services import ReporteANTService
from apps.reportes.infrastructure.models import ReporteANT

ROLES_LECTURA = ("inspector", "secretaria", "director_academico")
ROLES_GENERACION = ("secretaria", "director_academico")


class _RolMixin(LoginRequiredMixin, UserPassesTestMixin):
    roles_permitidos: tuple = ()

    def test_func(self):
        return self.request.user.rol in self.roles_permitidos


class ReporteANTListView(_RolMixin, ListView):
    """List all generated ANT reports."""

    template_name = "reportes/ant/listado.html"
    context_object_name = "reportes"
    paginate_by = 20
    roles_permitidos = ROLES_LECTURA

    def get_queryset(self):
        return ReporteANT.objects.select_related(
            "periodo", "generado_por"
        ).order_by("-fecha_generacion")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["periodos"] = Periodo.objects.order_by("-fecha_inicio")
        return ctx


class ReporteANTGenerarView(_RolMixin, View):
    """Render form (GET) and generate a new ANT report (POST)."""

    roles_permitidos = ROLES_GENERACION

    def get(self, request):
        import json
        from apps.academico.infrastructure.models import TipoLicencia
        periodos = Periodo.objects.select_related("tipo_licencia").order_by("-fecha_inicio")
        tipo_licencias = TipoLicencia.objects.filter(activo=True).order_by("codigo")
        periodos_json = json.dumps([
            {
                "id": p.id,
                "nombre": p.nombre,
                "activo": p.activo,
                "tipo_licencia_id": p.tipo_licencia_id,
            }
            for p in periodos
        ])
        return render(request, "reportes/ant/generar.html", {
            "periodos": periodos,
            "tipo_licencias": tipo_licencias,
            "periodos_json": periodos_json,
        })

    def post(self, request):
        periodo_id = request.POST.get("periodo_id")
        notas = request.POST.get("notas", "").strip()

        if not periodo_id:
            messages.error(request, "Debe seleccionar un período académico.")
            return redirect("reportes:ant_generar")

        periodo = get_object_or_404(Periodo, pk=periodo_id)

        try:
            service = ReporteANTAppService(
                periodo=periodo,
                generado_por=request.user,
                notas=notas,
            )
            reporte = service.generar()
            messages.success(
                request,
                f"Reporte ANT generado exitosamente "
                f"({reporte.total_estudiantes} estudiantes).",
            )
        except PeriodoSinEstudiantesError as e:
            messages.error(request, str(e))
        except Exception as e:
            from django.conf import settings
            if settings.DEBUG:
                raise
            messages.error(
                request,
                "Ocurrió un error al generar el reporte. Intente nuevamente.",
            )

        return redirect("reportes:ant_listado")


class ReporteANTDescargarView(_RolMixin, View):
    """Serve the PDF file as an attachment."""

    roles_permitidos = ROLES_LECTURA

    def get(self, request, pk):
        reporte = get_object_or_404(ReporteANT, pk=pk)
        if not reporte.archivo_pdf:
            raise Http404("Archivo PDF no disponible.")
        return FileResponse(
            reporte.archivo_pdf.open("rb"),
            as_attachment=True,
            filename=os.path.basename(reporte.archivo_pdf.name),
            content_type="application/pdf",
        )


class ReporteANTVerificarHashView(LoginRequiredMixin, View):
    """Return JSON with integrity check result for a stored report."""

    def get(self, request, pk):
        reporte = get_object_or_404(ReporteANT, pk=pk)
        if not reporte.archivo_pdf:
            return JsonResponse({"error": "Archivo no disponible."}, status=404)

        contenido = reporte.archivo_pdf.read()
        hash_actual = ReporteANTService.computar_hash(contenido)
        coincide = hash_actual == reporte.hash_sha256

        return JsonResponse({
            "hash_almacenado": reporte.hash_sha256,
            "hash_actual": hash_actual,
            "integridad_valida": coincide,
        })
