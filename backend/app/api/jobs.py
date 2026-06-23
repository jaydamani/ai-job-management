from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_recruiter
from app.models.recruiter import Recruiter
from app.schemas.candidate import CandidateWithApplicationResponse
from app.schemas.job import JobCloseResponse, JobCreate, JobResponse, JobUpdate
from app.schemas.pagination import PaginatedResponse
from app.services import candidate_service, job_service

router = APIRouter()


@router.get("", response_model=PaginatedResponse[JobResponse])
async def list_jobs(
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    title: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    employment_type: Optional[str] = Query(None),
    experience_level: Optional[str] = Query(None),
    remote_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Recruiter = Depends(get_current_recruiter),
):
    jobs, next_cursor, has_more = await job_service.list_jobs(
        db,
        current_user.id,
        cursor=cursor,
        limit=limit,
        status=status,
        title=title,
        department=department,
        location=location,
        employment_type=employment_type,
        experience_level=experience_level,
        remote_type=remote_type,
    )
    return PaginatedResponse(data=jobs, next_cursor=next_cursor, has_more=has_more)


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    data: JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Recruiter = Depends(get_current_recruiter),
):
    return await job_service.create_job(db, current_user.id, data)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Recruiter = Depends(get_current_recruiter),
):
    return await job_service.get_job(db, job_id, current_user.id)


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: UUID,
    data: JobUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Recruiter = Depends(get_current_recruiter),
):
    return await job_service.update_job(db, job_id, current_user.id, data)


@router.patch("/{job_id}/close", response_model=JobCloseResponse)
async def close_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Recruiter = Depends(get_current_recruiter),
):
    return await job_service.close_job(db, job_id, current_user.id)


@router.get("/{job_id}/candidates", response_model=PaginatedResponse[CandidateWithApplicationResponse])
async def list_job_candidates(
    job_id: UUID,
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: Recruiter = Depends(get_current_recruiter),
):
    items, next_cursor, has_more = await candidate_service.list_job_candidates(
        db, job_id, current_user.id, cursor=cursor, limit=limit
    )
    return PaginatedResponse(data=items, next_cursor=next_cursor, has_more=has_more)
