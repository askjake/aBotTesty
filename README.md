# Dish Chat Agent Installer Bundle

This repository contains the portable installer bundle for the Dish Chat Agent system.

## Contents

- `chat-agent-installer/` - Main installer package
  - `app/` - Application code (backend + frontend)
  - `installers/` - Platform-specific installers (Linux, macOS, Windows)
  - `scripts/` - Utility scripts (backup, health-check, update)
  - `docs/` - Documentation

- `transfer_bundle.sh` - Script to transfer bundle to deployment server

## Quick Start

### Linux/macOS
```bash
cd chat-agent-installer
./installers/linux/install.sh  # or ./installers/macos/install.sh
```

### Windows
```cmd
cd chat-agent-installer\installers\windows
install.bat
```

## Configuration

The transfer script requires environment variables for deployment:

```bash
export SSHPASS='your-password'
export TARGET_HOST='your-host'
export TARGET_USER='your-user'
export TARGET_PATH='~/deployment-path'

./transfer_bundle.sh bundle.tar.gz
```

## Security Notes

- Never commit credentials to this repository
- Use environment variables or secure vaults for secrets
- The `.gitignore` is configured to prevent accidental credential commits

## Documentation

See the `chat-agent-installer/docs/` directory for detailed documentation.

## License

Proprietary - Dish Technologies L.L.C.
