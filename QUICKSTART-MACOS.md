# Chat-Agent macOS Quick Start

## Installation

1. Extract the package:
   ```bash
   tar -xzf chat-agent-macos-installer.tar.gz
   cd chat-agent-installer
   ```

2. Run the installer:
   ```bash
   cd installers/macos
   ./install.sh
   ```

3. Follow the prompts to:
   - Install Homebrew (if needed)
   - Install dependencies
   - Configure database
   - Select tools
   - Configure startup

4. Access the application:
   ```
   http://localhost:3000
   ```
   
   Or launch from Applications: `Chat-Agent.app`

## Quick Commands

```bash
# Check status
launchctl list | grep chatagent

# Start services
launchctl load ~/Library/LaunchAgents/com.dish.chatagent.*.plist

# Stop services
launchctl unload ~/Library/LaunchAgents/com.dish.chatagent.*.plist

# View logs
tail -f ~/Library/Logs/ChatAgent/backend.log
```

## Troubleshooting

- **Services won't start**: Check logs in `~/Library/Logs/ChatAgent/`
- **Database errors**: Verify PostgreSQL is running: `brew services list`
- **Permission errors**: Check file permissions in `/Applications/ChatAgent`

For full documentation, see README.md
