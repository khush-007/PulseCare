from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.app.core.database import get_db
from backend.app.models.service import MedicalService
from backend.app.schemas.clinical import ServiceRead

router = APIRouter(prefix="/services", tags=["Medical Services"])


@router.get("/", response_model=List[ServiceRead])
async def list_services(
    department: Optional[str] = Query(None, description="Filter by clinical department"),
    db: AsyncSession = Depends(get_db),
):
    query = select(MedicalService).where(MedicalService.is_active == True)
    if department:
        query = query.where(MedicalService.department.ilike(f"%{department}%"))
    result = await db.execute(query)
    return result.scalars().all()
