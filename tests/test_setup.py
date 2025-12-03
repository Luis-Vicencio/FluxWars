#!/usr/bin/env python3
"""Test AI setup phase"""

from board import reset_board, get_state, toggle_piece, get_board, get_polarities

print("=== Testing AI Setup Phase ===\n")

# Reset board
reset_board()
print("✓ Board reset")

# Enable AI
state = get_state()
state["vs_ai"] = True
state["ai_difficulty"] = "easy"
state["ai_player"] = 2
print(f"✓ AI enabled (player {state['ai_player']})")
print(f"  Current phase: {state['phase']}")
print(f"  Current player: {state['current_player']}\n")

# Player 1 places home piece
print("--- Player 1 places home piece ---")
success, msg = toggle_piece(4, 3, 0)
print(f"  Result: {success} - {msg}")
state = get_state()
print(f"  New phase: {state['phase']}")
print(f"  New player: {state['current_player']}\n")

# AI (Player 2) should place automatically
if state['current_player'] == 2 and state['phase'] == 'home_setup':
    print("--- AI turn detected, placing piece ---")
    success, msg = toggle_piece(9, 10, 0)
    print(f"  Result: {success} - {msg}")
    state = get_state()
    print(f"  New phase: {state['phase']}")
    print(f"  New player: {state['current_player']}\n")

# Check board
board = get_board()
print("--- Board state ---")
for r in range(len(board)):
    for c in range(len(board[0])):
        if board[r][c] != 0:
            print(f"  [{r},{c}] = Player {board[r][c]}")

print("\n✓ Setup test complete!")
