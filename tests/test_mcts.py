#!/usr/bin/env python3
"""Test MCTS AI"""

from board import reset_board, get_state, toggle_piece, get_board, roll_dice, get_dice
from ai_player import get_ai_move

print("=== Testing MCTS AI ===\n")

# Reset and setup
reset_board()
state = get_state()
state["vs_ai"] = True
state["ai_difficulty"] = "normal"
state["ai_player"] = 2

print("✓ Board reset, AI enabled (Normal difficulty)\n")

# Place pieces
print("--- Placing pieces ---")
toggle_piece(4, 3, 0)  # Player 1
toggle_piece(9, 10, 0)  # Player 2 (AI)
print(f"Phase: {get_state()['phase']}")
print(f"Current player: {get_state()['current_player']}\n")

# Switch to AI player and test
print("--- Testing MCTS AI ---")
state = get_state()
state["current_player"] = 2  # AI's turn
dice = roll_dice()
print(f"Rolled dice: {dice}\n")

# Get and execute AI move
ai_func = get_ai_move("normal")
print(f"AI function: {ai_func.__name__}")

try:
    result = ai_func(simulations=50)  # Fewer simulations for testing
    print(f"\n✓ MCTS AI execution: {result}")
    print(f"Final player: {get_state()['current_player']}")
    print(f"Final dice: {get_dice()}")
except Exception as e:
    print(f"\n✗ MCTS AI error: {e}")
    import traceback
    traceback.print_exc()
