# Chat-Agent Windows Installer
# Requires: PowerShell 5.1+ and Administrator privileges

#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"

# Configuration
$AppName = "ChatAgent"
$InstallDir = "$env:ProgramFiles\$AppName"
$ConfigDir = "$env:ProgramData\$AppName"
$LogDir = "$env:ProgramData\$AppName\Logs"
$DataDir = "$env:ProgramData\$AppName\Data"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "                    Chat-Agent Installation Wizard" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Function to check if running as admin
function Test-Administrator {
    $user = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($user)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Administrator)) {
    Write-Host "Error: This installer must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Function to check if Chocolatey is installed
function Test-Chocolatey {
    try {
        choco --version | Out-Null
        return $true
    } catch {
        return $false
    }
}

# Function to install Chocolatey
function Install-Chocolatey {
    Write-Host "Installing Chocolatey package manager..." -ForegroundColor Yellow
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    Write-Host "✓ Chocolatey installed" -ForegroundColor Green
}

# Function to install dependencies
function Install-Dependencies {
    Write-Host "Installing system dependencies..." -ForegroundColor Yellow
    
    # Check and install Chocolatey if needed
    if (-not (Test-Chocolatey)) {
        Install-Chocolatey
        # Refresh environment
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    }
    
    # Install Python
    Write-Host "Installing Python 3.12..." -ForegroundColor Yellow
    choco install python312 -y
    
    # Install Node.js
    Write-Host "Installing Node.js..." -ForegroundColor Yellow
    choco install nodejs-lts -y
    
    # Install PostgreSQL
    $installPostgres = Read-Host "Install PostgreSQL? (Y/n)"
    if ($installPostgres -ne "n") {
        Write-Host "Installing PostgreSQL..." -ForegroundColor Yellow
        choco install postgresql14 -y --params '/Password:postgres'
    }
    
    # Install Git (useful for updates)
    Write-Host "Installing Git..." -ForegroundColor Yellow
    choco install git -y
    
    # Refresh environment variables
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    # Install pnpm
    Write-Host "Installing pnpm..." -ForegroundColor Yellow
    npm install -g pnpm
    
    Write-Host "✓ Dependencies installed" -ForegroundColor Green
}

# Function to create directories
function New-AppDirectories {
    Write-Host "Creating application directories..." -ForegroundColor Yellow
    
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
    New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
    New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
    
    Write-Host "✓ Directories created" -ForegroundColor Green
}

# Function to copy files
function Copy-AppFiles {
    Write-Host "Copying application files..." -ForegroundColor Yellow
    
    $sourceDir = Split-Path -Parent $PSScriptRoot
    Copy-Item -Path "$sourceDir\app\*" -Destination $InstallDir -Recurse -Force
    Copy-Item -Path "$sourceDir\app\config\.env.template" -Destination "$ConfigDir\.env" -Force
    
    Write-Host "✓ Files copied" -ForegroundColor Green
}

# Function to setup backend
function Install-Backend {
    Write-Host "Setting up backend..." -ForegroundColor Yellow
    
    Set-Location "$InstallDir\backend"
    
    # Create virtual environment
    python -m venv venv
    
    # Activate and install dependencies
    & ".\venv\Scripts\Activate.ps1"
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    deactivate
    
    Write-Host "✓ Backend setup complete" -ForegroundColor Green
}

# Function to setup frontend
function Install-Frontend {
    Write-Host "Setting up frontend..." -ForegroundColor Yellow
    
    Set-Location "$InstallDir\frontend"
    
    pnpm install
    pnpm build
    
    Write-Host "✓ Frontend setup complete" -ForegroundColor Green
}

# Function to configure database
function Set-DatabaseConfig {
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host "                        Database Configuration" -ForegroundColor Cyan
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host ""
    
    $configDb = Read-Host "Configure PostgreSQL database? (Y/n)"
    
    if ($configDb -ne "n") {
        $dbName = Read-Host "Database name [chatbot]"
        if ([string]::IsNullOrWhiteSpace($dbName)) { $dbName = "chatbot" }
        
        $dbUser = Read-Host "Database user [chatbot_user]"
        if ([string]::IsNullOrWhiteSpace($dbUser)) { $dbUser = "chatbot_user" }
        
        $dbPass = Read-Host "Database password" -AsSecureString
        $dbPassPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
            [Runtime.InteropServices.Marshal]::SecureStringToBSTR($dbPass)
        )
        
        # Update .env file
        $envFile = "$ConfigDir\.env"
        (Get-Content $envFile) -replace "POSTGRES_DB=.*", "POSTGRES_DB=$dbName" | Set-Content $envFile
        (Get-Content $envFile) -replace "POSTGRES_USER=.*", "POSTGRES_USER=$dbUser" | Set-Content $envFile
        (Get-Content $envFile) -replace "POSTGRES_PASSWORD=.*", "POSTGRES_PASSWORD=$dbPassPlain" | Set-Content $envFile
        
        Write-Host "✓ Database configuration saved" -ForegroundColor Green
        Write-Host ""
        Write-Host "Note: You'll need to create the database manually using pgAdmin or psql" -ForegroundColor Yellow
    }
}

