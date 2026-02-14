# LLM Provider Setup Guide

## Overview

The chat agent supports multiple LLM providers with automatic discovery and easy configuration.

## Supported Providers

| Provider | Type | Notes |
|----------|------|-------|
| OpenAI | Cloud | GPT-4, GPT-3.5 models |
| Anthropic | Cloud | Claude 3.5 Sonnet, Haiku |
| Google Gemini | Cloud | Gemini 1.5 Pro, Flash |
| Ollama | Local | Run models on your machine |
| AWS Bedrock | Cloud | Via AWS credentials |
| Custom | Any | OpenAI-compatible APIs |

## Quick Setup

### 1. Environment Variables (Recommended)

Create a `.env` file in `app/backend/`:

```bash
# Choose your provider(s)
OPENAI_API_KEY=sk-proj-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
GOOGLE_API_KEY=your-gemini-key-here

# Optional: Set defaults
PLLM_PROVIDER=openai
PLLM_MODEL=gpt-4o
```

### 2. Auto-Discovery

Run the smart startup script:

```bash
# It will automatically detect:
# - API keys from environment
# - Local Ollama instances  
# - Available providers

./scripts/smart-start.sh   # Linux/macOS
.\scripts\smart-start.ps1 # Windows
```

### 3. Manual Configuration

Use the web UI to add providers:

1. Open http://localhost:3000
2. Go to Settings → LLM Providers
3. Click "Add Provider"
4. Fill in the details
5. Click "Test" to verify
6. Save

## Provider-Specific Setup

### OpenAI (ChatGPT)

1. Get API key: https://platform.openai.com/api-keys
2. Set environment variable:
   ```bash
   export OPENAI_API_KEY="sk-proj-..."
   ```
3. Models: gpt-4o, gpt-4o-mini, gpt-3.5-turbo

### Anthropic (Claude)

1. Get API key: https://console.anthropic.com/
2. Set environment variable:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```
3. Models: claude-3-5-sonnet, claude-3-5-haiku

### Google Gemini

1. Get API key: https://aistudio.google.com/app/apikey
2. Set environment variable:
   ```bash
   export GOOGLE_API_KEY="..."
   ```
3. Models: gemini-1.5-pro, gemini-1.5-flash

### Ollama (Local)

1. Install: https://ollama.ai
2. Pull models:
   ```bash
   ollama pull llama3
   ollama pull mistral
   ollama pull codellama
   ```
3. Start server:
   ```bash
   ollama serve
   ```
4. Auto-discovered at http://localhost:11434

### Custom / Self-Hosted

For any OpenAI-compatible API:

1. Use "Custom" provider type
2. Set API Base URL
3. Set API key (if required)
4. Test connection

Example for LM Studio:
- API Base: `http://localhost:1234/v1`
- API Key: (not required)

## Troubleshooting

### No providers detected

```bash
# Check environment variables
env | grep API_KEY

# Check Ollama
curl http://localhost:11434/api/tags

# Run discovery manually
python scripts/detect-environment.py
```

### Provider test fails

1. Verify API key is correct
2. Check internet connection
3. Verify API base URL (for custom providers)
4. Check provider status page

### API rate limits

- OpenAI: https://platform.openai.com/account/limits
- Anthropic: https://console.anthropic.com/settings/limits
- Gemini: https://aistudio.google.com/app/apikey

## Security

- API keys are encrypted in the database
- Keys are never returned in API responses
- Environment variables take precedence
- Use `.env` files (not committed to git)

## Advanced Configuration

### Database Storage

Providers are stored in the `llm_providers` table:

```sql
SELECT * FROM llm_providers;
```

### Per-Chat Provider Selection

The UI allows selecting a provider for each chat. This is stored in the message metadata.

### Default Provider

Set via UI or API:

```bash
curl -X POST http://localhost:8000/rest/api/v1/llm-providers/{id}/set-default
```

## Examples

### Add OpenAI via API

```bash
curl -X POST http://localhost:8000/rest/api/v1/llm-providers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My OpenAI",
    "provider_type": "openai",
    "api_key": "sk-proj-...",
    "is_default": true
  }'
```

### Test a Provider

```bash
curl -X POST http://localhost:8000/rest/api/v1/llm-providers/test \
  -H "Content-Type: application/json" \
  -d '{"provider_id": "my_provider_id"}'
```

### List All Providers

```bash
curl http://localhost:8000/rest/api/v1/llm-providers
```
