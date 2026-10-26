from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from backend.app.core.config import settings
from backend.app.models.appointment import Appointment
from backend.app.models.doctor import Doctor
from backend.app.models.user import User


async def get_my_appointments(
    db: AsyncSession,
    current_user: Optional[User],
) -> Dict[str, Any]:
    """
    Retrieve appointments for the authenticated patient.
    STRICT SECURITY RULE: The patient ID is ALWAYS extracted from current_user.
    User prompt text is NEVER trusted for identity.
    """
    if not current_user:
        return {
            "status": "unauthorized",
            "message": "You must be logged in to view your appointments. Please sign in to your PulseCare account.",
            "appointments": [],
        }

    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.doctor).selectinload(Doctor.user))
        .where(Appointment.patient_id == current_user.id)
        .order_by(Appointment.appointment_date.asc(), Appointment.appointment_time.asc())
    )
    appointments = result.scalars().all()

    if not appointments:
        return {
            "status": "success",
            "message": f"Hello {current_user.full_name}, you currently have no scheduled appointments.",
            "patient_name": current_user.full_name,
            "appointments": [],
        }

    appts_list = []
    for a in appointments:
        doc_name = a.doctor.user.full_name if (a.doctor and a.doctor.user) else "PulseCare Doctor"
        appts_list.append({
            "appointment_id": a.id,
            "doctor": doc_name,
            "specialty": a.doctor.specialty if a.doctor else "General",
            "room": a.doctor.room_number if a.doctor else "Clinic",
            "date": a.appointment_date,
            "time": a.appointment_time,
            "status": a.status.value,
            "reason": a.reason,
            "notes": a.notes or "",
        })

    return {
        "status": "success",
        "patient_name": current_user.full_name,
        "count": len(appts_list),
        "appointments": appts_list,
    }


async def propose_appointment_booking(
    db: AsyncSession,
    doctor_id: int,
    preferred_date: Optional[str] = None,
    preferred_time: Optional[str] = None,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate an appointment proposal with a secure deep link to the booking interface.
    NON-DESTRUCTIVE: This tool NEVER alters the database or commits bookings automatically.
    """
    if not settings.FEATURE_PROPOSE_BOOKING:
        return {
            "status": "disabled",
            "message": "Appointment booking proposals are currently disabled in system configuration.",
        }

    result = await db.execute(
        select(Doctor).options(selectinload(Doctor.user)).where(Doctor.id == doctor_id)
    )
    doctor = result.scalars().first()
    if not doctor:
        return {
            "status": "not_found",
            "message": f"Doctor with ID {doctor_id} not found.",
        }

    doc_name = doctor.user.full_name if doctor.user else "Doctor"
    deep_link = f"/portal/appointments/book?doctorId={doctor_id}"
    if preferred_date:
        deep_link += f"&date={preferred_date}"
    if preferred_time:
        deep_link += f"&time={preferred_time}"

    return {
        "status": "proposal",
        "message": f"To schedule your visit with {doc_name} ({doctor.specialty}), please confirm through our official appointment interface.",
        "doctor_name": doc_name,
        "specialty": doctor.specialty,
        "consultation_fee": f"${doctor.consultation_fee:.2f}",
        "suggested_date": preferred_date or "Select in portal",
        "suggested_time": preferred_time or "Select in portal",
        "booking_url": deep_link,
        "requires_confirmation": True,
    }
