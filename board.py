# board.py

BOARD_SIZE = 15

import random
from collections import deque

dice_value = 0
selected_cluster = []

def roll_dice():
    global dice_value
    dice_value = random.randint(1, 6)
    return dice_value

def find_cluster(row, col):
    """Find all magnetically connected pieces starting from (row, col)."""
    start_owner = board[row][col]
    start_polarity = polarities[row][col]
    if start_owner == 0 or start_polarity not in ("+", "-"):
        return []

    visited = set()
    queue = deque([(row, col)])
    cluster = []

    while queue:
        r, c = queue.popleft()
        if (r, c) in visited:
            continue
        visited.add((r, c))
        cluster.append((r, c))

        current_owner = board[r][c]
        current_polarity = polarities[r][c]

        # Check four directions
        for dr, dc in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                neighbor_owner = board[nr][nc]
                neighbor_polarity = polarities[nr][nc]
                # Only accept neighbor if it has a polarity and owner and is opposite polarity
                if neighbor_owner in (1, 2, 3) and neighbor_polarity in ("+", "-") and current_polarity != neighbor_polarity:
                    queue.append((nr, nc))

    return cluster


def can_move_cluster(cluster, dr, dc):
    """Check if a cluster can move by (dr, dc) without collisions."""
    # Normalize cluster to set of tuples
    cluster_set = {tuple(c) for c in cluster}
    for (r, c) in cluster:
        nr, nc = r + dr, c + dc
        if not (0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE):
            return False
        # If destination occupied and not part of the same cluster -> cannot move
        if board[nr][nc] != 0 and (nr, nc) not in cluster_set:
            return False
    return True


def move_cluster(cluster, dr, dc):
    """Move the entire cluster by (dr, dc) without validation (lower-level)."""
    # This function assumes caller already validated.can be used internally.
    temp_cells = [(r, c, board[r][c], polarities[r][c]) for (r, c) in cluster]

    # Clear old cells
    for r, c, _, _ in temp_cells:
        board[r][c] = 0
        polarities[r][c] = ""

    # Move and place
    for r, c, owner, pol in temp_cells:
        nr, nc = r + dr, c + dc
        board[nr][nc] = owner
        polarities[nr][nc] = pol


def get_dice():
    return dice_value


