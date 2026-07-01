"""
Create the PostgreSQL database if it does not exist.

Usage:
    python scripts/init_db.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running as: python scripts/init_db.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from app.config import get_settings


def main() -> None:
    settings = get_settings()

    print(f"Connecting to PostgreSQL at {settings.postgres_host}:{settings.postgres_port}...")
    conn = psycopg2.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        dbname="postgres",
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    cur.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s",
        (settings.postgres_db,),
    )
    exists = cur.fetchone()

    if exists:
        print(f"Database '{settings.postgres_db}' already exists.")
    else:
        cur.execute(f'CREATE DATABASE "{settings.postgres_db}"')
        print(f"Database '{settings.postgres_db}' created successfully.")

    cur.close()
    conn.close()

    print("\nNext steps:")
    print("  1. Copy .env.example to .env and set your credentials")
    print("  2. alembic upgrade head")
    print("  3. python scripts/seed_from_rovo.py <path-to-rovo-json>")


if __name__ == "__main__":
    main()