# Function to configure tools
function Set-ToolsConfig {
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host "                        Tool Configuration" -ForegroundColor Cyan
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Select which tools to enable:" -ForegroundColor Yellow
    Write-Host ""
    
    $tools = @("public_web_search", "internal_search", "netra_search", "dish_internal_tool", "cluster_inspect")
    $enabledTools = @()
    
    foreach ($tool in $tools) {
        $enable = Read-Host "Enable $tool? (Y/n)"
        if ($enable -ne "n") {
            $enabledTools += $tool
        }
    }
    
    # Save to config
    $toolsString = $enabledTools -join ","
    Add-Content -Path "$ConfigDir\.env" -Value "ENABLED_TOOLS=$toolsString"
    
    Write-Host "✓ Tools configured" -ForegroundColor Green
}

# Function to create Windows services
function New-WindowsServices {
    Write-Host "Creating Windows services..." -ForegroundColor Yellow
    
    # Create NSSM wrapper scripts
    $backendScript = @"
@echo off
cd /d "$InstallDir\backend"
call venv\Scripts\activate.bat
set /p DUMMY=<"$ConfigDir\.env"
uvicorn app.main:app --host 0.0.0.0 --port 8000
"@
    
    $backendScript | Out-File -FilePath "$InstallDir\start-backend.bat" -Encoding ASCII
    
    $frontendScript = @"
@echo off
cd /d "$InstallDir\frontend"
set /p DUMMY=<"$ConfigDir\.env"
pnpm start
"@
    
    $frontendScript | Out-File -FilePath "$InstallDir\start-frontend.bat" -Encoding ASCII
    
    # Install NSSM for service management
    choco install nssm -y
    
    # Create services
    nssm install ChatAgentBackend "$InstallDir\start-backend.bat"
    nssm set ChatAgentBackend AppDirectory "$InstallDir\backend"
    nssm set ChatAgentBackend AppStdout "$LogDir\backend.log"
    nssm set ChatAgentBackend AppStderr "$LogDir\backend-error.log"
    
    nssm install ChatAgentFrontend "$InstallDir\start-frontend.bat"
    nssm set ChatAgentFrontend AppDirectory "$InstallDir\frontend"
    nssm set ChatAgentFrontend AppStdout "$LogDir\frontend.log"
    nssm set ChatAgentFrontend AppStderr "$LogDir\frontend-error.log"
    nssm set ChatAgentFrontend DependOnService ChatAgentBackend
    
    Write-Host "✓ Services created" -ForegroundColor Green
}

# Function to configure startup
function Set-StartupConfig {
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host "                        Startup Configuration" -ForegroundColor Cyan
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host ""
    
    $enableStartup = Read-Host "Enable services to start on boot? (Y/n)"
    
    if ($enableStartup -ne "n") {
        Set-Service -Name ChatAgentBackend -StartupType Automatic
        Set-Service -Name ChatAgentFrontend -StartupType Automatic
        Write-Host "✓ Services enabled for startup" -ForegroundColor Green
    }
    
    $startNow = Read-Host "Start services now? (Y/n)"
    
    if ($startNow -ne "n") {
        Start-Service -Name ChatAgentBackend
        Start-Sleep -Seconds 5
        Start-Service -Name ChatAgentFrontend
        Write-Host "✓ Services started" -ForegroundColor Green
    }
}

# Function to create desktop shortcut
function New-DesktopShortcut {
    $createShortcut = Read-Host "Create desktop shortcut? (Y/n)"
    
    if ($createShortcut -ne "n") {
        $WshShell = New-Object -ComObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\Chat-Agent.url")
        $Shortcut.TargetPath = "http://localhost:3000"
        $Shortcut.Save()
        Write-Host "✓ Desktop shortcut created" -ForegroundColor Green
    }
}

# Main installation flow
try {
    Write-Host "Starting installation..." -ForegroundColor Yellow
    Write-Host ""
    
    Install-Dependencies
    New-AppDirectories
    Copy-AppFiles
    Install-Backend
    Install-Frontend
    Set-DatabaseConfig
    Set-ToolsConfig
    New-WindowsServices
    Set-StartupConfig
    New-DesktopShortcut
    
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor Green
    Write-Host "                    Installation Complete!" -ForegroundColor Green
    Write-Host "================================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Application installed to: $InstallDir" -ForegroundColor Cyan
    Write-Host "Configuration: $ConfigDir\.env" -ForegroundColor Cyan
    Write-Host "Logs: $LogDir" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Useful commands:" -ForegroundColor Yellow
    Write-Host "  Start services:   Start-Service ChatAgentBackend, ChatAgentFrontend"
    Write-Host "  Stop services:    Stop-Service ChatAgentBackend, ChatAgentFrontend"
    Write-Host "  Check status:     Get-Service ChatAgent*"
    Write-Host "  View logs:        Get-Content $LogDir\backend.log -Tail 50 -Wait"
    Write-Host ""
    Write-Host "Access the application at: http://localhost:3000" -ForegroundColor Green
    Write-Host ""
    
    Read-Host "Press Enter to exit"
    
} catch {
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor Red
    Write-Host "                    Installation Failed!" -ForegroundColor Red
    Write-Host "================================================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please check the error message above and try again." -ForegroundColor Yellow
    Write-Host "For support, check the documentation or contact your administrator." -ForegroundColor Yellow
    Write-Host ""
    
    Read-Host "Press Enter to exit"
    exit 1
}
