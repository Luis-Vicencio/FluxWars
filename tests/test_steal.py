#!/usr/bin/env python3
"""
Test script to verify steal target detection logic.

Sets up a controlled board state with:
- Player 1 pieces on the left
- Player 2 (opponent) pieces adjacent to Player 1 with opposite polarity
- Validates that Player 1 can detect opponent pieces as steal targets
"""

import board

# Reset and setup a controlled game state
board.reset_board()

# Skip setup phases and go straight to main phase for testing
board.game_state["phase"] = "main"
board.game_state["current_player"] = 1

# Manually place some test pieces:
# Player 1: place a + at (5, 3) and - at (5, 4)
board.board[5][3] = 1
board.polarities[5][3] = "+"
board.board[5][4] = 1
board.polarities[5][4] = "-"

# Player 2 (opponent): place pieces adjacent to Player 1 with opposite polarity
# Place opponent - at (5, 2) (adjacent to Player 1's + at (5, 3))
board.board[5][2] = 2
board.polarities[5][2] = "-"
board.board[5][1] = 2
board.polarities[5][1] = "+"

# Place opponent + at (6, 4) (adjacent to Player 1's - at (5, 4))
board.board[6][4] = 2
board.polarities[6][4] = "+"
board.board[6][5] = 2
board.polarities[6][5] = "-"

# Create a fake initial cluster tracking (needed for steal detection)
# Add these opponent cells to tracked clusters
cluster1 = frozenset([(5, 2), (5, 1)])
cluster2 = frozenset([(6, 4), (6, 5)])
board.game_state["initial_neutral_clusters"] = [cluster1, cluster2]
board.game_state["total_neutral_clusters"] = 2
board.game_state["neutral_cluster_owners"] = {0: 2, 1: 2}

print("=" * 60)
print("TEST: Steal Target Detection")
print("=" * 60)
print("\nBoard Setup (rows 4-7, cols 0-6):")
print("Legend: 1=Player1, 2=Player2(opponent), 0=empty")
print("Polarity shown as +/-\n")

for r in range(4, 8):
    row_str = f"Row {r}: "
    for c in range(0, 7):
        owner = board.board[r][c]
        pol = board.polarities[r][c]
        if owner == 0:
            row_str += "  .  "
        else:
            row_str += f" {owner}{pol} "
    print(row_str)

print("\n" + "=" * 60)
print("Expected steal targets for Player 1:")
print("  - (5, 2): Player 2's '-' piece (adjacent to Player 1's '+' at (5,3))")
print("  - (6, 4): Player 2's '+' piece (adjacent to Player 1's '-' at (5,4))")
print("=" * 60)

# Test steal target detection
steal_targets = board.get_stealable_neutrals_for_player(1)

print(f"\nActual steal targets found: {steal_targets}")
print(f"Number of targets: {len(steal_targets)}")

if len(steal_targets) == 0:
    print("\n❌ FAIL: No steal targets found!")
    print("\nDebugging info:")
    print(f"  Current player: {board.game_state['current_player']}")
    print(f"  Phase: {board.game_state['phase']}")
    print(f"  Opponent (player 2) positions:")
    for r in range(board.BOARD_SIZE):
        for c in range(board.BOARD_SIZE):
            if board.board[r][c] == 2:
                print(f"    ({r}, {c}): polarity='{board.polarities[r][c]}'")
    
    print(f"\n  Player 1 positions:")
    for r in range(board.BOARD_SIZE):
        for c in range(board.BOARD_SIZE):
            if board.board[r][c] == 1:
                print(f"    ({r}, {c}): polarity='{board.polarities[r][c]}'")
    
    print("\n  Checking adjacencies manually:")
    # Check (5, 2) which should be stealable
    print(f"    (5,2) owner={board.board[5][2]}, pol='{board.polarities[5][2]}'")
    print(f"    (5,3) owner={board.board[5][3]}, pol='{board.polarities[5][3]}'")
    print(f"    -> Adjacent? Yes. Opposite polarity? {board.polarities[5][2]} vs {board.polarities[5][3]}")
    
elif len(steal_targets) == 2 and (5, 2) in steal_targets and (6, 4) in steal_targets:
    print("\n✅ PASS: Correct steal targets detected!")
else:
    print(f"\n⚠️  PARTIAL: Found {len(steal_targets)} targets, expected 2")
    print(f"   Expected: [(5, 2), (6, 4)]")
    print(f"   Got: {steal_targets}")

print("\n" + "=" * 60)
