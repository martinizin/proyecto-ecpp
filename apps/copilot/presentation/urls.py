"""
URL patterns for the Copilot bounded context (HU22).

JSON endpoints mounted at /copilot/:
- GET  /copilot/chat/                  — fetch active conversation
- POST /copilot/chat/                  — send a message (blocking)
- POST /copilot/chat/stream/           — send a message (SSE streaming)
- POST /copilot/nueva-conversacion/    — close and start a new conversation
"""

from django.urls import path

from apps.copilot.presentation.views import (
    CopilotChatStreamView,
    CopilotChatView,
    CopilotNuevaConversacionView,
)


app_name = "copilot"

urlpatterns = [
    path("chat/", CopilotChatView.as_view(), name="chat"),
    path("chat/stream/", CopilotChatStreamView.as_view(), name="chat_stream"),
    path("nueva-conversacion/", CopilotNuevaConversacionView.as_view(), name="nueva_conversacion"),
]
