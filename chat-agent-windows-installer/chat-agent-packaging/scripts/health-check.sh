#!/bin/bash
# Chat-Agent Health Check Script
# Checks if all components are running properly

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "================================================================================"
echo "                    Chat-Agent Health Check"
echo "================================================================================"
echo ""

# Check backend
echo -n "Backend (port 8000): "
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not responding${NC}"
fi

# Check frontend
echo -n "Frontend (port 3000): "
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not responding${NC}"
fi

# Check database
echo -n "Database: "
if command -v psql &> /dev/null; then
    if psql -h localhost -U chatbot_user -d chatbot -c "SELECT 1" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Connected${NC}"
    else
        echo -e "${RED}✗ Cannot connect${NC}"
    fi
else
    echo -e "${YELLOW}⚠ psql not found${NC}"
fi

echo ""
echo "For detailed logs, check:"
echo "  Backend:  /var/log/chat-agent/backend.log"
echo "  Frontend: /var/log/chat-agent/frontend.log"
echo ""
