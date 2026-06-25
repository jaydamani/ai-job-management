from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ApplicationCreate(BaseModel):
    job_id: UUID


class StatusUpdate(BaseModel):
    status: str


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    candidate_id: UUID
    job_id: UUID
    status: str
    fit_score: Optional[int] = None
    fit_explanation: Optional[str] = None
    ai_parsed_resume: Optional[Dict[str, Any]] = None
    interview_notes: Optional[str] = None
    applied_at: datetime
    updated_at: datetime


class ApplicationSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    job_title: Optional[str] = None
    status: str
    fit_score: Optional[int] = None
    fit_explanation: Optional[str] = None
    applied_at: datetime
    updated_at: datetime


class ResumeUploadResponse(BaseModel):
    resume_url: str
    ai_status: str
    parsed_resume: Optional[Dict[str, Any]] = None
    fit_score: Optional[int] = None
    fit_explanation: Optional[str] = None
