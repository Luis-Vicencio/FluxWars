<!-- .github/copilot-instructions.md -->

# Copilot / AI Agent Instructions — FluxWars

Short, focused notes to help an AI coding agent be productive in this repo.

- **Run locally:** install Flask and run the dev server from the repo root:
  - `pip install flask`
  - `python app.py` (starts Flask with `debug=True`)

- **Big picture:**
  - This is a single-process Flask app (entry: `app.py`) that keeps the entire game state in memory in `board.py`.
  - UI is server-driven HTML + client-side JS: `templates/index.html` renders initial state; `static/script.js` drives interactivity and calls REST endpoints.
  - `board.py` contains the game model: `board`, `polarities`, and `game_state` are global objects mutated in-place.

- **Key files to inspect first:**
  - `app.py` — Flask routes and how the UI talks to the server (endpoints listed below).
  - `board.py` — core game logic: placement, cluster-finding, movement, conversions, dice, and state machine.
  - `templates/index.html`, `static/script.js` — client rendering and fetch patterns (how payloads are structured and how the client expects responses).

- **Important endpoints & expected JSON payloads / responses (examples):**
  - `POST /toggle` — placement during setup. Body: `{ row: int, col: int, orientation: int }`. Returns `{ success, message, board, polarities, state }`.
  - `POST /roll_dice` — rolls dice. Returns `{ success, dice, board, polarities, state, steal_targets }`.
  - `POST /select_cluster` — select cluster on board. Body: `{ row, col }`. Returns `{ cluster: [...] }` (cluster as list of cells).
  - `POST /move_cluster` — move selected cluster. Body: `{ cluster, dr, dc, remaining_moves? }`. Returns `{ success, message, board, polarities, state, new_cluster }`.
  - `POST /steal` — steal neutral tile after a 6. Body: `{ row?, col? }`. Returns converted cells and updated state.
  - `POST /reset`, `GET /get_dice`, `POST /end_turn` — other small helpers.

- **State machine & phases (critical):**
  - `game_state['phase']` values: `home_setup`, `neutral_setup`, `main`, `ended`.
  - Placement rules in `toggle_piece` enforce halves and block column 7 (the divider). Do not place pieces crossing column 7.

- **Board representation conventions:**
  - `board` — 2D list of ints: `0` empty, `1` player1, `2` player2, `3` neutral.
  - `polarities` — 2D list of `"+"`/`"-"`/`""` strings aligned to `board`.
  - `PIECES` (in `board.py`) maps orientations `0/90/180/270` to offsets and polarities. Use these for placement logic.

- **Cluster logic nuance (must be preserved):**
  - `find_cluster(row,col)` — used for player-owned pieces: polarity-alternating clusters where neutral tiles may join but do not expand the cluster further.
  - `get_cluster(row,col)` — used for neutral clusters: simple 4-way adjacency, polarity ignored.
  - Movement rules in `move_cluster_cells` only move actor-owned tiles when a mixed cluster is provided; converted neutrals are limited to single-tile conversions per adjacency (no cascading flips). Tests/changes touching this area must preserve those semantics.

- **Client-side expectations:**
  - `static/script.js` expects JSON responses and uses `updateBoard(board, polarities, phase)` and `updateStatus(state)` to re-render. Many UI flows depend on fields like `state.current_player`, `state.phase`, `state.winner`, and `state.steal_allowed_player`.
  - The client snapshots `lastBoard` to animate neutral→player conversions; backend responses with updated `board` will trigger that animation.

- **Debugging tips:**
  - Server routes include exception handlers that return `traceback` in JSON when errors occur — use those tracebacks for quick debugging.
  - Since state is in-process, restarting the server resets the game. Use `reset` endpoint to programmatically clear state when testing.

- **Conventions & quick checks for PRs:**
  - Preserve in-place state semantics in `board.py` — avoid switching to fully immutable structures without adjusting all accessors in `app.py` and `script.js`.
  - Keep endpoints backward-compatible (responses include `board`, `polarities`, and `state`). Client relies on those being present.
  - When adding features, update both server behavior and `static/script.js` UI handlers together.

If anything here is unclear or you want more examples (e.g., exact request/response samples for each endpoint), tell me which endpoint or file to expand and I will iterate.
