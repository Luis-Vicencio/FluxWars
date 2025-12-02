# ==============================================================
# FIXED board.py — Full working version with correct cluster logic
# ==============================================================

BOARD_SIZE = 15

import random
from collections import deque

dice_value = 0
selected_cluster = []

def roll_dice():
    global dice_value
    dice_value = random.randint(1, 6)
    return dice_value


# ==============================================================
#   PLAYER CLUSTER FINDER — polarity-alternating, no opponents
# ==============================================================

def find_cluster(row, col):
    """
    Return cluster that follows these rules:

    - Only player-owned pieces spread the cluster.
    - Neutral pieces may join ONLY if:
        • they are directly touching a player piece
        • they have opposite polarity
    - Neutrals NEVER extend the cluster outward.
    """

    start_owner = board[row][col]
    start_pol = polarities[row][col]

    if start_owner not in (1, 2):
        return []  # cannot start on neutral or empty

    visited = set()
    queue = deque([(row, col)])
    cluster = []

    while queue:
        r, c = queue.popleft()
        if (r, c) in visited:
            continue

        visited.add((r, c))
        cluster.append((r, c))

        cur_owner = board[r][c]
        cur_pol = polarities[r][c]

        # Explore neighbors
        for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]:
            nr, nc = r+dr, c+dc
            if not (0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE):
                continue

            neigh_owner = board[nr][nc]
            neigh_pol = polarities[nr][nc]

            # -----------------------------
            # CASE 1: Player-owned neighbor
            # -----------------------------
            if neigh_owner == start_owner:
                # must be opposite polarity to be connected
                if neigh_pol in ("+","-") and neigh_pol != cur_pol:
                    queue.append((nr, nc))
                continue

            # -----------------------------
            # CASE 2: Neutral neighbor
            # -----------------------------
            if neigh_owner == 3:
                # neutral joins cluster ONLY if touching a player piece
                # AND opposite polarity
                if cur_owner == start_owner:
                    if neigh_pol in ("+","-") and neigh_pol != cur_pol:
                        # ADD NEUTRAL, but DO NOT EXPAND FROM IT
                        if (nr, nc) not in visited:
                            cluster.append((nr, nc))
                continue

            # Opponent pieces never connect
            continue

    return cluster


# ==============================================================
#   NEUTRAL CLUSTER FINDER (adjacency only)
# ==============================================================

def get_cluster(row, col):
    """
    Determine a neutral cluster strictly by adjacency.
    Used ONLY for initial neutral cluster grouping.
        - Only owner == 3
        - Only 4-way adjacency
        - Polarity does NOT matter
    """
    if not (0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE):
        return []
    if board[row][col] != 3:
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

        for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]:
            nr, nc = r+dr, c+dc
            if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                if board[nr][nc] == 3:
                    stack.append((nr, nc))

    return cluster


# ==============================================================
#   MOVE VALIDATION
# ==============================================================

def can_move_cluster(cluster, dr, dc):
    cluster_set = {tuple(c) for c in cluster}
    for (r, c) in cluster:
        nr, nc = r+dr, c+dc
        if not (0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE):
            return False
        if board[nr][nc] != 0 and (nr, nc) not in cluster_set:
            return False
    return True


# ==============================================================
#   MOVE EXECUTION WITH CORRECT SINGLE-TILE CONVERSION
# ==============================================================

def move_cluster_cells(cluster, dr, dc, actor_player=None):
    """
    Move cluster by (dr,dc).
    Only converts ONE neutral tile per touched opposite-polarity adjacency.
    No chain conversions. No multi-tile cluster flips.
    Returns: (success, message, new_cluster_or_none)
    """
    global board, polarities

    if game_state.get("phase") == "ended":
        return False, "Game over — no moves allowed.", None

    cluster_positions = [tuple(x) for x in cluster]
    cluster_set = set(cluster_positions)

    rows = len(board)
    cols = len(board[0])

    # prevent moving opponent pieces
    if actor_player in (1, 2):
        for (r,c) in cluster_positions:
            if board[r][c] not in (actor_player, 3):
                return False, "Cannot move opponent pieces.", None

    # calculate target
    new_positions = []
    for (r,c) in cluster_positions:
        nr, nc = r+dr, c+dc
        if not (0 <= nr < rows and 0 <= nc < cols):
            return False, "Out of bounds.", None
        new_positions.append((nr, nc))

    # collision check
    for pos in new_positions:
        if pos not in cluster_set:
            nr, nc = pos
            if board[nr][nc] != 0:
                return False, "Blocked.", None

    # copy board
    new_board = [row[:] for row in board]
    new_pol = [row[:] for row in polarities]

    # clear old
    for (r,c) in cluster_positions:
        new_board[r][c] = 0
        new_pol[r][c] = ""

    # place new
    for (r,c),(nr,nc) in zip(cluster_positions, new_positions):
        new_board[nr][nc] = board[r][c]
        new_pol[nr][nc] = polarities[r][c]

    board = new_board
    polarities = new_pol

    # --------------------------
    # SINGLE-TILE conversion rule
    # --------------------------
    converted_cells = []

    if actor_player in (1,2) and (dr != 0 or dc != 0):

        # Correct: derive moved positions from new board state
        moved_positions = []
        for (r, c) in cluster_positions:
            nr, nc = r + dr, c + dc
            if board[nr][nc] in (actor_player, 3):
                moved_positions.append((nr, nc))

        for (nr, nc) in moved_positions:
            moved_pol = polarities[nr][nc]
            if moved_pol not in ("+","-"):
                continue

            for ddr, ddc in [(1,0),(-1,0),(0,1),(0,-1)]:
                ar, ac = nr+ddr, nc+ddc
                if not (0 <= ar < rows and 0 <= ac < cols):
                    continue

                if board[ar][ac] != 3:   # must be neutral
                    continue

                neigh_pol = polarities[ar][ac]
                if neigh_pol in ("+","-") and neigh_pol != moved_pol:
                    board[ar][ac] = actor_player
                    converted_cells.append((ar, ac))

        # update stats
        for (cr,cc) in converted_cells:
            game_state["last_cluster_acquirer"] = actor_player
            game_state["acquired_clusters"][actor_player] += 1

        if converted_cells:
            check_winner()

    # Auto-cluster: find the new cluster starting from first moved piece
    new_cluster = None
    if actor_player in (1, 2) and new_positions:
        # Use find_cluster on the first moved position to get the new cluster
        first_pos = new_positions[0]
        new_cluster = find_cluster(first_pos[0], first_pos[1])

    return True, "Cluster moved." + (" Converted neutrals." if converted_cells else ""), new_cluster


