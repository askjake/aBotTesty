# Frontend Setup Script for Windows
# Run this after cloning the repo

Write-Host "Setting up Frontend Environment..." -ForegroundColor Green

# Check if we're in the right directory
if (-not (Test-Path "pnpm-workspace.yaml")) {
    Write-Host "Error: Run this from the frontend directory" -ForegroundColor Red
    exit 1
}

# Create .env.local files if they don't exist
Write-Host ""
Write-Host "Creating .env.local files..." -ForegroundColor Cyan

$apps = @("apps\chats", "apps\beta-reports")

foreach ($app in $apps) {
    $envLocal = "$app\.env.local"
    $envExample = "$app\.env.example"
    
    if (-not (Test-Path $envLocal)) {
        if (Test-Path $envExample) {
            Copy-Item $envExample $envLocal
            Write-Host "Created: $envLocal" -ForegroundColor Green
        } else {
            Write-Host "No .env.example found for $app" -ForegroundColor Yellow
        }
    } else {
        Write-Host "$envLocal already exists" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "Installing dependencies..." -ForegroundColor Cyan
pnpm install

Write-Host ""
Write-Host "Frontend setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To start development server:"
Write-Host "  pnpm dev" -ForegroundColor Cyan
Write-Host ""
Write-Host "The frontend will be available at:"
Write-Host "  http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
