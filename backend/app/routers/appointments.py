from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user, get_current_patient
from backend.app.models.appointment import Appointment, AppointmentStatus
from backend.app.models.doctor import Doctor
from backend.app.models.user import User
from backend.app.schemas.clinical import AppointmentRead, AppointmentCreate

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.get("/my", response_model=List[AppointmentRead])
async def get_my_appointments(
    current_user: User = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve appointments for the authenticated patient strictly using their session ID."""
    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.doctor).selectinload(Doctor.user))
        .where(Appointment.patient_id == current_user.id)
        .order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc())
    )
    appointments = result.scalars().all()
    
    response = []
    for appt in appointments:
        doc_name = appt.doctor.user.full_name if (appt.doctor and appt.doctor.user) else "Doctor"
        specialty = appt.doctor.specialty if appt.doctor else "General"
        response.append(
            AppointmentRead(
                id=appt.id,
                patient_id=appt.patient_id,
                doctor_id=appt.doctor_id,
                doctor_name=doc_name,
                specialty=specialty,
                appointment_date=appt.appointment_date,
                appointment_time=appt.appointment_time,
                status=appt.status,
                reason=appt.reason,
                notes=appt.notes,
                created_at=appt.created_at,
            )
        )
    return response


@router.post("/", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    req: AppointmentCreate,
    current_user: User = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    # Verify doctor exists
    doc_res = await db.execute(
        select(Doctor).options(selectinload(Doctor.user)).where(Doctor.id == req.doctor_id)
    )
    doctor = doc_res.scalars().first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with ID {req.doctor_id} not found",
        )
        
    new_appt = Appointment(
        patient_id=current_user.id,
        doctor_id=req.doctor_id,
        appointment_date=req.appointment_date,
        appointment_time=req.appointment_time,
        status=AppointmentStatus.SCHEDULED,
        reason=req.reason,
    )
    db.add(new_appt)
    await db.commit()
    await db.refresh(new_appt)
    
    return AppointmentRead(
        id=new_appt.id,
        patient_id=new_appt.patient_id,
        doctor_id=new_appt.doctor_id,
        doctor_name=doctor.user.full_name if doctor.user else "Doctor",
        specialty=doctor.specialty,
        appointment_date=new_appt.appointment_date,
        appointment_time=new_appt.appointment_time,
        status=new_appt.status,
        reason=new_appt.reason,
        notes=new_appt.notes,
        created_at=new_appt.created_at,
    )


@router.delete("/{appointment_id}")
async def cancel_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appt = result.scalars().first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    if appt.patient_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Unauthorized to cancel this appointment")
        
    appt.status = AppointmentStatus.CANCELLED
    await db.commit()
    return {"message": "Appointment cancelled successfully", "id": appointment_id}
