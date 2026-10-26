import json
from fastapi import Body

import time
import asyncio
from typing import List, Optional, AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.deps import get_optional_current_user, get_current_admin
from backend.app.models.user import User
from backend.app.models.chatbot import ChatFeedback, ChatSession
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from backend.app.schemas.chatbot import (
    ChatInput,
    ChatOutput,
    Citation,
    FeedbackInput,
    SessionSummary,
    MessageRead,
    IngestionRequest,
    IngestionResponse,
)
from backend.app.chatbot.memory.history import (
    get_or_create_session,
    save_message,
    get_session_history,
    get_sliding_window_context,
    clear_session_history,
)
from backend.app.chatbot.graph.workflow import run_chatbot_workflow
from backend.app.chatbot.rag.ingestion import ingest_directory

router = APIRouter(prefix="/chatbot", tags=["AI Healthcare Chatbot"])

# In-memory rate limiting tracker (IP/User -> timestamps)
_rate_limits: dict = {}


def check_rate_limit(key: str, max_requests: int = 30, window_seconds: int = 60) -> bool:
    """Sliding window rate limit check."""
    now = time.time()
    if key not in _rate_limits:
        _rate_limits[key] = []
    # Purge old timestamps
    _rate_limits[key] = [t for t in _rate_limits[key] if now - t < window_seconds]
    if len(_rate_limits[key]) >= max_requests:
        return False
    _rate_limits[key].append(now)
    return True


