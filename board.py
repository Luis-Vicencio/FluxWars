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
    "neutral_counts": {1: 0, 2: 0},
    # clusters acquired from neutrals by each player
    "acquired_clusters": {1: 0, 2: 0},
    # who acquired the last neutral cluster (1 or 2)
    "last_cluster_acquirer": None,
    # total neutral clusters initially placed on board
    "total_neutral_clusters": 0,
    # list of initial neutral clusters as frozensets of (r,c)
    "initial_neutral_clusters": [],
    # map index -> owner (None if not yet acquired)
    "neutral_cluster_owners": {},
    # winner: None or player number
    "winner": None
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
            # Enter neutral setup phase and trigger automatic neutral placement by AI
            state["phase"] = "neutral_setup"
            state["current_player"] = 1
            # Automatically place neutral pieces for both players
            ai_place_all_neutrals()
        return True, "Placed home piece."
    elif phase == "neutral_setup":
        # Neutral pieces are placed automatically by the server AI during neutral_setup.
        return False, "Neutral pieces are placed automatically by the server."

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
        "neutral_counts": {1: 0, 2: 0},
        "acquired_clusters": {1: 0, 2: 0},
        "last_cluster_acquirer": None,
        "total_neutral_clusters": 0,
        "initial_neutral_clusters": [],
        "neutral_cluster_owners": {},
        "winner": None
    }

def move_cluster_cells(cluster, dr, dc, actor_player=None):
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

    # If an actor_player is provided, convert only neutral pieces that are directly
    # adjacent to the moved cells AND have opposite polarity to the adjacent moved cell.
    # This enforces the "direct touch with opposite polarity" rule and prevents
    # chained conversions through neutral-neutral links.
    converted_any = False
    if actor_player in (1, 2):
        # compute new positions (they correspond by index)
        new_positions = [(r + dr, c + dc) for (r, c) in cluster_positions]
        seen_converted_cells = set()
        seen_converted_clusters = set()
        initial_clusters = game_state.get("initial_neutral_clusters", [])
        cluster_owner_map = game_state.get("neutral_cluster_owners", {})
        for (nr, nc) in new_positions:
            # polarity of the moved cell
            moved_pol = polarities[nr][nc]
            if moved_pol not in ('+', '-'):
                continue
            # check four neighbors for neutral pieces with opposite polarity
            for ddr, ddc in [(1,0),(-1,0),(0,1),(0,-1)]:
                ar, ac = nr + ddr, nc + ddc
                if not (0 <= ar < BOARD_SIZE and 0 <= ac < BOARD_SIZE):
                    continue
                if board[ar][ac] == 3:
                    neigh_pol = polarities[ar][ac]
                    if neigh_pol in ('+', '-') and neigh_pol != moved_pol:
                        # Find which initial cluster (if any) this neutral cell belongs to
                        converted_cluster_idx = None
                        for idx, cl in enumerate(initial_clusters):
                            if (ar, ac) in cl:
                                converted_cluster_idx = idx
                                break
                        if converted_cluster_idx is not None:
                            if converted_cluster_idx in seen_converted_clusters:
                                continue
                            # Convert entire initial cluster to actor_player
                            cl = initial_clusters[converted_cluster_idx]
                            prev_owner = cluster_owner_map.get(converted_cluster_idx)
                            # update board cells
                            for (cr, cc) in cl:
                                if board[cr][cc] == 3:
                                    board[cr][cc] = actor_player
                                    seen_converted_cells.add((cr, cc))
                            # update owner counts
                            if prev_owner != actor_player:
                                if prev_owner in (1,2):
                                    game_state["acquired_clusters"][prev_owner] -= 1
                                game_state["neutral_cluster_owners"][converted_cluster_idx] = actor_player
                                game_state["acquired_clusters"][actor_player] += 1
                                game_state["last_cluster_acquirer"] = actor_player
                            seen_converted_clusters.add(converted_cluster_idx)
                            converted_any = True
                        else:
                            # fallback: convert single neutral cell if initial clusters unknown
                            if (ar, ac) not in seen_converted_cells:
                                board[ar][ac] = actor_player
                                seen_converted_cells.add((ar, ac))
                                converted_any = True

        # After converting individual neutral pieces, check whether any initial neutral
        # clusters are now fully owned by one player — if so, mark them acquired.
        for idx, cluster in enumerate(game_state.get("initial_neutral_clusters", [])):
            if game_state.get("neutral_cluster_owners", {}).get(idx) is not None:
                continue
            # if all cells of this initial cluster are now owned by a single non-neutral player
            owners = set()
            for (cr, cc) in cluster:
                owners.add(board[cr][cc])
            # if owners is exactly {1} or {2}, cluster acquired
            owners.discard(0)
            owners.discard(3)
            if len(owners) == 1:
                owner = owners.pop()
                game_state["neutral_cluster_owners"][idx] = owner
                game_state["acquired_clusters"][owner] += 1
                game_state["last_cluster_acquirer"] = owner

        # After conversions, check for winner
        check_winner()

    return True, "Cluster moved." + (" Converted neutrals." if converted_any else "")

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


