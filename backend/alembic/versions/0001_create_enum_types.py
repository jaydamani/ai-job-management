"""create enum types

Revision ID: 0001
Revises:
Create Date: 2026-06-24

"""
from typing import Sequence, Union
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE employment_type_enum AS ENUM ('full_time', 'part_time', 'contract', 'internship')")
    op.execute("CREATE TYPE experience_level_enum AS ENUM ('junior', 'mid', 'senior', 'lead')")
    op.execute("CREATE TYPE remote_type_enum AS ENUM ('onsite', 'hybrid', 'remote')")
    op.execute("CREATE TYPE job_status_enum AS ENUM ('open', 'closed')")
    op.execute("CREATE TYPE application_status_enum AS ENUM ('applied', 'screened', 'interviewed', 'rejected', 'hired')")


def downgrade() -> None:
    op.execute("DROP TYPE IF EXISTS application_status_enum")
    op.execute("DROP TYPE IF EXISTS job_status_enum")
    op.execute("DROP TYPE IF EXISTS remote_type_enum")
    op.execute("DROP TYPE IF EXISTS experience_level_enum")
    op.execute("DROP TYPE IF EXISTS employment_type_enum")
