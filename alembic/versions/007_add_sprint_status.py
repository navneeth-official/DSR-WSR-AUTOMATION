"""Add sprint_status column to sprints."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_add_sprint_status"
down_revision: Union[str, None] = "006_fix_jira_stories_pkey_name"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sprints",
        sa.Column(
            "sprint_status",
            sa.String(length=50),
            server_default="inprogress",
            nullable=False,
        ),
    )

    op.execute(
        """
        UPDATE sprints
        SET sprint_status = CASE
            WHEN sprint_end_date IS NOT NULL AND sprint_end_date < CURRENT_DATE THEN 'ended'
            WHEN sprint_id % 2 = 0 THEN 'ended'
            ELSE 'inprogress'
        END
        """
    )

    op.create_index("ix_sprints_sprint_status", "sprints", ["sprint_status"])


def downgrade() -> None:
    op.drop_index("ix_sprints_sprint_status", table_name="sprints")
    op.drop_column("sprints", "sprint_status")
