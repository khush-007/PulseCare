import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import delete
from backend.app.models.chatbot import ChatSession, ChatMessage
from backend.app.models.user import User


async def get_or_create_session(
    db: AsyncSession,
    session_id: Optional[str] = None,
    user: Optional[User] = None,
    title: str = "PulseCare Healthcare Consultation",
) -> ChatSession:
    """Retrieve an active session or create a new isolated session."""
    if session_id:
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id, ChatSession.is_active == True)
        )
        session = result.scalars().first()
        if session:
            # If user is logged in now but session had no user, link them
            if user and not session.user_id:
                session.user_id = user.id
                await db.commit()
            return session

    # Create new session
    new_id = session_id or str(uuid.uuid4())
    new_session = ChatSession(
        id=new_id,
        user_id=user.id if user else None,
        title=title,
        is_active=True,
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    return new_session


async def save_message(
    db: AsyncSession,
    session_id: str,
    role: str,
    content: str,
    info_badge: str = "general",
    citations: Optional[List[Dict[str, Any]]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> ChatMessage:
    """Save a user or assistant message to database."""
    msg = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        info_badge=info_badge,
        citations=json.dumps(citations or []),
        metadata_json=json.dumps(metadata or {}),
    )
    db.add(msg)
    
    # Update session updated_at
    sess_res = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = sess_res.scalars().first()
    if session:
        session.updated_at = datetime.now(timezone.utc)
        
    await db.commit()
    await db.refresh(msg)
    return msg


async def get_session_history(
    db: AsyncSession,
    session_id: str,
    limit: int = 50,
) -> List[ChatMessage]:
    """Retrieve full message history for a session."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)
    )
    return result.scalars().all()


async def get_sliding_window_context(
    db: AsyncSession,
    session_id: str,
    window_size: int = 6,
) -> List[Dict[str, str]]:
    """
    Produce a sliding context window for the LangGraph agent.
    If older turns exceed window_size, aggregates older turns into a condensed summary.
    """
    history = await get_session_history(db, session_id, limit=30)
    if not history:
        return []

    if len(history) <= window_size:
        return [{"role": m.role, "content": m.content} for m in history]

    # Summarize older turns
    older_turns = history[:-window_size]
    recent_turns = history[-window_size:]

    older_summary_parts = []
    for m in older_turns:
        prefix = "User" if m.role == "user" else "Assistant"
        # truncate turns to preserve compact representation
        text_snip = m.content[:100].replace("\n", " ")
        older_summary_parts.append(f"{prefix}: {text_snip}")

    condensed_summary = (
        "[Prior conversation summary: " + "; ".join(older_summary_parts[-4:]) + "]"
    )

    context = [{"role": "system", "content": condensed_summary}]
    for m in recent_turns:
        context.append({"role": m.role, "content": m.content})

    return context


async def clear_session_history(
    db: AsyncSession,
    session_id: str,
    user: Optional[User] = None,
) -> bool:
    """Soft or hard delete user's session history for privacy compliance."""
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalars().first()
    if not session:
        return False

    # Check ownership if session is tied to a user
    if session.user_id and (not user or session.user_id != user.id):
        return False

    # Delete messages and session
    await db.execute(delete(ChatMessage).where(ChatMessage.session_id == session_id))
    await db.execute(delete(ChatSession).where(ChatSession.id == session_id))
    await db.commit()
    return True
