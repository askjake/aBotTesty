# Run Database Migrations Manually
# Run this from: chat-agent-installer/

Write-Host ""
Write-Host "===============================================================" -ForegroundColor Cyan
Write-Host "  Database Migration Helper" -ForegroundColor Cyan
Write-Host "===============================================================" -ForegroundColor Cyan
Write-Host ""

# Check location
if (-not (Test-Path "app\backend\app\alembic.ini")) {
    Write-Host "ERROR: Cannot find app/backend/app/alembic.ini" -ForegroundColor Red
    Write-Host ""
    Write-Host "Make sure you're in the chat-agent-installer directory" -ForegroundColor Yellow
    exit 1
}

Write-Host "Running database migrations..." -ForegroundColor Cyan
Write-Host ""

# Change to the correct directory (where alembic.ini is)
Push-Location "$PWD\app\backend\app"

# Activate venv if it exists
if (Test-Path "..\venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Cyan
    & "..\venv\Scripts\Activate.ps1"
}

# Run alembic
Write-Host ""
Write-Host "Running: alembic upgrade head" -ForegroundColor Cyan
Write-Host ""
alembic upgrade head

$result = $LASTEXITCODE
Pop-Location

Write-Host ""
if ($result -eq 0) {
    Write-Host "===============================================================" -ForegroundColor Green
    Write-Host "  [OK] Migrations Complete!" -ForegroundColor Green
    Write-Host "===============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Database tables have been created successfully." -ForegroundColor Green
    Write-Host "You can now start the application." -ForegroundColor Green
} else {
    Write-Host "===============================================================" -ForegroundColor Red
    Write-Host "  [ERROR] Migration Failed!" -ForegroundColor Red
    Write-Host "===============================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Check the error messages above for details." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Common issues:" -ForegroundColor Yellow
    Write-Host "  - Database not running: docker compose up -d" -ForegroundColor Cyan
    Write-Host "  - Wrong directory: Must be in chat-agent-installer/" -ForegroundColor Cyan
    Write-Host "  - Dependencies missing: pip install -r requirements.txt" -ForegroundColor Cyan
}

Write-Host ""
