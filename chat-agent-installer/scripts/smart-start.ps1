# Smart Chat Agent Startup for Windows
# PowerShell script

$ErrorActionPreference = "Stop"

Write-Host "🚀 Smart Chat Agent Startup" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $RepoRoot "app\backend"
$FrontendDir = Join-Path $RepoRoot "app\frontend"

# Run environment detection
Write-Host "Step 1: Environment Detection" -ForegroundColor Yellow
Write-Host "------------------------------" -ForegroundColor Yellow
python (Join-Path $ScriptDir "detect-environment.py")
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host ""
Write-Host "Step 2: Backend Setup" -ForegroundColor Yellow
Write-Host "------------------------------" -ForegroundColor Yellow
Set-Location $BackendDir

# Create venv if needed
if (-not (Test-Path "venv")) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Gray
    python -m venv venv
}

# Activate venv
& ".\venv\Scripts\Activate.ps1"

# Install dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Gray
pip install --upgrade pip -q
pip install -r requirements.txt -q

Write-Host "✓ Backend ready" -ForegroundColor Green

Write-Host ""
Write-Host "Step 3: Frontend Setup" -ForegroundColor Yellow
Write-Host "------------------------------" -ForegroundColor Yellow
Set-Location $FrontendDir

# Create workspace file if missing
if (-not (Test-Path "pnpm-workspace.yaml")) {
    @"
packages:
  - 'apps/*'
  - 'shared/*'
"@ | Out-File -FilePath "pnpm-workspace.yaml" -Encoding UTF8
    Write-Host "✓ Created pnpm-workspace.yaml" -ForegroundColor Green
}

# Install dependencies
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing Node dependencies (this may take a while)..." -ForegroundColor Gray
    pnpm install --no-frozen-lockfile
}

Write-Host "✓ Frontend ready" -ForegroundColor Green

Write-Host ""
Write-Host "Step 4: Starting Services" -ForegroundColor Yellow
Write-Host "------------------------------" -ForegroundColor Yellow

# Start backend in new window
Set-Location $BackendDir
$BackendScript = @"
& ".\venv\Scripts\Activate.ps1"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"@
$BackendScript | Out-File -FilePath "start-backend.ps1" -Encoding UTF8

Write-Host "Starting backend on http://localhost:8000..." -ForegroundColor Gray
Start-Process powershell -ArgumentList "-NoExit", "-File", ".\start-backend.ps1"

# Wait for backend
Start-Sleep -Seconds 3

# Start frontend in new window
Set-Location $FrontendDir
$FrontendScript = @"
pnpm dev
"@
$FrontendScript | Out-File -FilePath "start-frontend.ps1" -Encoding UTF8

Write-Host "Starting frontend on http://localhost:3000..." -ForegroundColor Gray
Start-Process powershell -ArgumentList "-NoExit", "-File", ".\start-frontend.ps1"

# Wait for frontend
Start-Sleep -Seconds 5

Write-Host ""
Write-Host "✅ Services Started!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "Frontend: http://localhost:3000" -ForegroundColor White
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "Two new PowerShell windows have been opened." -ForegroundColor Yellow
Write-Host "Close them to stop the services." -ForegroundColor Yellow
Write-Host ""

# Open browser
Start-Sleep -Seconds 2
Start-Process "http://localhost:3000"
