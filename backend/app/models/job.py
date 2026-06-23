import uuid
from sqlalchemy import Column, Text, Integer, ARRAY, String, CheckConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMPTZ
from sqlalchemy import Enum as SAEnum
from sqlalchemy.sql import func
from app.models.base import Base

employment_type_enum = SAEnum(
    "full_time", "part_time", "contract", "internship",
    name="employment_type_enum",
    create_type=False,
)
experience_level_enum = SAEnum(
    "junior", "mid", "senior", "lead",
    name="experience_level_enum",
    create_type=False,
)
remote_type_enum = SAEnum(
    "onsite", "hybrid", "remote",
    name="remote_type_enum",
    create_type=False,
)
job_status_enum = SAEnum(
    "open", "closed",
    name="job_status_enum",
    create_type=False,
)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recruiter_id = Column(UUID(as_uuid=True), ForeignKey("recruiters.id", ondelete="CASCADE"), nullable=False)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    department = Column(Text)
    location = Column(Text)
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    required_skills = Column(ARRAY(String), nullable=False, server_default="{}")
    employment_type = Column(employment_type_enum)
    experience_level = Column(experience_level_enum)
    remote_type = Column(remote_type_enum)
    status = Column(job_status_enum, nullable=False, server_default="open")
    created_at = Column(TIMESTAMPTZ, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMPTZ, nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max",
            name="chk_salary_range",
        ),
    )
