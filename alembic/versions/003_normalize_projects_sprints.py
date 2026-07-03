"""Normalize jira_stories into projects and sprints lookup tables."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_normalize_projects_sprints"
down_revision: Union[str, None] = "002_rovo_fields_and_title"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("project_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_key", sa.String(length=50), nullable=False),
        sa.Column("project_name", sa.String(length=200), nullable=False),
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
        sa.PrimaryKeyConstraint("project_id"),
        sa.UniqueConstraint("project_key"),
    )
    op.create_index("ix_projects_project_key", "projects", ["project_key"])

    op.create_table(
        "sprints",
        sa.Column("sprint_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("sprint_name", sa.String(length=200), nullable=False),
        sa.Column("sprint_start_date", sa.Date(), nullable=True),
        sa.Column("sprint_end_date", sa.Date(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.project_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("sprint_id"),
        sa.UniqueConstraint(
            "project_id",
            "sprint_name",
            name="uq_sprints_project_name",
        ),
    )
    op.create_index("ix_sprints_project_id", "sprints", ["project_id"])

    op.add_column("jira_stories", sa.Column("project_id", sa.Integer(), nullable=True))
    op.add_column("jira_stories", sa.Column("sprint_id", sa.Integer(), nullable=True))

    op.execute(
        """
        INSERT INTO projects (project_key, project_name)
        SELECT DISTINCT
            COALESCE(NULLIF(TRIM(project_key), ''), TRIM(project_name)) AS project_key,
            project_name
        FROM jira_stories
        ON CONFLICT (project_key) DO NOTHING
        """
    )

    op.execute(
        """
        UPDATE projects p
        SET project_name = sub.project_name
        FROM (
            SELECT
                COALESCE(NULLIF(TRIM(project_key), ''), TRIM(project_name)) AS project_key,
                MAX(project_name) AS project_name
            FROM jira_stories
            GROUP BY 1
        ) sub
        WHERE p.project_key = sub.project_key
          AND p.project_name IS DISTINCT FROM sub.project_name
        """
    )

    op.execute(
        """
        UPDATE jira_stories js
        SET project_id = p.project_id
        FROM projects p
        WHERE p.project_key = COALESCE(NULLIF(TRIM(js.project_key), ''), TRIM(js.project_name))
        """
    )

    op.execute(
        """
        INSERT INTO sprints (project_id, sprint_name, sprint_start_date, sprint_end_date)
        SELECT DISTINCT
            js.project_id,
            TRIM(js.sprint_name),
            js.sprint_start_date,
            js.sprint_end_date
        FROM jira_stories js
        WHERE js.sprint_name IS NOT NULL
          AND TRIM(js.sprint_name) <> ''
          AND js.project_id IS NOT NULL
        ON CONFLICT ON CONSTRAINT uq_sprints_project_name DO NOTHING
        """
    )

    op.execute(
        """
        UPDATE sprints sp
        SET
            sprint_start_date = COALESCE(sp.sprint_start_date, sub.sprint_start_date),
            sprint_end_date = COALESCE(sp.sprint_end_date, sub.sprint_end_date)
        FROM (
            SELECT
                js.project_id,
                TRIM(js.sprint_name) AS sprint_name,
                MAX(js.sprint_start_date) AS sprint_start_date,
                MAX(js.sprint_end_date) AS sprint_end_date
            FROM jira_stories js
            WHERE js.sprint_name IS NOT NULL
              AND TRIM(js.sprint_name) <> ''
            GROUP BY js.project_id, TRIM(js.sprint_name)
        ) sub
        WHERE sp.project_id = sub.project_id
          AND sp.sprint_name = sub.sprint_name
        """
    )

    op.execute(
        """
        UPDATE jira_stories js
        SET sprint_id = sp.sprint_id
        FROM sprints sp
        WHERE js.project_id = sp.project_id
          AND TRIM(js.sprint_name) = sp.sprint_name
          AND js.sprint_name IS NOT NULL
          AND TRIM(js.sprint_name) <> ''
        """
    )

    op.alter_column("jira_stories", "project_id", nullable=False)
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

    op.drop_index("ix_jira_stories_project_key", table_name="jira_stories")
    op.drop_index("ix_jira_stories_project_name", table_name="jira_stories")
    op.drop_index("ix_jira_stories_sprint_name", table_name="jira_stories")
    op.drop_column("jira_stories", "project_key")
    op.drop_column("jira_stories", "project_name")
    op.drop_column("jira_stories", "sprint_name")
    op.drop_column("jira_stories", "sprint_start_date")
    op.drop_column("jira_stories", "sprint_end_date")


def downgrade() -> None:
    op.add_column(
        "jira_stories",
        sa.Column("sprint_end_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "jira_stories",
        sa.Column("sprint_start_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "jira_stories",
        sa.Column("sprint_name", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "jira_stories",
        sa.Column("project_name", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "jira_stories",
        sa.Column("project_key", sa.String(length=50), nullable=True),
    )

    op.execute(
        """
        UPDATE jira_stories js
        SET
            project_key = p.project_key,
            project_name = p.project_name,
            sprint_name = sp.sprint_name,
            sprint_start_date = sp.sprint_start_date,
            sprint_end_date = sp.sprint_end_date
        FROM projects p
        LEFT JOIN sprints sp ON sp.sprint_id = js.sprint_id
        WHERE js.project_id = p.project_id
        """
    )

    op.alter_column("jira_stories", "project_name", nullable=False)

    op.drop_constraint("fk_jira_stories_sprint_id", "jira_stories", type_="foreignkey")
    op.drop_constraint("fk_jira_stories_project_id", "jira_stories", type_="foreignkey")
    op.drop_index("ix_jira_stories_sprint_id", table_name="jira_stories")
    op.drop_index("ix_jira_stories_project_id", table_name="jira_stories")
    op.drop_column("jira_stories", "sprint_id")
    op.drop_column("jira_stories", "project_id")

    op.create_index("ix_jira_stories_sprint_name", "jira_stories", ["sprint_name"])
    op.create_index("ix_jira_stories_project_name", "jira_stories", ["project_name"])
    op.create_index("ix_jira_stories_project_key", "jira_stories", ["project_key"])

    op.drop_index("ix_sprints_project_id", table_name="sprints")
    op.drop_table("sprints")
    op.drop_index("ix_projects_project_key", table_name="projects")
    op.drop_table("projects")
