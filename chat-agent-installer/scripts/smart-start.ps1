# Chat Agent Complete Startup Script for Windows
# This script handles EVERYTHING: dependencies, env setup, and startup

$ErrorActionPreference = "Stop"

function Write-Step {
    param($Message)
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host $Message -ForegroundColor Yellow
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
}

function Write-Success {
    param($Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Error {
    param($Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

Write-Host ""
Write-Host "══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   Chat Agent Complete Startup (Windows)      " -ForegroundColor Cyan
Write-Host "══════════════════════════════════════════════" -ForegroundColor Cyan

# Get paths
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $RepoRoot "app" "backend"
$FrontendDir = Join-Path $RepoRoot "app" "frontend"

Write-Host ""
Write-Host "Paths:" -ForegroundColor Gray
Write-Host "  Backend:  $BackendDir" -ForegroundColor Gray
Write-Host "  Frontend: $FrontendDir" -ForegroundColor Gray

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 1: Check Prerequisites
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Write-Step "Step 1: Checking Prerequisites"

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Success "Python: $pythonVersion"
} catch {
    Write-Error "Python not found!"
    Write-Host "Install from: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# Check Node.js
try {
    $nodeVersion = node --version 2>&1
    Write-Success "Node.js: $nodeVersion"
} catch {
    Write-Error "Node.js not found!"
    Write-Host "Install from: https://nodejs.org/" -ForegroundColor Yellow
    exit 1
}

# Check/Install pnpm
try {
    $pnpmVersion = pnpm --version 2>&1
    Write-Success "pnpm: v$pnpmVersion"
} catch {
    Write-Host "Installing pnpm globally..." -ForegroundColor Yellow
    npm install -g pnpm
    $pnpmVersion = pnpm --version 2>&1
    Write-Success "pnpm: v$pnpmVersion installed"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 2: Backend Setup
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Write-Step "Step 2: Backend Setup"

Set-Location $BackendDir

# Check for .env
if (-not (Test-Path ".env")) {
    Write-Host ""
    Write-Host "⚠ No .env file found! Creating template..." -ForegroundColor Yellow
    
    $envContent = @"
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
"@
    
    $envContent | Out-File -FilePath ".env" -Encoding UTF8 -NoNewline
    
    Write-Host ""
    Write-Host "CRITICAL: You MUST edit .env and add your OpenAI API key!" -ForegroundColor Red
    Write-Host "File: $BackendDir\.env" -ForegroundColor Yellow
    Write-Host ""
    
    $openEnv = Read-Host "Open .env in notepad now? (Y/n)"
    if ($openEnv -ne "n") {
        notepad ".env"
        Write-Host ""
        Read-Host "Press Enter after you've saved your API key"
    }
}

# Create venv
if (-not (Test-Path "venv")) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Gray
    python -m venv venv
    Write-Success "Virtual environment created"
}

# Install Python dependencies
Write-Host "Installing Python dependencies (may take a few minutes)..." -ForegroundColor Gray
& "venv\Scripts\python.exe" -m pip install --upgrade pip --quiet 2>&1 | Out-Null
& "venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet

Write-Success "Backend ready!"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 3: Frontend Setup
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Write-Step "Step 3: Frontend Setup"

Set-Location $FrontendDir

# Create pnpm-workspace.yaml
if (-not (Test-Path "pnpm-workspace.yaml")) {
    Write-Host "Creating pnpm-workspace.yaml..." -ForegroundColor Gray
    
    $workspace = @"
packages:
  - 'apps/*'
  - 'shared/*'
"@
    
    $workspace | Out-File -FilePath "pnpm-workspace.yaml" -Encoding UTF8 -NoNewline
    Write-Success "Created pnpm-workspace.yaml"
}

# Install Node dependencies
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing Node dependencies (this takes 2-5 minutes)..." -ForegroundColor Gray
    pnpm install --no-frozen-lockfile 2>&1 | Out-Null
    Write-Success "Node modules installed"
} else {
    Write-Success "Node modules already installed"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 4: Start Services
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Write-Step "Step 4: Starting Services"

# Backend start script
$backendScript = @"
Set-Location '$BackendDir'
`$env:VIRTUAL_ENV = '$BackendDir\venv'
& '$BackendDir\venv\Scripts\Activate.ps1'
Write-Host 'Starting backend on http://localhost:8000...' -ForegroundColor Cyan
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"@

$backendScriptPath = Join-Path $BackendDir "run-backend.ps1"
$backendScript | Out-File -FilePath $backendScriptPath -Encoding UTF8

# Frontend start script  
$frontendScript = @"
Set-Location '$FrontendDir'
Write-Host 'Starting frontend on http://localhost:3000...' -ForegroundColor Cyan
pnpm dev
"@

$frontendScriptPath = Join-Path $FrontendDir "run-frontend.ps1"
$frontendScript | Out-File -FilePath $frontendScriptPath -Encoding UTF8

# Launch backend
Write-Host "Launching backend server..." -ForegroundColor Gray
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $backendScriptPath

Start-Sleep -Seconds 5

# Launch frontend
Write-Host "Launching frontend server..." -ForegroundColor Gray
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $frontendScriptPath

Start-Sleep -Seconds 5

Write-Host ""
Write-Host "══════════════════════════════════════════════" -ForegroundColor Green
Write-Host "   ✓ Services Started Successfully!          " -ForegroundColor Green
Write-Host "══════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "Frontend: http://localhost:3000" -ForegroundColor White
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "Two PowerShell windows opened." -ForegroundColor Yellow
Write-Host "Close them to stop the services." -ForegroundColor Yellow
Write-Host ""

# Wait and open browser
Start-Sleep -Seconds 3
Write-Host "Opening browser..." -ForegroundColor Gray
Start-Process "http://localhost:3000"

Write-Host ""
Write-Host "Press any key to close this window..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
