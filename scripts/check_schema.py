"""Verify jira_stories schema exists in PostgreSQL."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg2

from app.config import get_settings

EXPECTED_COLUMNS = [
    ("jira_key", "character varying", "NO"),
    ("project_key", "character varying", "YES"),
    ("project_name", "character varying", "NO"),
    ("sprint_name", "character varying", "YES"),
    ("sprint_start_date", "date", "YES"),
    ("sprint_end_date", "date", "YES"),
    ("summary", "character varying", "NO"),
    ("description", "text", "YES"),
    ("issue_type", "character varying", "YES"),
    ("priority", "character varying", "YES"),
    ("assignee", "character varying", "YES"),
    ("reporter", "character varying", "YES"),
    ("status", "character varying", "NO"),
    ("story_points", "numeric", "YES"),
    ("created_date", "date", "YES"),
    ("updated_date", "date", "YES"),
    ("resolved_date", "date", "YES"),
    ("snapshot_date", "date", "YES"),
    ("title", "character varying", "YES"),
    ("completion", "numeric", "YES"),
    ("created_at", "timestamp with time zone", "NO"),
    ("updated_at", "timestamp with time zone", "NO"),
]

EXPECTED_INDEXES = {
    "ix_jira_stories_assignee",
    "ix_jira_stories_sprint_name",
    "ix_jira_stories_status",
    "ix_jira_stories_project_name",
    "ix_jira_stories_project_key",
    "jira_stories_pkey",
}

HEAD_REVISION = "002_rovo_fields_and_title"


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

    cur.execute(
        """
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'jira_stories'
        ORDER BY ordinal_position
        """
    )
    columns = cur.fetchall()

    cur.execute(
        """
        SELECT indexname
        FROM pg_indexes
        WHERE schemaname = 'public' AND tablename = 'jira_stories'
        ORDER BY indexname
        """
    )
    indexes = {row[0] for row in cur.fetchall()}

    try:
        cur.execute("SELECT version_num FROM alembic_version")
        alembic_version = cur.fetchone()[0]
    except psycopg2.Error:
        conn.rollback()
        alembic_version = None

    cur.execute("SELECT COUNT(*) FROM jira_stories")
    row_count = cur.fetchone()[0]

    cur.close()
    conn.close()

    if not columns:
        print("\nResult: jira_stories table NOT FOUND.")
        print("Run: alembic upgrade head")
        raise SystemExit(1)

    print("\nResult: jira_stories table exists.")
    print(f"Row count: {row_count}")
    print(f"Column count: {len(columns)} (expected {len(EXPECTED_COLUMNS)})")
    print("\nColumns:")
    for name, dtype, nullable in columns:
        print(f"  {name:20} {dtype:30} nullable={nullable}")

    print("\nIndexes:")
    for name in sorted(indexes):
        print(f"  {name}")

    if alembic_version:
        print(f"\nAlembic version: {alembic_version}")
    else:
        print("\nAlembic version table: not found (migrations may not have run)")

    column_ok = set(columns) == set(EXPECTED_COLUMNS)
    index_ok = EXPECTED_INDEXES.issubset(indexes)
    migration_ok = alembic_version == HEAD_REVISION

    print("\nSchema check:")
    print(f"  Columns match schema.sql: {'YES' if column_ok else 'NO'}")
    print(f"  Indexes present:         {'YES' if index_ok else 'NO'}")
    print(f"  Alembic at head:         {'YES' if migration_ok else 'NO'}")

    if column_ok and index_ok and migration_ok:
        print("\nAll checks passed.")
        raise SystemExit(0)

    if not column_ok:
        print("\nExpected columns:")
        for row in EXPECTED_COLUMNS:
            print(f"  {row}")
    if not index_ok:
        print(f"\nMissing indexes: {sorted(EXPECTED_INDEXES - indexes)}")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
