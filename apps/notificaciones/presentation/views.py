"""
API views for in-app notifications.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View

from apps.notificaciones.infrastructure.models import Notificacion


class NotificacionesListView(LoginRequiredMixin, View):
    """GET — Returns last 20 notifications for the authenticated user."""

    def get(self, request):
        qs = Notificacion.objects.filter(destinatario=request.user)[:20]
        no_leidas = Notificacion.objects.filter(destinatario=request.user, leida=False).count()

        notificaciones = [
            {
                "id": n.id,
                "tipo": n.tipo,
                "titulo": n.titulo,
                "mensaje": n.mensaje,
                "leida": n.leida,
                "url": n.url,
                "created_at": n.created_at.strftime("%d/%m/%Y %H:%M"),
            }
            for n in qs
        ]

        return JsonResponse({"notificaciones": notificaciones, "no_leidas": no_leidas})


class MarcarLeidaView(LoginRequiredMixin, View):
    """POST — Marks a single notification as read (only owner)."""

    def post(self, request, pk):
        try:
            notif = Notificacion.objects.get(pk=pk, destinatario=request.user)
        except Notificacion.DoesNotExist:
            return JsonResponse({"error": "No encontrada"}, status=404)

        notif.leida = True
        notif.save(update_fields=["leida"])
        return JsonResponse({"ok": True})


class MarcarTodasLeidasView(LoginRequiredMixin, View):
    """POST — Marks all user's notifications as read."""

    def post(self, request):
        count = Notificacion.objects.filter(destinatario=request.user, leida=False).update(
            leida=True
        )
        return JsonResponse({"ok": True, "actualizadas": count})


class ContadorNoLeidasView(LoginRequiredMixin, View):
    """GET — Returns unread count for badge display."""

    def get(self, request):
        count = Notificacion.objects.filter(destinatario=request.user, leida=False).count()
        return JsonResponse({"no_leidas": count})
