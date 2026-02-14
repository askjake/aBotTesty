#!/bin/bash
# Dish-Chat Portable Packaging Script
# This script packages Dish-Chat for deployment to another machine

set -e

echo "================================"
echo "Dish-Chat Packaging Script"
echo "================================"
echo ""

# Create temporary directory for packaging
PACKAGE_DIR="dish-chat-portable-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$PACKAGE_DIR"

echo "1. Copying application files..."
cp -r ~/Jakes-agent/dish-chat "$PACKAGE_DIR/"
cp -r ~/Jakes-agent/dish-chat-fe "$PACKAGE_DIR/"
cp ~/Jakes-agent/dishchat-manager.sh "$PACKAGE_DIR/"
cp ~/Jakes-agent/configure-llm.py "$PACKAGE_DIR/"
cp ~/Jakes-agent/LLM-CONFIG-README.md "$PACKAGE_DIR/"
cp ~/Jakes-agent/database-migration.sql "$PACKAGE_DIR/"

echo "2. Creating deployment instructions..."
cat > "$PACKAGE_DIR/DEPLOYMENT.md" << 'EOF'
# Dish-Chat Deployment Instructions

## Prerequisites
- PostgreSQL 12+
- Python 3.10+
- Node.js 18+
- npm or pnpm

## Installation Steps

### 1. Extract the package
```bash
tar -xzf dish-chat-portable-*.tar.gz
cd dish-chat-portable-*/
```

### 2. Set up PostgreSQL database
```bash
sudo -u postgres psql <<SQL
CREATE DATABASE dishchat;
CREATE USER dishchat_user WITH PASSWORD 'Chang3m3!';
GRANT ALL PRIVILEGES ON DATABASE dishchat TO dishchat_user;
\c dishchat
GRANT ALL ON SCHEMA public TO dishchat_user;
SQL
```

### 3. Run database migrations
```bash
psql -U dishchat_user -d dishchat -f database-migration.sql
```

### 4. Install Python dependencies
```bash
cd dish-chat
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
```

### 5. Install Node dependencies
```bash
cd dish-chat-fe
npm install
# or: pnpm install
cd ..
```

### 6. Configure environment
```bash
cd dish-chat
cp .env.example .env  # if it exists
nano .env
# Update:
# - POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PWD
# - Other settings as needed
cd ..
```

### 7. Configure LLM provider
```bash
python3 configure-llm.py
```

Follow the prompts to configure your preferred LLM provider:
- Anthropic (Claude) - Requires API key from console.anthropic.com
- OpenAI (GPT) - Requires API key from platform.openai.com  
- Ollama (Local) - Requires Ollama installed and running
- AWS Bedrock - Requires AWS credentials with Bedrock permissions

### 8. Start the application
```bash
chmod +x dishchat-manager.sh
./dishchat-manager.sh start
```

### 9. Verify deployment
Open your browser to: http://localhost:3000

Test:
- Create a new chat
- Send a message
- Verify AI response

## Troubleshooting

### Backend won't start
```bash
# Check logs
tail -f ~/dish-chat-logs/backend.log

# Check database connection
psql -U dishchat_user -d dishchat -c "SELECT 1"
```

### Frontend won't start
```bash
# Check logs
tail -f ~/dish-chat-logs/frontend.log

# Reinstall dependencies
cd dish-chat-fe
rm -rf node_modules
npm install
```

### AI responses not working
1. Verify API key is correctly configured in .env
2. Check you have internet connectivity (for cloud APIs)
3. For Ollama, ensure it's running: `ollama serve`
4. Check backend logs for specific error messages

## Configuration Files

- `dish-chat/.env` - Backend environment variables
- `dish-chat-fe/.env.local` - Frontend environment variables (optional)
- `.aws/credentials` - AWS credentials (if using Bedrock)

## Support

- Documentation: See LLM-CONFIG-README.md
- Logs: ~/dish-chat-logs/
- Management: ./dishchat-manager.sh status

EOF

echo "3. Creating .env template..."
cat > "$PACKAGE_DIR/dish-chat/.env.example" << 'EOF'
# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=dishchat
POSTGRES_USER=dishchat_user
POSTGRES_PWD=Chang3m3!

# LLM Configuration (set via configure-llm.py or manually)
# PLLM_PROVIDER=anthropic
# PLLM_MODEL=claude-sonnet-4-5-20251022
# ELLM_PROVIDER=anthropic
# ELLM_MODEL=claude-3-5-haiku-20241022

# Note: API keys are set as environment variables
# export ANTHROPIC_API_KEY=your-key-here
# export OPENAI_API_KEY=your-key-here

# Application Settings
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
LOCAL=true
DEBUG=false
EOF

echo "4. Cleaning up unnecessary files..."
# Remove .git, __pycache__, node_modules, etc.
find "$PACKAGE_DIR" -name ".git" -type d -exec rm -rf {} + 2>/dev/null || true
find "$PACKAGE_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$PACKAGE_DIR" -name "*.pyc" -delete 2>/dev/null || true
find "$PACKAGE_DIR" -name ".DS_Store" -delete 2>/dev/null || true
rm -rf "$PACKAGE_DIR/dish-chat-fe/node_modules" 2>/dev/null || true
rm -rf "$PACKAGE_DIR/dish-chat/.venv" 2>/dev/null || true

echo "5. Creating archive..."
tar -czf "${PACKAGE_DIR}.tar.gz" "$PACKAGE_DIR/"

echo ""
echo "================================"
echo "✓ Packaging complete!"
echo "================================"
echo ""
echo "Package created: ${PACKAGE_DIR}.tar.gz"
echo "Size: $(du -h ${PACKAGE_DIR}.tar.gz | cut -f1)"
echo ""
echo "To deploy on another machine:"
echo "  1. Copy ${PACKAGE_DIR}.tar.gz to the target machine"
echo "  2. Extract: tar -xzf ${PACKAGE_DIR}.tar.gz"
echo "  3. Follow instructions in DEPLOYMENT.md"
echo ""

# Cleanup
rm -rf "$PACKAGE_DIR"
