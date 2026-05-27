#!/usr/bin/env python3
"""
Dish-Chat LLM Configuration Helper
Interactive script to configure LLM providers
"""
import os
import sys
from pathlib import Path

def update_env(key, value, env_path):
    """Update or add environment variable in .env file"""
    if env_path.exists():
        with open(env_path, 'r') as f:
            lines = f.readlines()
    else:
        lines = []
    
    # Update existing or append
    updated = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            updated = True
            break
    
    if not updated:
        lines.append(f"{key}={value}\n")
    
    with open(env_path, 'w') as f:
        f.writelines(lines)

def main():
    print("="*80)
    print("Dish-Chat LLM Configuration Helper")
    print("="*80)
    
    # Find the .env file
    env_path = Path(__file__).parent / "dish-chat" / ".env"
    if not env_path.exists():
        env_path = Path.home() / "Jakes-agent" / "dish-chat" / ".env"
    
    if not env_path.exists():
        print("Error: Could not find .env file")
        print(f"Looked in: {env_path}")
        sys.exit(1)
    
    print(f"\nConfiguring: {env_path}")
    print()
    
    # Provider selection
    print("Select LLM Provider:")
    print("  1. Anthropic (Claude) - Recommended")
    print("  2. OpenAI (GPT)")
    print("  3. Ollama (Local)")
    print("  4. AWS Bedrock")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        # Anthropic
        print("\n--- Anthropic Configuration ---")
        print("Get your API key from: https://console.anthropic.com/")
        api_key = input("Enter Anthropic API key: ").strip()
        
        if not api_key.startswith("sk-ant-api"):
            print("Warning: API key should start with 'sk-ant-api'")
            cont = input("Continue anyway? (y/n): ")
            if cont.lower() != 'y':
                sys.exit(1)
        
        print("\nSelect Model:")
        print("  1. Claude Sonnet 4.5 (Recommended - Best balance)")
        print("  2. Claude Haiku 3.5 (Fast & efficient)")
        print("  3. Claude Opus 4.5 (Most capable)")
        
        model_choice = input("Enter choice (1-3): ").strip()
        models = {
            "1": "claude-sonnet-4-5-20251022",
            "2": "claude-3-5-haiku-20241022",
            "3": "claude-opus-4-5-20250514"
        }
        model = models.get(model_choice, models["1"])
        
        update_env("ANTHROPIC_API_KEY", api_key, env_path)
        update_env("PLLM_PROVIDER", "anthropic", env_path)
        update_env("PLLM_MODEL", model, env_path)
        update_env("ELLM_PROVIDER", "anthropic", env_path)
        update_env("ELLM_MODEL", "claude-3-5-haiku-20241022", env_path)
        
        print(f"\n✓ Configured Anthropic with {model}")
        
    elif choice == "2":
        # OpenAI
        print("\n--- OpenAI Configuration ---")
        print("Get your API key from: https://platform.openai.com/api-keys")
        api_key = input("Enter OpenAI API key: ").strip()
        
        if not api_key.startswith("sk-"):
            print("Warning: API key should start with 'sk-'")
        
        print("\nSelect Model:")
        print("  1. GPT-4 Turbo (Recommended)")
        print("  2. GPT-4")
        print("  3. GPT-3.5 Turbo")
        
        model_choice = input("Enter choice (1-3): ").strip()
        models = {
            "1": "gpt-4-turbo",
            "2": "gpt-4",
            "3": "gpt-3.5-turbo"
        }
        model = models.get(model_choice, models["1"])
        
        update_env("OPENAI_API_KEY", api_key, env_path)
        update_env("PLLM_PROVIDER", "openai", env_path)
        update_env("PLLM_MODEL", model, env_path)
        
        print(f"\n✓ Configured OpenAI with {model}")
        
    elif choice == "3":
        # Ollama
        print("\n--- Ollama Configuration ---")
        print("Make sure Ollama is running on your system")
        print("Default URL: http://localhost:11434")
        
        api_base = input("Enter Ollama URL (press Enter for default): ").strip()
        if not api_base:
            api_base = "http://localhost:11434"
        
        print("\nEnter model name (e.g., llama3.3:70b, llama3.2, mistral)")
        model = input("Model name: ").strip()
        if not model:
            model = "llama3.2"
        
        update_env("PLLM_PROVIDER", "ollama", env_path)
        update_env("PLLM_API_BASE", api_base, env_path)
        update_env("PLLM_MODEL", model, env_path)
        
        print(f"\n✓ Configured Ollama at {api_base} with {model}")
        
    elif choice == "4":
        # AWS Bedrock
        print("\n--- AWS Bedrock Configuration ---")
        print("Ensure AWS credentials are configured (via ~/.aws/credentials)")
        print("Requires IAM permissions for bedrock:InvokeModel*")
        
        print("\nSelect Model:")
        print("  1. Claude Sonnet 4.5 (us-east-1)")
        print("  2. Claude Haiku 3.5")
        
        model_choice = input("Enter choice (1-2): ").strip()
        models = {
            "1": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
            "2": "anthropic.claude-3-5-haiku-20241022-v1:0"
        }
        model = models.get(model_choice, models["1"])
        
        update_env("PLLM_PROVIDER", "aws-bedrock", env_path)
        update_env("PLLM_MODEL", model, env_path)
        
        print(f"\n✓ Configured AWS Bedrock with {model}")
    
    else:
        print("Invalid choice")
        sys.exit(1)
    
    print("\n" + "="*80)
    print("Configuration saved!")
    print("="*80)
    print("\nNext steps:")
    print("  1. Restart the backend:")
    print("     cd ~/Jakes-agent")
    print("     ./dishchat-manager.sh restart backend")
    print()
    print("  2. Test your configuration:")
    print("     Open http://10.79.85.47:3000 in your browser")
    print("     Create a chat and send a message")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nConfiguration cancelled")
        sys.exit(1)
