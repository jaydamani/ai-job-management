import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import CandidateJobApplication
from app.models.job import Job

VALID_STATUSES = {"applied", "screened", "interviewed", "rejected", "hired"}


async def update_status(
    db: AsyncSession,
    application_id: uuid.UUID,
    recruiter_id: uuid.UUID,
    status: str,
) -> CandidateJobApplication:
    if status not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}",
        )

    result = await db.execute(
        select(CandidateJobApplication)
        .join(Job, CandidateJobApplication.job_id == Job.id)
        .where(
            CandidateJobApplication.id == application_id,
            Job.recruiter_id == recruiter_id,
        )
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    app.status = status
    await db.commit()
    await db.refresh(app)
    return app
