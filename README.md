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
├── docker-compose.yml    # Local / EC2 PostgreSQL in Docker
├── docs/
│   └── AWS_DEPLOYMENT.md # Host on AWS for team access
├── sql/schema.sql          # Reference schema (managed by Alembic)
├── requirements.txt
├── .env.example            # Local PostgreSQL template
├── .env.docker.example     # Docker Postgres template
├── .env.aws.example        # AWS RDS / remote host template
└── .env                    # Your credentials (not committed to Git)
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

You should see **3 tables** (`projects`, `sprints`, `jira_stories`), indexes present, and Alembic at head (`006_fix_jira_stories_pkey_name`).

## Docker (local PostgreSQL without installing Postgres)

```powershell
copy .env.docker.example .env.docker
# Edit POSTGRES_PASSWORD in .env.docker

docker compose --env-file .env.docker up -d
copy .env.docker.example .env
python -m alembic upgrade head
```

See `docs/AWS_DEPLOYMENT.md` for full Docker + AWS instructions.

## Host on AWS for coworkers

Share one database so the team sees the same Jira story data.

1. **Recommended:** Create **AWS RDS PostgreSQL** (or run **Docker on EC2**).
2. Run migrations once: `python scripts/bootstrap_remote_db.py --seed-reference`
3. Share connection details securely (not Git) — see `.env.aws.example`.
4. Each coworker copies `.env.aws.example` → `.env` and connects via pgAdmin.

Full step-by-step: **[docs/AWS_DEPLOYMENT.md](docs/AWS_DEPLOYMENT.md)**

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

SELECT js.jira_key, p.project_name, js.summary, js.title, js.status
FROM jira_stories js
JOIN projects p ON p.project_id = js.project_id
ORDER BY js.jira_key;
```

## Database schema

Data is split across **3 normalized tables** to avoid duplication and enable fast filtering by numeric IDs:

| Table | Key columns | Purpose |
|-------|-------------|---------|
| `projects` | `project_id` (PK), `project_key`, `project_name` | One row per Jira project |
| `sprints` | `sprint_id` (PK), `sprint_name`, sprint dates | One row per unique sprint name |
| `jira_stories` | `jira_key` (PK), `project_id` (FK), `sprint_id` (FK), story fields | Story details — references project/sprint by ID |

**Filter examples (using your project and sprint names):**

```sql
-- All LOCO stories
SELECT js.jira_key, js.summary, js.status, s.sprint_name
FROM jira_stories js
JOIN projects p ON p.project_id = js.project_id
LEFT JOIN sprints s ON s.sprint_id = js.sprint_id
WHERE p.project_name = 'LOCO';

-- Stories in sprint "Q2.13FY26 Eridanus"
SELECT js.jira_key, p.project_name, js.summary, js.status
FROM jira_stories js
JOIN projects p ON p.project_id = js.project_id
JOIN sprints s ON s.sprint_id = js.sprint_id
WHERE s.sprint_name = 'Q2.13FY26 Eridanus';

-- Fast filter by numeric ids (after you know them)
SELECT * FROM jira_stories WHERE project_id = 3 AND sprint_id = 2;
```

**Your projects:** LOCO, Cost Core Service, GSS, Wentforth, Pharamacy, Supplier QA, SPUR, Pricing  
**Example sprint names:** `Nacogdoches - 248`, `Q2.13FY26 Eridanus`, `Q2.14 FY26 Fornax`

Optional: pre-seed project rows with `sql/reference_data.sql` before importing Rovo JSON.

Story columns from Rovo: `summary`, `description`, `issue_type`, `priority`, `assignee`, `reporter`, `status`, `story_points`, dates, plus `title` (AI team) and `completion` (inferred from status).

Full reference: `sql/schema.sql` · ER diagram: `sql/erd.md`

## Common commands

| Task | Command |
|------|---------|
| Create database | `python scripts/init_db.py` |
| Bootstrap AWS / remote DB | `python scripts/bootstrap_remote_db.py --seed-reference` |
| Start local Docker Postgres | `docker compose --env-file .env.docker up -d` |
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
- `.env.docker`, `.env.aws`
- `.venv/`
- `sample rovo response.txt` (local sample data)

## License

Internal HEB training project.
