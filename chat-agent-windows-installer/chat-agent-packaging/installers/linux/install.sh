#!/bin/bash
# Chat-Agent Linux Installer
# Supports: Ubuntu, Debian, CentOS, RHEL, Fedora

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="chat-agent"
INSTALL_DIR="/opt/$APP_NAME"
SERVICE_USER="$APP_NAME"
CONFIG_DIR="/etc/$APP_NAME"
LOG_DIR="/var/log/$APP_NAME"
DATA_DIR="/var/lib/$APP_NAME"

echo "================================================================================"
echo "                    Chat-Agent Installation Wizard"
echo "================================================================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: This installer must be run as root (use sudo)${NC}"
    exit 1
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    OS_VERSION=$VERSION_ID
else
    echo -e "${RED}Error: Cannot detect OS${NC}"
    exit 1
fi

echo -e "${GREEN}Detected OS: $OS $OS_VERSION${NC}"
echo ""

# Function to install dependencies
install_dependencies() {
    echo "Installing system dependencies..."
    
    case $OS in
        ubuntu|debian)
            apt-get update
            apt-get install -y python3 python3-pip python3-venv nodejs npm postgresql postgresql-contrib curl
            npm install -g pnpm
            ;;
        centos|rhel|fedora)
            if command -v dnf &> /dev/null; then
                dnf install -y python3 python3-pip nodejs npm postgresql postgresql-server curl
            else
                yum install -y python3 python3-pip nodejs npm postgresql postgresql-server curl
            fi
            npm install -g pnpm
            ;;
        *)
            echo -e "${YELLOW}Warning: Unsupported OS. You may need to install dependencies manually.${NC}"
            echo "Required: Python 3.10+, Node.js 20+, PostgreSQL 14+, pnpm"
            read -p "Continue anyway? (y/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
            ;;
    esac
    
    echo -e "${GREEN}✓ Dependencies installed${NC}"
}

# Function to create user
create_user() {
    if ! id "$SERVICE_USER" &>/dev/null; then
        echo "Creating service user: $SERVICE_USER"
        useradd -r -s /bin/false -d $INSTALL_DIR $SERVICE_USER
        echo -e "${GREEN}✓ User created${NC}"
    else
        echo -e "${YELLOW}User $SERVICE_USER already exists${NC}"
    fi
}

# Function to create directories
create_directories() {
    echo "Creating application directories..."
    mkdir -p $INSTALL_DIR
    mkdir -p $CONFIG_DIR
    mkdir -p $LOG_DIR
    mkdir -p $DATA_DIR
    
    chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR
    chown -R $SERVICE_USER:$SERVICE_USER $LOG_DIR
    chown -R $SERVICE_USER:$SERVICE_USER $DATA_DIR
    
    echo -e "${GREEN}✓ Directories created${NC}"
}

