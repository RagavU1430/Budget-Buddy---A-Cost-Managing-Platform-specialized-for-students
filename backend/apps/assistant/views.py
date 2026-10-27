"""Views for BudgetBuddy AI Assistant."""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .agent import build_user_finance_context, generate_assistant_response
from .guardrails import evaluate_input_guardrail
from .models import ChatMessage


class ChatView(APIView):
    """POST /api/assistant/chat/ — Send a question or command to BudgetBuddy AI.
    GET /api/assistant/chat/ — Retrieve recent conversation history."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        messages = ChatMessage.objects.filter(user=request.user).order_by("created_at")[:50]
        data = [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "action_type": m.action_type,
                "action_data": m.action_data,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ]
        return Response({"messages": data})

    def post(self, request):
        raw_message = request.data.get("message", "").strip()
        if not raw_message:
            return Response(
                {"error": "Message text is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 1. Evaluate input security guardrail
        is_safe, refusal_reason = evaluate_input_guardrail(raw_message)

        # Record user query in conversation history
        ChatMessage.objects.create(
            user=request.user,
            role=ChatMessage.Role.USER,
            content=raw_message,
        )

        if not is_safe:
            # Store refusal & return immediately without processing
            bot_msg = ChatMessage.objects.create(
                user=request.user,
                role=ChatMessage.Role.ASSISTANT,
                content=refusal_reason,
                action_type="guardrail_blocked",
            )
            return Response(
                {
                    "reply": bot_msg.content,
                    "action_type": "guardrail_blocked",
                    "action_data": {},
                    "guardrail_triggered": True,
                },
                status=status.HTTP_200_OK,
            )

        # 2. Process query through reasoning agent
        reply_text, action_type, action_data = generate_assistant_response(request.user, raw_message)

        # 3. Persist assistant reply
        ChatMessage.objects.create(
            user=request.user,
            role=ChatMessage.Role.ASSISTANT,
            content=reply_text,
            action_type=action_type,
            action_data=action_data,
        )

        return Response(
            {
                "reply": reply_text,
                "action_type": action_type,
                "action_data": action_data,
                "guardrail_triggered": False,
            },
            status=status.HTTP_200_OK,
        )


class ClearHistoryView(APIView):
    """POST /api/assistant/clear/ — Clear chat history for the authenticated user."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        ChatMessage.objects.filter(user=request.user).delete()
        return Response({"status": "cleared", "message": "Conversation history reset."})


class AssistantSummaryView(APIView):
    """GET /api/assistant/summary/ — Quick financial summary for assistant drawer widget."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        context = build_user_finance_context(request.user)
        return Response(
            {
                "current_month": context["current_month"],
                "total_expense": context["total_expense"],
                "remaining_budget": context["remaining_budget"],
                "safe_daily_spend": context["safe_daily_spend"],
                "currency": context["currency"],
                "curr_sym": context["curr_sym"],
                "overbudget_categories": context["overbudget_categories"],
            }
        )
