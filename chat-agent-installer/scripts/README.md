# Startup Scripts

This directory contains scripts to start the Dish-Chat application.

## Windows Users

### Option 1: Automated Quick Start (Recommended)
```powershell
cd C:\Users\Systems1\Documents\aBotTesty\chat-agent-installer
.\scripts\quick-start-windows.ps1
```

This will:
- Start PostgreSQL (Docker)
- Check/create virtual environment
- Install missing dependencies
- Start backend and frontend in separate windows
- Open browser automatically

### Option 2: Direct Start (Simpler)
```powershell
cd C:\Users\Systems1\Documents\aBotTesty\chat-agent-installer
.\scripts\direct-start.ps1
```

This is a simpler version that assumes you've already set everything up once.

### Option 3: Manual Start
See `../docs/MANUAL_STARTUP.md` for step-by-step manual instructions.

## Troubleshooting

### "Run this from chat-agent-installer directory" error

**Wrong:**
```powershell
cd chat-agent-installer\scripts
.\quick-start-windows.ps1  # ❌ Won't work from here
```

**Correct:**
```powershell
cd chat-agent-installer
.\scripts\quick-start-windows.ps1  # ✅ Works!
```

### "Could not import module app.main" error

This means you're trying to run uvicorn from the wrong directory.

**Wrong:**
```powershell
cd chat-agent-installer
python -m uvicorn app.main:app  # ❌ No!
```

**Correct:**
```powershell
cd chat-agent-installer\app\backend
python -m uvicorn app.main:app  # ✅ Yes!
```

### Scripts won't run ("cannot be loaded because running scripts is disabled")

You need to allow PowerShell scripts:
```powershell
# Run as Administrator:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then try the script again.

## What Each Script Does

- **quick-start-windows.ps1** - Full automated startup with checks
- **direct-start.ps1** - Simple startup for when everything is already configured
- **detect-environment.py** - Python script to detect available LLM providers

## After Starting

Once the scripts complete successfully, you should see:
- Backend running at http://localhost:8000
- Frontend running at http://localhost:3000
- Browser opens automatically to http://localhost:3000

To stop:
1. Close the backend PowerShell window (or press Ctrl+C)
2. Close the frontend PowerShell window (or press Ctrl+C)
3. Stop database: `docker compose down` (from chat-agent-installer directory)
