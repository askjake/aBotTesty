#!/bin/bash
# Chat-Agent macOS Installer
# Supports: macOS 11.0+ (Big Sur and later)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="ChatAgent"
INSTALL_DIR="/Applications/$APP_NAME"
CONFIG_DIR="$HOME/Library/Application Support/$APP_NAME"
LOG_DIR="$HOME/Library/Logs/$APP_NAME"
DATA_DIR="$HOME/Library/Application Support/$APP_NAME/Data"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"

echo "================================================================================"
echo "                    Chat-Agent Installation Wizard"
echo "================================================================================"
echo ""

# Check macOS version
MACOS_VERSION=$(sw_vers -productVersion)
MACOS_MAJOR=$(echo $MACOS_VERSION | cut -d. -f1)

if [ "$MACOS_MAJOR" -lt 11 ]; then
    echo -e "${RED}Error: This installer requires macOS 11.0 (Big Sur) or later${NC}"
    echo -e "${RED}Your version: $MACOS_VERSION${NC}"
    exit 1
fi

echo -e "${GREEN}Detected macOS: $MACOS_VERSION${NC}"
echo ""

# Function to check if Homebrew is installed
check_homebrew() {
    if ! command -v brew &> /dev/null; then
        echo -e "${YELLOW}Homebrew not found. Installing Homebrew...${NC}"
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        
        # Add Homebrew to PATH for Apple Silicon Macs
        if [[ $(uname -m) == 'arm64' ]]; then
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> $HOME/.zprofile
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
        
        echo -e "${GREEN}✓ Homebrew installed${NC}"
    else
        echo -e "${GREEN}✓ Homebrew already installed${NC}"
    fi
}

# Function to install dependencies
install_dependencies() {
    echo "Installing system dependencies..."
    
    # Update Homebrew
    brew update
    
    # Install Python
    if ! command -v python3.12 &> /dev/null; then
        echo "Installing Python 3.12..."
        brew install python@3.12
    else
        echo -e "${GREEN}✓ Python 3.12 already installed${NC}"
    fi
    
    # Install Node.js
    if ! command -v node &> /dev/null; then
        echo "Installing Node.js..."
        brew install node@20
    else
        echo -e "${GREEN}✓ Node.js already installed${NC}"
    fi
    
    # Install pnpm
    if ! command -v pnpm &> /dev/null; then
        echo "Installing pnpm..."
        npm install -g pnpm
    else
        echo -e "${GREEN}✓ pnpm already installed${NC}"
    fi
    
    # Ask about PostgreSQL
    echo ""
    read -p "Install PostgreSQL? (y/n) [y]: " install_postgres
    install_postgres=${install_postgres:-y}
    
    if [[ $install_postgres =~ ^[Yy]$ ]]; then
        if ! command -v postgres &> /dev/null; then
            echo "Installing PostgreSQL..."
            brew install postgresql@14
            brew services start postgresql@14
        else
            echo -e "${GREEN}✓ PostgreSQL already installed${NC}"
        fi
    fi
    
    echo -e "${GREEN}✓ Dependencies installed${NC}"
}

# Function to create directories
create_directories() {
    echo "Creating application directories..."
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$DATA_DIR"
    mkdir -p "$LAUNCH_AGENTS_DIR"
    
    echo -e "${GREEN}✓ Directories created${NC}"
}

# Function to copy files
copy_files() {
    echo "Copying application files..."
    
    # Get the directory where this script is located
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    SOURCE_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
    
    cp -R "$SOURCE_DIR/app/"* "$INSTALL_DIR/"
    cp "$SOURCE_DIR/app/config/.env.template" "$CONFIG_DIR/.env"
    
    chmod 600 "$CONFIG_DIR/.env"
    
    echo -e "${GREEN}✓ Files copied${NC}"
}

# Function to setup backend
setup_backend() {
    echo "Setting up backend..."
    cd "$INSTALL_DIR/backend"
    
    # Create virtual environment
    python3.12 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    deactivate
    
    echo -e "${GREEN}✓ Backend setup complete${NC}"
}

# Function to setup frontend
setup_frontend() {
    echo "Setting up frontend..."
    cd "$INSTALL_DIR/frontend"
    
    pnpm install
    pnpm build
    
    echo -e "${GREEN}✓ Frontend setup complete${NC}"
}

# Function to configure database
configure_database() {
    echo ""
    echo "================================================================================"
    echo "                        Database Configuration"
    echo "================================================================================"
    echo ""
    
    read -p "Configure PostgreSQL database? (y/n) [y]: " config_db
    config_db=${config_db:-y}
    
    if [[ $config_db =~ ^[Yy]$ ]]; then
        read -p "Database name [chatbot]: " db_name
        db_name=${db_name:-chatbot}
        
        read -p "Database user [chatbot_user]: " db_user
        db_user=${db_user:-chatbot_user}
        
        read -sp "Database password: " db_pass
        echo ""
        
        # Create database and user
        psql postgres -c "CREATE DATABASE $db_name;" 2>/dev/null || echo "Database may already exist"
        psql postgres -c "CREATE USER $db_user WITH PASSWORD '$db_pass';" 2>/dev/null || echo "User may already exist"
        psql postgres -c "GRANT ALL PRIVILEGES ON DATABASE $db_name TO $db_user;"
        
        # Update .env file
        sed -i '' "s/POSTGRES_DB=.*/POSTGRES_DB=$db_name/" "$CONFIG_DIR/.env"
        sed -i '' "s/POSTGRES_USER=.*/POSTGRES_USER=$db_user/" "$CONFIG_DIR/.env"
        sed -i '' "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$db_pass/" "$CONFIG_DIR/.env"
        
        echo -e "${GREEN}✓ Database configured${NC}"
    fi
}

