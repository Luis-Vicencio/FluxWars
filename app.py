#app.py

from flask import Flask, render_template, request, jsonify
from board import (
    get_board,
    get_state,
    toggle_piece,
    get_polarities,
    reset_board,
    roll_dice,
    find_cluster,
    can_move_cluster,
    move_cluster,
    get_dice
)

app = Flask(__name__)

@app.route("/")
def index():
    return render_template(
        "index.html",
        board=get_board(),
        polarities=get_polarities(),
        state=get_state()
    )

# --- Placement Phase ---
@app.route("/toggle", methods=["POST"])
def toggle():
    data = request.get_json()
    row, col = data["row"], data["col"]
    orientation = int(data["orientation"])

    success, message = toggle_piece(row, col, orientation)

    return jsonify({
        "success": success,
        "message": message,
        "board": get_board(),
        "polarities": get_polarities(),
        "state": get_state()
    })

@app.route("/reset", methods=["POST"])
def reset():
    reset_board()
    return jsonify({
        "success": True,
        "message": "Board reset.",
        "board": get_board(),
        "polarities": get_polarities(),
        "state": get_state()
    })

# --- Movement Phase ---
@app.route("/roll_dice", methods=["POST"])
def roll_dice_route():
    from board import roll_dice, get_dice  # import inside to avoid circular issues
    value = roll_dice()
    return jsonify({
        "success": True,
        "dice": value
    })

@app.route("/select_cluster", methods=["POST"])
def select_cluster_route():
    data = request.get_json()
    row, col = data["row"], data["col"]
    cluster = find_cluster(row, col)
    return jsonify({"cluster": cluster})

@app.route("/move_cluster", methods=["POST"])
def move_cluster_route():
    data = request.get_json()
    cluster = data["cluster"]
    dr = data["dr"]
    dc = data["dc"]
    remaining_moves = data.get("remaining_moves", 0)

    from board import move_cluster_cells, get_board, get_polarities, get_state, next_player

    success, message = move_cluster_cells(cluster, dr, dc)

    state = get_state()

    if success and remaining_moves <= 1:
        # Player ran out of moves → switch turn
        next_player()
        message = "Turn ended. Next player's turn."

    return jsonify({
        "success": success,
        "message": message,
        "board": get_board(),
        "polarities": get_polarities(),
        "state": get_state()
    })


@app.route("/get_dice", methods=["GET"])
def get_dice_route():
    return jsonify({"dice": get_dice()})

if __name__ == "__main__":
    app.run(debug=True)


