import uuid
from sqlalchemy import Column, Integer, Text, CheckConstraint, UniqueConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, JSONB
from sqlalchemy import Enum as SAEnum
from sqlalchemy.sql import func
from app.models.base import Base

application_status_enum = SAEnum(
    "applied", "screened", "interviewed", "rejected", "hired",
    name="application_status_enum",
    create_type=False,
)


class CandidateJobApplication(Base):
    __tablename__ = "candidate_job_applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    status = Column(application_status_enum, nullable=False, server_default="applied")
    fit_score = Column(Integer)
    fit_explanation = Column(Text)
    ai_parsed_resume = Column(JSONB)
    interview_notes = Column(Text)
    applied_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("fit_score BETWEEN 0 AND 100", name="chk_fit_score_range"),
        UniqueConstraint("candidate_id", "job_id", name="uq_candidate_job"),
    )
