from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    specialty = Column(String(100), index=True, nullable=False)
    qualifications = Column(String(255), nullable=False)
    bio = Column(String(1000), nullable=True)
    consultation_fee = Column(Float, default=100.0, nullable=False)
    available_days = Column(String(100), default="Monday,Tuesday,Wednesday,Thursday,Friday", nullable=False)
    available_time_start = Column(String(20), default="09:00", nullable=False)
    available_time_end = Column(String(20), default="17:00", nullable=False)
    room_number = Column(String(50), default="Room 101", nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="doctor_profile")
    appointments = relationship("Appointment", back_populates="doctor", foreign_keys="Appointment.doctor_id")