# ==============================================================
#   ACCESSORS
# ==============================================================

def get_board():
    return board

def get_polarities():
    return polarities

def get_state():
    return game_state

def get_dice():
    return dice_value


# ==============================================================
#   STATE + PIECE PLACEMENT + PHASES
# ==============================================================

board = [[0 for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
polarities = [['' for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]

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
    "steal_allowed_player": None,
    "winner": None,
    "main_turns": 0,
    "max_main_turns": 4,
}

PIECES = {
    0:   [((0, 0), '+'), ((0, 1), '-')],
    90:  [((0, 0), '+'), ((1, 0), '-')],
    180: [((0, 0), '+'), ((0, -1), '-')],
    270: [((0, 0), '+'), ((-1, 0), '-')],
}

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
        # switch
        if player == 1:
            state["current_player"] = 2
        else:
            state["phase"] = "neutral_setup"
            state["current_player"] = 1
            ai_place_all_neutrals()
        return True, "Placed home piece."

    elif phase == "neutral_setup":
        return False, "Neutral pieces are placed automatically by the server."

    return False, "Unknown error."


# ==============================================================
#   RESET BOARD
# ==============================================================

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
        "steal_allowed_player": None,
        "winner": None,
        "main_turns": 0,
        "max_main_turns": 4,
    }


# ==============================================================
#   TURN PROGRESSION
# ==============================================================

def next_player():
    if game_state.get("phase") == "ended":
        return game_state["current_player"]

    if game_state.get("phase") == "main":
        game_state["main_turns"] += 1

        if game_state["main_turns"] >= game_state.get("max_main_turns", 4):
            check_winner()

            if game_state.get("winner") is None:
                a1 = game_state["acquired_clusters"][1]
                a2 = game_state["acquired_clusters"][2]
                if a1 > a2:
                    game_state["winner"] = 1
                elif a2 > a1:
                    game_state["winner"] = 2
                else:
                    last = game_state.get("last_cluster_acquirer")
                    if last in (1,2):
                        game_state["winner"] = last
                    else:
                        # explicit draw when counts equal and no last acquirer
                        game_state["winner"] = "draw"

            game_state["phase"] = "ended"
            return game_state["current_player"]

    game_state["current_player"] = 2 if game_state["current_player"] == 1 else 1
    return game_state["current_player"]


# ==============================================================
#   SERIALIZATION FOR CLIENT
# ==============================================================

def get_state_serializable():
    import copy
    s = copy.deepcopy(game_state)
    inc = s.get("initial_neutral_clusters")
    if inc:
        serial = []
        for cluster in inc:
            serial.append([list(x) for x in cluster])
        s["initial_neutral_clusters"] = serial
    return s


# ==============================================================
#   AI NEUTRAL PLACEMENT
# ==============================================================

def ai_place_neutral_for_player(player, max_attempts=2000, min_distance=4):
    cols = range(8, BOARD_SIZE) if player == 1 else range(0, 7)
    attempts = 0
    while attempts < max_attempts:
        attempts += 1
        orientation = random.choice(list(PIECES.keys()))
        piece = PIECES[orientation]
        col = random.choice(list(cols))
        row = random.randrange(0, BOARD_SIZE)

        touches_middle = any((col + dc) == 7 for (dr, dc), _ in piece)
        if touches_middle:
            continue

        ok, _ = can_place(piece, row, col)
        if not ok:
            continue

        def too_close(r0, c0):
            for r in range(BOARD_SIZE):
                for c in range(BOARD_SIZE):
                    if board[r][c] == 3:
                        if abs(r-r0) + abs(c-c0) < min_distance:
                            return True
            return False

        conflict = False
        for (dr, dc), _ in piece:
            rr, cc = row+dr, col+dc
            if too_close(rr, cc):
                conflict = True
                break
        if conflict:
            continue

        place_piece(piece, row, col, 3)
        game_state["neutral_counts"][player] += 1
        return True

    return False


def ai_place_all_neutrals(threshold=4):
    players = [1,2]
    attempts = 0
    max_attempts = 20000

    while (game_state["neutral_counts"][1] < threshold or 
           game_state["neutral_counts"][2] < threshold) and attempts < max_attempts:

        for p in players:
            if game_state["neutral_counts"][p] >= threshold:
                continue
            placed = ai_place_neutral_for_player(p)
            attempts += 1

    # Compute neutral clusters
    if (game_state["neutral_counts"][1] >= threshold and 
        game_state["neutral_counts"][2] >= threshold):

        visited = set()
        total = 0
        initial_clusters = []

        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if board[r][c] == 3 and (r, c) not in visited:
                    cluster = get_cluster(r, c)
                    coords = [tuple(x) for x in cluster]
                    for (rr,cc) in coords:
                        visited.add((rr,cc))
                    total += 1
                    initial_clusters.append(frozenset(coords))

        game_state["total_neutral_clusters"] = total
        game_state["initial_neutral_clusters"] = initial_clusters
        game_state["neutral_cluster_owners"] = {i: None for i in range(len(initial_clusters))}
        game_state["phase"] = "main"
        game_state["current_player"] = 1
        game_state["main_turns"] = 0


# ==============================================================
#   STEAL MECHANICS
# ==============================================================

def get_stealable_neutrals_for_player(player):
    opponent = 2 if player == 1 else 1
    res = []

    initial_clusters = game_state.get('initial_neutral_clusters', [])
    if initial_clusters:
        for cl in initial_clusters:
            for (r,c) in cl:
                if board[r][c] != opponent:
                    continue
                pol = polarities[r][c]
                if pol not in ('+','-'):
                    continue

                eligible = False
                for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]:
                    nr, nc = r+dr, c+dc
                    if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                        if board[nr][nc] == player:
                            neigh = polarities[nr][nc]
                            if neigh in ('+','-') and neigh != pol:
                                eligible = True
                                break
                if eligible:
                    res.append((r,c))

        if not res:
            adj_only = []
            for cl in initial_clusters:
                for (r,c) in cl:
                    if board[r][c] != opponent:
                        continue
                    for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]:
                        nr, nc = r+dr, c+dc
                        if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                            if board[nr][nc] == player:
                                adj_only.append((r,c))
                                break
            return adj_only

        return res

    # fallback
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] != 3:
                continue
            pol = polarities[r][c]
            if pol not in ('+','-'):
                continue

            eligible = False
            for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]:
                nr, nc = r+dr, c+dc
                if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                    if board[nr][nc] == player:
                        neigh = polarities[nr][nc]
                        if neigh in ('+','-') and neigh != pol:
                            eligible = True
                            break
            if eligible:
                res.append((r,c))

    return res


