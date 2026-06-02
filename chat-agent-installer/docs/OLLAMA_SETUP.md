# Ollama Setup Guide for Dish-Chat

This guide will help you set up Dish-Chat with Ollama for **free, local AI models** with no API costs.

## Why Ollama?

- ✅ **Free** - No API costs
- ✅ **Private** - Your data stays on your machine
- ✅ **Fast** - No internet latency
- ✅ **Powerful** - Supports Llama 3.2, Mistral, DeepSeek, and more

## Prerequisites

- Windows 10/11, macOS, or Linux
- 8GB+ RAM (16GB recommended)
- 10GB+ free disk space

---

## Step 1: Install Ollama

### Windows:
1. Download: https://ollama.ai/download/windows
2. Run the installer
3. Ollama will run automatically in the background

### macOS:
1. Download: https://ollama.ai/download/mac
2. Open the .dmg file and drag Ollama to Applications
3. Launch Ollama from Applications

### Linux:
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

---

## Step 2: Download Models

Open a terminal/PowerShell and run:

```bash
# Recommended: Llama 3.2 (3B - fast, good quality)
ollama pull llama3.2

# For embeddings (required for document search)
ollama pull nomic-embed-text

# Optional: Other models
ollama pull deepseek-r1:8b     # Great for reasoning
ollama pull mistral            # General purpose
ollama pull codellama          # For coding tasks
```

**Note:** First download will take a few minutes per model.

---

## Step 3: Verify Ollama is Running

```bash
ollama list
```

You should see your downloaded models.

Test the API:
```bash
curl http://localhost:11434/v1/models
```

---

## Step 4: Configure Dish-Chat

Edit your `.env` file in `chat-agent-installer/app/backend/.env`:

```bash
# Primary LLM (for chat)
PLLM_PROVIDER=openai
PLLM_API_BASE=http://localhost:11434/v1
PLLM_MODEL=llama3.2

# Evaluation LLM
ELLM_PROVIDER=openai
ELLM_API_BASE=http://localhost:11434/v1
ELLM_MODEL=llama3.2

# Embedding Model
EMBED_PROVIDER=openai
EMBED_API_BASE=http://localhost:11434/v1
EMBED_MODEL=nomic-embed-text

# API Key (not needed but required by OpenAI client)
OPENAI_API_KEY=not-needed-for-ollama

# IMPORTANT: Disable cache points (Ollama doesn't support them)
MAX_CACHEPOINT_CNT=0
```

**Why `PLLM_PROVIDER=openai`?**
Ollama provides an OpenAI-compatible API, so we use the OpenAI provider but point it to Ollama's endpoint.

---

## Step 5: Start Dish-Chat

### Windows:
```powershell
cd chat-agent-installer
.\scripts\smart-start.ps1
```

### Linux/macOS:
```bash
cd chat-agent-installer
./scripts/smart-start.sh
```

Or manually:
```bash
# Terminal 1 - Backend
cd chat-agent-installer/app/backend
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 - Frontend
cd chat-agent-installer/app/frontend
pnpm dev
```

---

## Step 6: Test It!

1. Open http://localhost:3000
2. Create a new chat
3. Type a message
4. You should get a response from Ollama!

---

## Troubleshooting

### "Connection refused" or "Cannot connect to Ollama"

**Check if Ollama is running:**
```bash
ollama list
```

**On Windows:** Check if Ollama is running in the system tray (bottom right)

**Restart Ollama:**
```bash
# macOS/Linux
sudo systemctl restart ollama

# Windows: Close Ollama from system tray and restart it
```

---

### "Invalid message format" error

Make sure `MAX_CACHEPOINT_CNT=0` is set in your `.env` file.

Restart the backend after changing the `.env` file.

---

### Models not found

```bash
ollama list
```

If empty, pull the models:
```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```

---

### Slow responses

Try a smaller model:
```bash
ollama pull llama3.2:1b  # Smaller, faster version
```

Update your `.env`:
```bash
PLLM_MODEL=llama3.2:1b
```

---

## Switching Models

You can switch models without restarting:

1. Pull a new model:
   ```bash
   ollama pull mistral
   ```

2. Update `.env`:
   ```bash
   PLLM_MODEL=mistral
   ```

3. Restart backend (hot reload will pick it up)

---

## Recommended Models

| Model | Size | Best For | Speed |
|-------|------|----------|-------|
| llama3.2:1b | 1.3GB | Quick responses | ⚡⚡⚡ |
| llama3.2 (3b) | 2GB | Balanced | ⚡⚡ |
| deepseek-r1:8b | 4.7GB | Reasoning tasks | ⚡ |
| mistral | 4.1GB | General purpose | ⚡ |
| codellama | 3.8GB | Coding | ⚡ |

---

## Benefits of Ollama

- **No rate limits** - Chat as much as you want
- **No API costs** - Completely free
- **Privacy** - Everything stays on your machine
- **Offline** - Works without internet (after downloading models)
- **Fast** - No network latency

---

## Need More Help?

- Ollama Docs: https://ollama.ai/docs
- Dish-Chat GitHub Issues: https://github.com/askjake/aBotTesty/issues
- Check logs in your backend terminal for errors

---

## Next Steps

Once you have Ollama working, you can:
- Try different models (mistral, codellama, etc.)
- Upload documents for RAG (Retrieval-Augmented Generation)
- Use web search tools
- Clone and analyze code repositories

Enjoy your free, local AI assistant! 🎉
