
import sys
sys.path.insert(0, "/tmp/dish_chat_agent/llm-multi-provider/repo/chat-agent-installer/app/backend")

try:
    from app.config import get_settings
    settings = get_settings()
    print("✅ Config loaded successfully!")
    print(f"   OPENAI_API_KEY set: {bool(settings.OPENAI_API_KEY)}")
    print(f"   PLLM_PROVIDER: {settings.PLLM_PROVIDER}")
    print(f"   DEBUG: {settings.DEBUG}")
except Exception as e:
    print(f"❌ Failed to load config: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
