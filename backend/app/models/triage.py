import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey
from backend.app.core.database import Base


class TriageSeverity(str, enum.Enum):
    EMERGENCY = "emergency"      # Immediate 911 / ER
    URGENT = "urgent"            # Same-day clinic or urgent care
    NON_URGENT = "non_urgent"    # Routine appointment within 1-2 days
    SELF_CARE = "self_care"      # Home care with monitoring


class TriageAssessment(Base):
    __tablename__ = "triage_assessments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    symptoms_text = Column(Text, nullable=False)
    severity_level = Column(String(50), nullable=False)
    recommended_action = Column(Text, nullable=False)
    recommended_specialty = Column(String(100), nullable=True)
    triage_score = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
