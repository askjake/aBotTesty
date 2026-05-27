# Chat-Agent Windows Quick Start

## Installation

1. Extract the ZIP file:
   - Right-click `chat-agent-windows-installer.zip`
   - Select "Extract All..."

2. Run the installer:
   - Right-click PowerShell
   - Select "Run as Administrator"
   - Navigate to: `chat-agent-installer\installers\windows`
   - Run: `.\install.ps1`
   
   OR simply double-click: `install.bat`

3. Follow the prompts to:
   - Install dependencies (Python, Node.js, PostgreSQL)
   - Configure database
   - Select tools
   - Configure startup

4. Access the application:
   ```
   http://localhost:3000
   ```

## Quick Commands

```powershell
# Check status
Get-Service ChatAgent*

# Start services
Start-Service ChatAgentBackend, ChatAgentFrontend

# Stop services
Stop-Service ChatAgentBackend, ChatAgentFrontend

# View logs
Get-Content "C:\ProgramData\ChatAgent\Logs\backend.log" -Tail 50 -Wait
```

## Troubleshooting

- **Services won't start**: Check Event Viewer for errors
- **Database errors**: Verify PostgreSQL is running (Services panel)
- **Permission errors**: Ensure you ran installer as Administrator

For full documentation, see README.md
