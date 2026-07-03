"""Reorder jira_stories columns for pgAdmin readability."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_reorder_jira_stories_columns"
down_revision: Union[str, None] = "004_sprint_without_project"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("fk_jira_stories_project_id", "jira_stories", type_="foreignkey")
    op.drop_constraint("fk_jira_stories_sprint_id", "jira_stories", type_="foreignkey")
    op.drop_index("ix_jira_stories_project_id", table_name="jira_stories")
    op.drop_index("ix_jira_stories_sprint_id", table_name="jira_stories")
    op.drop_index("ix_jira_stories_assignee", table_name="jira_stories")
    op.drop_index("ix_jira_stories_status", table_name="jira_stories")

    op.create_table(
        "jira_stories_new",
        sa.Column("jira_key", sa.String(length=50), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("sprint_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("story_points", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("status", sa.String(length=100), nullable=False),
        sa.Column("assignee", sa.String(length=200), nullable=True),
        sa.Column("reporter", sa.String(length=200), nullable=True),
        sa.Column("issue_type", sa.String(length=100), nullable=True),
        sa.Column("priority", sa.String(length=50), nullable=True),
        sa.Column("completion", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("created_date", sa.Date(), nullable=True),
        sa.Column("updated_date", sa.Date(), nullable=True),
        sa.Column("resolved_date", sa.Date(), nullable=True),
        sa.Column("snapshot_date", sa.Date(), nullable=True),
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

    op.execute(
        """
        INSERT INTO jira_stories_new (
            jira_key, project_id, sprint_id, title, summary, description,
            story_points, status, assignee, reporter, issue_type, priority,
            completion, created_date, updated_date, resolved_date, snapshot_date,
            created_at, updated_at
        )
        SELECT
            jira_key, project_id, sprint_id, title, summary, description,
            story_points, status, assignee, reporter, issue_type, priority,
            completion, created_date, updated_date, resolved_date, snapshot_date,
            created_at, updated_at
        FROM jira_stories
        """
    )

    op.drop_table("jira_stories")
    op.rename_table("jira_stories_new", "jira_stories")

    op.create_foreign_key(
        "fk_jira_stories_project_id",
        "jira_stories",
        "projects",
        ["project_id"],
        ["project_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_jira_stories_sprint_id",
        "jira_stories",
        "sprints",
        ["sprint_id"],
        ["sprint_id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_jira_stories_project_id", "jira_stories", ["project_id"])
    op.create_index("ix_jira_stories_sprint_id", "jira_stories", ["sprint_id"])
    op.create_index("ix_jira_stories_assignee", "jira_stories", ["assignee"])
    op.create_index("ix_jira_stories_status", "jira_stories", ["status"])


def downgrade() -> None:
    op.drop_constraint("fk_jira_stories_project_id", "jira_stories", type_="foreignkey")
    op.drop_constraint("fk_jira_stories_sprint_id", "jira_stories", type_="foreignkey")
    op.drop_index("ix_jira_stories_project_id", table_name="jira_stories")
    op.drop_index("ix_jira_stories_sprint_id", table_name="jira_stories")
    op.drop_index("ix_jira_stories_assignee", table_name="jira_stories")
    op.drop_index("ix_jira_stories_status", table_name="jira_stories")

    op.create_table(
        "jira_stories_old",
        sa.Column("jira_key", sa.String(length=50), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("sprint_id", sa.Integer(), nullable=True),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("issue_type", sa.String(length=100), nullable=True),
        sa.Column("priority", sa.String(length=50), nullable=True),
        sa.Column("assignee", sa.String(length=200), nullable=True),
        sa.Column("reporter", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=100), nullable=False),
        sa.Column("story_points", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("created_date", sa.Date(), nullable=True),
        sa.Column("updated_date", sa.Date(), nullable=True),
        sa.Column("resolved_date", sa.Date(), nullable=True),
        sa.Column("snapshot_date", sa.Date(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("completion", sa.Numeric(precision=5, scale=2), nullable=True),
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

    op.execute(
        """
        INSERT INTO jira_stories_old (
            jira_key, project_id, sprint_id, summary, description, issue_type,
            priority, assignee, reporter, status, story_points, created_date,
            updated_date, resolved_date, snapshot_date, title, completion,
            created_at, updated_at
        )
        SELECT
            jira_key, project_id, sprint_id, summary, description, issue_type,
            priority, assignee, reporter, status, story_points, created_date,
            updated_date, resolved_date, snapshot_date, title, completion,
            created_at, updated_at
        FROM jira_stories
        """
    )

    op.drop_table("jira_stories")
    op.rename_table("jira_stories_old", "jira_stories")

    op.create_foreign_key(
        "fk_jira_stories_project_id",
        "jira_stories",
        "projects",
        ["project_id"],
        ["project_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_jira_stories_sprint_id",
        "jira_stories",
        "sprints",
        ["sprint_id"],
        ["sprint_id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_jira_stories_project_id", "jira_stories", ["project_id"])
    op.create_index("ix_jira_stories_sprint_id", "jira_stories", ["sprint_id"])
    op.create_index("ix_jira_stories_assignee", "jira_stories", ["assignee"])
    op.create_index("ix_jira_stories_status", "jira_stories", ["status"])
