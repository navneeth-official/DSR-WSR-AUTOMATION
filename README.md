# Jira Automation — DSR/WSR Database

PostgreSQL database and Python tooling to store Jira story data from **Rovo AI** for DSR/WSR reporting.

## Prerequisites

- **Python 3.11+**
- **PostgreSQL** installed and running (default port `5432`)
- **pgAdmin 4** (optional, for visual DB inspection)

## Project structure

```
├── app/                    # Application code (models, DB session, import service)
├── alembic/                # Database migrations
├── scripts/
│   ├── init_db.py          # Create PostgreSQL database
│   ├── seed_from_rovo.py   # Import Rovo JSON into jira_stories
│   └── check_schema.py     # Verify table/columns exist
├── sql/schema.sql          # Reference schema (managed by Alembic)
├── requirements.txt
├── .env.example            # Environment variable template
└── .env                    # Your local credentials (not committed to Git)
```

## 1. Clone and set up Python

```powershell
cd "DSR WSR Automation DB"

# Create virtual environment
py -3 -m venv .venv

# Activate (PowerShell)
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

## 2. Configure environment variables

Copy the example file and edit it with your PostgreSQL credentials:

```powershell
copy .env.example .env
```

Edit `.env`:

```env
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/dsr_wsr_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=dsr_wsr_db
```

> **Password tip:** If your password contains `@`, URL-encode it in `DATABASE_URL` (e.g. `@` → `%40`).

## 3. Create the database

This connects to PostgreSQL and creates `dsr_wsr_db` if it does not exist:

```powershell
python scripts/init_db.py
```

## 4. Run migrations (create tables)

Applies Alembic migrations and creates the `jira_stories` table:

```powershell
python -m alembic upgrade head
```

## 5. Import Rovo AI data

Point the seed script at a Rovo JSON file (array of story objects):

```powershell
python scripts/seed_from_rovo.py "path\to\rovo-response.json"
```

Example with the local sample file (not in Git):

```powershell
python scripts/seed_from_rovo.py "sample rovo response.txt"
```

Re-running the import **updates** existing rows by `jira_key` (upsert).

## 6. Verify the setup

### Option A — Command line

```powershell
python scripts/check_schema.py
```

You should see **22 columns**, indexes present, and Alembic at head (`002_rovo_fields_and_title`).

### Option B — pgAdmin 4

1. Connect to your PostgreSQL server.
2. Open database **`dsr_wsr_db`**.
3. Navigate to **Schemas → public → Tables → jira_stories**.
4. Right-click → **View/Edit Data → All Rows** to see imported stories.

Or run in **Query Tool**:

```sql
SELECT COUNT(*) FROM jira_stories;

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'jira_stories'
ORDER BY ordinal_position;

SELECT jira_key, project_name, summary, title, status
FROM jira_stories
ORDER BY jira_key;
```

## Database schema

The `jira_stories` table stores all Rovo JSON fields plus extra columns:

| Column | Source |
|--------|--------|
| `jira_key` | Rovo — primary key |
| `project_key`, `project_name` | Rovo |
| `sprint_name`, `sprint_start_date`, `sprint_end_date` | Rovo |
| `summary`, `description` | Rovo |
| `issue_type`, `priority` | Rovo |
| `assignee`, `reporter`, `status` | Rovo |
| `story_points` | Rovo |
| `created_date`, `updated_date`, `resolved_date`, `snapshot_date` | Rovo |
| `title` | Reserved for AI team (empty on import) |
| `completion` | Inferred from status (e.g. Done → 100%) |
| `created_at`, `updated_at` | Database audit timestamps |

Full reference: `sql/schema.sql`

## Common commands

| Task | Command |
|------|---------|
| Create database | `python scripts/init_db.py` |
| Apply migrations | `python -m alembic upgrade head` |
| Import Rovo JSON | `python scripts/seed_from_rovo.py <file>` |
| Verify schema | `python scripts/check_schema.py` |
| Check migration status | `python -m alembic current` |

## Troubleshooting

**Connection refused**
- Ensure PostgreSQL is running (Windows Services or pgAdmin connection test).

**`database "dsr_wsr_db" does not exist`**
- Run `python scripts/init_db.py`.

**`column ... does not exist`**
- Run `python -m alembic upgrade head`.

**Alembic error with `%` in password**
- URL-encode special characters in `DATABASE_URL` inside `.env`.

**`psql` not found**
- Use pgAdmin Query Tool or the Python scripts above; `psql` is not required.

## What not to commit

These are listed in `.gitignore`:

- `.env` (real credentials)
- `.venv/`
- `sample rovo response.txt` (local sample data)

## License

Internal HEB training project.
