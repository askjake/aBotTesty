#!/usr/bin/env python3
"""
Auto-detect available LLM providers and environment configuration
"""
import os
import sys
import json
import subprocess
from pathlib import Path

print("🔍 Detecting Environment...")
print("="*60)

detected_config = {
    "python": None,
    "node": None,
    "pnpm": None,
    "providers": [],
    "api_keys": {}
}

# Check Python
try:
    result = subprocess.run(["python", "--version"], capture_output=True, text=True)
    detected_config["python"] = result.stdout.strip() or result.stderr.strip()
    print(f"✓ Python: {detected_config['python']}")
except:
    print("✗ Python: Not found")

# Check Node.js
try:
    result = subprocess.run(["node", "--version"], capture_output=True, text=True)
    detected_config["node"] = result.stdout.strip()
    print(f"✓ Node.js: {detected_config['node']}")
except:
    print("✗ Node.js: Not found")

# Check pnpm
try:
    result = subprocess.run(["pnpm", "--version"], capture_output=True, text=True)
    detected_config["pnpm"] = result.stdout.strip()
    print(f"✓ pnpm: {detected_config['pnpm']}")
except:
    print("✗ pnpm: Not found (run: npm install -g pnpm)")

print()
print("🔑 Detecting API Keys...")
print("="*60)

# Check for API keys
api_key_vars = {
    "OPENAI_API_KEY": "OpenAI",
    "ANTHROPIC_API_KEY": "Anthropic",
    "GOOGLE_API_KEY": "Google Gemini",
}

for var, name in api_key_vars.items():
    value = os.getenv(var)
    if value:
        detected_config["api_keys"][var] = "***" + value[-4:]
        detected_config["providers"].append(name)
        print(f"✓ {name}: Found ({var})")
    else:
        print(f"✗ {name}: Not found (set {var})")

# Check for Ollama
print()
print("🤖 Checking for Ollama...")
print("="*60)
try:
    import httpx
    response = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
    if response.status_code == 200:
        models = response.json().get("models", [])
        detected_config["providers"].append("Ollama")
        print(f"✓ Ollama: Found at http://localhost:11434")
        print(f"  Models: {', '.join([m['name'] for m in models[:3]])}{'...' if len(models) > 3 else ''}")
    else:
        print("✗ Ollama: Not responding")
except:
    print("✗ Ollama: Not found (install from https://ollama.ai)")

# Summary
print()
print("📊 Summary")
print("="*60)
print(f"Detected Providers: {', '.join(detected_config['providers']) or 'None'}")

if not detected_config["providers"]:
    print()
    print("⚠️  No LLM providers detected!")
    print("   Please configure at least one:")
    print("   - Set OPENAI_API_KEY environment variable")
    print("   - Set ANTHROPIC_API_KEY environment variable")  
    print("   - Install Ollama (https://ollama.ai)")
    sys.exit(1)

# Save detected config
output_file = Path(__file__).parent / "detected_config.json"
with open(output_file, 'w') as f:
    json.dump(detected_config, f, indent=2)

print(f"\nℹ️  Configuration saved to: {output_file}")
print("✅ Environment detection complete!")
