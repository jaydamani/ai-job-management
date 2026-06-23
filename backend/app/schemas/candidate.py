from datetime import date, datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict

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
    resume_s3_key: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CandidateDetailResponse(CandidateResponse):
    applications: List[ApplicationSummaryResponse] = []


class CandidateWithApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: str
    phone: Optional[str] = None
    resume_s3_key: Optional[str] = None
    application_id: UUID
    application_status: str
    fit_score: Optional[int] = None
    fit_explanation: Optional[str] = None
    applied_at: datetime
