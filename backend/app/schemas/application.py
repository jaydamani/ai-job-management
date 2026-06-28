from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    strengths: Optional[List[str]] = None
    gaps: Optional[List[str]] = None
    ai_status: Optional[str] = None
    resume_s3_key: Optional[str] = Field(default=None, exclude=True)
    resume_url: Optional[str] = None
    applied_at: datetime
    updated_at: datetime

    @model_validator(mode='after')
    def set_resume_url(self) -> 'ApplicationResponse':
        if self.resume_s3_key and self.resume_url is None:
            from app.services.storage_service import get_presigned_url
            self.resume_url = get_presigned_url(self.resume_s3_key)
        return self


class ApplicationSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    job_title: Optional[str] = None
    status: str
    fit_score: Optional[int] = None
    fit_explanation: Optional[str] = None
    resume_s3_key: Optional[str] = Field(default=None, exclude=True)
    resume_url: Optional[str] = None
    applied_at: datetime
    updated_at: datetime

    @model_validator(mode='after')
    def set_resume_url(self) -> 'ApplicationSummaryResponse':
        if self.resume_s3_key and self.resume_url is None:
            from app.services.storage_service import get_presigned_url
            self.resume_url = get_presigned_url(self.resume_s3_key)
        return self


class ResumeUploadResponse(BaseModel):
    resume_url: str
    ai_status: str
    ai_parsed_resume: Optional[Dict[str, Any]] = None
    fit_score: Optional[int] = None
    fit_explanation: Optional[str] = None
    strengths: Optional[List[str]] = None
    gaps: Optional[List[str]] = None


class RescoreResponse(BaseModel):
    ai_status: str
    ai_parsed_resume: Optional[Dict[str, Any]] = None
    fit_score: Optional[int] = None
    fit_explanation: Optional[str] = None
    strengths: Optional[List[str]] = None
    gaps: Optional[List[str]] = None
