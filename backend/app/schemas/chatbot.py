from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class Citation(BaseModel):
    title: str
    section: str
    source_url: Optional[str] = None
    last_updated: Optional[str] = None
    snippet: Optional[str] = None


class ChatInput(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User prompt text")
    session_id: Optional[str] = Field(None, description="Existing session UUID, or null to auto-generate")


class ChatOutput(BaseModel):
    session_id: str
    message_id: int
    content: str
    info_badge: str = Field("general", description="'verified' or 'general'")
    citations: List[Citation] = Field(default_factory=list)
    route: str
    latency_ms: float
    is_emergency: bool = False
    suggested_actions: List[str] = Field(default_factory=list)


class FeedbackInput(BaseModel):
    message_id: int
    rating: str = Field(..., pattern="^(thumbs_up|thumbs_down)$")
    comment: Optional[str] = Field(None, max_length=500)


class SessionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    session_id: str
    role: str
    content: str
    info_badge: str
    citations: List[Citation] = Field(default_factory=list)
    created_at: datetime


class IngestionRequest(BaseModel):
    directory_path: Optional[str] = None
    reindex: bool = False


class IngestionResponse(BaseModel):
    status: str
    documents_ingested: int
    total_chunks: int
    message: str
