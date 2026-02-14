# Chat-Agent Installation Package

Complete installation package for the Chat-Agent application, including backend (FastAPI/Python), frontend (Next.js/React), and all necessary components.

## 📦 Package Contents

```
chat-agent-package/
├── app/
│   ├── backend/           # Python FastAPI backend
│   ├── frontend/          # Next.js React frontend
│   └── config/            # Configuration templates
├── installers/
│   ├── linux/             # Linux installer (Ubuntu, Debian, CentOS, RHEL, Fedora)
│   ├── windows/           # Windows installer (PowerShell)
│   └── macos/             # macOS installer (Homebrew-based)
├── scripts/               # Utility scripts
└── docs/                  # Additional documentation

```

## 🚀 Quick Start

### Linux
```bash
cd installers/linux
sudo ./install.sh
```

### Windows
1. Right-click PowerShell and select "Run as Administrator"
2. Navigate to the installers/windows directory
3. Run: `.\install.ps1`
   
Or simply double-click `install.bat`

### macOS
```bash
cd installers/macos
./install.sh
```

## 📋 System Requirements

### All Platforms
- **Python**: 3.10 or higher (3.12 recommended)
- **Node.js**: 20.x or higher
- **PostgreSQL**: 14.x or higher
- **RAM**: 4GB minimum, 8GB recommended
- **Disk Space**: 2GB for application + database storage

### Linux
- Ubuntu 20.04+, Debian 11+, CentOS 8+, RHEL 8+, or Fedora 35+
- systemd for service management

### Windows
- Windows 10 or Windows Server 2019 or later
- PowerShell 5.1 or higher
- Administrator privileges

### macOS
- macOS 11.0 (Big Sur) or later
- Homebrew package manager (will be installed if not present)

## 🔧 Installation Process

The installer will guide you through:

1. **Dependency Installation**
   - Python, Node.js, PostgreSQL, and other required packages
   - Automatic detection of already-installed components

2. **Application Setup**
   - Backend virtual environment and Python dependencies
   - Frontend build and Node.js dependencies
   - Configuration file creation

3. **Database Configuration**
   - PostgreSQL database and user creation
   - Connection string configuration
   - Schema initialization

4. **Tool Selection**
   - Choose which tools to enable:
     - `public_web_search` - Search public web
     - `internal_search` - Search internal systems
     - `netra_search` - Netra log search
     - `dish_internal_tool` - DISH internal tools
     - `cluster_inspect` - Kubernetes cluster inspection

5. **Service Configuration**
   - Automatic service creation
   - Optional startup on boot
   - Service management setup

## 🔐 Security Considerations

### Configuration File
After installation, edit the configuration file to set secure values:

**Linux**: `/etc/chat-agent/.env`  
**Windows**: `C:\ProgramData\ChatAgent\.env`  
**macOS**: `~/Library/Application Support/ChatAgent/.env`

### Required Security Settings
```bash
# Generate secure random keys
SECRET_KEY=<generate-32-char-random-string>
ENCRYPTION_KEY=<generate-32-char-random-string>

# Set strong database password
POSTGRES_PASSWORD=<strong-password>
```

### API Keys
If using external services, add your API keys:
```bash
ANTHROPIC_API_KEY=<your-key>
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>
```

## 🎯 Tool Permissions

During installation, you'll configure which tools are available. Each tool has different permission requirements:

### public_web_search
- **Purpose**: Search public internet
- **Permissions**: Internet access
- **Security**: No sensitive data sent externally

### internal_search
- **Purpose**: Search DISH internal systems (Confluence, JIRA, Git)
- **Permissions**: Network access to internal systems
- **Security**: Requires VPN/internal network

### netra_search
- **Purpose**: Search Netra logs and records
- **Permissions**: Netra system access
- **Security**: Internal only

### dish_internal_tool
- **Purpose**: Access CART, CCTools, Portal
- **Permissions**: DISH internal tool access
- **Security**: Requires authentication

### cluster_inspect
- **Purpose**: Kubernetes cluster inspection
- **Permissions**: kubectl access, cluster credentials
- **Security**: Read-only operations

## 🚦 Post-Installation

### Verify Installation

**Linux**:
```bash
sudo systemctl status chat-agent-backend
sudo systemctl status chat-agent-frontend
```

**Windows**:
```powershell
Get-Service ChatAgent*
```

**macOS**:
```bash
launchctl list | grep chatagent
```

### Access the Application

Open your browser and navigate to:
```
http://localhost:3000
```

### View Logs

**Linux**:
```bash
# Backend logs
sudo journalctl -u chat-agent-backend -f

# Or direct log files
tail -f /var/log/chat-agent/backend.log
```

