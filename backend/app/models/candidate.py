import uuid
from sqlalchemy import Column, Text, Integer, Date, CheckConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMPTZ
from sqlalchemy.sql import func
from app.models.base import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recruiter_id = Column(UUID(as_uuid=True), ForeignKey("recruiters.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    email = Column(Text, nullable=False)
    phone = Column(Text)
    location_preference = Column(Text)
    linkedin_url = Column(Text)
    portfolio_url = Column(Text)
    github_url = Column(Text)
    expected_salary_min = Column(Integer)
    expected_salary_max = Column(Integer)
    notice_period_days = Column(Integer)
    earliest_joining_date = Column(Date)
    source = Column(Text)
    referred_by = Column(Text)
    notes = Column(Text)
    resume_s3_key = Column(Text)
    created_at = Column(TIMESTAMPTZ, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMPTZ, nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "expected_salary_min IS NULL OR expected_salary_max IS NULL OR expected_salary_min <= expected_salary_max",
            name="chk_expected_salary",
        ),
        CheckConstraint(
            "notice_period_days IS NULL OR notice_period_days >= 0",
            name="chk_notice_period",
        ),
    )
