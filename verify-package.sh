#!/bin/bash
# Package Verification Script
# Verifies the integrity and contents of installation packages

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "================================================================================"
echo "                    Chat-Agent Package Verification"
echo "================================================================================"
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if packages exist
echo "Checking package files..."
PACKAGES=(
    "chat-agent-linux-installer.tar.gz"
    "chat-agent-windows-installer.zip"
    "chat-agent-macos-installer.tar.gz"
    "chat-agent-universal-installer.tar.gz"
)

for pkg in "${PACKAGES[@]}"; do
    if [ -f "$pkg" ]; then
        size=$(du -h "$pkg" | cut -f1)
        echo -e "  ${GREEN}✓${NC} $pkg ($size)"
    else
        echo -e "  ${RED}✗${NC} $pkg (missing)"
        exit 1
    fi
done

echo ""
echo "Checking documentation..."
DOCS=(
    "INSTALLATION-SUMMARY.md"
    "QUICKSTART-LINUX.md"
    "QUICKSTART-WINDOWS.md"
    "QUICKSTART-MACOS.md"
)

for doc in "${DOCS[@]}"; do
    if [ -f "$doc" ]; then
        echo -e "  ${GREEN}✓${NC} $doc"
    else
        echo -e "  ${RED}✗${NC} $doc (missing)"
        exit 1
    fi
done

echo ""
echo "Verifying Linux package contents..."
if tar -tzf chat-agent-linux-installer.tar.gz | grep -q "installers/linux/install.sh"; then
    echo -e "  ${GREEN}✓${NC} Linux installer found"
else
    echo -e "  ${RED}✗${NC} Linux installer missing"
    exit 1
fi

if tar -tzf chat-agent-linux-installer.tar.gz | grep -q "app/backend/requirements.txt"; then
    echo -e "  ${GREEN}✓${NC} Backend files found"
else
    echo -e "  ${RED}✗${NC} Backend files missing"
    exit 1
fi

if tar -tzf chat-agent-linux-installer.tar.gz | grep -q "app/frontend/package.json"; then
    echo -e "  ${GREEN}✓${NC} Frontend files found"
else
    echo -e "  ${RED}✗${NC} Frontend files missing"
    exit 1
fi

echo ""
echo "Verifying Windows package contents..."
if unzip -l chat-agent-windows-installer.zip | grep -q "installers/windows/install.ps1"; then
    echo -e "  ${GREEN}✓${NC} Windows installer found"
else
    echo -e "  ${RED}✗${NC} Windows installer missing"
    exit 1
fi

echo ""
echo "Verifying macOS package contents..."
if tar -tzf chat-agent-macos-installer.tar.gz | grep -q "installers/macos/install.sh"; then
    echo -e "  ${GREEN}✓${NC} macOS installer found"
else
    echo -e "  ${RED}✗${NC} macOS installer missing"
    exit 1
fi

echo ""
echo "================================================================================"
echo -e "                    ${GREEN}All Verifications Passed!${NC}"
echo "================================================================================"
echo ""
echo "Package is ready for distribution."
echo ""
