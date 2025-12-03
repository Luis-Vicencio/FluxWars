#!/usr/bin/env python3
"""Test LLM AI - requires API key"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Check for API key
if not os.environ.get("OPENAI_API_KEY") and not os.environ.get("ANTHROPIC_API_KEY"):
    print("❌ No API key found!")
    print("\nPlease set one of:")
    print("  export OPENAI_API_KEY='sk-your-key-here'")
    print("  export ANTHROPIC_API_KEY='sk-ant-your-key-here'")
    print("\nSee LLM_SETUP.md for detailed instructions.")
    sys.exit(1)

from board import reset_board, get_state, toggle_piece, get_board, roll_dice, get_dice
from ai_player import get_ai_move

print("=== Testing LLM AI ===\n")

# Check if libraries are installed
provider = os.environ.get("LLM_PROVIDER", "openai")
try:
    if provider == "openai":
        import openai
        print(f"✓ OpenAI library installed")
    elif provider == "anthropic":
        import anthropic
        print(f"✓ Anthropic library installed")
except ImportError:
    print(f"❌ {provider.capitalize()} library not installed!")
    print(f"\nInstall with: pip install {provider}")
    sys.exit(1)

# Reset and setup
reset_board()
state = get_state()
state["vs_ai"] = True
state["ai_difficulty"] = "expert"
state["ai_player"] = 2

print(f"✓ Board reset, AI enabled (Expert difficulty)")
print(f"  Provider: {provider}")
print(f"  Model: {os.environ.get('LLM_MODEL', 'gpt-4' if provider == 'openai' else 'claude-3-sonnet-20240229')}\n")

# Place pieces
print("--- Placing pieces ---")
toggle_piece(4, 3, 0)  # Player 1
toggle_piece(9, 10, 0)  # Player 2 (AI)
print(f"Phase: {get_state()['phase']}")
print(f"Current player: {get_state()['current_player']}\n")

# Switch to AI player and test
print("--- Testing LLM AI ---")
state = get_state()
state["current_player"] = 2  # AI's turn
dice = roll_dice()
print(f"Rolled dice: {dice}\n")

# Get and execute AI move
ai_func = get_ai_move("expert")
print(f"AI function: {ai_func.__name__}\n")

print("Calling LLM (this may take 5-10 seconds)...")
print("-" * 50)

try:
    result = ai_func()
    print("-" * 50)
    print(f"\n✓ LLM AI execution: {result}")
    print(f"Final player: {get_state()['current_player']}")
    print(f"Final dice: {get_dice()}")
    print("\n✓ LLM AI test complete!")
except Exception as e:
    print("-" * 50)
    print(f"\n✗ LLM AI error: {e}")
    import traceback
    traceback.print_exc()
    print("\nNote: If the LLM call failed, check:")
    print("  1. Your API key is valid")
    print("  2. Your account has credits")
    print("  3. You have internet connectivity")