# Function to copy files
copy_files() {
    echo "Copying application files..."
    cp -r app/* $INSTALL_DIR/
    cp app/config/.env.template $CONFIG_DIR/.env
    
    chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR
    chmod 600 $CONFIG_DIR/.env
    
    echo -e "${GREEN}✓ Files copied${NC}"
}

# Function to setup backend
setup_backend() {
    echo "Setting up backend..."
    cd $INSTALL_DIR/backend
    
    # Create virtual environment
    sudo -u $SERVICE_USER python3 -m venv venv
    sudo -u $SERVICE_USER venv/bin/pip install --upgrade pip
    sudo -u $SERVICE_USER venv/bin/pip install -r requirements.txt
    
    echo -e "${GREEN}✓ Backend setup complete${NC}"
}

# Function to setup frontend
setup_frontend() {
    echo "Setting up frontend..."
    cd $INSTALL_DIR/frontend
    
    sudo -u $SERVICE_USER pnpm install
    sudo -u $SERVICE_USER pnpm build
    
    echo -e "${GREEN}✓ Frontend setup complete${NC}"
}

# Function to configure database
configure_database() {
    echo ""
    echo "================================================================================"
    echo "                        Database Configuration"
    echo "================================================================================"
    echo ""
    echo "Do you want to configure PostgreSQL database?"
    echo "1) Yes, configure new database"
    echo "2) No, I'll configure it manually"
    read -p "Choice [1-2]: " db_choice
    
    if [ "$db_choice" = "1" ]; then
        read -p "Database name [chatbot]: " db_name
        db_name=${db_name:-chatbot}
        
        read -p "Database user [chatbot_user]: " db_user
        db_user=${db_user:-chatbot_user}
        
        read -sp "Database password: " db_pass
        echo ""
        
        # Create database and user
        sudo -u postgres psql -c "CREATE DATABASE $db_name;" 2>/dev/null || echo "Database may already exist"
        sudo -u postgres psql -c "CREATE USER $db_user WITH PASSWORD '$db_pass';" 2>/dev/null || echo "User may already exist"
        sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $db_name TO $db_user;"
        
        # Update .env file
        sed -i "s/POSTGRES_DB=.*/POSTGRES_DB=$db_name/" $CONFIG_DIR/.env
        sed -i "s/POSTGRES_USER=.*/POSTGRES_USER=$db_user/" $CONFIG_DIR/.env
        sed -i "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$db_pass/" $CONFIG_DIR/.env
        
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
    echo "ENABLED_TOOLS=$(IFS=,; echo "${enabled_tools[*]}")" >> $CONFIG_DIR/.env
    
    echo -e "${GREEN}✓ Tools configured${NC}"
}

# Function to create systemd service
create_service() {
    echo "Creating systemd service..."
    
    # Backend service
    cat > /etc/systemd/system/chat-agent-backend.service << EOF
[Unit]
Description=Chat-Agent Backend
After=network.target postgresql.service

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR/backend
Environment="PATH=$INSTALL_DIR/backend/venv/bin"
EnvironmentFile=$CONFIG_DIR/.env
ExecStart=$INSTALL_DIR/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # Frontend service
    cat > /etc/systemd/system/chat-agent-frontend.service << EOF
[Unit]
Description=Chat-Agent Frontend
After=network.target chat-agent-backend.service

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR/frontend
Environment="PATH=/usr/bin:/usr/local/bin"
EnvironmentFile=$CONFIG_DIR/.env
ExecStart=/usr/bin/pnpm start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    
    echo -e "${GREEN}✓ Services created${NC}"
}

# Function to configure startup
configure_startup() {
    echo ""
    echo "================================================================================"
    echo "                        Startup Configuration"
    echo "================================================================================"
    echo ""
    read -p "Enable services to start on boot? (y/n) [y]: " enable_startup
    enable_startup=${enable_startup:-y}
    
    if [[ $enable_startup =~ ^[Yy]$ ]]; then
        systemctl enable chat-agent-backend
        systemctl enable chat-agent-frontend
        echo -e "${GREEN}✓ Services enabled for startup${NC}"
    fi
    
    read -p "Start services now? (y/n) [y]: " start_now
    start_now=${start_now:-y}
    
    if [[ $start_now =~ ^[Yy]$ ]]; then
        systemctl start chat-agent-backend
        systemctl start chat-agent-frontend
        echo -e "${GREEN}✓ Services started${NC}"
    fi
}

# Main installation flow
echo "Starting installation..."
echo ""

install_dependencies
create_user
create_directories
copy_files
setup_backend
setup_frontend
configure_database
configure_tools
create_service
configure_startup

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
echo "  Start services:   sudo systemctl start chat-agent-backend chat-agent-frontend"
echo "  Stop services:    sudo systemctl stop chat-agent-backend chat-agent-frontend"
echo "  Check status:     sudo systemctl status chat-agent-backend chat-agent-frontend"
echo "  View logs:        sudo journalctl -u chat-agent-backend -f"
echo ""
echo "Access the application at: http://localhost:3000"
echo ""
