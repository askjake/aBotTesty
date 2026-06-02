# Dish-Chat Migration & Configuration

This directory contains the complete Dish-Chat migration work, including database fixes, LLM configuration system, and portable deployment tools.

## 📁 Directory Structure

```
dish-chat-migration/
├── scripts/
│   ├── configure-llm.py          # Interactive LLM configuration tool
│   └── package-for-deployment.sh # Packaging script for portable deployment
├── deployment/
│   └── database-migration.sql    # Complete database schema fix script
└── documentation/
    └── LLM-CONFIG-README.md      # User documentation for LLM setup
```

## 🎯 Quick Start

### For Current Installation (10.79.85.47)

1. **Configure LLM Provider:**
   ```bash
   cd ~/aBotTesty/dish-chat-migration/scripts
   python3 configure-llm.py
   ```

2. **Restart Backend:**
   ```bash
   cd ~/Jakes-agent
   ./dishchat-manager.sh restart backend
   ```

3. **Test:**
   - Open: http://10.79.85.47:3000
   - Create a chat and send a message

### For New Machine Deployment

1. **Clone this repository:**
   ```bash
   git clone https://github.com/montjac/aBotTesty.git
   cd aBotTesty/dish-chat-migration
   ```

2. **Set up database:**
   ```bash
   # Create PostgreSQL database
   sudo -u postgres psql <<SQL
   CREATE DATABASE dishchat;
   CREATE USER dishchat_user WITH PASSWORD 'Chang3m3!';
   GRANT ALL PRIVILEGES ON DATABASE dishchat TO dishchat_user;
   SQL
   
   # Apply schema fixes
   psql -U dishchat_user -d dishchat -f deployment/database-migration.sql
   ```

3. **Install and configure:**
   ```bash
   # Follow deployment instructions in documentation/
   python3 scripts/configure-llm.py
   ```

## 🔧 What Was Fixed

### Database Schema Issues
- ✅ Created missing PostgreSQL enums (`chatstatusenum`, `message_role_enum`)
- ✅ Converted 7 columns from VARCHAR to UUID
- ✅ Created `message_metadata` table
- ✅ Fixed all foreign key constraints

### Backend Configuration
- ✅ Fixed CORS for cross-origin requests
- ✅ Configured LLM provider settings framework
- ✅ Added settings management API endpoint

### Configuration System
- ✅ Interactive CLI tool for LLM configuration
- ✅ Support for 4 providers: Anthropic, OpenAI, Ollama, AWS Bedrock
- ✅ Automatic .env file management
- ✅ User-friendly (no technical knowledge required)

### Portable Deployment
- ✅ Complete database migration script
- ✅ Packaging script for easy transfer
- ✅ Comprehensive documentation

## 📚 Documentation

See [documentation/LLM-CONFIG-README.md](documentation/LLM-CONFIG-README.md) for:
- Detailed LLM provider setup instructions
- API key requirements
- Model selection guide
- Troubleshooting tips

## 🚀 Supported LLM Providers

| Provider | API Key Required | Best For |
|----------|------------------|----------|
| **Anthropic (Claude)** | Yes | General chat, code, reasoning (Recommended) |
| **OpenAI (GPT)** | Yes | Code generation, chat |
| **Ollama** | No (local) | Privacy, offline use |
| **AWS Bedrock** | AWS credentials | Enterprise deployments |

## 🔐 Security Notes

- API keys are stored in `.env` file (not committed to git)
- Use environment variables for production deployments
- Consider using secret management services (AWS Secrets Manager, HashiCorp Vault)
- File permissions are set to 600 (owner read/write only)

## 📦 Package for Deployment

To create a portable package:

```bash
cd ~/Jakes-agent
./package-for-deployment.sh
```

This creates `dish-chat-portable-YYYYMMDD-HHMMSS.tar.gz` containing:
- Complete application code
- Database migration script
- Configuration tools
- Documentation

## 🌐 Access URLs

After deployment:
- **Frontend:** http://YOUR-SERVER:3000
- **Backend:** http://YOUR-SERVER:8000
- **API Docs:** http://YOUR-SERVER:8000/docs

## 🐛 Troubleshooting

### Backend won't start
```bash
tail -f ~/dish-chat-logs/backend.log
```

### Frontend issues
```bash
tail -f ~/dish-chat-logs/frontend.log
```

### Database connection
```bash
psql -U dishchat_user -d dishchat -c "SELECT 1"
```

### AI responses not working
1. Verify API key: `cat ~/Jakes-agent/dish-chat/.env | grep API_KEY`
2. Check provider: `cat ~/Jakes-agent/dish-chat/.env | grep PROVIDER`
3. Review backend logs for specific errors

## 📝 Migration Date

**Completed:** 2026-02-14  
**System:** 10.79.85.47 (dsgpu3080-Lambda-Vector)  
**Status:** ✅ Production Ready (requires API key)

## 🎓 Credits

Migration and configuration system by AI Assistant  
Dish-Chat by Dish Technologies L.L.C.

---

For detailed deployment instructions, see the documentation directory.
For support, check the logs in `~/dish-chat-logs/`.

