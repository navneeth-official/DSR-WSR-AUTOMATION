"""Remove project_id from sprints; one global row per sprint name."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_sprint_without_project"
down_revision: Union[str, None] = "003_normalize_projects_sprints"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Merge duplicate sprint names (same name under different projects → one sprint_id).
    op.execute(
        """
        WITH canonical AS (
            SELECT sprint_name, MIN(sprint_id) AS keep_id
            FROM sprints
            GROUP BY sprint_name
        ),
        duplicates AS (
            SELECT s.sprint_id AS drop_id, c.keep_id
            FROM sprints s
            JOIN canonical c ON c.sprint_name = s.sprint_name
            WHERE s.sprint_id <> c.keep_id
        )
        UPDATE jira_stories js
        SET sprint_id = d.keep_id
        FROM duplicates d
        WHERE js.sprint_id = d.drop_id
        """
    )

    op.execute(
        """
        DELETE FROM sprints s
        USING (
            SELECT sprint_name, MIN(sprint_id) AS keep_id
            FROM sprints
            GROUP BY sprint_name
        ) c
        WHERE s.sprint_name = c.sprint_name
          AND s.sprint_id <> c.keep_id
        """
    )

    op.drop_constraint("uq_sprints_project_name", "sprints", type_="unique")
    op.drop_index("ix_sprints_project_id", table_name="sprints")
    op.drop_constraint("sprints_project_id_fkey", "sprints", type_="foreignkey")
    op.drop_column("sprints", "project_id")

    op.create_unique_constraint("uq_sprints_sprint_name", "sprints", ["sprint_name"])
    op.create_index("ix_sprints_sprint_name", "sprints", ["sprint_name"])


def downgrade() -> None:
    op.drop_index("ix_sprints_sprint_name", table_name="sprints")
    op.drop_constraint("uq_sprints_sprint_name", "sprints", type_="unique")

    op.add_column(
        "sprints",
        sa.Column("project_id", sa.Integer(), nullable=True),
    )

    op.execute(
        """
        UPDATE sprints sp
        SET project_id = sub.project_id
        FROM (
            SELECT DISTINCT ON (js.sprint_id)
                js.sprint_id,
                js.project_id
            FROM jira_stories js
            WHERE js.sprint_id IS NOT NULL
            ORDER BY js.sprint_id, js.project_id
        ) sub
        WHERE sp.sprint_id = sub.sprint_id
        """
    )

    op.execute(
        """
        UPDATE sprints
        SET project_id = (SELECT MIN(project_id) FROM projects)
        WHERE project_id IS NULL
        """
    )

    op.alter_column("sprints", "project_id", nullable=False)
    op.create_foreign_key(
        "sprints_project_id_fkey",
        "sprints",
        "projects",
        ["project_id"],
        ["project_id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_sprints_project_id", "sprints", ["project_id"])
    op.create_unique_constraint(
        "uq_sprints_project_name",
        "sprints",
        ["project_id", "sprint_name"],
    )
