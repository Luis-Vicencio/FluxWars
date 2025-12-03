#!/usr/bin/env python
"""Simple test to debug AI issues"""

# Test imports
try:
    from board import (find_cluster, move_cluster_cells, get_dice, BOARD_SIZE, 
                       get_board, get_polarities, get_state, roll_dice, next_player, 
                       reset_board, toggle_piece)
    print("✓ All board imports successful")
except Exception as e:
    print(f"✗ Board import error: {e}")
    exit(1)

try:
    from ai_player import get_ai_move, easy_ai_move
    print("✓ AI player imports successful")
except Exception as e:
    print(f"✗ AI player import error: {e}")
    exit(1)

# Setup a test game
print("\n--- Setting up test game ---")
reset_board()
state = get_state()
state["vs_ai"] = True
state["ai_difficulty"] = "easy"
state["ai_player"] = 2

# Place pieces for both players
print("Placing player 1 piece...")
toggle_piece(4, 3, 0)  # Player 1

print("Placing player 2 piece...")
toggle_piece(9, 10, 0)  # Player 2 (AI)

# Check state
state = get_state()
print(f"Phase: {state['phase']}")
print(f"Current player: {state['current_player']}")

if state['phase'] == 'main':
    print("\n--- Testing AI move ---")
    try:
        ai_func = get_ai_move(state.get("ai_difficulty", "easy"))
        print(f"AI function: {ai_func.__name__}")
        
        # Make it AI's turn
        if state['current_player'] == 1:
            next_player()
            state = get_state()
            print(f"Switched to player {state['current_player']}")
        
        print("Calling AI move function...")
        result = ai_func()
        print(f"AI move result: {result}")
        
        if result:
            print("✓ AI move successful!")
            state = get_state()
            print(f"New current player: {state['current_player']}")
            print(f"Dice: {get_dice()}")
        else:
            print("✗ AI move returned False")
            
    except Exception as e:
        import traceback
        print(f"✗ AI move error: {e}")
        print(traceback.format_exc())
else:
    print(f"Not in main phase yet (phase: {state['phase']})")
