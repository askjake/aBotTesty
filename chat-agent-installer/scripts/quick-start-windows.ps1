# Complete Quick Start for Windows
# Run this from chat-agent-installer/ directory

Write-Host "Starting Dish-Chat..." -ForegroundColor Green
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "docker-compose.yml")) {
    Write-Host "Error: Run this from chat-agent-installer directory" -ForegroundColor Red
    Write-Host "Expected location: chat-agent-installer/" -ForegroundColor Yellow
    Write-Host "Current location: $PWD" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor Cyan
    Write-Host "  cd C:\Users\Systems1\Documents\aBotTesty\chat-agent-installer" -ForegroundColor Cyan
    Write-Host "  .\scripts\quick-start-windows.ps1" -ForegroundColor Cyan
    exit 1
}

Write-Host "[OK] Running from correct directory" -ForegroundColor Green
Write-Host ""

# Check for running processes
Write-Host "Checking for running processes on ports 3000/3001..." -ForegroundColor Cyan
$port3000 = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue
$port3001 = Get-NetTCPConnection -LocalPort 3001 -State Listen -ErrorAction SilentlyContinue

if ($port3000 -or $port3001) {
    Write-Host "WARNING: Ports already in use. Killing old processes..." -ForegroundColor Yellow
    Get-Process -Name node -ErrorAction SilentlyContinue | Stop-Process -Force
    Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {`$_.Path -like '*chat-agent-installer*'} | Stop-Process -Force
    Start-Sleep -Seconds 2
    Write-Host "[OK] Old processes killed" -ForegroundColor Green
}

# Check if Docker is running
$dockerRunning = $false
try {
    docker ps | Out-Null
    $dockerRunning = $true
} catch {
    Write-Host "Warning: Docker is not running" -ForegroundColor Yellow
}

if ($dockerRunning) {
    Write-Host "Starting PostgreSQL database..." -ForegroundColor Cyan
    docker compose up -d
    
    Write-Host "Waiting for database to be ready..." -ForegroundColor Cyan
    Start-Sleep -Seconds 5
    Write-Host "[OK] Database ready!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Docker not available. Make sure PostgreSQL is running manually:" -ForegroundColor Yellow
    Write-Host "  Host: 127.0.0.1" -ForegroundColor Cyan
    Write-Host "  Port: 5434" -ForegroundColor Cyan
    Write-Host "  Database: dishchat" -ForegroundColor Cyan
    Write-Host "  User: dev_user" -ForegroundColor Cyan
    Write-Host ""
}

# Check if venv exists in backend
$backendVenv = Join-Path $PWD "app\backend\venv"
if (-not (Test-Path $backendVenv)) {
    Write-Host "Warning: Virtual environment not found at $backendVenv" -ForegroundColor Yellow
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    
    $backendPath = Join-Path $PWD "app\backend"
    Push-Location $backendPath
    python -m venv venv
    & ".\venv\Scripts\Activate.ps1"
    pip install -r requirements.txt
    Pop-Location
    
    Write-Host "[OK] Virtual environment created" -ForegroundColor Green
}

# Check if .env exists
$envFile = Join-Path $PWD "app\backend\.env"
if (-not (Test-Path $envFile)) {
    Write-Host ""
    Write-Host "WARNING: .env file not found" -ForegroundColor Yellow
    Write-Host "Creating .env from .env.example..." -ForegroundColor Cyan
    
    $envExample = Join-Path $PWD "app\backend\.env.example"
    if (Test-Path $envExample) {
        Copy-Item $envExample $envFile
        Write-Host "[OK] Created .env file" -ForegroundColor Green
        Write-Host ""
        Write-Host "IMPORTANT: Edit app/backend/.env and add your API keys!" -ForegroundColor Yellow
        Write-Host "  - Add OPENAI_API_KEY or other LLM provider keys" -ForegroundColor Yellow
        Write-Host ""
    }
}

# Run database migrations from correct directory
Write-Host ""
Write-Host "Running database migrations..." -ForegroundColor Cyan
Push-Location "$PWD\app\backend\app"
if (Test-Path "..\venv\Scripts\Activate.ps1") {
    & "..\venv\Scripts\Activate.ps1"
}
alembic upgrade head
$migrationResult = $LASTEXITCODE
Pop-Location

if ($migrationResult -eq 0) {
    Write-Host "[OK] Migrations complete" -ForegroundColor Green
} else {
    Write-Host "WARNING: Migration had issues (may be okay if already migrated)" -ForegroundColor Yellow
}

# Start Backend
Write-Host ""
Write-Host "Starting Backend..." -ForegroundColor Cyan
$backendCmd = "cd '$PWD\app\backend'; & '.\venv\Scripts\Activate.ps1'; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

# Wait for backend to start
Write-Host "Waiting for backend to start..." -ForegroundColor Cyan
Start-Sleep -Seconds 10

# Check if frontend dependencies are installed
$frontendNodeModules = Join-Path $PWD "app\frontend\node_modules"
if (-not (Test-Path $frontendNodeModules)) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
    $frontendPath = Join-Path $PWD "app\frontend"
    Push-Location $frontendPath
    pnpm install
    Pop-Location
    Write-Host "[OK] Frontend dependencies installed" -ForegroundColor Green
}

# Start Frontend
Write-Host "Starting Frontend..." -ForegroundColor Cyan
$frontendCmd = "cd '$PWD\app\frontend'; pnpm dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

# Wait for frontend to start
Write-Host "Waiting for frontend to start..." -ForegroundColor Cyan
Start-Sleep -Seconds 8

# Open browser
Write-Host ""
Write-Host "Opening browser..." -ForegroundColor Green
Start-Sleep -Seconds 3
Start-Process "http://localhost:3000"

Write-Host ""
Write-Host "===============================================================" -ForegroundColor Green
Write-Host "  Services Started Successfully!" -ForegroundColor Green
Write-Host "===============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Services:" -ForegroundColor Cyan
Write-Host "  Database: 127.0.0.1:5434 (PostgreSQL)" -ForegroundColor White
Write-Host "  Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs: http://localhost:8000/api/docs" -ForegroundColor White
Write-Host "  Frontend: http://localhost:3000" -ForegroundColor White
Write-Host ""
Write-Host "To stop all services:" -ForegroundColor Yellow
Write-Host "  1. Close the Backend and Frontend PowerShell windows" -ForegroundColor White
Write-Host "  2. Run: docker compose down" -ForegroundColor White
Write-Host ""
Write-Host "Troubleshooting:" -ForegroundColor Yellow
Write-Host "  - Check backend logs in the Backend window" -ForegroundColor White
Write-Host "  - Check frontend logs in the Frontend window" -ForegroundColor White
Write-Host "  - Verify .env file has API keys: app\backend\.env" -ForegroundColor White
Write-Host "  - Run migrations manually: .\scripts\run-migrations.ps1" -ForegroundColor White
Write-Host ""
