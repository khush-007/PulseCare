from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from backend.app.models.doctor import Doctor
from backend.app.models.appointment import Appointment, AppointmentStatus


async def search_doctors(
    db: AsyncSession,
    specialty: Optional[str] = None,
    name: Optional[str] = None,
    day_of_week: Optional[str] = None,
) -> Dict[str, Any]:
    """Search available doctors using parameterized queries via the ORM layer."""
    query = select(Doctor).options(selectinload(Doctor.user)).where(Doctor.is_available == True)
    
    if specialty:
        query = query.where(Doctor.specialty.ilike(f"%{specialty}%"))
    if day_of_week:
        query = query.where(Doctor.available_days.ilike(f"%{day_of_week}%"))
        
    result = await db.execute(query)
    doctors = result.scalars().all()
    
    matched = []
    for d in doctors:
        doc_name = d.user.full_name if d.user else "Unknown Doctor"
        if name and name.lower() not in doc_name.lower():
            continue
        matched.append({
            "doctor_id": d.id,
            "name": doc_name,
            "specialty": d.specialty,
            "qualifications": d.qualifications,
            "consultation_fee": f"${d.consultation_fee:.2f}",
            "available_days": d.available_days,
            "hours": f"{d.available_time_start} - {d.available_time_end}",
            "room": d.room_number,
        })
        
    if not matched:
        return {
            "status": "not_found",
            "message": f"No doctors found matching criteria (specialty={specialty}, name={name}, day={day_of_week}).",
            "doctors": [],
        }
        
    return {
        "status": "success",
        "count": len(matched),
        "doctors": matched[:5],  # Result limit to prevent token blowup
    }


async def get_doctor_profile(db: AsyncSession, doctor_id: int) -> Dict[str, Any]:
    """Retrieve verified profile information for a specific doctor by ID."""
    result = await db.execute(
        select(Doctor).options(selectinload(Doctor.user)).where(Doctor.id == doctor_id)
    )
    doctor = result.scalars().first()
    if not doctor:
        return {
            "status": "not_found",
            "message": f"Doctor with ID {doctor_id} does not exist in PulseCare records.",
        }
        
    return {
        "status": "success",
        "doctor_id": doctor.id,
        "name": doctor.user.full_name if doctor.user else "Unknown Doctor",
        "specialty": doctor.specialty,
        "qualifications": doctor.qualifications,
        "bio": doctor.bio,
        "consultation_fee": f"${doctor.consultation_fee:.2f}",
        "available_days": doctor.available_days,
        "available_hours": f"{doctor.available_time_start} - {doctor.available_time_end}",
        "room_number": doctor.room_number,
        "accepting_patients": doctor.is_available,
    }


async def get_doctor_availability(
    db: AsyncSession,
    doctor_id: int,
    date_str: Optional[str] = None,
) -> Dict[str, Any]:
    """Check working schedule and booked appointment slots for a doctor."""
    result = await db.execute(
        select(Doctor).options(selectinload(Doctor.user)).where(Doctor.id == doctor_id)
    )
    doctor = result.scalars().first()
    if not doctor:
        return {
            "status": "not_found",
            "message": f"Doctor with ID {doctor_id} not found.",
        }

    # Query already scheduled appointments on date
    booked_times = []
    if date_str:
        appts_res = await db.execute(
            select(Appointment).where(
                Appointment.doctor_id == doctor_id,
                Appointment.appointment_date == date_str,
                Appointment.status == AppointmentStatus.SCHEDULED,
            )
        )
        booked = appts_res.scalars().all()
        booked_times = [b.appointment_time for b in booked]

    return {
        "status": "success",
        "doctor_id": doctor.id,
        "doctor_name": doctor.user.full_name if doctor.user else "Unknown Doctor",
        "specialty": doctor.specialty,
        "available_days": doctor.available_days,
        "daily_hours": f"{doctor.available_time_start} to {doctor.available_time_end}",
        "date_queried": date_str or "general schedule",
        "already_booked_slots": booked_times,
        "booking_instruction": "Appointments must be confirmed through the PulseCare booking interface.",
    }
