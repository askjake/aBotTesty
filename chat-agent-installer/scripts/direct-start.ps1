# Direct Start Script - For manual startup
# Run this from: chat-agent-installer/

Write-Host ""
Write-Host "===============================================================" -ForegroundColor Cyan
Write-Host "  Dish-Chat Direct Start" -ForegroundColor Cyan
Write-Host "===============================================================" -ForegroundColor Cyan
Write-Host ""

# Check location
if (-not (Test-Path "app\backend\app\main.py")) {
    Write-Host "ERROR: Cannot find app/backend/app/main.py" -ForegroundColor Red
    Write-Host ""
    Write-Host "Make sure you're in the chat-agent-installer directory:" -ForegroundColor Yellow
    Write-Host "  cd C:\Users\Systems1\Documents\aBotTesty\chat-agent-installer" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

Write-Host "[OK] Found backend files" -ForegroundColor Green

# Check for processes on ports 3000 and 3001
Write-Host ""
Write-Host "Checking for processes on ports 3000 and 3001..." -ForegroundColor Cyan
$port3000 = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue
$port3001 = Get-NetTCPConnection -LocalPort 3001 -State Listen -ErrorAction SilentlyContinue

if ($port3000 -or $port3001) {
    Write-Host "WARNING: Ports 3000 or 3001 are already in use!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please close any running frontend/backend processes first." -ForegroundColor Yellow
    Write-Host "Or run these commands to kill them:" -ForegroundColor Cyan
    Write-Host "  Get-Process -Name node -ErrorAction SilentlyContinue | Stop-Process -Force" -ForegroundColor Cyan
    Write-Host "  Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {`$_.Path -like '*chat-agent-installer*'} | Stop-Process -Force" -ForegroundColor Cyan
    Write-Host ""
    $response = Read-Host "Do you want to kill these processes now? (y/n)"
    if ($response -eq 'y' -or $response -eq 'Y') {
        Get-Process -Name node -ErrorAction SilentlyContinue | Stop-Process -Force
        Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {`$_.Path -like '*chat-agent-installer*'} | Stop-Process -Force
        Start-Sleep -Seconds 2
        Write-Host "[OK] Processes killed" -ForegroundColor Green
    } else {
        Write-Host "Exiting. Please close the processes manually and try again." -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "[OK] Ports 3000 and 3001 are available" -ForegroundColor Green
}

# Check database
Write-Host ""
Write-Host "Checking PostgreSQL database..." -ForegroundColor Cyan
$dbRunning = docker ps --filter "name=dishchat-postgres" --format "{{.Names}}" 2>$null
if ($dbRunning) {
    Write-Host "[OK] PostgreSQL is running" -ForegroundColor Green
} else {
    Write-Host "WARNING: PostgreSQL not detected. Starting..." -ForegroundColor Yellow
    docker compose up -d 2>$null
    if ($LASTEXITCODE -eq 0) {
        Start-Sleep -Seconds 5
        Write-Host "[OK] PostgreSQL started" -ForegroundColor Green
    } else {
        Write-Host "ERROR: Could not start PostgreSQL with Docker" -ForegroundColor Red
        Write-Host "Please start PostgreSQL manually or install Docker" -ForegroundColor Yellow
        Write-Host ""
    }
}

# Check if database tables exist (run migrations if needed)
Write-Host ""
Write-Host "Checking database tables..." -ForegroundColor Cyan
$checkMigration = $false
try {
    $migrationCheck = docker exec dishchat-postgres psql -U dev_user -d dishchat -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'chat';" 2>$null
    if ($migrationCheck -match "\s*0\s*") {
        $checkMigration = $true
    }
} catch {
    $checkMigration = $true
}

if ($checkMigration) {
    Write-Host "WARNING: Database tables not found. Running migrations..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Running: alembic upgrade head" -ForegroundColor Cyan
    Write-Host ""
    
    # IMPORTANT: alembic.ini is in app/backend/app/ so we need to run from there
    Push-Location "$PWD\app\backend\app"
    if (Test-Path "..\venv\Scripts\Activate.ps1") {
        & "..\venv\Scripts\Activate.ps1"
    }
    alembic upgrade head
    $alembicResult = $LASTEXITCODE
    Pop-Location
    
    if ($alembicResult -eq 0) {
        Write-Host ""
        Write-Host "[OK] Database migrations complete" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "ERROR: Database migration failed!" -ForegroundColor Red
        Write-Host "You may need to run migrations manually:" -ForegroundColor Yellow
        Write-Host "  cd app\backend\app" -ForegroundColor Cyan
        Write-Host "  alembic upgrade head" -ForegroundColor Cyan
        Write-Host ""
    }
} else {
    Write-Host "[OK] Database tables exist" -ForegroundColor Green
}

# Backend
Write-Host ""
Write-Host "Starting Backend (http://localhost:8000)..." -ForegroundColor Cyan
$backendCmd = "cd '$PWD\app\backend'; if (Test-Path '.\venv\Scripts\Activate.ps1') { & '.\venv\Scripts\Activate.ps1' } else { Write-Host 'No venv found - using system Python' -ForegroundColor Yellow }; Write-Host 'Starting uvicorn...' -ForegroundColor Green; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd
Write-Host "[OK] Backend starting in new window..." -ForegroundColor Green

# Wait for backend to start
Start-Sleep -Seconds 8

# Frontend
Write-Host ""
Write-Host "Starting Frontend (http://localhost:3000)..." -ForegroundColor Cyan
$frontendCmd = "cd '$PWD\app\frontend'; Write-Host 'Starting pnpm dev...' -ForegroundColor Green; pnpm dev"

Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd
Write-Host "[OK] Frontend starting in new window..." -ForegroundColor Green

# Wait and open browser
Start-Sleep -Seconds 8
Write-Host ""
Write-Host "Opening browser..." -ForegroundColor Cyan
Start-Process "http://localhost:3000"

Write-Host ""
Write-Host "===============================================================" -ForegroundColor Green
Write-Host "  [DONE] Startup Complete!" -ForegroundColor Green
Write-Host "===============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Access Points:" -ForegroundColor Cyan
Write-Host "  Frontend:  http://localhost:3000" -ForegroundColor White
Write-Host "  Backend:   http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs:  http://localhost:8000/api/docs" -ForegroundColor White
Write-Host "  Database:  127.0.0.1:5434" -ForegroundColor White
Write-Host ""
Write-Host "To stop:" -ForegroundColor Yellow
Write-Host "  1. Close both PowerShell windows (Backend and Frontend)" -ForegroundColor White
Write-Host "  2. (Optional) Stop database: docker compose down" -ForegroundColor White
Write-Host ""
