# Simple Startup Script for Windows
# No auto-detection, just starts the services

Write-Host "🚀 Starting Chat Agent..." -ForegroundColor Green

# Check if we're in the right directory
if (-not (Test-Path "appackend")) {
    Write-Host "❌ Error: Run this from chat-agent-installer directory" -ForegroundColor Red
    exit 1
}

# Check for .env file
if (-not (Test-Path "appackend\.env")) {
    Write-Host "⚠️  No .env file found. Creating from example..." -ForegroundColor Yellow
    if (Test-Path "appackend\.env.example") {
        Copy-Item "appackend\.env.example" "appackend\.env"
        Write-Host "✅ Created .env file. Please edit it with your API keys!" -ForegroundColor Green
        Write-Host "   File location: appackend\.env" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Press any key after you've added your API keys..."
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }
}

# Start Backend
Write-Host "
📦 Starting Backend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWDppackend'; .env\Scriptsctivate; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

# Wait a bit for backend to start
Start-Sleep -Seconds 3

# Start Frontend
Write-Host "🎨 Starting Frontend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWDpprontend'; pnpm dev"

# Wait for frontend to start
Start-Sleep -Seconds 5

# Open browser
Write-Host "🌐 Opening browser..." -ForegroundColor Green
Start-Process "http://localhost:3000"

Write-Host "
✅ Services started!" -ForegroundColor Green
Write-Host "   Backend:  http://localhost:8000" -ForegroundColor Cyan
Write-Host "   Frontend: http://localhost:3000" -ForegroundColor Cyan
Write-Host "
Close the PowerShell windows to stop the services." -ForegroundColor Yellow
