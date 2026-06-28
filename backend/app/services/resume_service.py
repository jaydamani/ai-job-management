import logging
import uuid
from typing import Any, Dict, List, Optional

import magic
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.application import CandidateJobApplication
from app.models.job import Job
from app.services import ai_service, storage_service

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


async def upload_and_analyze(
    db: AsyncSession,
    candidate: Candidate,
    file_bytes: bytes,
    filename: str,
    application_id: Optional[uuid.UUID] = None,
) -> Dict[str, Any]:
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 5 MB)")

    mime = magic.from_buffer(file_bytes, mime=True)
    if mime != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    s3_key = storage_service.upload_resume(file_bytes, str(candidate.id))
    resume_url = storage_service.get_presigned_url(s3_key)

    if application_id:
        app_res = await db.execute(
            select(CandidateJobApplication).where(
                CandidateJobApplication.id == application_id,
                CandidateJobApplication.candidate_id == candidate.id,
            )
        )
        upload_app = app_res.scalar_one_or_none()
        if upload_app:
            upload_app.resume_s3_key = s3_key
    await db.commit()

    parsed_resume: Optional[Dict[str, Any]] = None
    ai_status = "failed"
    last_fit_score = None
    last_fit_explanation = None
    last_strengths: Optional[List[str]] = None
    last_gaps: Optional[List[str]] = None

    try:
        parsed_resume = await ai_service.parse_resume(file_bytes)
        ai_status = "complete"
    except ValueError as e:
        if "UNSCANNABLE_PDF" in str(e):
            raise HTTPException(
                status_code=422,
                detail={"error_code": "UNSCANNABLE_PDF", "message": "Cannot extract text from this PDF"},
            )
        logger.warning("Resume parse failed for candidate %s: %s", candidate.id, e)
    except Exception as e:
        logger.warning("Resume parse failed for candidate %s: %s", candidate.id, e)

    if parsed_resume:
        query = (
            select(CandidateJobApplication, Job)
            .join(Job, CandidateJobApplication.job_id == Job.id)
            .where(CandidateJobApplication.candidate_id == candidate.id)
        )
        if application_id:
            query = query.where(CandidateJobApplication.id == application_id)
        query = query.order_by(CandidateJobApplication.applied_at.desc())
        result = await db.execute(query)
        rows = result.all()

        for app, job in rows:
            try:
                fit_result = await ai_service.score_fit(job, parsed_resume)
                app.ai_parsed_resume = parsed_resume
                app.fit_score = fit_result.get("score")
                app.fit_explanation = fit_result.get("explanation")
                app.strengths = fit_result.get("strengths")
                app.gaps = fit_result.get("gaps")
                app.ai_status = "complete"
                last_fit_score = app.fit_score
                last_fit_explanation = app.fit_explanation
                last_strengths = app.strengths
                last_gaps = app.gaps
            except Exception as e:
                logger.warning("Fit scoring failed for application %s: %s", app.id, e)
                app.ai_parsed_resume = parsed_resume
                app.ai_status = "failed"

        await db.commit()

    return {
        "resume_url": resume_url,
        "ai_status": ai_status,
        "ai_parsed_resume": parsed_resume,
        "fit_score": last_fit_score,
        "fit_explanation": last_fit_explanation,
        "strengths": last_strengths,
        "gaps": last_gaps,
    }
