"""initial schema

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-24

"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "recruiters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.Text, nullable=False, unique=True),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_recruiters_email", "recruiters", ["email"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("recruiter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recruiters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.Text, nullable=False),
        sa.Column("expires_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_refresh_tokens_recruiter", "refresh_tokens", ["recruiter_id"])
    op.create_index("idx_refresh_tokens_lookup", "refresh_tokens", ["recruiter_id", "revoked", "expires_at"])

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("recruiter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recruiters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("department", sa.Text),
        sa.Column("location", sa.Text),
        sa.Column("salary_min", sa.Integer),
        sa.Column("salary_max", sa.Integer),
        sa.Column("required_skills", postgresql.ARRAY(sa.String), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("employment_type", sa.Enum("full_time", "part_time", "contract", "internship", name="employment_type_enum")),
        sa.Column("experience_level", sa.Enum("junior", "mid", "senior", "lead", name="experience_level_enum")),
        sa.Column("remote_type", sa.Enum("onsite", "hybrid", "remote", name="remote_type_enum")),
        sa.Column("status", sa.Enum("open", "closed", name="job_status_enum"), nullable=False, server_default=sa.text("'open'")),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max", name="chk_salary_range"),
    )
    op.create_index("idx_jobs_recruiter_status", "jobs", ["recruiter_id", "status"])
    op.create_index("idx_jobs_title_trgm", "jobs", ["title"], postgresql_using="gin", postgresql_ops={"title": "gin_trgm_ops"})
    op.create_index("idx_jobs_skills_gin", "jobs", ["required_skills"], postgresql_using="gin")

    op.create_table(
        "candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("recruiter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recruiters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("email", sa.Text, nullable=False),
        sa.Column("phone", sa.Text),
        sa.Column("location_preference", sa.Text),
        sa.Column("linkedin_url", sa.Text),
        sa.Column("portfolio_url", sa.Text),
        sa.Column("github_url", sa.Text),
        sa.Column("expected_salary_min", sa.Integer),
        sa.Column("expected_salary_max", sa.Integer),
        sa.Column("notice_period_days", sa.Integer),
        sa.Column("earliest_joining_date", sa.Date),
        sa.Column("source", sa.Text),
        sa.Column("referred_by", sa.Text),
        sa.Column("notes", sa.Text),
        sa.Column("resume_s3_key", sa.Text),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint(
            "expected_salary_min IS NULL OR expected_salary_max IS NULL OR expected_salary_min <= expected_salary_max",
            name="chk_expected_salary",
        ),
        sa.CheckConstraint("notice_period_days IS NULL OR notice_period_days >= 0", name="chk_notice_period"),
    )
    op.create_index("idx_candidates_recruiter", "candidates", ["recruiter_id"])
    op.create_index("idx_candidates_email_recruiter", "candidates", ["recruiter_id", "email"], unique=True)

    op.create_table(
        "candidate_job_applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.Enum("applied", "screened", "interviewed", "rejected", "hired", name="application_status_enum"), nullable=False, server_default=sa.text("'applied'")),
        sa.Column("fit_score", sa.Integer, sa.CheckConstraint("fit_score BETWEEN 0 AND 100", name="chk_fit_score_range")),
        sa.Column("fit_explanation", sa.Text),
        sa.Column("ai_parsed_resume", postgresql.JSONB),
        sa.Column("interview_notes", sa.Text),
        sa.Column("applied_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("candidate_id", "job_id", name="uq_candidate_job"),
    )
    op.create_index("idx_apps_job_fitscore", "candidate_job_applications", ["job_id", sa.text("fit_score DESC NULLS LAST")])
    op.create_index("idx_apps_candidate", "candidate_job_applications", ["candidate_id"])
    op.create_index("idx_apps_parsed_resume_gin", "candidate_job_applications", ["ai_parsed_resume"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_table("candidate_job_applications")
    op.drop_table("candidates")
    op.drop_table("jobs")
    op.drop_table("refresh_tokens")
    op.drop_table("recruiters")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute("DROP TYPE IF EXISTS application_status_enum")
    op.execute("DROP TYPE IF EXISTS job_status_enum")
    op.execute("DROP TYPE IF EXISTS remote_type_enum")
    op.execute("DROP TYPE IF EXISTS experience_level_enum")
    op.execute("DROP TYPE IF EXISTS employment_type_enum")
