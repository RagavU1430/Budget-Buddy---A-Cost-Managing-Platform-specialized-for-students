"""Assistant router — port of ``apps/assistant`` (ChatView, AssistantSummaryView, ClearHistoryView).

Endpoints:
- POST /api/assistant/chat/
- GET  /api/assistant/chat/
- GET  /api/assistant/summary/
- POST /api/assistant/clear/
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, status
from sqlalchemy import delete, select

from app.api.deps import CurrentUser, DbSession, json_body
from app.core.errors import bad_request_detail
from app.core.serializers import chat_dict
from app.db import models
from app.services.assistant_agent import (
    build_user_finance_context,
    clear_pending_action,
    generate_assistant_response,
)
from app.services.assistant_guardrails import evaluate_input_guardrail

router = APIRouter()


@router.get("/assistant/chat/", response_model=None)
async def list_chat_messages(user: CurrentUser, db: DbSession):
    """Retrieve recent conversation history (last 50 messages, ascending by created_at)."""
    stmt = (
        select(models.ChatMessage)
        .where(models.ChatMessage.user_id == user.id)
        .order_by(models.ChatMessage.created_at.asc())
        .limit(50)
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()
    return {"messages": [chat_dict(m) for m in messages]}


@router.post("/assistant/chat/", response_model=None)
async def send_chat_message(request: Request, user: CurrentUser, db: DbSession):
    """Send a question or command to BudgetBuddy AI."""
    body = await json_body(request)
    raw_message = (body.get("message") or "").strip()
    if not raw_message:
        raise bad_request_detail("Message text is required.")

    # 1. Evaluate input security guardrail
    is_safe, refusal_reason = evaluate_input_guardrail(raw_message)

    # Record user message in conversation history
    user_msg = models.ChatMessage(
        user_id=user.id,
        role="user",
        content=raw_message,
        action_type="",
        action_data={},
    )
    db.add(user_msg)
    await db.flush()

    if not is_safe:
        # Refusal - persist assistant refusal message
        bot_msg = models.ChatMessage(
            user_id=user.id,
            role="assistant",
            content=refusal_reason or "",
            action_type="guardrail_blocked",
            action_data={},
        )
        db.add(bot_msg)
        await db.commit()
        return {
            "reply": bot_msg.content,
            "action_type": "guardrail_blocked",
            "action_data": {},
            "guardrail_triggered": True,
        }

    # 2. Process query through reasoning agent
    reply_text, action_type, action_data = await generate_assistant_response(db, user, raw_message)

    # 3. Persist assistant reply
    bot_msg = models.ChatMessage(
        user_id=user.id,
        role="assistant",
        content=reply_text,
        action_type=action_type,
        action_data=action_data,
    )
    db.add(bot_msg)
    await db.commit()

    return {
        "reply": reply_text,
        "action_type": action_type,
        "action_data": action_data,
        "guardrail_triggered": False,
    }


@router.get("/assistant/summary/", response_model=None)
async def assistant_summary(user: CurrentUser, db: DbSession):
    """Quick financial summary for assistant drawer widget."""
    context = await build_user_finance_context(db, user)
    return {
        "current_month": context["current_month"],
        "total_expense": context["total_expense"],
        "remaining_budget": context["remaining_budget"],
        "safe_daily_spend": context["safe_daily_spend"],
        "currency": context["currency"],
        "curr_sym": context["curr_sym"],
        "overbudget_categories": context["overbudget_categories"],
    }


@router.post("/assistant/clear/", response_model=None)
async def clear_chat_history(user: CurrentUser, db: DbSession):
    """Clear chat conversation history for authenticated user."""
    await db.execute(delete(models.ChatMessage).where(models.ChatMessage.user_id == user.id))
    await clear_pending_action(db, user)
    await db.commit()
    return {"status": "cleared", "message": "Conversation history reset."}
