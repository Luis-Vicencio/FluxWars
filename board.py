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
    if dice_value != 0:
        # Dice already rolled this turn, return existing value
        return dice_value
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


def _apply_post_move_effects(moved_positions, actor_player, cluster_positions, new_moving_positions):
    """
    Apply force-pull and conversion rules after tiles have been moved on the global `board`.
    Returns list of converted tile positions (r,c).
    """
    global board, polarities, game_state
    converted_cells = []

    # --------------------------
    # FORCE-PULL: magnets attract if opposite polarity and exactly one cell between
    # (same rules as previously implemented)
    # --------------------------
    pulls = []  # list of tuples: (owner, [(fr,fc),(pr,pc)], [(t1r,t1c),(t2r,t2c)], [pol1,pol2])
    scheduled_targets = set()

    rows = len(board)
    cols = len(board[0])
    for (nr, nc) in moved_positions:
        moved_pol = polarities[nr][nc]
        moved_owner = board[nr][nc]
        if moved_pol not in ("+","-"):
            continue
        for ddr, ddc in [(1,0),(-1,0),(0,1),(0,-1)]:
            mid_r, mid_c = nr+ddr, nc+ddc
            far_r, far_c = nr+2*ddr, nc+2*ddc
            if not (0 <= mid_r < rows and 0 <= mid_c < cols and 0 <= far_r < rows and 0 <= far_c < cols):
                continue
            # middle must be empty
            if board[mid_r][mid_c] != 0:
                continue
            # far must be a magnetic tile with opposite polarity
            far_owner = board[far_r][far_c]
            far_pol = polarities[far_r][far_c]
            if far_pol not in ("+","-") or far_pol == moved_pol:
                continue

            # Only allow player clusters to pull neutrals toward themselves
            if not (moved_owner in (1,2) and far_owner == 3):
                continue

            # Find the paired tile for the far tile (its 2x1 piece partner)
            pair = None
            for adr, adc in [(1,0),(-1,0),(0,1),(0,-1)]:
                pr, pc = far_r+adr, far_c+adc
                if not (0 <= pr < rows and 0 <= pc < cols):
                    continue
                if (pr, pc) == (nr, nc):
                    # skip the moved tile itself
                    continue
                if board[pr][pc] == far_owner and polarities[pr][pc] in ("+","-") and polarities[pr][pc] != far_pol:
                    pair = (pr, pc)
                    break
            if not pair:
                continue

            # targets for the pulled piece (move toward moved tile by one step)
            target_far = (mid_r, mid_c)
            target_pair = (pair[0]-ddr, pair[1]-ddc)

            # validate targets in bounds
            if not (0 <= target_pair[0] < rows and 0 <= target_pair[1] < cols):
                continue

            # targets must be empty or be the current positions of the originals
            original_cells = [(far_r, far_c), pair]
            original_set = set(original_cells)
            # allow moving into a slot currently occupied by one of the originals (it will be cleared)
            if board[target_far[0]][target_far[1]] != 0 and (target_far not in original_set):
                continue
            if board[target_pair[0]][target_pair[1]] != 0 and (target_pair not in original_set):
                continue
            if target_far in scheduled_targets or target_pair in scheduled_targets:
                continue

            # schedule this pull
            target_cells = [target_far, target_pair]
            pulls.append((far_owner, original_cells, target_cells, [far_pol, polarities[pair[0]][pair[1]]]))
            scheduled_targets.add(target_far)
            scheduled_targets.add(target_pair)

    # Apply scheduled pulls (clear old cells then set new positions)
    global magnet_ids
    for owner, originals, targets, pols in pulls:
        # preserve magnet ID
        magnet_id = magnet_ids[originals[0][0]][originals[0][1]]
        # clear originals
        for (or_r, or_c) in originals:
            board[or_r][or_c] = 0
            polarities[or_r][or_c] = ""
            magnet_ids[or_r][or_c] = 0
        # set targets in same order with same magnet ID
        for (t, p) in zip(targets, pols):
            tr, tc = t
            board[tr][tc] = owner
            polarities[tr][tc] = p
            magnet_ids[tr][tc] = magnet_id

    # Only allow conversion if actor_player is 1 or 2 and the cluster includes player-owned tiles
    if actor_player in (1,2) and any(board[r][c] == actor_player for (r,c) in cluster_positions):
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
                    # Keep the same magnet_id when converting ownership
                    converted_cells.append((ar, ac))

        # update stats: recompute ownership of initial neutral clusters
        if converted_cells:
            game_state["last_cluster_acquirer"] = actor_player
            # Re-evaluate each initial neutral cluster's owner and update counts
            for idx, cl in enumerate(game_state.get("initial_neutral_clusters", [])):
                owners = set(board[r][c] for (r, c) in cl)
                owners.discard(0)
                owners.discard(3)

                if len(owners) == 1:
                    owner = owners.pop()
                    prev = game_state["neutral_cluster_owners"].get(idx)
                    if prev != owner:
                        if prev in (1, 2):
                            game_state["acquired_clusters"][prev] -= 1

                        game_state["neutral_cluster_owners"][idx] = owner
                        game_state["acquired_clusters"][owner] += 1

            check_winner()

    return converted_cells


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
    # Only allow moves if dice has been rolled
    if dice_value == 0:
        return False, "You must roll the dice before moving.", None
    # Only allow current player to move
    if actor_player != game_state.get("current_player"):
        return False, "It's not your turn.", None

    cluster_positions = [tuple(x) for x in cluster]
    cluster_set = set(cluster_positions)
    # Determine which tiles should actually move:
    # - If the cluster includes any tiles owned by the actor_player, only move those actor-owned tiles
    # - Otherwise (cluster is neutral-only), allow moving the neutral tiles
    global board, polarities

    rows = len(board)
    cols = len(board[0])

    actor_owned_present = False
    for (r, c) in cluster_positions:
        if board[r][c] == actor_player:
            actor_owned_present = True
            break

    if actor_owned_present:
        # Move the entire cluster (player-owned tiles + joined neutral tiles).
        # For neutral tiles, always move both blocks of a 2x1 magnet if any block is included.
        moving_positions = set(cluster_positions)
        # Find all neutral tiles in cluster
        neutral_tiles = [pos for pos in cluster_positions if board[pos[0]][pos[1]] == 3]
        for (nr, nc) in neutral_tiles:
            # For each neutral tile, find its 2x1 partner
            for ddr, ddc in [(1,0),(-1,0),(0,1),(0,-1)]:
                pr, pc = nr+ddr, nc+ddc
                if 0 <= pr < rows and 0 <= pc < cols:
                    if board[pr][pc] == 3 and polarities[pr][pc] in ("+","-") and polarities[pr][pc] != polarities[nr][nc]:
                        # Add both blocks to moving_positions
                        moving_positions.add((pr, pc))
                        moving_positions.add((nr, nc))
        moving_positions = list(moving_positions)
    else:
        moving_positions = list(cluster_positions)

    moving_set = set(moving_positions)

    rows = len(board)
    cols = len(board[0])

    # prevent moving opponent pieces
    if actor_player in (1, 2):
        for (r,c) in cluster_positions:
            if board[r][c] not in (actor_player, 3):
                return False, "Cannot move opponent pieces.", None

    # calculate target for only the moving positions
    new_moving_positions = []
    for (r,c) in moving_positions:
        nr, nc = r+dr, c+dc
        if not (0 <= nr < rows and 0 <= nc < cols):
            return False, "Out of bounds.", None
        new_moving_positions.append((nr, nc))

    # collision check against non-moving cells
    # allow moving into neutral tiles (board == 3) so player pieces can displace/capture neutrals
    for pos in new_moving_positions:
        if pos not in moving_set:
            nr, nc = pos
            # allow moving into empty or neutral cells; block other players' tiles
            if board[nr][nc] != 0 and board[nr][nc] != 3:
                return False, "Blocked.", None

    # copy board
    global magnet_ids
    new_board = [row[:] for row in board]
    new_pol = [row[:] for row in polarities]
    new_ids = [row[:] for row in magnet_ids]

    # clear old positions only for moving tiles
    for (r,c) in moving_positions:
        new_board[r][c] = 0
        new_pol[r][c] = ""
        new_ids[r][c] = 0

    # place moved tiles
    for (r,c),(nr,nc) in zip(moving_positions, new_moving_positions):
        new_board[nr][nc] = board[r][c]
        new_pol[nr][nc] = polarities[r][c]
        new_ids[nr][nc] = magnet_ids[r][c]

    board = new_board
    polarities = new_pol
    magnet_ids = new_ids

    # derive moved positions from new board state (only for moved tiles)
    moved_positions = []
    for (r, c) in moving_positions:
        nr, nc = r + dr, c + dc
        if board[nr][nc] in (actor_player, 3):
            moved_positions.append((nr, nc))

    # Apply post-move effects (force-pull and conversions)
    converted_cells = _apply_post_move_effects(moved_positions, actor_player, cluster_positions, new_moving_positions)

    # Auto-cluster: find the new cluster starting from first moved piece
    new_cluster = None
    if new_moving_positions:
        first_pos = new_moving_positions[0]
        # determine owner after move and pick proper cluster finder
        owner_after = board[first_pos[0]][first_pos[1]]
        if owner_after == 3:
            new_cluster = get_cluster(first_pos[0], first_pos[1])
        elif owner_after in (1, 2):
            new_cluster = find_cluster(first_pos[0], first_pos[1])

    return True, "Cluster moved." + (" Converted neutrals." if converted_cells else ""), new_cluster