def check_winner():
    """Evaluate win conditions and set game_state['winner'] if a winner is found.

    Rules implemented:
    - If a player has a strict majority of the initially placed neutral clusters -> they win.
    - If all neutral clusters have been acquired and both players have the same number,
      the player who acquired the last cluster (game_state['last_cluster_acquirer']) wins.
    """
    total = game_state.get("total_neutral_clusters", 0)
    if total == 0:
        return None

    a1 = game_state["acquired_clusters"][1]
    a2 = game_state["acquired_clusters"][2]

    # strict majority
    if a1 > total // 2:
        game_state["winner"] = 1
        game_state["phase"] = "ended"
        return 1
    if a2 > total // 2:
        game_state["winner"] = 2
        game_state["phase"] = "ended"
        return 2

    # all acquired, but tie — last acquirer wins
    if a1 + a2 >= total:
        if a1 == a2 and game_state.get("last_cluster_acquirer") in (1, 2):
            game_state["winner"] = game_state["last_cluster_acquirer"]
            game_state["phase"] = "ended"
            return game_state["winner"]

    return None


def get_state_serializable():
    """Return a JSON-serializable copy of game_state.

    Converts frozensets (initial_neutral_clusters) into lists of [r,c] lists.
    """
    import copy
    s = copy.deepcopy(game_state)
    inc = s.get("initial_neutral_clusters")
    if inc:
        serial = []
        for cluster in inc:
            # cluster may be a frozenset of (r,c) tuples
            serial.append([list(x) for x in cluster])
        s["initial_neutral_clusters"] = serial
    return s


def ai_place_neutral_for_player(player, max_attempts=2000, min_distance=4):
    """Attempt to place one neutral piece on the opponent's half for `player`.
    Enforces a minimum Manhattan distance (`min_distance`) from existing neutral
    pieces to keep neutrals spaced out. Returns True if placed, False otherwise."""
    cols = range(8, BOARD_SIZE) if player == 1 else range(0, 7)
    attempts = 0
    while attempts < max_attempts:
        attempts += 1
        orientation = random.choice(list(PIECES.keys()))
        piece = PIECES[orientation]
        col = random.choice(list(cols))
        row = random.randrange(0, BOARD_SIZE)

        # Reject any placement touching the forbidden middle column
        touches_middle = any((col + dc) == 7 for (dr, dc), _ in piece)
        if touches_middle:
            continue

        ok, _ = can_place(piece, row, col)
        if not ok:
            continue

        # Ensure spacing: every cell of the new piece must be at least min_distance
        # away (Manhattan) from any existing neutral cell
        def too_close_to_neutral(r0, c0):
            for r in range(BOARD_SIZE):
                for c in range(BOARD_SIZE):
                    if board[r][c] == 3:
                        if abs(r - r0) + abs(c - c0) < min_distance:
                            return True
            return False

        conflict = False
        for (dr, dc), _ in piece:
            rcell, ccell = row + dr, col + dc
            if too_close_to_neutral(rcell, ccell):
                conflict = True
                break
        if conflict:
            continue

        # Place neutral piece (owner = 3)
        place_piece(piece, row, col, 3)
        game_state["neutral_counts"][player] += 1
        return True

    return False


def ai_place_all_neutrals(threshold=4):
    """Automatically place neutral pieces alternately for players until each reaches threshold.
    This function mutates the board and game_state. If placement fails after many attempts,
    it will stop to avoid infinite loops."""
    # Alternate placements starting with player 1
    players = [1, 2]
    total_attempts = 0
    max_total_attempts = 20000
    while (game_state["neutral_counts"][1] < threshold or game_state["neutral_counts"][2] < threshold) and total_attempts < max_total_attempts:
        for p in players:
            if game_state["neutral_counts"][p] >= threshold:
                continue
            placed = ai_place_neutral_for_player(p)
            total_attempts += 1
            if not placed:
                # If unable to place for this player after many tries, continue trying overall
                continue
    # If both thresholds satisfied, compute total neutral clusters, move to main phase
    # and set current player to 1
    if game_state["neutral_counts"][1] >= threshold and game_state["neutral_counts"][2] >= threshold:
        # compute total neutral clusters on the board (contiguous same-owner clusters)
        visited = set()
        total = 0
        initial_clusters = []
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if board[r][c] == 3 and (r, c) not in visited:
                    cluster = get_cluster(r, c)
                    coords = [tuple(x) for x in cluster]
                    for (cr, cc) in coords:
                        visited.add((cr, cc))
                    total += 1
                    initial_clusters.append(frozenset(coords))
        game_state["total_neutral_clusters"] = total
        # store initial clusters and initialize owners map
        game_state["initial_neutral_clusters"] = initial_clusters
        game_state["neutral_cluster_owners"] = {i: None for i in range(len(initial_clusters))}
        game_state["phase"] = "main"
        game_state["current_player"] = 1