# Function to configure tools
configure_tools() {
    echo ""
    echo "================================================================================"
    echo "                        Tool Configuration"
    echo "================================================================================"
    echo ""
    echo "Select which tools to enable:"
    echo ""
    
    tools=("public_web_search" "internal_search" "netra_search" "dish_internal_tool" "cluster_inspect")
    enabled_tools=()
    
    for tool in "${tools[@]}"; do
        read -p "Enable $tool? (y/n) [y]: " enable
        enable=${enable:-y}
        if [[ $enable =~ ^[Yy]$ ]]; then
            enabled_tools+=("$tool")
        fi
    done
    
    # Save to config
    echo "ENABLED_TOOLS=$(IFS=,; echo "${enabled_tools[*]}")" >> "$CONFIG_DIR/.env"
    
    echo -e "${GREEN}✓ Tools configured${NC}"
}

# Function to create LaunchAgents
create_launch_agents() {
    echo "Creating Launch Agents..."
    
    # Backend LaunchAgent
    cat > "$LAUNCH_AGENTS_DIR/com.dish.chatagent.backend.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.dish.chatagent.backend</string>
    <key>ProgramArguments</key>
    <array>
        <string>$INSTALL_DIR/backend/venv/bin/uvicorn</string>
        <string>app.main:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>8000</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$INSTALL_DIR/backend</string>
    <key>StandardOutPath</key>
    <string>$LOG_DIR/backend.log</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/backend-error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
    <key>RunAtLoad</key>
    <false/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
EOF

    # Frontend LaunchAgent
    cat > "$LAUNCH_AGENTS_DIR/com.dish.chatagent.frontend.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.dish.chatagent.frontend</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/pnpm</string>
        <string>start</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$INSTALL_DIR/frontend</string>
    <key>StandardOutPath</key>
    <string>$LOG_DIR/frontend.log</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/frontend-error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
    <key>RunAtLoad</key>
    <false/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
EOF

    echo -e "${GREEN}✓ Launch Agents created${NC}"
}

# Function to configure startup
configure_startup() {
    echo ""
    echo "================================================================================"
    echo "                        Startup Configuration"
    echo "================================================================================"
    echo ""
    
    read -p "Enable services to start on login? (y/n) [y]: " enable_startup
    enable_startup=${enable_startup:-y}
    
    if [[ $enable_startup =~ ^[Yy]$ ]]; then
        # Update plist files to enable RunAtLoad
        /usr/libexec/PlistBuddy -c "Set :RunAtLoad true" "$LAUNCH_AGENTS_DIR/com.dish.chatagent.backend.plist"
        /usr/libexec/PlistBuddy -c "Set :RunAtLoad true" "$LAUNCH_AGENTS_DIR/com.dish.chatagent.frontend.plist"
        echo -e "${GREEN}✓ Services enabled for startup${NC}"
    fi
    
    read -p "Start services now? (y/n) [y]: " start_now
    start_now=${start_now:-y}
    
    if [[ $start_now =~ ^[Yy]$ ]]; then
        launchctl load "$LAUNCH_AGENTS_DIR/com.dish.chatagent.backend.plist"
        sleep 3
        launchctl load "$LAUNCH_AGENTS_DIR/com.dish.chatagent.frontend.plist"
        echo -e "${GREEN}✓ Services started${NC}"
    fi
}

# Function to create app bundle
create_app_bundle() {
    echo "Creating application bundle..."
    
    # Create .app structure
    APP_BUNDLE="/Applications/Chat-Agent.app"
    mkdir -p "$APP_BUNDLE/Contents/MacOS"
    mkdir -p "$APP_BUNDLE/Contents/Resources"
    
    # Create launcher script
    cat > "$APP_BUNDLE/Contents/MacOS/Chat-Agent" << 'EOF'
#!/bin/bash
open "http://localhost:3000"
EOF
    chmod +x "$APP_BUNDLE/Contents/MacOS/Chat-Agent"
    
    # Create Info.plist
    cat > "$APP_BUNDLE/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>Chat-Agent</string>
    <key>CFBundleIdentifier</key>
    <string>com.dish.chatagent</string>
    <key>CFBundleName</key>
    <string>Chat-Agent</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
</dict>
</plist>
EOF
    
    echo -e "${GREEN}✓ Application bundle created${NC}"
}

# Main installation flow
echo "Starting installation..."
echo ""

check_homebrew
install_dependencies
create_directories
copy_files
setup_backend
setup_frontend
configure_database
configure_tools
create_launch_agents
configure_startup
create_app_bundle

echo ""
echo "================================================================================"
echo "                    Installation Complete!"
echo "================================================================================"
echo ""
echo "Application installed to: $INSTALL_DIR"
echo "Configuration: $CONFIG_DIR/.env"
echo "Logs: $LOG_DIR"
echo ""
echo "Useful commands:"
echo "  Start services:   launchctl load ~/Library/LaunchAgents/com.dish.chatagent.*.plist"
echo "  Stop services:    launchctl unload ~/Library/LaunchAgents/com.dish.chatagent.*.plist"
echo "  View logs:        tail -f $LOG_DIR/backend.log"
echo ""
echo "Access the application at: http://localhost:3000"
echo "Or launch from Applications folder: Chat-Agent.app"
echo ""
