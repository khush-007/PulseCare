from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Any, List, Optional

from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.models.user_memory import UserMemory
from backend.app.core.deps import get_optional_current_user

router = APIRouter(prefix="/memory", tags=["User Memory"])

@router.get("/{key}", response_model=Any)
async def get_memory(key: str, current_user: Optional[User] = Depends(get_optional_current_user), db: AsyncSession = Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    result = await db.execute(
        select(UserMemory).where(UserMemory.user_id == current_user.id, UserMemory.key == key)
    )
    mem = result.scalars().first()
    if not mem:
        raise HTTPException(status_code=404, detail="Memory key not found")
    return mem.value

@router.post("/", status_code=status.HTTP_201_CREATED)
async def set_memory(data: dict, current_user: Optional[User] = Depends(get_optional_current_user), db: AsyncSession = Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    key = data.get("key")
    value = data.get("value")
    if not key:
        raise HTTPException(status_code=400, detail="Missing 'key' in request body")
    result = await db.execute(
        select(UserMemory).where(UserMemory.user_id == current_user.id, UserMemory.key == key)
    )
    mem = result.scalars().first()
    if mem:
        mem.value = value
    else:
        mem = UserMemory(user_id=current_user.id, key=key, value=value)
        db.add(mem)
    await db.commit()
    return {"status": "success", "key": key}

@router.delete("/{key}")
async def delete_memory(key: str, current_user: Optional[User] = Depends(get_optional_current_user), db: AsyncSession = Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    result = await db.execute(
        select(UserMemory).where(UserMemory.user_id == current_user.id, UserMemory.key == key)
    )
    mem = result.scalars().first()
    if not mem:
        raise HTTPException(status_code=404, detail="Memory key not found")
    await db.delete(mem)
    await db.commit()
    return {"status": "deleted", "key": key}
