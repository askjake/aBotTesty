# Dish-Chat LLM Configuration

## Quick Setup

Run the configuration helper:
```bash
cd ~/Jakes-agent
python3 configure-llm.py
```

This will guide you through setting up your preferred LLM provider.

## Supported Providers

### 1. Anthropic (Claude) - Recommended
- Get API key: https://console.anthropic.com/
- Best for: General chat, code, reasoning
- Models: Claude Sonnet 4.5, Haiku 3.5, Opus 4.5

### 2. OpenAI (GPT)
- Get API key: https://platform.openai.com/api-keys
- Best for: Code, chat
- Models: GPT-4 Turbo, GPT-4, GPT-3.5 Turbo

### 3. Ollama (Local)
- Install: https://ollama.ai/
- Best for: Privacy, offline use
- Models: llama3.3:70b, llama3.2, mistral, etc.

### 4. AWS Bedrock
- Requires: AWS credentials with Bedrock permissions
- Best for: Enterprise use
- Models: Claude via AWS

## Manual Configuration

Edit `~/Jakes-agent/dish-chat/.env`:

### For Anthropic:
```bash
ANTHROPIC_API_KEY=sk-ant-api-your-key-here
PLLM_PROVIDER=anthropic
PLLM_MODEL=claude-sonnet-4-5-20251022
ELLM_PROVIDER=anthropic
ELLM_MODEL=claude-3-5-haiku-20241022
```

### For OpenAI:
```bash
OPENAI_API_KEY=sk-your-key-here
PLLM_PROVIDER=openai
PLLM_MODEL=gpt-4-turbo
```

### For Ollama:
```bash
PLLM_PROVIDER=ollama
PLLM_API_BASE=http://localhost:11434
PLLM_MODEL=llama3.2
```

### For AWS Bedrock:
```bash
PLLM_PROVIDER=aws-bedrock
PLLM_MODEL=us.anthropic.claude-sonnet-4-5-20250929-v1:0
# Ensure ~/.aws/credentials is configured
```

## After Configuration

Restart the backend:
```bash
cd ~/Jakes-agent
./dishchat-manager.sh restart backend
```

Test at: http://10.79.85.47:3000
