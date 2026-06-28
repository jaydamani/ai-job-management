"""move resume_s3_key from candidates to candidate_job_applications

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-28

"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "candidate_job_applications",
        sa.Column("resume_s3_key", sa.Text, nullable=True),
    )
    op.drop_column("candidates", "resume_s3_key")


def downgrade() -> None:
    op.add_column(
        "candidates",
        sa.Column("resume_s3_key", sa.Text, nullable=True),
    )
    op.drop_column("candidate_job_applications", "resume_s3_key")
