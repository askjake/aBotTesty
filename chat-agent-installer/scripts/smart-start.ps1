# Smart Chat Agent Startup for Windows
# PowerShell script - Run from scripts directory

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Smart Chat Agent Startup (Windows)   " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $RepoRoot "app\backend"
$FrontendDir = Join-Path $RepoRoot "app\frontend"

Write-Host "Directories:" -ForegroundColor Yellow
Write-Host "  Backend:  $BackendDir"
Write-Host "  Frontend: $FrontendDir"
Write-Host ""

# Step 1: Check prerequisites
Write-Host "Step 1: Checking Prerequisites" -ForegroundColor Yellow
Write-Host "------------------------------" -ForegroundColor Yellow

$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python not found! Please install Python 3.12 from https://www.python.org/" -ForegroundColor Red
    exit 1
}
Write-Host "Python: $pythonVersion" -ForegroundColor Green

$nodeVersion = node --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Node.js not found! Please install from https://nodejs.org/" -ForegroundColor Red
    exit 1
}
Write-Host "Node.js: $nodeVersion" -ForegroundColor Green

$pnpmVersion = pnpm --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing pnpm..." -ForegroundColor Yellow
    npm install -g pnpm
}
Write-Host "pnpm: v$pnpmVersion" -ForegroundColor Green

Write-Host ""

# Step 2: Setup Backend
Write-Host "Step 2: Backend Setup" -ForegroundColor Yellow
Write-Host "------------------------------" -ForegroundColor Yellow

Set-Location $BackendDir

# Check for .env file
if (-not (Test-Path ".env")) {
    Write-Host "WARNING: No .env file found!" -ForegroundColor Yellow
    Write-Host "Creating template .env file..." -ForegroundColor Yellow
    
    $envTemplate = @'
DEBUG=true
LOCAL=true
AUTH_DISABLED=true
PLLM_PROVIDER=openai
PLLM_MODEL=gpt-4o
ELLM_PROVIDER=openai
ELLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-proj-YOUR-KEY-HERE
EMBED_PROVIDER=openai
EMBED_MODEL=text-embedding-3-small
LANGGRAPH_RECURSION_LIMIT=200
'@
    
    Set-Content -Path ".env" -Value $envTemplate
    
    Write-Host ""
    Write-Host "IMPORTANT: Edit .env and add your OpenAI API key!" -ForegroundColor Red
    Write-Host "File location: $BackendDir\.env" -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "Press Enter after you've added your API key, or Ctrl+C to exit"
}

# Create venv if needed
if (-not (Test-Path "venv")) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Gray
    python -m venv venv
}

# Activate and install
Write-Host "Installing Python dependencies..." -ForegroundColor Gray
& "$BackendDir\venv\Scripts\pip.exe" install --upgrade pip --quiet
& "$BackendDir\venv\Scripts\pip.exe" install -r requirements.txt --quiet

Write-Host "Backend ready!" -ForegroundColor Green
Write-Host ""

# Step 3: Setup Frontend  
Write-Host "Step 3: Frontend Setup" -ForegroundColor Yellow
Write-Host "------------------------------" -ForegroundColor Yellow

Set-Location $FrontendDir

# Create pnpm-workspace.yaml if missing
if (-not (Test-Path "pnpm-workspace.yaml")) {
    Write-Host "Creating pnpm-workspace.yaml..." -ForegroundColor Gray
    
    $workspaceContent = @'
packages:
  - 'apps/*'
  - 'shared/*'
'@
    
    Set-Content -Path "pnpm-workspace.yaml" -Value $workspaceContent
}

# Install dependencies
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing Node dependencies (this takes a few minutes)..." -ForegroundColor Gray
    pnpm install --no-frozen-lockfile
} else {
    Write-Host "Node modules already installed" -ForegroundColor Green
}

Write-Host "Frontend ready!" -ForegroundColor Green
Write-Host ""

# Step 4: Start services
Write-Host "Step 4: Starting Services" -ForegroundColor Yellow
Write-Host "------------------------------" -ForegroundColor Yellow

# Create backend start script
$backendStartScript = @'
& "$env:VIRTUAL_ENV\Scripts\Activate.ps1"
Write-Host "Starting backend on http://localhost:8000..." -ForegroundColor Cyan
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
'@

$backendScriptPath = Join-Path $BackendDir "start-backend.ps1"
Set-Content -Path $backendScriptPath -Value $backendStartScript

# Create frontend start script
$frontendStartScript = @'
Write-Host "Starting frontend on http://localhost:3000..." -ForegroundColor Cyan
pnpm dev
'@

$frontendScriptPath = Join-Path $FrontendDir "start-frontend.ps1"
Set-Content -Path $frontendScriptPath -Value $frontendStartScript

# Start backend in new window
Write-Host "Launching backend..." -ForegroundColor Gray
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $backendScriptPath -WorkingDirectory $BackendDir

Start-Sleep -Seconds 5

# Start frontend in new window
Write-Host "Launching frontend..." -ForegroundColor Gray
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $frontendScriptPath -WorkingDirectory $FrontendDir

Start-Sleep -Seconds 5

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "   Services Started Successfully!       " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "Frontend: http://localhost:3000" -ForegroundColor White
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "Two PowerShell windows opened - close them to stop services" -ForegroundColor Yellow
Write-Host ""

# Open browser after delay
Start-Sleep -Seconds 3
Write-Host "Opening browser..." -ForegroundColor Gray
Start-Process "http://localhost:3000"

Write-Host ""
Write-Host "Press any key to exit this window..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
