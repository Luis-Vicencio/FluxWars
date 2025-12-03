from flask import Flask, render_template, request, jsonify
from board import (
    get_board,
    get_state,
    get_state_serializable,
    toggle_piece,
    get_polarities,
    reset_board,
    roll_dice,
    find_cluster,
    get_cluster,
    can_move_cluster,
    rotate_cluster_cells,
    get_dice,
)

app = Flask(__name__)


@app.route("/")
def index():
    return render_template(
        "index.html",
        board=get_board(),
        polarities=get_polarities(),
        state=get_state_serializable(),
    )


# --- Placement Phase ---
@app.route("/toggle", methods=["POST"])
def toggle():
    try:
        data = request.get_json()
        row, col = data["row"], data["col"]
        orientation = int(data["orientation"])

        success, message = toggle_piece(row, col, orientation)

        return jsonify(
            {
                "success": success,
                "message": message,
                "board": get_board(),
                "polarities": get_polarities(),
                "state": get_state_serializable(),
            }
        )
    except Exception as e:
        import traceback

        tb = traceback.format_exc()
        # return error to client for easier debugging
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"Server error during toggle: {str(e)}",
                    "traceback": tb,
                }
            ),
            500,
        )


@app.route("/reset", methods=["POST"])
def reset():
    reset_board()
    return jsonify(
        {
            "success": True,
            "message": "Board reset.",
            "board": get_board(),
            "polarities": get_polarities(),
            "state": get_state_serializable(),
        }
    )


# --- Movement Phase ---
@app.route("/roll_dice", methods=["POST"])
def roll_dice_route():
    # roll the dice; do NOT switch player here — player keeps the turn until moves exhausted
    try:
        from board import roll_dice, get_board, get_polarities, get_state, next_player
        from board import get_state, get_stealable_neutrals_for_player

        value = roll_dice()
        state = get_state()
        steal_targets = None
        if value == 6:
            cp = state["current_player"]
            # mark allowed stealer on server state
            state["steal_allowed_player"] = cp
            steal_targets = get_stealable_neutrals_for_player(cp)
            
            # DEBUG: Log steal target detection details
            print(f"\n=== STEAL TARGET DEBUG ===")
            print(f"Current player: {cp}")
            print(f"Phase: {state['phase']}")
            print(f"Steal targets found: {steal_targets}")
            print(f"Number of targets: {len(steal_targets) if steal_targets else 0}")
            
            # Log opponent positions
            opponent = 2 if cp == 1 else 1
            board_state = get_board()
            pols = get_polarities()
            opponent_pieces = []
            for r in range(len(board_state)):
                for c in range(len(board_state[0])):
                    if board_state[r][c] == opponent:
                        opponent_pieces.append((r, c, pols[r][c]))
            print(f"Opponent (player {opponent}) pieces: {opponent_pieces[:10]}")  # limit output
            
            # Log player pieces
            player_pieces = []
            for r in range(len(board_state)):
                for c in range(len(board_state[0])):
                    if board_state[r][c] == cp:
                        player_pieces.append((r, c, pols[r][c]))
            print(f"Player {cp} pieces: {player_pieces[:10]}")  # limit output
            print(f"=========================\n")

        return jsonify({
            "success": True,
            "dice": value,
            "board": get_board(),
            "polarities": get_polarities(),
            "state": get_state_serializable(),
            "steal_targets": [list(x) for x in (steal_targets or [])],
        })
    except Exception as e:
        import traceback

        tb = traceback.format_exc()
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"Server error during roll_dice: {str(e)}",
                    "traceback": tb,
                }
            ),
            500,
        )


@app.route("/select_cluster", methods=["POST"])
def select_cluster_route():
    data = request.get_json()
    row, col = data["row"], data["col"]
    # Allow selecting neutral clusters (owner == 3) as well as player clusters
    board = get_board()
    owner = None
    try:
        owner = board[row][col]
    except Exception:
        owner = None

    if owner == 3:
        cluster = get_cluster(row, col)
    else:
        cluster = find_cluster(row, col)

    return jsonify({"cluster": cluster})


