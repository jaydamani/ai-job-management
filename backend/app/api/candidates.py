from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_recruiter
from app.models.recruiter import Recruiter
from app.schemas.application import ApplicationCreate, ApplicationResponse, ApplicationSummaryResponse, ResumeUploadResponse
from app.schemas.candidate import (
    CandidateCreate,
    CandidateDetailResponse,
    CandidateResponse,
    CandidateUpdate,
)
from app.schemas.pagination import PaginatedResponse
from app.services import candidate_service, resume_service

router = APIRouter()


@router.get("", response_model=PaginatedResponse[CandidateResponse])
async def list_candidates(
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: Recruiter = Depends(get_current_recruiter),
):
    candidates, next_cursor, has_more = await candidate_service.list_candidates(
        db, current_user.id, cursor=cursor, limit=limit
    )
    return PaginatedResponse(data=candidates, next_cursor=next_cursor, has_more=has_more)


@router.post("", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    data: CandidateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Recruiter = Depends(get_current_recruiter),
):
    return await candidate_service.create_candidate(db, current_user.id, data)


@router.get("/{candidate_id}", response_model=CandidateDetailResponse)
async def get_candidate(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Recruiter = Depends(get_current_recruiter),
):
    candidate, app_dicts = await candidate_service.get_candidate_with_applications(
        db, candidate_id, current_user.id
    )
    data = CandidateDetailResponse.model_validate(candidate)
    data.applications = [ApplicationSummaryResponse.model_validate(d) for d in app_dicts]
    return data


@router.put("/{candidate_id}", response_model=CandidateResponse)
async def update_candidate(
    candidate_id: UUID,
    data: CandidateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Recruiter = Depends(get_current_recruiter),
):
    return await candidate_service.update_candidate(db, candidate_id, current_user.id, data)


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_candidate(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Recruiter = Depends(get_current_recruiter),
):
    await candidate_service.delete_candidate(db, candidate_id, current_user.id)


@router.post("/{candidate_id}/resume", response_model=ResumeUploadResponse)
async def upload_resume(
    candidate_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: Recruiter = Depends(get_current_recruiter),
):
    candidate = await candidate_service.get_candidate(db, candidate_id, current_user.id)
    file_bytes = await file.read()
    result = await resume_service.upload_and_analyze(
        db, candidate, file_bytes, file.filename or "resume.pdf"
    )
    return ResumeUploadResponse(**result)


@router.post("/{candidate_id}/applications", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    candidate_id: UUID,
    data: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Recruiter = Depends(get_current_recruiter),
):
    return await candidate_service.create_application(
        db, candidate_id, current_user.id, data.job_id
    )
