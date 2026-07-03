"""Rename jira_stories PK index after column reorder migration."""

from typing import Sequence, Union

from alembic import op

revision: str = "006_fix_jira_stories_pkey_name"
down_revision: Union[str, None] = "005_reorder_jira_stories_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER INDEX IF EXISTS jira_stories_new_pkey RENAME TO jira_stories_pkey")


def downgrade() -> None:
    op.execute("ALTER INDEX IF EXISTS jira_stories_pkey RENAME TO jira_stories_new_pkey")
