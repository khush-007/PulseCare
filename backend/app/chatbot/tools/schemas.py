from typing import Optional, List
from pydantic import BaseModel, Field


class SearchDoctorsInput(BaseModel):
    specialty: Optional[str] = Field(None, description="Medical specialty (e.g. Cardiology, Neurology, Pediatrics, Dermatology, Orthopedics)")
    name: Optional[str] = Field(None, description="Doctor full name or partial name")
    day_of_week: Optional[str] = Field(None, description="Day of the week (e.g. Monday, Tuesday, Friday)")


class DoctorProfileInput(BaseModel):
    doctor_id: int = Field(..., description="Unique integer ID of the doctor")


class DoctorAvailabilityInput(BaseModel):
    doctor_id: int = Field(..., description="Unique integer ID of the doctor")
    date_str: Optional[str] = Field(None, description="Date in YYYY-MM-DD format")


class ListServicesInput(BaseModel):
    department: Optional[str] = Field(None, description="Clinical department to filter by (e.g. Cardiology, Dermatology)")


class GetMyAppointmentsInput(BaseModel):
    # Note: caller identity is NEVER taken from input fields to prevent authorization bypass.
    pass


class LookupMedicineInput(BaseModel):
    name: str = Field(..., min_length=2, description="Brand or generic name of medicine (e.g. Amoxicillin, Lisinopril, Metformin)")


class HandoffToTriageInput(BaseModel):
    symptom_text: str = Field(..., min_length=3, description="Patient's described symptoms to evaluate for urgency")


class ProposeAppointmentBookingInput(BaseModel):
    doctor_id: int = Field(..., description="Doctor ID to book with")
    preferred_date: Optional[str] = Field(None, description="Preferred date in YYYY-MM-DD format")
    preferred_time: Optional[str] = Field(None, description="Preferred time in HH:MM format")
    reason: Optional[str] = Field(None, description="Short reason for visit")
