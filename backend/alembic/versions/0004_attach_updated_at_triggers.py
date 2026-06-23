"""attach updated_at triggers

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-24

"""
from typing import Sequence, Union
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TRIGGER trg_jobs_updated_at
            BEFORE UPDATE ON jobs
            FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """)
    op.execute("""
        CREATE TRIGGER trg_candidates_updated_at
            BEFORE UPDATE ON candidates
            FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """)
    op.execute("""
        CREATE TRIGGER trg_apps_updated_at
            BEFORE UPDATE ON candidate_job_applications
            FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_apps_updated_at ON candidate_job_applications")
    op.execute("DROP TRIGGER IF EXISTS trg_candidates_updated_at ON candidates")
    op.execute("DROP TRIGGER IF EXISTS trg_jobs_updated_at ON jobs")
