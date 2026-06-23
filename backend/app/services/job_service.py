import uuid
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.schemas.job import JobCreate, JobUpdate
from app.schemas.pagination import decode_cursor, encode_cursor


async def create_job(db: AsyncSession, recruiter_id: uuid.UUID, data: JobCreate) -> Job:
    job = Job(recruiter_id=recruiter_id, **data.model_dump())
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def get_job(db: AsyncSession, job_id: uuid.UUID, recruiter_id: uuid.UUID) -> Job:
    result = await db.execute(
        select(Job).where(Job.id == job_id, Job.recruiter_id == recruiter_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


async def list_jobs(
    db: AsyncSession,
    recruiter_id: uuid.UUID,
    cursor: Optional[str] = None,
    limit: int = 20,
    status: Optional[str] = None,
    title: Optional[str] = None,
    department: Optional[str] = None,
    location: Optional[str] = None,
    employment_type: Optional[str] = None,
    experience_level: Optional[str] = None,
    remote_type: Optional[str] = None,
) -> tuple:
    query = select(Job).where(Job.recruiter_id == recruiter_id)

    if status:
        query = query.where(Job.status == status)
    if title:
        query = query.where(Job.title.ilike(f"%{title}%"))
    if department:
        query = query.where(Job.department.ilike(f"%{department}%"))
    if location:
        query = query.where(Job.location.ilike(f"%{location}%"))
    if employment_type:
        query = query.where(Job.employment_type == employment_type)
    if experience_level:
        query = query.where(Job.experience_level == experience_level)
    if remote_type:
        query = query.where(Job.remote_type == remote_type)

    if cursor:
        parts = decode_cursor(cursor)
        cursor_ts = datetime.fromisoformat(parts[0])
        cursor_id = uuid.UUID(parts[1])
        query = query.where(
            or_(
                Job.created_at < cursor_ts,
                and_(Job.created_at == cursor_ts, Job.id < cursor_id),
            )
        )

    query = query.order_by(Job.created_at.desc(), Job.id.desc()).limit(limit + 1)
    result = await db.execute(query)
    jobs = list(result.scalars().all())

    has_more = len(jobs) > limit
    if has_more:
        jobs = jobs[:limit]

    next_cursor = None
    if has_more and jobs:
        last = jobs[-1]
        next_cursor = encode_cursor(last.created_at.isoformat(), str(last.id))

    return jobs, next_cursor, has_more


async def update_job(
    db: AsyncSession, job_id: uuid.UUID, recruiter_id: uuid.UUID, data: JobUpdate
) -> Job:
    job = await get_job(db, job_id, recruiter_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(job, field, value)
    await db.commit()
    await db.refresh(job)
    return job


async def close_job(db: AsyncSession, job_id: uuid.UUID, recruiter_id: uuid.UUID) -> Job:
    job = await get_job(db, job_id, recruiter_id)
    job.status = "closed"
    await db.commit()
    await db.refresh(job)
    return job
