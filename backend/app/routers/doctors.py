from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from backend.app.core.database import get_db
from backend.app.models.doctor import Doctor
from backend.app.models.user import User
from backend.app.schemas.clinical import DoctorRead

router = APIRouter(prefix="/doctors", tags=["Doctors"])


@router.get("/", response_model=List[DoctorRead])
async def list_doctors(
    specialty: Optional[str] = Query(None, description="Filter by clinical specialty"),
    search: Optional[str] = Query(None, description="Search doctor name or specialty"),
    db: AsyncSession = Depends(get_db),
):
    query = select(Doctor).options(selectinload(Doctor.user)).where(Doctor.is_available == True)
    
    if specialty:
        query = query.where(Doctor.specialty.ilike(f"%{specialty}%"))
    
    result = await db.execute(query)
    doctors = result.scalars().all()
    
    # Map doctor model with User name
    response = []
    for d in doctors:
        doc_dict = {
            "id": d.id,
            "user_id": d.user_id,
            "name": d.user.full_name if d.user else "Unknown Doctor",
            "specialty": d.specialty,
            "qualifications": d.qualifications,
            "bio": d.bio,
            "consultation_fee": d.consultation_fee,
            "available_days": d.available_days,
            "available_time_start": d.available_time_start,
            "available_time_end": d.available_time_end,
            "room_number": d.room_number,
            "is_available": d.is_available,
        }
        if search:
            search_lower = search.lower()
            if (search_lower in doc_dict["name"].lower() or 
                search_lower in d.specialty.lower() or 
                search_lower in (d.bio or "").lower()):
                response.append(DoctorRead(**doc_dict))
        else:
            response.append(DoctorRead(**doc_dict))
            
    return response


@router.get("/{doctor_id}", response_model=DoctorRead)
async def get_doctor_profile(doctor_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Doctor).options(selectinload(Doctor.user)).where(Doctor.id == doctor_id)
    )
    doctor = result.scalars().first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with ID {doctor_id} not found",
        )
    return DoctorRead(
        id=doctor.id,
        user_id=doctor.user_id,
        name=doctor.user.full_name if doctor.user else "Unknown Doctor",
        specialty=doctor.specialty,
        qualifications=doctor.qualifications,
        bio=doctor.bio,
        consultation_fee=doctor.consultation_fee,
        available_days=doctor.available_days,
        available_time_start=doctor.available_time_start,
        available_time_end=doctor.available_time_end,
        room_number=doctor.room_number,
        is_available=doctor.is_available,
    )
