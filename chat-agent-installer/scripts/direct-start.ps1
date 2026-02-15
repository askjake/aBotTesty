# Direct Start Script - For manual startup without Docker/checks
# Run this from: chat-agent-installer/

Write-Host ""
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Dish-Chat Direct Start" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Check location
if (-not (Test-Path "app\backend\app\main.py")) {
    Write-Host "❌ Error: Cannot find app/backend/app/main.py" -ForegroundColor Red
    Write-Host ""
    Write-Host "Make sure you're in the chat-agent-installer directory:" -ForegroundColor Yellow
    Write-Host "  cd C:\Users\Systems1\Documents\aBotTesty\chat-agent-installer" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

Write-Host "✓ Found backend files" -ForegroundColor Green

# Check database
Write-Host ""
Write-Host "Checking PostgreSQL database..." -ForegroundColor Cyan
$dbRunning = docker ps --filter "name=dishchat-postgres" --format "{{.Names}}" 2>$null
if ($dbRunning) {
    Write-Host "✓ PostgreSQL is running" -ForegroundColor Green
} else {
    Write-Host "⚠️  PostgreSQL not detected. Starting..." -ForegroundColor Yellow
    docker compose up -d 2>$null
    if ($LASTEXITCODE -eq 0) {
        Start-Sleep -Seconds 5
        Write-Host "✓ PostgreSQL started" -ForegroundColor Green
    } else {
        Write-Host "❌ Could not start PostgreSQL with Docker" -ForegroundColor Red
        Write-Host "Please start PostgreSQL manually or install Docker" -ForegroundColor Yellow
        Write-Host ""
    }
}

# Backend
Write-Host ""
Write-Host "Starting Backend (http://localhost:8000)..." -ForegroundColor Cyan
$backendCmd = @"
cd '$PWD\app\backend'
if (Test-Path '.\venv\Scripts\Activate.ps1') {
    & '.\venv\Scripts\Activate.ps1'
} else {
    Write-Host 'No venv found - using system Python' -ForegroundColor Yellow
}
Write-Host 'Starting uvicorn...' -ForegroundColor Green
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd
Write-Host "✓ Backend starting in new window..." -ForegroundColor Green

# Frontend
Start-Sleep -Seconds 3
Write-Host ""
Write-Host "Starting Frontend (http://localhost:3000)..." -ForegroundColor Cyan
$frontendCmd = @"
cd '$PWD\app\frontend'
Write-Host 'Starting pnpm dev...' -ForegroundColor Green
pnpm dev
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd
Write-Host "✓ Frontend starting in new window..." -ForegroundColor Green

# Wait and open browser
Start-Sleep -Seconds 5
Write-Host ""
Write-Host "Opening browser..." -ForegroundColor Cyan
Start-Process "http://localhost:3000"

Write-Host ""
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  ✓ Startup Complete!" -ForegroundColor Green
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Green
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
