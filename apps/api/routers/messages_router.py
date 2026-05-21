"""
Conversation memory routes: /messages, /history.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db, scoped_client_id
from marketplace.auth.dependencies import check_user_rate_limit
from marketplace.core.models import MessageIn, MessageOut
from marketplace.settings import MEMORY_MAX_MESSAGES
from marketplace.storage.messages import ConversationMessage
from marketplace.storage.users import User

router = APIRouter(tags=["messages"])


@router.post("/messages", response_model=MessageOut)
def create_message(
    msg: MessageIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_user_rate_limit),
):
    now = datetime.now(timezone.utc).isoformat()
    scoped = scoped_client_id(msg.client_id, current_user) or msg.client_id
    row = ConversationMessage(
        client_id=scoped, role=msg.role, content=msg.content, created_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return MessageOut(
        id=row.id,
        client_id=row.client_id,
        role=row.role,
        content=row.content,
        created_at=row.created_at,
    )


@router.get("/history", response_model=list[MessageOut])
def get_history(
    client_id: str,
    limit: int = MEMORY_MAX_MESSAGES,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_user_rate_limit),
):
    scoped = scoped_client_id(client_id, current_user) or client_id
    rows = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.client_id == scoped)
        .order_by(ConversationMessage.id.desc())
        .limit(limit)
        .all()
    )
    rows.reverse()
    return [
        MessageOut(
            id=r.id,
            client_id=r.client_id,
            role=r.role,
            content=r.content,
            created_at=r.created_at,
        )
        for r in rows
    ]
