from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from backend.app.models.user import UserRole
from backend.app.models.appointment import AppointmentStatus


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: str
    role: UserRole
    phone: Optional[str] = None
    is_active: bool
    created_at: datetime


class DoctorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    name: Optional[str] = None
    specialty: str
    qualifications: str
    bio: Optional[str] = None
    consultation_fee: float
    available_days: str
    available_time_start: str
    available_time_end: str
    room_number: str
    is_available: bool


class AppointmentCreate(BaseModel):
    doctor_id: int
    appointment_date: str  # YYYY-MM-DD
    appointment_time: str  # HH:MM
    reason: str


class AppointmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    patient_id: int
    doctor_id: int
    doctor_name: Optional[str] = None
    specialty: Optional[str] = None
    appointment_date: str
    appointment_time: str
    status: AppointmentStatus
    reason: str
    notes: Optional[str] = None
    created_at: datetime


class ServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    department: str
    description: str
    base_fee: float
    duration_minutes: int
    is_active: bool


class MedicineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    generic_name: str
    dosage_form: str
    standard_dosage: str
    indications: str
    contraindications: str
    side_effects: str
    requires_prescription: bool
    price: float


class TriageRequest(BaseModel):
    symptoms: str
    duration_days: Optional[int] = 1
    existing_conditions: Optional[List[str]] = None


class TriageResponse(BaseModel):
    severity_level: str
    is_emergency: bool
    recommended_action: str
    recommended_specialty: Optional[str] = None
    emergency_contacts: List[str]
    triage_score: float
