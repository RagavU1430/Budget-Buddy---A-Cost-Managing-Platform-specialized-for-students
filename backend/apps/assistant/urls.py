from django.urls import path
from .views import AssistantSummaryView, ChatView, ClearHistoryView

urlpatterns = [
    path("assistant/chat/", ChatView.as_view(), name="assistant-chat"),
    path("assistant/summary/", AssistantSummaryView.as_view(), name="assistant-summary"),
    path("assistant/clear/", ClearHistoryView.as_view(), name="assistant-clear"),
]
