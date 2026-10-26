import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), default="Healthcare Assistant Session", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(50), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    info_badge = Column(String(50), default="general", nullable=False)  # 'verified' or 'general'
    citations = Column(Text, default="[]", nullable=False)             # JSON array of citation objects
    metadata_json = Column(Text, default="{}", nullable=False)         # JSON object with node latencies, route, etc.
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")
    feedbacks = relationship("ChatFeedback", back_populates="message", cascade="all, delete-orphan")


class ChatFeedback(Base):
    __tablename__ = "chat_feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    rating = Column(String(20), nullable=False)  # 'thumbs_up' or 'thumbs_down'
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    message = relationship("ChatMessage", back_populates="feedbacks")


class KnowledgeDocumentChunk(Base):
    __tablename__ = "knowledge_document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(String(100), index=True, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    section = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    doc_type = Column(String(50), index=True, nullable=False)       # 'faq', 'feature', 'policy', 'medical_guide', 'pdf'
    trust_level = Column(String(50), default="official", nullable=False)  # 'official', 'verified_clinical', 'general'
    source_url = Column(String(255), nullable=True)
    last_updated = Column(String(50), nullable=False)
    user_id = Column(Integer, nullable=True, index=True)  # Owner of the document
    embedding_json = Column(Text, nullable=False)                  # Serialized list[float]
    metadata_json = Column(Text, default="{}", nullable=False)
