# Database Setup Guide

The Dish-Chat application requires PostgreSQL to store:
- Chat history
- Messages
- User data
- LangGraph checkpoints
- LLM provider configurations

## Quick Start with Docker (Recommended)

The easiest way to run PostgreSQL is using Docker:

### 1. Install Docker Desktop

- **Windows**: Download from https://www.docker.com/products/docker-desktop
- **macOS**: Download from https://www.docker.com/products/docker-desktop
- **Linux**: Install using your package manager

### 2. Start PostgreSQL

```bash
# From the chat-agent-installer directory
docker compose up -d
```

This will:
- ✅ Download PostgreSQL 16 image
- ✅ Create database `dishchat`
- ✅ Create user `dev_user` with password `dev123`
- ✅ Expose on port 5434 (so it doesn't conflict with other PostgreSQL installs)
- ✅ Persist data in Docker volume

### 3. Verify it's running

```bash
docker compose ps
```

Should show `dishchat-postgres` as `Up (healthy)`

### 4. Stop PostgreSQL (when done)

```bash
docker compose down
```

To completely remove (including data):
```bash
docker compose down -v
```

## Manual PostgreSQL Installation

If you prefer to install PostgreSQL directly:

### Windows

1. Download PostgreSQL from: https://www.postgresql.org/download/windows/
2. Run installer, set password for `postgres` user
3. Create database and user:

```sql
-- Connect to PostgreSQL (psql or pgAdmin)
CREATE DATABASE dishchat;
CREATE USER dev_user WITH PASSWORD 'dev123';
GRANT ALL PRIVILEGES ON DATABASE dishchat TO dev_user;
```

4. Update `.env` to use port 5432 (default PostgreSQL port):
```
POSTGRES_PORT=5432
```

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE dishchat;
CREATE USER dev_user WITH PASSWORD 'dev123';
GRANT ALL PRIVILEGES ON DATABASE dishchat TO dev_user;
\q
EOF
```

### macOS

```bash
brew install postgresql@16
brew services start postgresql@16

# Create database and user
psql postgres << EOF
CREATE DATABASE dishchat;
CREATE USER dev_user WITH PASSWORD 'dev123';
GRANT ALL PRIVILEGES ON DATABASE dishchat TO dev_user;
\q
EOF
```

## Run Database Migrations

After PostgreSQL is running, initialize the database schema:

```bash
cd chat-agent-installer/app/backend
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
alembic upgrade head
```

This creates all required tables, including the new `llm_providers` table.

## Verify Connection

Test the connection:

```bash
psql -h 127.0.0.1 -p 5434 -U dev_user -d dishchat
# Password: dev123
```

Should connect successfully.

Or from Python:

```python
import asyncpg
import asyncio

async def test():
    conn = await asyncpg.connect(
        "postgresql://dev_user:dev123@127.0.0.1:5434/dishchat"
    )
    version = await conn.fetchval("SELECT version();")
    print(f"Connected! PostgreSQL version: {version}")
    await conn.close()

asyncio.run(test())
```

## Troubleshooting

### Connection Timeout (30 seconds)

**Symptom**: Backend shows `PoolTimeout - couldn't get a connection after 30.00 sec`

**Causes**:
1. PostgreSQL not running
2. PostgreSQL on different port
3. Firewall blocking connection
4. Wrong credentials

**Fix**:
```bash
# Check if PostgreSQL is running
docker compose ps                    # If using Docker
# or
sudo systemctl status postgresql     # If using system PostgreSQL

# Check if port 5434 is listening
netstat -an | grep 5434              # Linux/macOS
netstat -an | findstr 5434           # Windows

# Try connecting manually
psql -h 127.0.0.1 -p 5434 -U dev_user -d dishchat
```

### Port Already in Use

If port 5434 is already taken, update `.env`:

```
POSTGRES_PORT=5435
```

And update `docker-compose.yml`:
```yaml
ports:
  - "5435:5432"
```

### Cannot Run Docker

If you can't use Docker, install PostgreSQL manually (see above).

## Configuration

All database settings are in `app/backend/.env`:

```bash
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5434
POSTGRES_DB=dishchat
POSTGRES_USER=dev_user
POSTGRES_PWD=dev123
```

The connection URLs are auto-generated:
```bash
POSTGRES_URL=postgresql://dev_user:dev123@127.0.0.1:5434/dishchat
POSTGRES_SQLALCHEMY_URL=postgresql+asyncpg://dev_user:dev123@127.0.0.1:5434/dishchat
```

## Quick Start Checklist

☐ Install Docker Desktop (or PostgreSQL)
☐ Run `docker compose up -d` from chat-agent-installer/
☐ Wait for database to be healthy (~10 seconds)
☐ Run database migrations: `alembic upgrade head`
☐ Start backend: `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
☐ Backend should show "Application startup complete"
☐ Start frontend: `pnpm dev`
☐ Open http://localhost:3000

---

**TL;DR**: Run `docker compose up -d` before starting the backend!
