from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_recruiter
from app.models.recruiter import Recruiter
from app.schemas.application import ApplicationResponse, StatusUpdate
from app.services import application_service

router = APIRouter()


@router.patch("/{application_id}/status", response_model=ApplicationResponse)
async def update_application_status(
    application_id: UUID,
    data: StatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Recruiter = Depends(get_current_recruiter),
):
    return await application_service.update_status(
        db, application_id, current_user.id, data.status
    )
