import uuid
from fastapi import Cookie, Depends, HTTPException
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import settings
from app.models.recruiter import Recruiter


async def get_current_recruiter(
    access_token: str = Cookie(None),
    db: AsyncSession = Depends(get_db),
) -> Recruiter:
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(access_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    recruiter_id = payload.get("sub")
    if not recruiter_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(select(Recruiter).where(Recruiter.id == uuid.UUID(recruiter_id)))
    recruiter = result.scalar_one_or_none()
    if not recruiter:
        raise HTTPException(status_code=401, detail="Recruiter not found")

    return recruiter