@app.route("/move_cluster", methods=["POST"])
def move_cluster_route():
    try:
        data = request.get_json()
        cluster = data["cluster"]
        dr = data["dr"]
        dc = data["dc"]
        # Do NOT switch player on roll; player keeps the turn until they exhaust moves.
        remaining_moves = data.get("remaining_moves", None)
        from board import move_cluster_cells, get_board, get_polarities, get_state, next_player

        # actor is the player who is making this move (before any next_player call)
        state_before = get_state()
        actor = state_before["current_player"]

        success, message, new_cluster = move_cluster_cells(cluster, dr, dc, actor_player=actor)

        state = get_state()

        # Only switch player when remaining_moves is provided and the player has exhausted moves
        if success and remaining_moves is not None and remaining_moves <= 0:
            next_player()
            message = "Turn ended. Next player's turn."

        return jsonify(
            {
                "success": success,
                "message": message,
                "board": get_board(),
                "polarities": get_polarities(),
                    "state": get_state_serializable(),
                    "new_cluster": [[int(r), int(c)] for (r, c) in new_cluster] if new_cluster else None,
            }
        )
    except Exception as e:
        import traceback

        tb = traceback.format_exc()
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"Server error during move_cluster: {str(e)}",
                    "traceback": tb,
                }
            ),
            500,
        )


@app.route("/rotate_cluster", methods=["POST"])
def rotate_cluster_route():
    try:
        data = request.get_json()
        cluster = data["cluster"]
        remaining_moves = data.get("remaining_moves", None)
        from board import rotate_cluster_cells, get_board, get_polarities, get_state, next_player

        state_before = get_state()
        actor = state_before["current_player"]

        success, message, new_cluster = rotate_cluster_cells(cluster, actor_player=actor)

        state = get_state()
        if success and remaining_moves is not None and remaining_moves <= 0:
            next_player()
            message = "Turn ended. Next player's turn."

        return jsonify(
            {
                "success": success,
                "message": message,
                "board": get_board(),
                "polarities": get_polarities(),
                "state": get_state_serializable(),
                "new_cluster": [[int(r), int(c)] for (r, c) in new_cluster] if new_cluster else None,
            }
        )
    except Exception as e:
        import traceback

        tb = traceback.format_exc()
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"Server error during rotate_cluster: {str(e)}",
                    "traceback": tb,
                }
            ),
            500,
        )


@app.route("/get_dice", methods=["GET"])
def get_dice_route():
    return jsonify({"dice": get_dice()})


@app.route("/end_turn", methods=["POST"])
def end_turn_route():
    try:
        from board import next_player, get_board, get_polarities, get_state_serializable

        next_player()
        return jsonify({
            "success": True,
            "message": "Turn ended by player.",
            "board": get_board(),
            "polarities": get_polarities(),
            "state": get_state_serializable(),
        })
    except Exception as e:
        import traceback

        tb = traceback.format_exc()
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"Server error during end_turn: {str(e)}",
                    "traceback": tb,
                }
            ),
            500,
        )


@app.route("/steal", methods=["POST"])
def steal_route():
    try:
        data = request.get_json() or {}
        source_row = data.get("source_row")
        source_col = data.get("source_col")
        target_row = data.get("target_row")
        target_col = data.get("target_col")

        from board import (
            get_state,
            steal_and_place_magnet,
            get_board,
            get_polarities,
            get_state_serializable,
        )

        state = get_state()
        actor = state["current_player"]

        # ensure steal was allowed for this player
        if state.get("steal_allowed_player") != actor:
            return jsonify({"success": False, "message": "Steal not allowed right now."}), 400

        if source_row is None or source_col is None or target_row is None or target_col is None:
            return jsonify({"success": False, "message": "Missing source or target coordinates."}), 400

        source = (int(source_row), int(source_col))
        target = (int(target_row), int(target_col))

        success, message, moved_cells = steal_and_place_magnet(actor, source, target)
        if success:
            # clear steal permission after use
            state["steal_allowed_player"] = None
            return jsonify({
                "success": True,
                "message": message,
                "moved_cells": [list(x) for x in moved_cells],
                "board": get_board(),
                "polarities": get_polarities(),
                "state": get_state_serializable(),
            })
        else:
            return jsonify({"success": False, "message": message}), 400
    except Exception as e:
        import traceback

        tb = traceback.format_exc()
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"Server error during steal: {str(e)}",
                    "traceback": tb,
                }
            ),
            500,
        )


if __name__ == "__main__":
    app.run(debug=True)
