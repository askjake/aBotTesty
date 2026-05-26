# Windows Quick Start Guide

Get Dish-Chat running on Windows in 5 minutes! 🚀

## Prerequisites

Install these if you don't have them:

1. **Python 3.11+**: https://www.python.org/downloads/
   - ✅ Check "Add Python to PATH" during installation
2. **Node.js 18+**: https://nodejs.org/
3. **pnpm**: Open PowerShell and run:
   ```powershell
   npm install -g pnpm
   ```
4. **PostgreSQL** (or use Docker)

---

## Option 1: Quick Start with Ollama (FREE - No API Keys Needed!)

### Step 1: Install Ollama
1. Download: https://ollama.ai/download/windows
2. Install and run
3. Open PowerShell and run:
   ```powershell
   ollama pull llama3.2
   ollama pull nomic-embed-text
   ```

### Step 2: Clone Repository
```powershell
cd C:\Users\<YourUsername>\Documents
git clone https://github.com/askjake/aBotTesty.git
cd aBotTesty\chat-agent-installer
```

### Step 3: Setup Database (Docker)
```powershell
cd app\backend
docker-compose up -d
```

Or install PostgreSQL manually and create database `dishchat`.

### Step 4: Configure Environment
```powershell
cd app\backend
copy .env.example .env
```

Edit `.env` in Notepad:
```bash
# Use Ollama (free, local)
PLLM_PROVIDER=openai
PLLM_API_BASE=http://localhost:11434/v1
PLLM_MODEL=llama3.2

ELLM_PROVIDER=openai
ELLM_API_BASE=http://localhost:11434/v1
ELLM_MODEL=llama3.2

EMBED_PROVIDER=openai
EMBED_API_BASE=http://localhost:11434/v1
EMBED_MODEL=nomic-embed-text

OPENAI_API_KEY=not-needed-for-ollama

# CRITICAL: Must be 0 for Ollama
MAX_CACHEPOINT_CNT=0
```

### Step 5: Install & Start
```powershell
# From chat-agent-installer directory
.\scripts\smart-start.ps1
```

This will:
- Create virtual environment
- Install dependencies
- Run database migrations
- Start backend and frontend
- Open browser automatically

**Done!** 🎉 Chat with your local AI at http://localhost:3000

---

## Option 2: Quick Start with OpenAI

### Step 1: Get API Key
1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Copy it

### Step 2: Clone & Setup
```powershell
cd C:\Users\<YourUsername>\Documents
git clone https://github.com/askjake/aBotTesty.git
cd aBotTesty\chat-agent-installer\app\backend

# Setup database
docker-compose up -d

# Configure
copy .env.example .env
```

Edit `.env`:
```bash
PLLM_PROVIDER=openai
PLLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-proj-YOUR-KEY-HERE

# You can set this to 4 for OpenAI (enables caching with Anthropic)
# But 0 works fine too
MAX_CACHEPOINT_CNT=0
```

### Step 3: Start
```powershell
cd ..\..  # Back to chat-agent-installer
.\scripts\smart-start.ps1
```

**Done!** 🎉

---

## Manual Setup (If Scripts Don't Work)

### 1. Setup Backend
```powershell
cd chat-agent-installer\app\backend

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup database
docker-compose up -d

# Run migrations
alembic upgrade head

# Start server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Setup Frontend (New PowerShell Window)
```powershell
cd chat-agent-installer\app\frontend

# Install dependencies
pnpm install

# Start dev server
pnpm dev
```

**Open:** http://localhost:3000

---

## Troubleshooting

### "Python not found"
- Reinstall Python and check "Add to PATH"
- Or add manually: System Properties → Environment Variables → Path → Add Python directory

### "pnpm not found"
```powershell
npm install -g pnpm
```

### "Docker not running"
- Install Docker Desktop for Windows
- Or install PostgreSQL manually and set `POSTGRES_HOST=localhost`

### "Port 8000 already in use"
Find and kill the process:
```powershell
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### "Invalid message format" (Ollama)
Make sure `.env` has:
```bash
MAX_CACHEPOINT_CNT=0
```

Restart backend after changing `.env`.

### Backend won't start
Check logs in the terminal. Common issues:
- Database not running (`docker-compose up -d`)
- Wrong Python version (need 3.11+)
- Missing dependencies (`pip install -r requirements.txt`)

### Frontend errors
```powershell
cd app\frontend
rm -rf node_modules .next
pnpm install
pnpm dev
```

---

## Common Commands

### Restart Everything
```powershell
# Stop (Ctrl+C in each terminal)
# Then:
.\scripts\smart-start.ps1
```

### Update Code
```powershell
git pull origin main
cd app\backend
.\venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head

cd ..\frontend
pnpm install
```

### Check Ollama Status
```powershell
ollama list
ollama ps  # Shows running models
```

### View Logs
- Backend: Check the PowerShell window running uvicorn
- Frontend: Check the PowerShell window running pnpm dev
- Database: `docker logs dishchat-postgres`

---

## What's Next?

Once running, you can:
- **Chat** with AI models (Ollama, OpenAI, Claude, etc.)
- **Upload documents** for RAG (PDF, DOCX, TXT)
- **Search the web** using integrated tools
- **Clone & analyze** GitHub repositories
- **Run Python code** in a sandboxed environment
- **Customize** system prompts and settings

See `docs/` folder for more guides:
- `OLLAMA_SETUP.md` - Detailed Ollama configuration
- `LLM_SETUP_GUIDE.md` - Multi-provider setup
- `README.md` - Full documentation

---

## Need Help?

- GitHub Issues: https://github.com/askjake/aBotTesty/issues
- Check `docs/` folder for detailed guides
- Review error messages in terminal - they usually tell you what's wrong!

Enjoy your AI assistant! 🎉
