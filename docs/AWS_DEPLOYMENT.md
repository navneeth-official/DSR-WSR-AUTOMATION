# AWS deployment — shared PostgreSQL for the team

This guide covers hosting `dsr_wsr_db` on AWS so coworkers can connect from pgAdmin or Python scripts.

## Choose an approach

| Approach | Best for | Docker? |
|----------|----------|---------|
| **A. AWS RDS PostgreSQL** (recommended) | Production / team shared DB | No — AWS manages Postgres |
| **B. Docker on EC2** | Lower cost, you manage updates/backups | Yes — `docker compose` on a VM |
| **C. Docker on your PC** | Local dev only | Yes — not for team access |

For coworkers on different machines, use **RDS** or **Docker on EC2** with a **public or VPN-reachable endpoint**.

---

## Option A — AWS RDS PostgreSQL (recommended)

### 1. Create the database (AWS Console)

1. Open **AWS Console → RDS → Create database**.
2. **Engine:** PostgreSQL 16 (or 15+).
3. **Template:** Free tier (dev) or Production.
4. **DB instance identifier:** `dsr-wsr-db`
5. **Master username:** `postgres`
6. **Master password:** strong password (save in a team password manager).
7. **DB name:** `dsr_wsr_db`
8. **Instance class:** `db.t3.micro` (dev) or larger for production.
9. **Storage:** 20 GB gp3 (default is fine to start).
10. **Connectivity:**
    - **Public access:** Yes (only if coworkers connect from outside AWS without VPN).
    - **VPC security group:** create new → add inbound rule below.
11. Create database. Wait until status is **Available**.

### 2. Security group (who can connect)

RDS → your instance → **VPC security group** → **Inbound rules**:

| Type | Port | Source | Purpose |
|------|------|--------|---------|
| PostgreSQL | 5432 | Your office IP `/32` | Teammates on office network |
| PostgreSQL | 5432 | Coworker IP `/32` | Each remote worker (or use VPN) |

Avoid `0.0.0.0/0` (entire internet) unless this is a short-lived dev setup.

### 3. Get the endpoint

RDS → **Connectivity & security** → copy **Endpoint**, e.g.:

```text
dsr-wsr-db.xxxxx.us-east-1.rds.amazonaws.com
```

### 4. Initialize schema (one person, once)

On a machine with this repo cloned:

```powershell
copy .env.aws.example .env
# Edit .env with RDS endpoint and password (URL-encode @ in DATABASE_URL)

pip install -r requirements.txt
python -m alembic upgrade head
python scripts/check_schema.py
```

Optional — seed projects:

```powershell
# Run sql/reference_data.sql in pgAdmin Query Tool, or:
python scripts/seed_from_rovo.py "path\to\rovo-response.json"
```

### 5. Share connection details with coworkers (secure channel)

Send each teammate (Teams/1Password — **not Git**):

```text
Host:     dsr-wsr-db.xxxxx.us-east-1.rds.amazonaws.com
Port:     5432
Database: dsr_wsr_db
User:     postgres
Password: (shared team password)
SSL:      prefer or require
```

Each coworker copies `.env.aws.example` → `.env`, fills values, then uses pgAdmin or Python scripts.

### 6. pgAdmin connection (coworkers)

1. Register → Server
2. **Connection tab:** Host = RDS endpoint, Port = 5432, Database = `dsr_wsr_db`, Username/Password
3. **SSL tab:** SSL mode = **Require** (if RDS enforces SSL)

---

## Option B — Docker PostgreSQL on EC2

Use this if you want full control and lower cost than RDS. You are responsible for backups and updates.

### 1. Launch EC2

1. **AMI:** Amazon Linux 2023 or Ubuntu 22.04
2. **Instance type:** `t3.small` or larger
3. **Storage:** 30 GB+
4. **Security group inbound:**
   - SSH (22) — your IP only
   - PostgreSQL (5432) — office IP or teammate IPs (not `0.0.0.0/0` in production)