**Windows**:
```powershell
# View logs
Get-Content "C:\ProgramData\ChatAgent\Logs\backend.log" -Tail 50 -Wait
```

**macOS**:
```bash
tail -f ~/Library/Logs/ChatAgent/backend.log
```

## 🔄 Starting and Stopping Services

### Linux
```bash
# Start
sudo systemctl start chat-agent-backend chat-agent-frontend

# Stop
sudo systemctl stop chat-agent-backend chat-agent-frontend

# Restart
sudo systemctl restart chat-agent-backend chat-agent-frontend

# Enable on boot
sudo systemctl enable chat-agent-backend chat-agent-frontend

# Disable on boot
sudo systemctl disable chat-agent-backend chat-agent-frontend
```

### Windows
```powershell
# Start
Start-Service ChatAgentBackend, ChatAgentFrontend

# Stop
Stop-Service ChatAgentBackend, ChatAgentFrontend

# Restart
Restart-Service ChatAgentBackend, ChatAgentFrontend

# Set startup type
Set-Service ChatAgentBackend -StartupType Automatic
Set-Service ChatAgentFrontend -StartupType Automatic
```

### macOS
```bash
# Start
launchctl load ~/Library/LaunchAgents/com.dish.chatagent.backend.plist
launchctl load ~/Library/LaunchAgents/com.dish.chatagent.frontend.plist

# Stop
launchctl unload ~/Library/LaunchAgents/com.dish.chatagent.backend.plist
launchctl unload ~/Library/LaunchAgents/com.dish.chatagent.frontend.plist
```

## 🔧 Configuration

### Environment Variables

Edit the `.env` file in the configuration directory:

```bash
# Backend
BACKEND_PORT=8000
BACKEND_HOST=0.0.0.0
DEBUG=false

# Frontend
FRONTEND_PORT=3000
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=chatbot
POSTGRES_USER=chatbot_user
POSTGRES_PASSWORD=your_password

# Security
SECRET_KEY=your_secret_key
ENCRYPTION_KEY=your_encryption_key

# Tools
ENABLED_TOOLS=public_web_search,internal_search

# Optional: AWS
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret

# Optional: LLM
ANTHROPIC_API_KEY=your_key
```

### Changing Ports

If you need to change the default ports:

1. Edit the `.env` file
2. Update `BACKEND_PORT` and `FRONTEND_PORT`
3. Update `NEXT_PUBLIC_BACKEND_URL` to match new backend port
4. Restart services

## 🗑️ Uninstallation

### Linux
```bash
# Stop and disable services
sudo systemctl stop chat-agent-backend chat-agent-frontend
sudo systemctl disable chat-agent-backend chat-agent-frontend

# Remove service files
sudo rm /etc/systemd/system/chat-agent-*.service
sudo systemctl daemon-reload

# Remove application
sudo rm -rf /opt/chat-agent
sudo rm -rf /etc/chat-agent
sudo rm -rf /var/log/chat-agent
sudo rm -rf /var/lib/chat-agent

# Remove user
sudo userdel chat-agent
```

### Windows
```powershell
# Stop and remove services
Stop-Service ChatAgentBackend, ChatAgentFrontend
nssm remove ChatAgentBackend confirm
nssm remove ChatAgentFrontend confirm

# Remove application
Remove-Item -Recurse -Force "$env:ProgramFiles\ChatAgent"
Remove-Item -Recurse -Force "$env:ProgramData\ChatAgent"
```

### macOS
```bash
# Stop and remove services
launchctl unload ~/Library/LaunchAgents/com.dish.chatagent.*.plist
rm ~/Library/LaunchAgents/com.dish.chatagent.*.plist

# Remove application
rm -rf /Applications/ChatAgent
rm -rf ~/Library/Application\ Support/ChatAgent
rm -rf ~/Library/Logs/ChatAgent
rm -rf /Applications/Chat-Agent.app
```

## 🐛 Troubleshooting

### Backend won't start

1. Check logs for errors
2. Verify database connection
3. Ensure all dependencies are installed
4. Check port 8000 is not in use

### Frontend won't start

1. Check logs for errors
2. Verify backend is running
3. Check `NEXT_PUBLIC_BACKEND_URL` in config
4. Check port 3000 is not in use

### Database connection errors

1. Verify PostgreSQL is running
2. Check database credentials in `.env`
3. Ensure database and user exist
4. Test connection: `psql -U chatbot_user -d chatbot -h localhost`

### Permission errors (Linux)

1. Check file ownership: `ls -la /opt/chat-agent`
2. Ensure chat-agent user exists: `id chat-agent`
3. Fix permissions: `sudo chown -R chat-agent:chat-agent /opt/chat-agent`

