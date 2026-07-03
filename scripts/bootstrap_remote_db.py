"""
Bootstrap a fresh remote database: migrations + optional reference projects.

Usage:
    python scripts/bootstrap_remote_db.py
    python scripts/bootstrap_remote_db.py --seed-reference
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg2

from app.config import get_settings


def run(cmd: list[str]) -> None:
    print(f"\n> {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap remote PostgreSQL schema")
    parser.add_argument(
        "--seed-reference",
        action="store_true",
        help="Load sql/reference_data.sql (8 projects)",
    )
    args = parser.parse_args()
    settings = get_settings()
    root = Path(__file__).resolve().parents[1]
    python = sys.executable

    print(
        f"Target: {settings.postgres_host}:{settings.postgres_port} / "
        f"db={settings.postgres_db}"
    )

    try:
        conn = psycopg2.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            user=settings.postgres_user,
            password=settings.postgres_password,
            dbname=settings.postgres_db,
        )
        conn.close()
        print("Connection OK.")
    except psycopg2.Error as exc:
        print(f"Connection failed: {exc}")
        print("Check .env (use .env.aws.example for RDS).")
        raise SystemExit(1) from exc

    run([python, "-m", "alembic", "upgrade", "head"])
    run([python, str(root / "scripts" / "check_schema.py")])

    if args.seed_reference:
        sql = (root / "sql" / "reference_data.sql").read_text(encoding="utf-8")
        conn = psycopg2.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            user=settings.postgres_user,
            password=settings.postgres_password,
            dbname=settings.postgres_db,
        )
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
            print("\nReference projects loaded from sql/reference_data.sql")
        finally:
            conn.close()

    print("\nRemote database is ready for the team.")


if __name__ == "__main__":
    main()
