import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.application import CandidateJobApplication
from app.models.job import Job
from app.schemas.candidate import CandidateCreate, CandidateUpdate
from app.schemas.pagination import decode_cursor, encode_cursor
from app.services.skill_taxonomy import normalize_skill_query

logger = logging.getLogger(__name__)

_MAX_BULK_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


async def create_candidate(
    db: AsyncSession, recruiter_id: uuid.UUID, data: CandidateCreate
) -> tuple:
    result = await db.execute(
        select(Candidate).where(
            Candidate.recruiter_id == recruiter_id,
            Candidate.email == data.email,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Candidate with this email already exists")

    candidate_fields = data.model_dump(exclude={'job_id'})
    candidate = Candidate(recruiter_id=recruiter_id, **candidate_fields)
    db.add(candidate)
    await db.flush()

    application_dict = None
    if data.job_id:
        job_result = await db.execute(
            select(Job).where(Job.id == data.job_id, Job.recruiter_id == recruiter_id)
        )
        job = job_result.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        application = CandidateJobApplication(candidate_id=candidate.id, job_id=data.job_id)
        db.add(application)
        await db.flush()
        application_dict = {
            "id": application.id,
            "job_id": application.job_id,
            "job_title": job.title,
            "status": application.status,
            "fit_score": application.fit_score,
            "fit_explanation": application.fit_explanation,
            "resume_s3_key": application.resume_s3_key,
            "applied_at": application.applied_at,
            "updated_at": application.updated_at,
        }

    await db.commit()
    await db.refresh(candidate)
    return candidate, [application_dict] if application_dict else []


async def get_candidate(
    db: AsyncSession, candidate_id: uuid.UUID, recruiter_id: uuid.UUID
) -> Candidate:
    result = await db.execute(
        select(Candidate).where(
            Candidate.id == candidate_id, Candidate.recruiter_id == recruiter_id
        )
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


async def get_candidate_with_applications(
    db: AsyncSession, candidate_id: uuid.UUID, recruiter_id: uuid.UUID
) -> tuple:
    candidate = await get_candidate(db, candidate_id, recruiter_id)
    result = await db.execute(
        select(CandidateJobApplication, Job.title.label("job_title"))
        .join(Job, CandidateJobApplication.job_id == Job.id)
        .where(CandidateJobApplication.candidate_id == candidate_id)
        .order_by(CandidateJobApplication.applied_at.desc())
    )
    applications = [
        {
            "id": app.id,
            "job_id": app.job_id,
            "job_title": job_title,
            "status": app.status,
            "fit_score": app.fit_score,
            "fit_explanation": app.fit_explanation,
            "strengths": app.strengths,
            "gaps": app.gaps,
            "ai_parsed_resume": app.ai_parsed_resume,
            "ai_status": app.ai_status,
            "resume_s3_key": app.resume_s3_key,
            "applied_at": app.applied_at,
            "updated_at": app.updated_at,
        }
        for app, job_title in result.all()
    ]
    return candidate, applications


async def list_candidates(
    db: AsyncSession,
    recruiter_id: uuid.UUID,
    cursor: Optional[str] = None,
    limit: int = 20,
) -> tuple:
    query = select(Candidate).where(Candidate.recruiter_id == recruiter_id)

    if cursor:
        parts = decode_cursor(cursor)
        cursor_ts = datetime.fromisoformat(parts[0])
        cursor_id = uuid.UUID(parts[1])
        query = query.where(
            or_(
                Candidate.created_at < cursor_ts,
                and_(Candidate.created_at == cursor_ts, Candidate.id < cursor_id),
            )
        )

    query = query.order_by(Candidate.created_at.desc(), Candidate.id.desc()).limit(limit + 1)
    result = await db.execute(query)
    candidates = list(result.scalars().all())

    has_more = len(candidates) > limit
    if has_more:
        candidates = candidates[:limit]

    next_cursor = None
    if has_more and candidates:
        last = candidates[-1]
        next_cursor = encode_cursor(last.created_at.isoformat(), str(last.id))

    return candidates, next_cursor, has_more


async def update_candidate(
    db: AsyncSession,
    candidate_id: uuid.UUID,
    recruiter_id: uuid.UUID,
    data: CandidateUpdate,
) -> Candidate:
    candidate = await get_candidate(db, candidate_id, recruiter_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(candidate, field, value)
    await db.commit()
    await db.refresh(candidate)
    return candidate


async def delete_candidate(
    db: AsyncSession, candidate_id: uuid.UUID, recruiter_id: uuid.UUID
) -> None:
    candidate = await get_candidate(db, candidate_id, recruiter_id)
    await db.delete(candidate)
    await db.commit()


async def create_application(
    db: AsyncSession,
    candidate_id: uuid.UUID,
    recruiter_id: uuid.UUID,
    job_id: uuid.UUID,
) -> CandidateJobApplication:
    await get_candidate(db, candidate_id, recruiter_id)

    job_result = await db.execute(
        select(Job).where(Job.id == job_id, Job.recruiter_id == recruiter_id)
    )
    if not job_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Job not found")

    existing = await db.execute(
        select(CandidateJobApplication).where(
            CandidateJobApplication.candidate_id == candidate_id,
            CandidateJobApplication.job_id == job_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Candidate already applied to this job")

    application = CandidateJobApplication(candidate_id=candidate_id, job_id=job_id)
    db.add(application)
    await db.commit()
    await db.refresh(application)
    return application


async def list_job_candidates(
    db: AsyncSession,
    job_id: uuid.UUID,
    recruiter_id: uuid.UUID,
    cursor: Optional[str] = None,
    limit: int = 20,
    pipeline_status: Optional[str] = None,
    min_score: Optional[int] = None,
    search: Optional[str] = None,
    search_resume: bool = False,
    min_experience: Optional[float] = None,
    skill: Optional[str] = None,
) -> tuple:
    job_result = await db.execute(
        select(Job).where(Job.id == job_id, Job.recruiter_id == recruiter_id)
    )
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    query = (
        select(CandidateJobApplication, Candidate)
        .join(Candidate, CandidateJobApplication.candidate_id == Candidate.id)
        .where(CandidateJobApplication.job_id == job_id)
    )

    if pipeline_status:
        query = query.where(CandidateJobApplication.status == pipeline_status)

    if min_score is not None:
        query = query.where(CandidateJobApplication.fit_score >= min_score)

    if search:
        pattern = f"%{search}%"
        conditions = [
            Candidate.name.ilike(pattern),
            Candidate.email == search,
            Candidate.phone.ilike(pattern),
        ]
        if search_resume:
            from sqlalchemy import cast, String
            conditions.append(cast(CandidateJobApplication.ai_parsed_resume, String).ilike(pattern))
        query = query.where(or_(*conditions))

    if min_experience is not None:
        from sqlalchemy import func, cast as sa_cast, Float
        query = query.where(
            sa_cast(
                func.jsonb_extract_path_text(CandidateJobApplication.ai_parsed_resume, "total_experience_years"),
                Float,
            ) >= min_experience
        )

    if skill:
        from sqlalchemy import func, text
        normalized_skill = normalize_skill_query(skill) or skill
        query = query.where(
            func.exists(
                text(
                    "SELECT 1 FROM jsonb_array_elements_text"
                    "(candidate_job_applications.ai_parsed_resume->'skills') AS s"
                    " WHERE lower(s) = lower(:skill_value)"
                ).bindparams(skill_value=normalized_skill)
            )
        )

    if cursor:
        parts = decode_cursor(cursor)
        score_str, ts_str, id_str = parts[0], parts[1], parts[2]
        cursor_ts = datetime.fromisoformat(ts_str)
        cursor_id = uuid.UUID(id_str)

        if score_str == "null":
            query = query.where(
                CandidateJobApplication.fit_score.is_(None),
                or_(
                    CandidateJobApplication.applied_at < cursor_ts,
                    and_(
                        CandidateJobApplication.applied_at == cursor_ts,
                        CandidateJobApplication.id < cursor_id,
                    ),
                ),
            )
        else:
            cursor_score = int(score_str)
            query = query.where(
                or_(
                    CandidateJobApplication.fit_score < cursor_score,
                    and_(
                        CandidateJobApplication.fit_score == cursor_score,
                        or_(
                            CandidateJobApplication.applied_at < cursor_ts,
                            and_(
                                CandidateJobApplication.applied_at == cursor_ts,
                                CandidateJobApplication.id < cursor_id,
                            ),
                        ),
                    ),
                    CandidateJobApplication.fit_score.is_(None),
                )
            )

    query = query.order_by(
        CandidateJobApplication.fit_score.desc().nulls_last(),
        CandidateJobApplication.applied_at.desc(),
        CandidateJobApplication.id.desc(),
    ).limit(limit + 1)

    result = await db.execute(query)
    rows = result.all()

    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]

    if not rows:
        return [], None, False

    items = []
    for app, candidate in rows:
        score_str = str(app.fit_score) if app.fit_score is not None else "null"
        items.append({
            "id": candidate.id,
            "name": candidate.name,
            "email": candidate.email,
            "phone": candidate.phone,
            "location_preference": candidate.location_preference,
            "linkedin_url": candidate.linkedin_url,
            "portfolio_url": candidate.portfolio_url,
            "github_url": candidate.github_url,
            "created_at": candidate.created_at,
            "application": {
                "id": app.id,
                "job_id": app.job_id,
                "job_title": job.title,
                "status": app.status,
                "fit_score": app.fit_score,
                "fit_explanation": app.fit_explanation,
                "strengths": app.strengths,
                "gaps": app.gaps,
                "ai_parsed_resume": app.ai_parsed_resume,
                "ai_status": app.ai_status,
                "resume_s3_key": app.resume_s3_key,
                "applied_at": app.applied_at,
            },
            "_cursor_parts": (score_str, app.applied_at.isoformat(), str(app.id)),
        })

    next_cursor = None
    if has_more and items:
        last = items[-1]
        next_cursor = encode_cursor(*last["_cursor_parts"])

    for item in items:
        del item["_cursor_parts"]

    return items, next_cursor, has_more


async def bulk_upload_resumes(
    db: AsyncSession,
    job_id: uuid.UUID,
    recruiter_id: uuid.UUID,
    files: list,
) -> list:
    from app.services import ai_service, storage_service
    import magic

    job_result = await db.execute(
        select(Job).where(Job.id == job_id, Job.recruiter_id == recruiter_id)
    )
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    results = []
    for file_bytes, filename in files:
        base = {"name": filename, "email": None, "candidate_id": None,
                "fit_score": None, "fit_explanation": None,
                "strengths": None, "gaps": None, "resume_url": None}
        try:
            if len(file_bytes) > _MAX_BULK_FILE_SIZE:
                results.append({**base, "status": "failed", "error": "File too large (max 5 MB)"})
                continue

            mime = magic.from_buffer(file_bytes, mime=True)
            if mime != "application/pdf":
                results.append({**base, "status": "failed", "error": "Only PDF files are accepted"})
                continue

            parsed_resume = await ai_service.parse_resume(file_bytes)
            name = (parsed_resume.get("name") or "").strip() or filename
            email = parsed_resume.get("email") or None
            base = {**base, "name": name, "email": email}

            # find or create candidate by email
            candidate = None
            if email:
                existing = await db.execute(
                    select(Candidate).where(
                        Candidate.recruiter_id == recruiter_id,
                        Candidate.email == email,
                    )
                )
                candidate = existing.scalar_one_or_none()

            if not candidate:
                fallback_email = email or f"bulk-{uuid.uuid4().hex[:8]}@noemail.local"
                candidate = Candidate(recruiter_id=recruiter_id, name=name, email=fallback_email)
                db.add(candidate)
                await db.flush()

            # find or create application
            existing_app = await db.execute(
                select(CandidateJobApplication).where(
                    CandidateJobApplication.candidate_id == candidate.id,
                    CandidateJobApplication.job_id == job_id,
                )
            )
            application = existing_app.scalar_one_or_none()
            if not application:
                application = CandidateJobApplication(candidate_id=candidate.id, job_id=job_id)
                db.add(application)
                await db.flush()

            s3_key = storage_service.upload_resume(file_bytes, str(candidate.id))
            resume_url = storage_service.get_presigned_url(s3_key)
            application.resume_s3_key = s3_key

            fit_result = await ai_service.score_fit(job, parsed_resume)
            application.ai_parsed_resume = parsed_resume
            application.fit_score = fit_result.get("score")
            application.fit_explanation = fit_result.get("explanation")
            application.strengths = fit_result.get("strengths")
            application.gaps = fit_result.get("gaps")
            application.ai_status = "complete"

            await db.commit()

            results.append({
                "candidate_id": candidate.id,
                "name": candidate.name,
                "email": candidate.email,
                "fit_score": application.fit_score,
                "fit_explanation": application.fit_explanation,
                "strengths": application.strengths,
                "gaps": application.gaps,
                "resume_url": resume_url,
                "status": "success",
                "error": None,
            })
        except Exception as e:
            await db.rollback()
            error_msg = str(e)
            if "UNSCANNABLE_PDF" in error_msg:
                error_msg = "Cannot extract text from this PDF"
            logger.warning("Bulk upload failed for %s: %s", filename, e)
            results.append({**base, "status": "failed", "error": error_msg})

    results.sort(key=lambda r: (r["status"] == "failed", -(r.get("fit_score") or 0)))
    return results
