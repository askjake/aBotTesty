# Performance Tips for Dish-Chat with Ollama

## 🐌 Why is Ollama Slow?

Local AI models are running on your CPU/GPU, not in the cloud. Speed depends on:
- Your hardware (CPU, GPU, RAM)
- Model size (larger = slower)
- Context length (longer conversations = slower)

## ⚡ Speed Optimization Tips

### 1. Use Smaller/Faster Models

**Current:** `llama3.2` (3B parameters)  
**Try:**
```bash
ollama pull llama3.2:1b     # Smallest, fastest (1B parameters)
ollama pull qwen2.5:0.5b    # Ultra-fast (500M parameters)
```

Update your `.env`:
```bash
PLLM_MODEL=llama3.2:1b
ELLM_MODEL=llama3.2:1b
```

Speed comparison:
- `llama3.2:1b` - ⚡⚡⚡ Very fast
- `llama3.2` (3b) - ⚡⚡ Moderate  
- `llama3.2:latest` (8b) - ⚡ Slower but smarter

### 2. Use GPU Acceleration

If you have an NVIDIA GPU:

**Check if Ollama is using GPU:**
```bash
ollama ps
```

Look for GPU usage. If not using GPU, Ollama will be much slower.

**Enable GPU:**
- Ensure you have NVIDIA drivers installed
- Ollama automatically uses GPU if available
- Check NVIDIA GPU: `nvidia-smi` (in CMD)

### 3. Reduce Context Length

In your `.env`:
```bash
PLLM_CTX_LEN=32000   # Down from 200000
```

Smaller context = faster responses.

### 4. Pre-load the Model

Models load on first request (slow). Keep Ollama running:
```bash
ollama serve
```

Or pre-load:
```bash
ollama run llama3.2 ""
```

This keeps the model in memory for faster subsequent requests.

### 5. Use Streaming (Already Enabled)

Streaming is enabled by default - you see responses as they generate, making it feel faster.

---

## 🚀 Alternative: Cloud APIs (Faster but Costs Money)

If speed is critical:

### OpenAI (Fast, but costs money)
```bash
PLLM_PROVIDER=openai
PLLM_API_BASE=https://api.openai.com/v1
PLLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=your-real-key-here
```

### Anthropic Claude (Fast, but costs money)
```bash
PLLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-key-here
PLLM_MODEL=claude-3-5-haiku-20241022
```

Cloud APIs are instant but have per-token costs.

---

## 🔧 Hardware Requirements

**Minimum:**
- 8GB RAM
- Modern CPU (4+ cores)
- Speed: Slow but usable

**Recommended:**
- 16GB+ RAM
- NVIDIA GPU (8GB+ VRAM)
- Speed: Fast and smooth

**Optimal:**
- 32GB+ RAM
- NVIDIA RTX 3080+ (10GB+ VRAM)
- Speed: Near-instant responses

---

## 📊 Model Speed Comparison

| Model | Size | Speed | Quality | Best For |
|-------|------|-------|---------|----------|
| qwen2.5:0.5b | 500MB | ⚡⚡⚡⚡ | ⭐⭐ | Quick Q&A |
| llama3.2:1b | 1.3GB | ⚡⚡⚡ | ⭐⭐⭐ | General use |
| llama3.2 (3b) | 2GB | ⚡⚡ | ⭐⭐⭐⭐ | Balanced |
| llama3.2:latest (8b) | 4.7GB | ⚡ | ⭐⭐⭐⭐⭐ | Complex tasks |
| deepseek-r1:8b | 4.7GB | ⚡ | ⭐⭐⭐⭐⭐ | Reasoning |

---

## 🎯 Recommended Setup

**For Speed:**
```bash
PLLM_MODEL=llama3.2:1b
PLLM_CTX_LEN=32000
```

**For Quality:**
```bash
PLLM_MODEL=llama3.2:latest
PLLM_CTX_LEN=200000
```

**For Balance:**
```bash
PLLM_MODEL=llama3.2
PLLM_CTX_LEN=100000
```

---

## 💡 Pro Tips

1. **Keep Ollama running** - Don't restart it between chats
2. **Pre-load model** - `ollama run llama3.2 ""`
3. **Close other apps** - Free up RAM/CPU
4. **Use smaller models** - llama3.2:1b is surprisingly good
5. **Monitor usage** - `ollama ps` shows what's running

---

## 🆘 Still Too Slow?

Consider:
- **Cloud API** - OpenAI gpt-4o-mini is fast and cheap ($0.15 per million tokens)
- **Groq** - Ultra-fast inference (70+ tokens/sec) with free tier
- **Better hardware** - Upgrade to GPU if using AI frequently

---

## ✅ Current Setup is WORKING

Even if slow, you now have:
- ✅ Free unlimited AI
- ✅ Complete privacy
- ✅ No API costs
- ✅ Offline capability

Speed will improve with:
- Better hardware
- Smaller models
- GPU acceleration

Enjoy your working local AI! 🎉
