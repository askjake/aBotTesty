# Chat-Agent Linux Quick Start

## Installation

1. Extract the package:
   ```bash
   tar -xzf chat-agent-linux-installer.tar.gz
   cd chat-agent-installer
   ```

2. Run the installer:
   ```bash
   cd installers/linux
   sudo ./install.sh
   ```

3. Follow the prompts to:
   - Install dependencies
   - Configure database
   - Select tools
   - Configure startup

4. Access the application:
   ```
   http://localhost:3000
   ```

## Quick Commands

```bash
# Check status
sudo systemctl status chat-agent-backend chat-agent-frontend

# Start services
sudo systemctl start chat-agent-backend chat-agent-frontend

# Stop services
sudo systemctl stop chat-agent-backend chat-agent-frontend

# View logs
sudo journalctl -u chat-agent-backend -f

# Health check
./scripts/health-check.sh
```

## Troubleshooting

- **Services won't start**: Check logs with `journalctl -u chat-agent-backend`
- **Database errors**: Verify PostgreSQL is running and credentials are correct
- **Port conflicts**: Check if ports 8000 and 3000 are available

For full documentation, see README.md
