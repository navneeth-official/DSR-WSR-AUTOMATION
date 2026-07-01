"""Align jira_stories columns with Rovo JSON fields and add title."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_rovo_fields_and_title"
down_revision: Union[str, None] = "001_create_jira_stories"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jira_stories", sa.Column("project_key", sa.String(length=50), nullable=True))
    op.add_column(
        "jira_stories",
        sa.Column("sprint_start_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "jira_stories",
        sa.Column("sprint_end_date", sa.Date(), nullable=True),
    )
    op.add_column("jira_stories", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "jira_stories",
        sa.Column("issue_type", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "jira_stories",
        sa.Column("priority", sa.String(length=50), nullable=True),
    )
    op.add_column("jira_stories", sa.Column("updated_date", sa.Date(), nullable=True))
    op.add_column("jira_stories", sa.Column("resolved_date", sa.Date(), nullable=True))
    op.add_column("jira_stories", sa.Column("snapshot_date", sa.Date(), nullable=True))
    op.add_column(
        "jira_stories",
        sa.Column("title", sa.String(length=500), nullable=True),
    )

    op.alter_column("jira_stories", "track", new_column_name="project_name")
    op.alter_column("jira_stories", "sprint", new_column_name="sprint_name")
    op.alter_column("jira_stories", "date_assigned", new_column_name="created_date")
    op.alter_column("jira_stories", "reportee", new_column_name="reporter")

    op.drop_index("ix_jira_stories_sprint", table_name="jira_stories")
    op.drop_index("ix_jira_stories_track", table_name="jira_stories")
    op.create_index("ix_jira_stories_sprint_name", "jira_stories", ["sprint_name"])
    op.create_index("ix_jira_stories_project_name", "jira_stories", ["project_name"])
    op.create_index("ix_jira_stories_project_key", "jira_stories", ["project_key"])


def downgrade() -> None:
    op.drop_index("ix_jira_stories_project_key", table_name="jira_stories")
    op.drop_index("ix_jira_stories_project_name", table_name="jira_stories")
    op.drop_index("ix_jira_stories_sprint_name", table_name="jira_stories")

    op.alter_column("jira_stories", "project_name", new_column_name="track")
    op.alter_column("jira_stories", "sprint_name", new_column_name="sprint")
    op.alter_column("jira_stories", "created_date", new_column_name="date_assigned")
    op.alter_column("jira_stories", "reporter", new_column_name="reportee")

    op.create_index("ix_jira_stories_sprint", "jira_stories", ["sprint"])
    op.create_index("ix_jira_stories_track", "jira_stories", ["track"])

    op.drop_column("jira_stories", "title")
    op.drop_column("jira_stories", "snapshot_date")
    op.drop_column("jira_stories", "resolved_date")
    op.drop_column("jira_stories", "updated_date")
    op.drop_column("jira_stories", "priority")
    op.drop_column("jira_stories", "issue_type")
    op.drop_column("jira_stories", "description")
    op.drop_column("jira_stories", "sprint_end_date")
    op.drop_column("jira_stories", "sprint_start_date")
    op.drop_column("jira_stories", "project_key")
