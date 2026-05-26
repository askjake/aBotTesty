#!/bin/bash
# Chat-Agent Update Script
# Updates the application to a new version

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

INSTALL_DIR="/opt/chat-agent"

echo "================================================================================"
echo "                    Chat-Agent Update"
echo "================================================================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
    exit 1
fi

# Backup current installation
echo "Creating backup..."
BACKUP_DIR="/opt/chat-agent-backup-$(date +%Y%m%d-%H%M%S)"
cp -r $INSTALL_DIR $BACKUP_DIR
echo -e "${GREEN}✓ Backup created: $BACKUP_DIR${NC}"

# Stop services
echo "Stopping services..."
systemctl stop chat-agent-backend chat-agent-frontend
echo -e "${GREEN}✓ Services stopped${NC}"

# Update backend
echo "Updating backend..."
cd $INSTALL_DIR/backend
sudo -u chat-agent venv/bin/pip install --upgrade -r requirements.txt
echo -e "${GREEN}✓ Backend updated${NC}"

# Update frontend
echo "Updating frontend..."
cd $INSTALL_DIR/frontend
sudo -u chat-agent pnpm install
sudo -u chat-agent pnpm build
echo -e "${GREEN}✓ Frontend updated${NC}"

# Start services
echo "Starting services..."
systemctl start chat-agent-backend chat-agent-frontend
echo -e "${GREEN}✓ Services started${NC}"

echo ""
echo "Update complete!"
echo "Backup location: $BACKUP_DIR"
echo ""