def steal_neutral_cell(actor_player, target=None):
    if actor_player not in (1,2):
        return False, "Invalid player", []

    if game_state.get("phase") == "ended":
        return False, "Game over — cannot steal.", []

    eligible = get_stealable_neutrals_for_player(actor_player)
    if not eligible:
        return False, "No eligible neutral pieces to steal", []

    if target:
        if target not in eligible:
            return False, "Requested target not eligible", []
        chosen = target
    else:
        chosen = random.choice(eligible)

    cr, cc = chosen

    board[cr][cc] = actor_player

    # Update cluster ownership
    for idx, cl in enumerate(game_state.get("initial_neutral_clusters", [])):
        owners = set(board[r][c] for (r,c) in cl)
        owners.discard(0)
        owners.discard(3)

        if len(owners) == 1:
            owner = owners.pop()
            prev = game_state["neutral_cluster_owners"].get(idx)
            if prev != owner:
                if prev in (1,2):
                    game_state["acquired_clusters"][prev] -= 1

                game_state["neutral_cluster_owners"][idx] = owner
                game_state["acquired_clusters"][owner] += 1
                game_state["last_cluster_acquirer"] = owner

    check_winner()

    return True, "Stole neutral piece.", [chosen]


# ==============================================================
#   WINNING LOGIC
# ==============================================================

def check_winner():
    total = game_state.get("total_neutral_clusters", 0)
    if total == 0:
        return None

    a1 = game_state["acquired_clusters"][1]
    a2 = game_state["acquired_clusters"][2]

    if a1 > total // 2:
        game_state["winner"] = 1
        game_state["phase"] = "ended"
        return 1
    if a2 > total // 2:
        game_state["winner"] = 2
        game_state["phase"] = "ended"
        return 2

    if a1 + a2 >= total:
        if a1 == a2:
            last = game_state.get("last_cluster_acquirer")
            if last in (1,2):
                game_state["winner"] = last
            else:
                game_state["winner"] = "draw"
            game_state["phase"] = "ended"
            return game_state["winner"]

    return None
