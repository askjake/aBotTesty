# Complete Quick Start for Windows
# This script starts PostgreSQL AND the application

Write-Host "Starting Dish-Chat..." -ForegroundColor Green

# Check if we're in the right directory
if (-not (Test-Path "docker-compose.yml")) {
    Write-Host "Error: Run this from chat-agent-installer directory" -ForegroundColor Red
    Write-Host "Expected location: chat-agent-installer/" -ForegroundColor Yellow
    exit 1
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
    Write-Host ""
    Write-Host "Starting PostgreSQL database..." -ForegroundColor Cyan
    docker compose up -d
    
    Write-Host "Waiting for database to be ready..." -ForegroundColor Cyan
    Start-Sleep -Seconds 5
    
    # Check database is healthy
    $dbHealthy = docker compose ps --format json | ConvertFrom-Json | Where-Object { $_.Health -eq "healthy" }
    if ($dbHealthy) {
        Write-Host "Database is ready!" -ForegroundColor Green
    } else {
        Write-Host "Database is starting... (may take a few more seconds)" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "Docker not available. Make sure PostgreSQL is running manually:" -ForegroundColor Yellow
    Write-Host "  Host: 127.0.0.1" -ForegroundColor Cyan
    Write-Host "  Port: 5434" -ForegroundColor Cyan
    Write-Host "  Database: dishchat" -ForegroundColor Cyan
    Write-Host "  User: dev_user" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Press any key to continue (or Ctrl+C to abort)..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

# Start Backend
Write-Host ""
Write-Host "Starting Backend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\app\backend'; .\venv\Scripts\activate; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

# Wait for backend to start
Write-Host "Waiting for backend to start..." -ForegroundColor Cyan
Start-Sleep -Seconds 10

# Start Frontend
Write-Host "Starting Frontend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\app\frontend'; pnpm dev"

# Wait for frontend to start
Start-Sleep -Seconds 5

# Open browser
Write-Host "Opening browser..." -ForegroundColor Green
Start-Process "http://localhost:3000"

Write-Host ""
Write-Host "Services started!" -ForegroundColor Green
Write-Host "  Database: 127.0.0.1:5434 (PostgreSQL)" -ForegroundColor Cyan
Write-Host "  Backend:  http://localhost:8000" -ForegroundColor Cyan
Write-Host "  Frontend: http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "To stop all services:" -ForegroundColor Yellow
Write-Host "  1. Close the Backend and Frontend PowerShell windows" -ForegroundColor Yellow
Write-Host "  2. Run: docker compose down" -ForegroundColor Yellow
Write-Host ""
