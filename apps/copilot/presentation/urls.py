"""
URL patterns for the Copilot bounded context (HU22).

Three JSON endpoints mounted at /copilot/:
- GET  /copilot/chat/                  — fetch active conversation
- POST /copilot/chat/                  — send a message
- POST /copilot/nueva-conversacion/    — close and start a new conversation
"""

from django.urls import path

from apps.copilot.presentation.views import (
    CopilotChatView,
    CopilotNuevaConversacionView,
)


app_name = "copilot"

urlpatterns = [
    path("chat/", CopilotChatView.as_view(), name="chat"),
    path("nueva-conversacion/", CopilotNuevaConversacionView.as_view(), name="nueva_conversacion"),
]
