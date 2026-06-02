#!/bin/bash
# Chat-Agent Backup Script
# Creates a complete backup of the application and database

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

BACKUP_DIR="${1:-/opt/chat-agent-backups}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_NAME="chat-agent-backup-$TIMESTAMP"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

echo "================================================================================"
echo "                    Chat-Agent Backup"
echo "================================================================================"
echo ""

# Create backup directory
mkdir -p $BACKUP_PATH

# Backup application files
echo "Backing up application files..."
tar -czf $BACKUP_PATH/app.tar.gz -C /opt chat-agent
echo -e "${GREEN}✓ Application backed up${NC}"

# Backup configuration
echo "Backing up configuration..."
tar -czf $BACKUP_PATH/config.tar.gz -C /etc chat-agent
echo -e "${GREEN}✓ Configuration backed up${NC}"

# Backup database
echo "Backing up database..."
pg_dump -h localhost -U chatbot_user chatbot | gzip > $BACKUP_PATH/database.sql.gz
echo -e "${GREEN}✓ Database backed up${NC}"

# Create backup info file
cat > $BACKUP_PATH/backup-info.txt << EOF
Backup created: $(date)
Hostname: $(hostname)
Application version: $(cat /opt/chat-agent/backend/app/version.txt 2>/dev/null || echo "unknown")
Database: chatbot
EOF

echo ""
echo "Backup complete!"
echo "Location: $BACKUP_PATH"
echo ""
echo "To restore:"
echo "  1. Extract app: tar -xzf $BACKUP_PATH/app.tar.gz -C /opt"
echo "  2. Extract config: tar -xzf $BACKUP_PATH/config.tar.gz -C /etc"
echo "  3. Restore DB: gunzip < $BACKUP_PATH/database.sql.gz | psql -h localhost -U chatbot_user chatbot"
echo ""