def rotate_cluster_cells(cluster, actor_player=None):
    """
    Rotate a single 2-cell magnet (cluster of two adjacent cells) 90 degrees clockwise
    around the first cell in `cluster`.
    Returns (success, message, new_cluster)
    """
    global board, polarities

    if game_state.get("phase") == "ended":
        return False, "Game over — no moves allowed.", None
    if dice_value == 0:
        return False, "You must roll the dice before rotating.", None
    if actor_player != game_state.get("current_player"):
        return False, "It's not your turn.", None

    cluster_positions = [tuple(x) for x in cluster]
    if len(cluster_positions) != 2:
        return False, "Can only rotate a single 2-cell piece.", None

    (r1, c1), (r2, c2) = cluster_positions
    # ensure adjacency
    dr = r2 - r1
    dc = c2 - c1
    if (abs(dr) + abs(dc)) != 1:
        return False, "Cells are not a 2-cell piece.", None

    # require piece to belong to actor (do not rotate opponent pieces)
    if board[r1][c1] != actor_player or board[r2][c2] != actor_player:
        return False, "Can only rotate your own pieces.", None

    rows = len(board)
    cols = len(board[0])

    # compute new offset for second cell after 90° clockwise rotation: (dr,dc) -> (dc, -dr)
    ndr, ndc = dc, -dr
    new_r2 = r1 + ndr
    new_c2 = c1 + ndc

    if not (0 <= new_r2 < rows and 0 <= new_c2 < cols):
        return False, "Rotation out of bounds.", None

    # allow target if empty or current original cells (we'll clear originals)
    originals = {(r1, c1), (r2, c2)}
    if board[new_r2][new_c2] != 0 and (new_r2, new_c2) not in originals:
        return False, "Rotation blocked.", None

    # perform rotation: clear originals then set new positions
    global magnet_ids
    new_board = [row[:] for row in board]
    new_pol = [row[:] for row in polarities]
    new_ids = [row[:] for row in magnet_ids]
    
    # preserve the magnet ID
    magnet_id = magnet_ids[r1][c1]

    # clear originals
    for (or_r, or_c) in originals:
        new_board[or_r][or_c] = 0
        new_pol[or_r][or_c] = ""
        new_ids[or_r][or_c] = 0

    # pivot (r1,c1) stays; second cell moves to (new_r2,new_c2)
    new_board[r1][c1] = actor_player
    new_pol[r1][c1] = polarities[r1][c1]
    new_ids[r1][c1] = magnet_id

    new_board[new_r2][new_c2] = actor_player
    new_pol[new_r2][new_c2] = polarities[r2][c2]
    new_ids[new_r2][new_c2] = magnet_id

    board = new_board
    polarities = new_pol
    magnet_ids = new_ids

    # moved positions list
    moved_positions = [(r1, c1), (new_r2, new_c2)]
    new_moving_positions = [(r1, c1), (new_r2, new_c2)]

    # apply post-move effects (force-pull & conversions)
    converted_cells = _apply_post_move_effects(moved_positions, actor_player, cluster_positions, new_moving_positions)

    # find new cluster
    new_cluster = None
    owner_after = board[r1][c1]
    if owner_after == 3:
        new_cluster = get_cluster(r1, c1)
    elif owner_after in (1, 2):
        new_cluster = find_cluster(r1, c1)

    return True, "Rotated piece." + (" Converted neutrals." if converted_cells else ""), new_cluster


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
magnet_ids = [[0 for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
next_magnet_id = 1

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
    global next_magnet_id
    magnet_id = next_magnet_id
    next_magnet_id += 1
    
    for (dr, dc), polarity in piece:
        r, c = row + dr, col + dc
        board[r][c] = value
        polarities[r][c] = polarity
        magnet_ids[r][c] = magnet_id

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


    # Only allow placement during setup phases
    if phase == "home_setup":
        for (dr, dc), _ in piece:
            if not is_in_half(player, col + dc):
                return False, f"Home piece must be fully inside player {player}'s half."
    elif phase == "neutral_setup":
        for (dr, dc), _ in piece:
            if not is_in_opponent_half(player, col + dc):
                return False, f"Neutral piece must be placed on the opponent's half."
    else:
        # Block placement/conversion in main phase or ended phase
        return False, "Cannot place or convert pieces during main phase."

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
    global board, polarities, magnet_ids, next_magnet_id, game_state, dice_value, selected_cluster
    board = [[0 for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    polarities = [['' for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    magnet_ids = [[0 for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    next_magnet_id = 1
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

    # switch active player and reset dice for the new turn
    game_state["current_player"] = 2 if game_state["current_player"] == 1 else 1
    global dice_value
    dice_value = 0
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
    """
    Return opponent-owned cells that can be stolen by `player`.
    
    Stealing rules:
    - Can steal ANY opponent piece EXCEPT their home piece
    - Player must have at least one piece on the board
    - Opponent piece must have a polarity ('+' or '-')
    
    Returns list of (row, col) tuples for all opponent pieces.
    """
    opponent = 2 if player == 1 else 1
    res = []
    
    # Check if player has any pieces on the board
    player_has_pieces = False
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] == player:
                player_has_pieces = True
                break
        if player_has_pieces:
            break
    
    if not player_has_pieces:
        return []
    
    # Get opponent's home piece coordinates to exclude them
    home_info = game_state.get("homes", {}).get(opponent)
    home_cells = set()
    if home_info:
        home_row, home_col, home_orientation = home_info
        piece_offsets = PIECES[home_orientation]
        for (dr, dc), _ in piece_offsets:
            home_cells.add((home_row + dr, home_col + dc))
    
    # Return all opponent pieces with polarity (excluding home pieces)
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] == opponent and (r, c) not in home_cells:
                pol = polarities[r][c]
                if pol in ('+', '-'):
                    res.append((r, c))
    
    return res


def steal_and_place_magnet(actor_player, source, target):
    """
    Steal an opponent's magnet and place it at the target location.
    
    Args:
        actor_player: The player stealing (1 or 2)
        source: (row, col) of the opponent piece to steal
        target: (row, col) where to place the stolen magnet
    
    Returns:
        (success, message, moved_cells)
    """
    if actor_player not in (1,2):
        return False, "Invalid player", []

    if game_state.get("phase") == "ended":
        return False, "Game over — cannot steal.", []

    opponent = 2 if actor_player == 1 else 1
    
    # Check if source is a home piece - cannot steal home pieces
    home_info = game_state.get("homes", {}).get(opponent)
    if home_info:
        home_row, home_col, home_orientation = home_info
        piece_offsets = PIECES[home_orientation]
        for (dr, dc), _ in piece_offsets:
            if (home_row + dr, home_col + dc) == source:
                return False, "Cannot steal opponent's home piece", []

    eligible = get_stealable_neutrals_for_player(actor_player)
    if not eligible:
        return False, "No eligible pieces to steal", []

    if source not in eligible:
        return False, "Requested piece not eligible for stealing", []

    sr, sc = source
    tr, tc = target

    # Find the partner cell of the source magnet using magnet ID
    source_pol = polarities[sr][sc]
    source_magnet_id = magnet_ids[sr][sc]
    partner = None
    partner_pol = None
    
    # Find the cell with the same magnet ID (the other half of the 2x1 magnet)
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if (r, c) != (sr, sc) and magnet_ids[r][c] == source_magnet_id:
                partner = (r, c)
                partner_pol = polarities[r][c]
                break
        if partner:
            break
    
    if not partner:
        return False, "Could not find partner cell for magnet", []
    
    # Verify partner belongs to opponent
    if board[partner[0]][partner[1]] != opponent:
        return False, "Partner cell doesn't belong to opponent", []

    # Validate target placement
    # Target must be empty or be one of the source cells we're moving
    source_cells = {source, partner}
    if board[tr][tc] != 0 and (tr, tc) not in source_cells:
        return False, "Target location is occupied", []
    
    # Target must be adjacent to actor's cluster with opposite polarity
    target_adjacent_valid = False
    target_pol_needed = None
    
    for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]:
        ar, ac = tr+dr, tc+dc
        if 0 <= ar < BOARD_SIZE and 0 <= ac < BOARD_SIZE:
            if board[ar][ac] == actor_player:
                adj_pol = polarities[ar][ac]
                if adj_pol in ('+','-'):
                    # Target cell needs opposite polarity to connect
                    target_adjacent_valid = True
                    # We'll place source_pol at target if it's opposite to adjacent
                    if adj_pol != source_pol:
                        target_pol_needed = source_pol
                    break
    
    if not target_adjacent_valid:
        return False, "Target must be adjacent to your cluster", []
    
    # Determine orientation: which cell goes to target, which goes to partner location
    # We place source magnet at target, and need to find valid spot for partner
    # Partner must be adjacent to target
    partner_target = None
    for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]:
        pr, pc = tr+dr, tc+dc
        if 0 <= pr < BOARD_SIZE and 0 <= pc < BOARD_SIZE:
            if board[pr][pc] == 0 or (pr, pc) in source_cells:
                partner_target = (pr, pc)
                break
    
    if not partner_target:
        return False, "No space for partner cell near target", []

    # Clear source cells
    global next_magnet_id
    board[sr][sc] = 0
    polarities[sr][sc] = ""
    magnet_ids[sr][sc] = 0
    board[partner[0]][partner[1]] = 0
    polarities[partner[0]][partner[1]] = ""
    magnet_ids[partner[0]][partner[1]] = 0

    # Assign new magnet ID for the stolen magnet
    new_magnet_id = next_magnet_id
    next_magnet_id += 1

    # Place stolen magnet at target with new ID
    board[tr][tc] = actor_player
    polarities[tr][tc] = source_pol
    magnet_ids[tr][tc] = new_magnet_id
    board[partner_target[0]][partner_target[1]] = actor_player
    polarities[partner_target[0]][partner_target[1]] = partner_pol
    magnet_ids[partner_target[0]][partner_target[1]] = new_magnet_id

    moved_cells = [(tr, tc), partner_target]

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

    return True, f"Stole opponent magnet to ({tr},{tc}).", moved_cells


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
