"""Create jira_stories table."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_create_jira_stories"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jira_stories",
        sa.Column("jira_key", sa.String(length=50), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("track", sa.String(length=200), nullable=False),
        sa.Column("sprint", sa.String(length=200), nullable=True),
        sa.Column("date_assigned", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=100), nullable=False),
        sa.Column("story_points", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column(
            "completion",
            sa.Numeric(precision=5, scale=2),
            nullable=True,
            comment="Story completion percentage (0-100)",
        ),
        sa.Column("assignee", sa.String(length=200), nullable=True),
        sa.Column("reportee", sa.String(length=200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("jira_key"),
    )

    op.create_index("ix_jira_stories_assignee", "jira_stories", ["assignee"])
    op.create_index("ix_jira_stories_sprint", "jira_stories", ["sprint"])
    op.create_index("ix_jira_stories_status", "jira_stories", ["status"])
    op.create_index("ix_jira_stories_track", "jira_stories", ["track"])


def downgrade() -> None:
    op.drop_index("ix_jira_stories_track", table_name="jira_stories")
    op.drop_index("ix_jira_stories_status", table_name="jira_stories")
    op.drop_index("ix_jira_stories_sprint", table_name="jira_stories")
    op.drop_index("ix_jira_stories_assignee", table_name="jira_stories")
    op.drop_table("jira_stories")