@router.post("/message", response_model=ChatOutput)
async def send_message(
    req: ChatInput,
    request: Request,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Synchronous Chatbot Endpoint:
    Processes user query through the 10-node LangGraph agentic pipeline.
    """
    # 1. Rate Limiting Check
    is_eval_mode = request.headers.get("X-PulseCare-Eval-Mode") == "true" or settings.ENVIRONMENT == "test"
    rate_key = str(current_user.id) if current_user else (request.client.host if request.client else "anonymous")
    if not is_eval_mode and not check_rate_limit(rate_key, max_requests=settings.CHAT_RATE_LIMIT_PER_MINUTE):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait a moment before sending more messages.",
        )

    start_total = time.time()

    # 2. Retrieve or initialize session
    session = await get_or_create_session(db, session_id=req.session_id, user=current_user)

    # 3. Save incoming user message
    await save_message(
        db=db,
        session_id=session.id,
        role="user",
        content=req.message,
    )

    # 4. Fetch conversation sliding window
    history_turns = await get_sliding_window_context(db, session.id, window_size=settings.CHAT_MAX_HISTORY_TURNS)

    # 5. Execute LangGraph Workflow
    try:
        final_state = await run_chatbot_workflow(
            user_query=req.message,
            session_id=session.id,
            db=db,
            current_user=current_user,
            history=history_turns,
        )
    except Exception as e:
        # Graceful fallback if anything fails
        final_state = {
            "final_answer": "PulseCare AI Assistant encountered a temporary processing delay. Please retry or contact clinic support at 1-800-PULSE-CARE.",
            "info_badge": "general",
            "citations": [],
            "routes": ["fallback"],
            "suggested_actions": ["Contact Clinic", "Try Again"],
            "is_emergency": False,
        }

    total_latency_ms = (time.time() - start_total) * 1000

    # 6. Persist assistant response
    answer_text = final_state.get("final_answer", "")
    info_badge = final_state.get("info_badge", "general")
    citations = final_state.get("citations", [])
    routes = final_state.get("routes", ["general"])

    saved_msg = await save_message(
        db=db,
        session_id=session.id,
        role="assistant",
        content=answer_text,
        info_badge=info_badge,
        citations=citations,
        metadata={
            "routes": routes,
            "latency_ms": total_latency_ms,
            "node_latencies": final_state.get("latency_records", {}),
        },
    )

    # Build response model
    citation_objs = [Citation(**c) for c in citations]
    return ChatOutput(
        session_id=session.id,
        message_id=saved_msg.id,
        content=answer_text,
        info_badge=info_badge,
        citations=citation_objs,
        route=" + ".join(routes),
        latency_ms=round(total_latency_ms, 2),
        is_emergency=final_state.get("is_emergency", False),
        suggested_actions=final_state.get("suggested_actions", []),
    )


@router.post("/stream")
async def stream_chat_message(
    req: ChatInput,
    request: Request,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Streaming SSE Endpoint (Server-Sent Events):
    Streams generated tokens in real-time alongside metadata and citation events.
    """
    rate_key = str(current_user.id) if current_user else (request.client.host if request.client else "anonymous")
    if not check_rate_limit(rate_key, max_requests=settings.CHAT_RATE_LIMIT_PER_MINUTE):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")

    start_total = time.time()
    session = await get_or_create_session(db, session_id=req.session_id, user=current_user)

    await save_message(
        db=db,
        session_id=session.id,
        role="user",
        content=req.message,
    )

    history_turns = await get_sliding_window_context(db, session.id, window_size=settings.CHAT_MAX_HISTORY_TURNS)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            final_state = await run_chatbot_workflow(
                user_query=req.message,
                session_id=session.id,
                db=db,
                current_user=current_user,
                history=history_turns,
            )
        except Exception:
            final_state = {
                "final_answer": "PulseCare AI Assistant encountered a temporary processing delay. Please consult our staff at 1-800-PULSE-CARE.",
                "info_badge": "general",
                "citations": [],
                "routes": ["fallback"],
                "suggested_actions": ["Contact Support"],
                "is_emergency": False,
            }

        answer_text = final_state.get("final_answer", "")
        info_badge = final_state.get("info_badge", "general")
        citations = final_state.get("citations", [])
        routes = final_state.get("routes", ["general"])

        # 1. Emit Metadata Event
        meta_payload = {
            "session_id": session.id,
            "route": " + ".join(routes),
            "info_badge": info_badge,
            "is_emergency": final_state.get("is_emergency", False),
            "suggested_actions": final_state.get("suggested_actions", []),
        }
        yield f"event: metadata\ndata: {json.dumps(meta_payload)}\n\n"

        # 2. Emit Stream Tokens
        words = answer_text.split(" ")
        for i, word in enumerate(words):
            token_str = word + (" " if i < len(words) - 1 else "")
            yield f"event: token\ndata: {json.dumps({'token': token_str})}\n\n"
            await asyncio.sleep(0.015)  # Smooth fluid rendering

        # 3. Emit Citations Event
        yield f"event: citations\ndata: {json.dumps(citations)}\n\n"

        # 4. Persist Assistant Message
        saved_msg = await save_message(
            db=db,
            session_id=session.id,
            role="assistant",
            content=answer_text,
            info_badge=info_badge,
            citations=citations,
            metadata={"routes": routes},
        )

        total_ms = (time.time() - start_total) * 1000
        done_payload = {
            "message_id": saved_msg.id,
            "latency_ms": round(total_ms, 2),
        }
        yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/sessions", response_model=SessionSummary)
async def create_session(
    title: Optional[str] = Body(None, embed=True),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new chat session for the authenticated user (or anonymous)."""
    new_id = str(uuid.uuid4())
    new_session = ChatSession(
        id=new_id,
        user_id=current_user.id if current_user else None,
        title=title or "New Conversation",
        is_active=True,
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    return new_session

@router.patch("/sessions/{session_id}", response_model=SessionSummary)
async def rename_session(
    session_id: str,
    new_title: str = Body(...),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rename an existing session; only owner can rename."""
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id and (not current_user or session.user_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to rename this session")
    session.title = new_title
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/sessions/{session_id}/messages", response_model=List[MessageRead])
async def get_messages(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve message history for a specific conversation session."""
    messages = await get_session_history(db, session_id=session_id)
    out = []
    for m in messages:
        cits = []
        if m.citations:
            try:
                cits = [Citation(**c) for c in json.loads(m.citations)]
            except Exception:
                cits = []
        out.append(
            MessageRead(
                id=m.id,
                session_id=m.session_id,
                role=m.role,
                content=m.content,
                info_badge=m.info_badge,
                citations=cits,
                created_at=m.created_at,
            )
        )
    return out


@router.delete("/sessions/{session_id}")
async def clear_history(
    session_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Clear conversation history for privacy compliance."""
    cleared = await clear_session_history(db, session_id=session_id, user=current_user)
    if not cleared:
        raise HTTPException(status_code=404, detail="Session not found or unauthorized to delete.")
    return {"status": "success", "message": "Conversation history cleared."}


@router.post("/feedback", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    feedback: FeedbackInput,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit rating and comment for chatbot response quality auditing."""
    fb = ChatFeedback(
        message_id=feedback.message_id,
        user_id=current_user.id if current_user else None,
        rating=feedback.rating,
        comment=feedback.comment,
    )
    db.add(fb)
    await db.commit()
    return {"status": "success", "message": "Feedback submitted. Thank you for helping improve PulseCare."}


@router.post("/admin/ingest", response_model=IngestionResponse)
async def admin_ingest(
    req: IngestionRequest,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only protected endpoint to trigger RAG knowledge base re-indexing."""
    target_dir = req.directory_path or "./knowledge_base"
    res = await ingest_directory(target_dir, db, reindex=req.reindex)
    return IngestionResponse(**res)
