from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.application import ApplicationSummaryResponse


class CandidateCreate(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    location_preference: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    github_url: Optional[str] = None
    expected_salary_min: Optional[int] = None
    expected_salary_max: Optional[int] = None
    notice_period_days: Optional[int] = None
    earliest_joining_date: Optional[date] = None
    source: Optional[str] = None
    referred_by: Optional[str] = None
    notes: Optional[str] = None
    job_id: Optional[UUID] = None


class CandidateUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location_preference: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    github_url: Optional[str] = None
    expected_salary_min: Optional[int] = None
    expected_salary_max: Optional[int] = None
    notice_period_days: Optional[int] = None
    earliest_joining_date: Optional[date] = None
    source: Optional[str] = None
    referred_by: Optional[str] = None
    notes: Optional[str] = None


class CandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recruiter_id: UUID
    name: str
    email: str
    phone: Optional[str] = None
    location_preference: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    github_url: Optional[str] = None
    expected_salary_min: Optional[int] = None
    expected_salary_max: Optional[int] = None
    notice_period_days: Optional[int] = None
    earliest_joining_date: Optional[date] = None
    source: Optional[str] = None
    referred_by: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CandidateDetailResponse(CandidateResponse):
    applications: List[ApplicationSummaryResponse] = []


class ApplicationInCandidateList(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    job_title: Optional[str] = None
    status: str
    fit_score: Optional[int] = None
    fit_explanation: Optional[str] = None
    strengths: Optional[List[str]] = None
    gaps: Optional[List[str]] = None
    ai_parsed_resume: Optional[Dict[str, Any]] = None
    ai_status: Optional[str] = None
    resume_s3_key: Optional[str] = Field(default=None, exclude=True)
    resume_url: Optional[str] = None
    applied_at: datetime

    @model_validator(mode='after')
    def set_resume_url(self) -> 'ApplicationInCandidateList':
        if self.resume_s3_key and self.resume_url is None:
            from app.services.storage_service import get_presigned_url
            self.resume_url = get_presigned_url(self.resume_s3_key)
        return self


class CandidateWithApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: str
    phone: Optional[str] = None
    location_preference: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    github_url: Optional[str] = None
    created_at: datetime
    application: ApplicationInCandidateList


class BulkUploadItemResult(BaseModel):
    candidate_id: Optional[UUID] = None
    name: str
    email: Optional[str] = None
    fit_score: Optional[int] = None
    fit_explanation: Optional[str] = None
    strengths: Optional[List[str]] = None
    gaps: Optional[List[str]] = None
    resume_url: Optional[str] = None
    status: str
    error: Optional[str] = None


class BulkUploadResponse(BaseModel):
    results: List[BulkUploadItemResult]
    total: int
    succeeded: int
    failed: int