5. Assign an **Elastic IP** (optional but recommended — stable hostname for team)

### 2. Install Docker on EC2

Amazon Linux example:

```bash
sudo yum update -y
sudo yum install -y docker
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker ec2-user
# Log out and back in, then:
docker compose version || sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose && sudo chmod +x /usr/local/bin/docker-compose
```

### 3. Deploy the database container

Copy the project to EC2 (git clone) or copy only:

- `docker-compose.yml`
- `.env.docker.example`

On EC2:

```bash
cd dsr-wsr-automation-db
cp .env.docker.example .env.docker
nano .env.docker   # set a strong POSTGRES_PASSWORD
docker compose --env-file .env.docker up -d
docker compose ps
```

Postgres listens on EC2 port **5432**. Database `dsr_wsr_db` is created automatically.

### 4. Run migrations against EC2

From your laptop (with EC2 IP in `.env`):

```env
POSTGRES_HOST=3.12.34.56
DATABASE_URL=postgresql://postgres:PASSWORD@3.12.34.56:5432/dsr_wsr_db
```

```powershell
python -m alembic upgrade head
python scripts/check_schema.py
```

### 5. Backups (EC2 Docker — your responsibility)

```bash
docker exec dsr_wsr_postgres pg_dump -U postgres dsr_wsr_db > backup_$(date +%F).sql
```

Upload backups to S3 on a schedule (cron). RDS does this automatically.

---

## Option C — Local Docker (dev machine only)

For running Postgres locally without installing PostgreSQL on Windows:

```powershell
copy .env.docker.example .env.docker
# Edit password in .env.docker

docker compose --env-file .env.docker up -d
copy .env.docker.example .env
# Point .env DATABASE_URL to localhost

python -m alembic upgrade head
python scripts/check_schema.py
```

Stop:

```powershell
docker compose --env-file .env.docker down
```

Data persists in Docker volume `postgres_data`.

---

## Team workflow summary

```text
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Rovo JSON  │────▶│  seed_from_rovo  │────▶│  AWS PostgreSQL │
│  (import)   │     │  (one teammate)  │     │  dsr_wsr_db     │
└─────────────┘     └──────────────────┘     └────────┬────────┘
                                                      │
                        ┌─────────────────────────────┼─────────────────────────────┐
                        ▼                             ▼                             ▼
                   pgAdmin (you)              pgAdmin (coworker)           Python scripts
```

1. **Admin** creates RDS or EC2 + Docker, runs `alembic upgrade head`, imports data.
2. **Admin** shares host/user/password securely.
3. **Coworkers** set `.env` and connect — they see the **same data** (one shared database).
4. **Imports** can be re-run by anyone with `.env` and the Rovo JSON file (upsert by `jira_key`).

---

## Checklist before go-live

- [ ] Strong password, not in Git
- [ ] Security group limits IP access (not open to world)
- [ ] `alembic upgrade head` run on shared DB
- [ ] `python scripts/check_schema.py` passes
- [ ] At least one coworker tested pgAdmin connection
- [ ] Backup plan (RDS automated backups or EC2 pg_dump + S3)
- [ ] `.env` in `.gitignore` (already configured)

---

## Troubleshooting

**Connection timed out**
- Security group missing inbound 5432 for client IP
- RDS "Publicly accessible" = No but client is outside VPC

**Password authentication failed**
- Wrong password in `.env`
- For `DATABASE_URL`, URL-encode `@` as `%40`

**SSL required**
- Add `?sslmode=require` to `DATABASE_URL`

**Coworker sees empty tables**
- They connected to wrong database or fresh DB without import
- Run `SELECT current_database();` and compare with admin

---

## Related files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Postgres 16 container |
| `.env.docker.example` | Local / EC2 Docker env |
| `.env.aws.example` | RDS / remote connection template |
| `sql/reference_data.sql` | Optional project seed |
| `scripts/seed_from_rovo.py` | Import story data |