# 0 = empty, 1 = player1, 2 = player2, 3 = neutral
board = [[0 for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
polarities = [['' for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]

game_state = {
    "current_player": 1,
    "phase": "home_setup",  # home_setup -> neutral_setup -> main
    "homes": {1: None, 2: None},
    "neutral_counts": {1: 0, 2: 0}
}

# Each tuple ((dr, dc), polarity)
PIECES = {
    0: [((0, 0), '+'), ((0, 1), '-')],      # →  plus on left, minus on right
    90: [((0, 0), '+'), ((1, 0), '-')],     # ↓  plus on top, minus below
    180: [((0, 0), '+'), ((0, -1), '-')],   # ←  plus on right, minus on left
    270: [((0, 0), '+'), ((-1, 0), '-')],   # ↑  plus on bottom, minus on top
}

def get_board():
    return board

def get_polarities():
    return polarities

def get_state():
    return game_state

def can_place(piece, row, col):
    for dr, dc in [p[0] for p in piece]:
        r, c = row + dr, col + dc
        if r < 0 or r >= BOARD_SIZE or c < 0 or c >= BOARD_SIZE:
            return False, "Out of bounds"
        if board[r][c] != 0:
            return False, "Cell already occupied"
    return True, ""

def is_in_half(player, col):
    if player == 1:
        return 0 <= col <= 6
    elif player == 2:
        return 8 <= col <= 14
    return False

def is_in_opponent_half(player, col):
    if player == 1:
        return 8 <= col <= 14
    elif player == 2:
        return 0 <= col <= 6
    return False

def place_piece(piece, row, col, value):
    for (dr, dc), polarity in piece:
        r, c = row + dr, col + dc
        board[r][c] = value
        polarities[r][c] = polarity

def toggle_piece(row, col, orientation):
    state = game_state
    phase = state["phase"]
    player = state["current_player"]

    if orientation not in PIECES:
        return False, f"Invalid orientation {orientation}"

    piece = PIECES[orientation]

    # Reject any placement crossing column 7
    for (dr, dc), _ in piece:
        if col + dc == 7:
            return False, "Placement touches the forbidden middle column."

    # Phase-based half checks
    if phase == "home_setup":
        for (dr, dc), _ in piece:
            if not is_in_half(player, col + dc):
                return False, f"Home piece must be fully inside player {player}'s half."
    elif phase == "neutral_setup":
        for (dr, dc), _ in piece:
            if not is_in_opponent_half(player, col + dc):
                return False, f"Neutral piece must be placed on the opponent's half."
    else:
        return False, f"Cannot place in phase '{phase}'."

    # Check occupancy
    ok, reason = can_place(piece, row, col)
    if not ok:
        return False, reason

    # Place piece
    if phase == "home_setup":
        place_piece(piece, row, col, player)
        state["homes"][player] = (row, col, orientation)
        # switch to the other player or next phase
        if player == 1:
            state["current_player"] = 2
        else:
            state["phase"] = "neutral_setup"
            state["current_player"] = 1
        return True, "Placed home piece."
    elif phase == "neutral_setup":
        place_piece(piece, row, col, 3)
        state["neutral_counts"][player] += 1
        state["current_player"] = 2 if player == 1 else 1
        # adjust the threshold as you wanted earlier (now set to 4 each)
        if state["neutral_counts"][1] >= 4 and state["neutral_counts"][2] >= 4:
            state["phase"] = "main"
            state["current_player"] = 1
        return True, "Placed neutral piece."

    return False, "Unknown error."


def reset_board():
    global board, polarities, game_state, dice_value, selected_cluster
    board = [[0 for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    polarities = [['' for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    dice_value = 0
    selected_cluster = []
    game_state = {
        "current_player": 1,
        "phase": "home_setup",
        "homes": {1: None, 2: None},
        "neutral_counts": {1: 0, 2: 0}
    }

def move_cluster_cells(cluster, dr, dc):
    """
    Move all cells in cluster by (dr, dc) if valid.
    - cluster: iterable of (r,c) pairs (tuples or lists)
    - returns (True, "message") on success, (False, "message") on failure.
    """
    global board, polarities

    # normalize cluster to list of tuples and preserve order (important)
    cluster_positions = [tuple(x) for x in cluster]
    cluster_set = set(cluster_positions)

    rows = len(board)
    cols = len(board[0])

    # 1) Compute new positions and check bounds
    new_positions = []
    for (r, c) in cluster_positions:
        nr, nc = r + dr, c + dc
        if not (0 <= nr < rows and 0 <= nc < cols):
            return False, "Out of bounds!"
        new_positions.append((nr, nc))

    # 2) Check collisions: if destination cell is occupied and not part of the cluster -> blocked
    for pos in new_positions:
        if pos not in cluster_set:
            nr, nc = pos
            if board[nr][nc] != 0:
                return False, "Invalid move — space blocked!"

    # 3) Create copies and apply move to avoid in-place overwrite issues
    new_board = [row[:] for row in board]
    new_polarities = [row[:] for row in polarities]

    # Clear old positions on the copy
    for (r, c) in cluster_positions:
        new_board[r][c] = 0
        new_polarities[r][c] = ""

    # Place pieces at new positions (preserve owner/polarity from old board)
    for (r, c), (nr, nc) in zip(cluster_positions, new_positions):
        new_board[nr][nc] = board[r][c]
        new_polarities[nr][nc] = polarities[r][c]

    # 4) Commit
    board = new_board
    polarities = new_polarities

    return True, "Cluster moved."

def next_player():
    """Switch to the next player."""
    global game_state
    game_state["current_player"] = 2 if game_state["current_player"] == 1 else 1
    return game_state["current_player"]

def get_cluster(row, col):
    """Return connected cluster for given cell (same player). Returns list of [r,c]."""
    if not (0 <= row < len(board) and 0 <= col < len(board[0])):
        return []
    player = board[row][col]
    if player == 0:
        return []

    visited = set()
    cluster = []
    stack = [(row, col)]

    while stack:
        r, c = stack.pop()
        if (r, c) in visited:
            continue
        visited.add((r, c))
        cluster.append([r, c])
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < len(board) and 0 <= nc < len(board[0]) and board[nr][nc] == player:
                stack.append((nr, nc))
    return cluster
