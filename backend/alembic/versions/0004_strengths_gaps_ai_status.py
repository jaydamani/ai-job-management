"""add strengths, gaps, ai_status to candidate_job_applications

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-28

"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("candidate_job_applications", sa.Column("strengths", postgresql.JSONB(), nullable=True))
    op.add_column("candidate_job_applications", sa.Column("gaps", postgresql.JSONB(), nullable=True))
    op.add_column("candidate_job_applications", sa.Column("ai_status", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("candidate_job_applications", "ai_status")
    op.drop_column("candidate_job_applications", "gaps")
    op.drop_column("candidate_job_applications", "strengths")
