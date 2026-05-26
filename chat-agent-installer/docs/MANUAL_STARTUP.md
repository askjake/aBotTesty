# Manual Startup Guide (Windows)

If the automated scripts aren't working, follow these manual steps:

## Prerequisites Check

1. **PostgreSQL Running**
   ```powershell
   # From chat-agent-installer/ directory
   docker compose up -d
   # Wait 5 seconds
   docker ps  # Should show dishchat-postgres running
   ```

2. **Backend Dependencies Installed**
   ```powershell
   cd app/backend
   # Check if venv exists
   if (!(Test-Path venv)) {
       python -m venv venv
       .\venv\Scripts\Activate.ps1
       pip install -r requirements.txt
   }
   ```

3. **Frontend Dependencies Installed**
   ```powershell
   cd app/frontend
   # Check if node_modules exists
   if (!(Test-Path node_modules)) {
       pnpm install
   }
   ```

4. **Environment File Configured**
   ```powershell
   cd app/backend
   # Copy example if .env doesn't exist
   if (!(Test-Path .env)) {
       copy .env.example .env
       notepad .env  # Add your API keys
   }
   ```

## Start Services

### Terminal 1: Backend

```powershell
# Start from project root
cd C:\Users\Systems1\Documents\aBotTesty\chat-agent-installer

# Navigate to backend
cd app\backend

# Activate venv
.\venv\Scripts\Activate.ps1

# Start uvicorn
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using WatchFiles
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Test:** Open http://localhost:8000/api/docs - should see Swagger UI

### Terminal 2: Frontend

```powershell
# Start from project root  
cd C:\Users\Systems1\Documents\aBotTesty\chat-agent-installer

# Navigate to frontend
cd app\frontend

# Start dev server
pnpm dev
```

**Expected output:**
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

**Test:** Open http://localhost:3000 - should see the app

## Troubleshooting

### Backend won't start

**Error:** `ModuleNotFoundError: No module named 'app'`
- **Cause:** Running from wrong directory
- **Fix:** Must run `python -m uvicorn app.main:app` from `app/backend/` directory

**Error:** `Could not import module "app.main"`
- **Cause:** Not in the backend directory
- **Fix:**
  ```powershell
  cd C:\Users\Systems1\Documents\aBotTesty\chat-agent-installer\app\backend
  python -m uvicorn app.main:app --reload
  ```

**Error:** `sqlalchemy.exc.OperationalError: could not connect to server`
- **Cause:** PostgreSQL not running
- **Fix:**
  ```powershell
  cd C:\Users\Systems1\Documents\aBotTesty\chat-agent-installer
  docker compose up -d
  # Wait 10 seconds then try again
  ```

**Error:** `ModuleNotFoundError: No module named 'fastapi'` (or other packages)
- **Cause:** Dependencies not installed or venv not activated
- **Fix:**
  ```powershell
  cd app\backend
  .\venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  ```

### Frontend won't start

**Error:** `'pnpm' is not recognized`
- **Cause:** pnpm not installed
- **Fix:** `npm install -g pnpm`

**Error:** `Cannot find module` errors
- **Cause:** Dependencies not installed
- **Fix:**
  ```powershell
  cd app\frontend
  pnpm install
  ```

### Database issues

**Error:** `docker: command not found` or Docker not responding
- **Cause:** Docker Desktop not running
- **Fix:** Start Docker Desktop, wait for it to fully start, then:
  ```powershell
  cd chat-agent-installer
  docker compose up -d
  ```

**Check database is running:**
```powershell
docker ps
# Should show: dishchat-postgres with status "Up X seconds"
```

**Connect to database (for debugging):**
```powershell
docker exec -it dishchat-postgres psql -U dev_user -d dishchat
# Inside psql:
\dt  # List tables
\q   # Quit
```

## Quick Reference

### File Locations
```
C:\Users\Systems1\Documents\aBotTesty\
└── chat-agent-installer/
    ├── app/
    │   ├── backend/          ← Run uvicorn from here
    │   │   ├── venv/         ← Virtual environment
    │   │   ├── app/
    │   │   │   └── main.py   ← Main FastAPI app
    │   │   ├── .env          ← Your API keys
    │   │   └── requirements.txt
    │   └── frontend/         ← Run pnpm from here
    │       ├── node_modules/
    │       └── package.json
    ├── docker-compose.yml    ← PostgreSQL config
    └── scripts/
        └── direct-start.ps1  ← Automated startup
```

### Commands Cheat Sheet

```powershell
# ===== STARTUP =====
# Database
cd chat-agent-installer
docker compose up -d

# Backend (new terminal)
cd chat-agent-installer\app\backend
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (new terminal)
cd chat-agent-installer\app\frontend
pnpm dev

# ===== SHUTDOWN =====
# Stop backend: Ctrl+C in backend terminal
# Stop frontend: Ctrl+C in frontend terminal
# Stop database:
cd chat-agent-installer
docker compose down

# ===== RESET =====
# If everything is broken, nuclear option:
cd chat-agent-installer
docker compose down -v  # Deletes database
cd app\backend
Remove-Item -Recurse -Force venv
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..\..
docker compose up -d
# Then run migrations:
cd app\backend
alembic upgrade head
```

## Verification

Once everything is running:

1. **Backend Health Check**
   - Open: http://localhost:8000/api/docs
   - Should see Swagger UI with all endpoints

2. **Frontend Check**
   - Open: http://localhost:3000
   - Should see the chat interface

3. **Database Check**
   ```powershell
   docker exec dishchat-postgres psql -U dev_user -d dishchat -c "SELECT version();"
   # Should show PostgreSQL version
   ```

4. **Test Chat**
   - Open http://localhost:3000
   - Create a new chat
   - Send a message
   - Should get a response (if API keys configured)

## Still Having Issues?

1. Check all terminals for error messages
2. Verify all prerequisites are met
3. Try the "RESET" commands above
4. Check that ports 8000, 3000, and 5434 aren't in use by other apps
5. Make sure you're in the correct directories when running commands
