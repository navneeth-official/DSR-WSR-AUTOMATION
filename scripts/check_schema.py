"""Verify normalized schema exists in PostgreSQL."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg2

from app.config import get_settings

JIRA_STORY_COLUMNS = [
    ("jira_key", "character varying", "NO"),
    ("project_id", "integer", "NO"),
    ("sprint_id", "integer", "YES"),
    ("title", "character varying", "YES"),
    ("summary", "character varying", "NO"),
    ("description", "text", "YES"),
    ("story_points", "numeric", "YES"),
    ("status", "character varying", "NO"),
    ("assignee", "character varying", "YES"),
    ("reporter", "character varying", "YES"),
    ("issue_type", "character varying", "YES"),
    ("priority", "character varying", "YES"),
    ("completion", "numeric", "YES"),
    ("created_date", "date", "YES"),
    ("updated_date", "date", "YES"),
    ("resolved_date", "date", "YES"),
    ("snapshot_date", "date", "YES"),
    ("created_at", "timestamp with time zone", "NO"),
    ("updated_at", "timestamp with time zone", "NO"),
]

PROJECT_COLUMNS = [
    ("project_id", "integer", "NO"),
    ("project_key", "character varying", "NO"),
    ("project_name", "character varying", "NO"),
    ("created_at", "timestamp with time zone", "NO"),
    ("updated_at", "timestamp with time zone", "NO"),
]

SPRINT_COLUMNS = [
    ("sprint_id", "integer", "NO"),
    ("sprint_name", "character varying", "NO"),
    ("sprint_status", "character varying", "NO"),
    ("sprint_start_date", "date", "YES"),
    ("sprint_end_date", "date", "YES"),
    ("created_at", "timestamp with time zone", "NO"),
    ("updated_at", "timestamp with time zone", "NO"),
]

EXPECTED_INDEXES = {
    "jira_stories": {
        "ix_jira_stories_assignee",
        "ix_jira_stories_project_id",
        "ix_jira_stories_sprint_id",
        "ix_jira_stories_status",
        "jira_stories_pkey",
    },
    "projects": {
        "ix_projects_project_key",
        "projects_pkey",
        "projects_project_key_key",
    },
    "sprints": {
        "ix_sprints_sprint_name",
        "ix_sprints_sprint_status",
        "sprints_pkey",
        "uq_sprints_sprint_name",
    },
}

HEAD_REVISION = "007_add_sprint_status"


def fetch_columns(cur, table_name: str) -> list[tuple[str, str, str]]:
    cur.execute(
        """
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table_name,),
    )
    return cur.fetchall()


def fetch_indexes(cur, table_name: str) -> set[str]:
    cur.execute(
        """
        SELECT indexname
        FROM pg_indexes
        WHERE schemaname = 'public' AND tablename = %s
        ORDER BY indexname
        """,
        (table_name,),
    )
    return {row[0] for row in cur.fetchall()}


def main() -> None:
    settings = get_settings()
    print(
        f"Checking PostgreSQL at {settings.postgres_host}:{settings.postgres_port} "
        f"/ db={settings.postgres_db}"
    )

    try:
        conn = psycopg2.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            user=settings.postgres_user,
            password=settings.postgres_password,
            dbname=settings.postgres_db,
        )
    except psycopg2.OperationalError as exc:
        print(f"\nConnection failed: {exc}")
        print("\nTips:")
        print("  1. Copy .env.example to .env and set your credentials")
        print("  2. Ensure PostgreSQL is running")
        print("  3. Run: python scripts/init_db.py")
        print("  4. Run: alembic upgrade head")
        raise SystemExit(1) from exc

    cur = conn.cursor()

    tables = {
        "projects": PROJECT_COLUMNS,
        "sprints": SPRINT_COLUMNS,
        "jira_stories": JIRA_STORY_COLUMNS,
    }

    all_ok = True

    for table_name, expected in tables.items():
        columns = fetch_columns(cur, table_name)
        indexes = fetch_indexes(cur, table_name)

        print(f"\n=== {table_name} ===")
        if not columns:
            print("  Table NOT FOUND.")
            all_ok = False
            continue

        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cur.fetchone()[0]
        print(f"  Row count: {row_count}")
        print(f"  Column count: {len(columns)} (expected {len(expected)})")

        for name, dtype, nullable in columns:
            print(f"    {name:20} {dtype:30} nullable={nullable}")

        print("  Indexes:")
        for name in sorted(indexes):
            print(f"    {name}")

        column_ok = set(columns) == set(expected)
        index_ok = EXPECTED_INDEXES[table_name].issubset(indexes)
        print(f"  Columns OK: {'YES' if column_ok else 'NO'}")
        print(f"  Indexes OK: {'YES' if index_ok else 'NO'}")
        if not column_ok or not index_ok:
            all_ok = False

    try:
        cur.execute("SELECT version_num FROM alembic_version")
        alembic_version = cur.fetchone()[0]
    except psycopg2.Error:
        conn.rollback()
        alembic_version = None

    cur.close()
    conn.close()

    migration_ok = alembic_version == HEAD_REVISION
    print(f"\nAlembic version: {alembic_version or 'not found'}")
    print(f"At head ({HEAD_REVISION}): {'YES' if migration_ok else 'NO'}")

    if all_ok and migration_ok:
        print("\nAll checks passed.")
        raise SystemExit(0)

    raise SystemExit(1)


if __name__ == "__main__":
    main()
