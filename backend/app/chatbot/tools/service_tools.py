from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.app.models.service import MedicalService


async def list_services(
    db: AsyncSession,
    department: Optional[str] = None,
) -> Dict[str, Any]:
    """List clinical services, departments, and transparent fees."""
    query = select(MedicalService).where(MedicalService.is_active == True)
    if department:
        query = query.where(MedicalService.department.ilike(f"%{department}%"))
        
    result = await db.execute(query)
    services = result.scalars().all()
    
    if not services:
        return {
            "status": "not_found",
            "message": f"No services found for department '{department}'.",
            "services": [],
        }
        
    items = []
    for s in services:
        items.append({
            "service_id": s.id,
            "name": s.name,
            "department": s.department,
            "description": s.description,
            "base_fee": f"${s.base_fee:.2f}",
            "duration": f"{s.duration_minutes} minutes",
        })
        
    return {
        "status": "success",
        "count": len(items),
        "services": items,
    }