## 📚 Additional Documentation

- **Backend API**: See `docs/backend-api.md`
- **Frontend Guide**: See `docs/frontend-guide.md`
- **Tool Configuration**: See `docs/tools-configuration.md`
- **Security Best Practices**: See `docs/security.md`

## 🆘 Support

For issues or questions:

1. Check the logs (see "View Logs" section above)
2. Review the troubleshooting section
3. Check the documentation in the `docs/` directory
4. Contact your system administrator

## 📝 License

Internal use only. All rights reserved.

## 🔄 Version

**Version**: 1.0.0  
**Build Date**: 2026-02-04  
**Python**: 3.12+  
**Node.js**: 20+  
**PostgreSQL**: 14+


---

## 🤖 Multi-LLM Provider Support

This chat agent now supports multiple LLM providers! You can use:

- **OpenAI** (ChatGPT) - GPT-4, GPT-3.5
- **Anthropic** (Claude) - Claude 3.5 Sonnet, Haiku
- **Google** (Gemini) - Gemini 1.5 Pro, Flash
- **Ollama** (Local) - Run models locally on your machine
- **AWS Bedrock** - Claude via AWS
- **Custom** - Any OpenAI-compatible API

### Quick Start with LLM Providers

#### Option 1: Auto-Discovery (Recommended)

The app will automatically detect available providers when you start it:

```bash
# Linux/macOS
./scripts/smart-start.sh

# Windows
.\scripts\smart-start.ps1
```

This will:
1. Detect API keys from environment variables
2. Discover local Ollama instances
3. Start the application with available providers

#### Option 2: Manual Configuration

1. Set environment variables for your preferred providers:

```bash
# For OpenAI
export OPENAI_API_KEY="sk-proj-your-key-here"

# For Anthropic
export ANTHROPIC_API_KEY="sk-ant-your-key-here"

# For Google Gemini
export GOOGLE_API_KEY="your-gemini-key-here"
```

2. Or install Ollama for local LLMs:

```bash
# Install Ollama from https://ollama.ai
ollama pull llama3
ollama serve  # Runs on http://localhost:11434
```

3. Configure providers in the UI:
   - Open the app at http://localhost:3000
   - Click "⚙️ Settings" → "LLM Providers"
   - Click "➕ Add Provider" or "🔍 Auto-Discover"

### Managing LLM Providers

#### Via Web UI

1. **Add a Provider:**
   - Settings → LLM Providers → Add Provider
   - Enter name, type, and API key
   - Click "Test" to verify connection

2. **Switch Providers:**
   - Use the dropdown in the chat interface
   - Select your preferred provider for each conversation

3. **Set Default:**
   - Click "Set Default" on your preferred provider
   - All new chats will use this provider

#### Via Environment Variables

The app reads these environment variables on startup:

```bash
# LLM Provider Configuration
OPENAI_API_KEY=sk-proj-...        # For OpenAI/ChatGPT
ANTHROPIC_API_KEY=sk-ant-...      # For Anthropic/Claude
GOOGLE_API_KEY=...                # For Google/Gemini

# Legacy configuration (still supported)
PLLM_PROVIDER=openai              # Default: aws-bedrock
PLLM_MODEL=gpt-4o                 # Power model
ELLM_PROVIDER=openai              # Efficient provider
ELLM_MODEL=gpt-4o-mini            # Efficient model
```

### Using Ollama (Local LLMs)

1. Install Ollama: https://ollama.ai
2. Pull a model:
   ```bash
   ollama pull llama3
   ollama pull mistral
   ollama pull codellama
   ```
3. Start Ollama: `ollama serve`
4. The app will auto-discover it on startup!

### Custom / Self-Hosted LLMs

For any OpenAI-compatible API:

1. Add a "Custom" provider in Settings
2. Set the API Base URL (e.g., `http://localhost:8080/v1`)
3. Optionally set an API key if required
4. Test the connection

### API Endpoints

The following new REST API endpoints are available:

```
GET    /rest/api/v1/llm-providers              # List all providers
POST   /rest/api/v1/llm-providers              # Create provider
GET    /rest/api/v1/llm-providers/{id}         # Get provider
PUT    /rest/api/v1/llm-providers/{id}         # Update provider
DELETE /rest/api/v1/llm-providers/{id}         # Delete provider
POST   /rest/api/v1/llm-providers/{id}/set-default  # Set as default
POST   /rest/api/v1/llm-providers/test         # Test connection
POST   /rest/api/v1/llm-providers/discover     # Auto-discover
```

Full API documentation: http://localhost:8000/docs

---
