from sqlalchemy import Column, Integer, String, Float, Boolean, Text
from backend.app.core.database import Base


class MedicalService(Base):
    __tablename__ = "medical_services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), unique=True, index=True, nullable=False)
    department = Column(String(100), index=True, nullable=False)
    description = Column(Text, nullable=False)
    base_fee = Column(Float, nullable=False)
    duration_minutes = Column(Integer, default=30, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
