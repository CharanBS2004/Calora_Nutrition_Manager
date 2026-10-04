import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.entities import User, ChatMessage
from app.schemas.all_schemas import ChatRequest, ChatResponse, ActionButton
from app.services.agent.agent_orchestrator import agent_orchestrator
from app.services.llm_client import LLMConfigurationError, LLMResponseError

router = APIRouter(prefix="/coach", tags=["AI Coach & Agent"])

@router.post("/chat", response_model=ChatResponse)
def chat_with_coach(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Conversational AI Coach endpoint powered by LangGraph agent.
    Executes reasoning, tool use, post-action reflection, and safety guardrails.
    """
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message cannot be empty.")

    try:
        out = agent_orchestrator.run(
            user_id=current_user.id,
            user_message=request.message.strip(),
            db=db,
            context=request.context
        )
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (LLMResponseError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # Fetch last inserted assistant message id
    last_msg = db.query(ChatMessage).filter(
        ChatMessage.user_id == current_user.id,
        ChatMessage.role == "assistant"
    ).order_by(ChatMessage.id.desc()).first()

    msg_id = last_msg.id if last_msg else 1

    action_objs = [
        ActionButton(
            label=btn["label"],
            action_type=btn["action_type"],
            payload=btn.get("payload", {})
        ) for btn in out.get("action_buttons", [])
    ]

    return ChatResponse(
        message_id=msg_id,
        role="assistant",
        reply=out["reply"],
        tool_calls=out.get("tool_calls", []),
        goal_impact=out.get("goal_impact"),
        uncertainty_flag=out.get("uncertainty_flag", False),
        clarification_needed=out.get("clarification_needed"),
        suggested_options=out.get("suggested_options", []),
        action_buttons=action_objs,
        created_at=datetime.now(timezone.utc)
    )

@router.get("/history")
def get_chat_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve chat history with strict user isolation."""
    messages = db.query(ChatMessage).filter(
        ChatMessage.user_id == current_user.id
    ).order_by(ChatMessage.created_at.asc()).limit(limit).all()

    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "uncertainty_flag": m.uncertainty_flag,
            "tool_calls": json.loads(m.tool_calls_json) if m.tool_calls_json else [],
            "actions": json.loads(m.contextual_actions_json) if m.contextual_actions_json else [],
            "created_at": m.created_at
        } for m in messages
    ]

@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
def clear_chat_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clear conversation history for authenticated user."""
    db.query(ChatMessage).filter(ChatMessage.user_id == current_user.id).delete()
    db.commit()
    return None
