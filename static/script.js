let orientation = 0;
const orientations = [0, 90, 180, 270];
let orientationIndex = 0;
let ghostCells = [];
let selectedCluster = [];
let diceValue = 0;
let currentPhase = "home_setup";
let lastBoard = null; // snapshot for detecting conversions

// ======================= MAIN SETUP =======================

document.addEventListener("DOMContentLoaded", () => {
    const rotateBtn = document.getElementById("rotateBtn");
    const orientationLabel = document.getElementById("orientationLabel");
    const boardDiv = document.getElementById("board");
    const rollDiceBtn = document.getElementById("rollDiceBtn");
    const diceResult = document.getElementById("diceResult");
    const mainMenu = document.getElementById("mainMenu");
    const gameContainer = document.getElementById("gameContainer");
    const modal = document.getElementById("modal");
    const modalBody = document.getElementById("modalBody");
    const closeModal = document.getElementById("closeModal");
    const bgLayer = document.querySelector('#gameContainer .bg-layer'); // harmless if null

    // --- MAIN MENU BUTTONS ---
    document.getElementById("startGameBtn").addEventListener("click", () => {
        mainMenu.style.display = "none";
        gameContainer.style.display = "block";
    });

    document.getElementById("settingsBtn").addEventListener("click", () => {
        showModal("<h3>Settings</h3><p>No settings available yet — coming soon!</p>");
    });

    document.getElementById("helpBtn").addEventListener("click", () => {
        showModal(`
            <h3>Help</h3>
            <ul>
                <li>Place your home piece on your side (left or right).</li>
                <li>Neutral pieces are automatically placed for each player.</li>
                <li>In the main phase, roll the dice to move your magnetic clusters.</li>
                <li>Opposite polarities (+/–) attract, same polarities repel.</li>
                <li>The game ends after 4 total main-phase turns.</li>
            </ul>
        `);
    });

    document.getElementById("aboutBtn").addEventListener("click", () => {
        showModal(`
            <h3>About</h3>
            <p><strong>Flux Wars</strong><br>
            Created with Flask, HTML, and JavaScript.<br>
            Inspired by the dynamics of magnetic fields.</p>
        `);
    });

    closeModal.addEventListener("click", () => modal.style.display = "none");
    window.addEventListener("click", (e) => {
        if (e.target === modal) modal.style.display = "none";
    });

    function showModal(content) {
        modalBody.innerHTML = content;
        modal.style.display = "block";
    }

    // Gentle mouse-based parallax for background layer (if present)
    if (bgLayer && gameContainer) {
        let width = gameContainer.clientWidth;
        let height = gameContainer.clientHeight;
        function onMouseMove(e) {
            const rect = gameContainer.getBoundingClientRect();
            const x = (e.clientX - rect.left) / width - 0.5; // -0.5..0.5
            const y = (e.clientY - rect.top) / height - 0.5;
            const maxTranslate = 16; // px
            const tx = (-x) * maxTranslate;
            const ty = (-y) * maxTranslate;
            bgLayer.style.transform = `scale(1.03) translate(${tx}px, ${ty}px)`;
        }
        function onMouseLeave() {
            bgLayer.style.transform = '';
        }
        gameContainer.addEventListener('mousemove', onMouseMove);
        gameContainer.addEventListener('mouseleave', onMouseLeave);
        window.addEventListener('resize', () => {
            width = gameContainer.clientWidth; height = gameContainer.clientHeight;
        });
    }

    // --- ROTATE BUTTON ---
    rotateBtn.addEventListener("click", async () => {
        // In setup phases, rotate piece orientation as before
        if (currentPhase !== "main") {
            orientationIndex = (orientationIndex + 1) % orientations.length;
            orientation = orientations[orientationIndex];
            orientationLabel.textContent = `${orientation}°`;
            clearGhostPreview();
            return;
        }

        // In main phase: rotate selected cluster for cost of one move
        if (!selectedCluster || !selectedCluster.length) {
            showModal('<h3>Rotate piece</h3><p>Select a piece to rotate first.</p>');
            return;
        }
        if (diceValue <= 0) {
            showModal('<h3>No moves remaining</h3><p>Roll the dice first.</p>');
            return;
        }

        const res = await fetch('/rotate_cluster', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cluster: selectedCluster, remaining_moves: diceValue - 1 })
        });
        const data = await res.json();
        if (data.success) {
            addHistoryEntry('Rotated piece');
            if (data.board && data.polarities) updateBoard(data.board, data.polarities, data.state?.phase || currentPhase);
            if (data.state) updateStatus(data.state);
            // update selected cluster to server-provided new cluster
            selectedCluster = data.new_cluster || [];
            highlightCluster(selectedCluster);
            diceValue -= 1;
            const diceResult = document.getElementById('diceResult');
            if (diceResult) diceResult.textContent = `🎲 Moves left: ${diceValue}`;
            if (diceValue <= 0) {
                selectedCluster = [];
                showModal('<h3>Out of moves</h3><p>You have no moves left this turn.</p>');
            }
        } else {
            showModal(`<h3>Rotation failed</h3><p>${data.message || 'Could not rotate this piece.'}</p>`);
        }
    });

    // --- BOARD CLICK (phase-dependent) ---
    boardDiv.addEventListener("click", async (e) => {
        const cell = e.target.closest(".cell");
        if (!cell) return;

        const row = parseInt(cell.dataset.row);
        const col = parseInt(cell.dataset.col);

        if (col === 7 && currentPhase !== "main") return; // divider guard

        if (currentPhase === "main") {
            // SELECT CLUSTER (main phase)
            if (diceValue === 0) {
                showModal('<h3>Roll required</h3><p>Roll the dice first!</p>');
                return;
            }
            const res = await fetch("/select_cluster", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ row, col }),
            });
            const data = await res.json();
            if (data.cluster?.length) {
                selectedCluster = data.cluster;
                highlightCluster(selectedCluster);
            }
        } else {
            // PLACE PIECE (setup phase)
            const res = await fetch("/toggle", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ row, col, orientation }),
            });
            const data = await res.json();
            if (data.success) {
                updateStatus(data.state);
                updateBoard(data.board, data.polarities, data.state.phase);
                clearGhostPreview();
            } else {
                showModal(`<h3>Invalid placement</h3><p>${data.message || 'That placement is not allowed.'}</p>`);
            }
        }
    });

    // --- GHOST PREVIEW (setup only) ---
    boardDiv.addEventListener("mousemove", (e) => {
        if (currentPhase === "main") return;
        const cell = e.target.closest(".cell");
        if (!cell) return;
        const row = parseInt(cell.dataset.row);
        const col = parseInt(cell.dataset.col);
        showGhostPreview(row, col);
    });
    boardDiv.addEventListener("mouseleave", clearGhostPreview);

    // --- ROLL DICE ---
    rollDiceBtn.addEventListener("click", async () => {
        const diceAnim = document.getElementById('diceAnim');
        diceAnim.classList.add('dice-rolling');
        // small delay to show animation for better UX
        const res = await fetch("/roll_dice", { method: "POST" });
        const data = await res.json();
        diceAnim.classList.remove('dice-rolling');
        if (data.success) {
            diceValue = data.dice;
            diceResult.textContent = `🎲 You rolled a ${diceValue}`;
            const diceResultBubble = document.getElementById('diceResultBubble');
            if (diceResultBubble) diceResultBubble.style.display = 'inline-flex';
            addHistoryEntry(`Player rolled ${diceValue}`);
            // Update UI to reflect new turn/board state returned by server
            if (data.state) updateStatus(data.state);
            if (data.board && data.polarities) updateBoard(data.board, data.polarities, data.state?.phase || currentPhase);
            // If server indicates steal opportunity (rolled a 6), show steal UI
            if (data.steal_targets && data.steal_targets.length) {
                showStealOptions(data.steal_targets);
            } else if (data.steal_targets && data.steal_targets.length === 0 && data.dice === 6) {
                // rolled a 6 but no targets
                addHistoryEntry('Rolled 6 but no stealable neutrals available');
                showModal('<h3>No steal targets</h3><p>There are no eligible neutral pieces adjacent to opponent clusters to steal.</p>');
            }
        } else {
            diceResult.textContent = "❌ Dice roll failed.";
        }
    });

    // --- MOVEMENT KEYS (main phase) ---
    document.addEventListener("keydown", async (e) => {
        if (currentPhase !== "main" || !selectedCluster.length || diceValue <= 0) return;
        let dr = 0, dc = 0;
        if (e.key === "ArrowUp") dr = -1;
        else if (e.key === "ArrowDown") dr = 1;
        else if (e.key === "ArrowLeft") dc = -1;
        else if (e.key === "ArrowRight") dc = 1;
        else return;

        const res = await fetch("/move_cluster", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            // send remaining_moves so server knows when to switch turns
            body: JSON.stringify({ cluster: selectedCluster, dr, dc, remaining_moves: diceValue - 1 }),
        });
        const data = await res.json();
        if (data.success) {
            addHistoryEntry(`Moved cluster by (${dr},${dc})`);
            updateBoard(data.board, data.polarities, data.state?.phase || "main");
            if (data.state) updateStatus(data.state);
            // Auto-select the new cluster returned by server for next move
            selectedCluster = data.new_cluster || [];
            highlightCluster(selectedCluster);
            diceValue -= 1;
            diceResult.textContent = `🎲 Moves left: ${diceValue}`;
            const diceResultBubble = document.getElementById('diceResultBubble');
            if (diceResultBubble) diceResultBubble.style.display = diceValue > 0 ? 'inline-flex' : 'none';
            if (diceValue <= 0) {
                selectedCluster = [];
                showModal('<h3>Out of moves</h3><p>You have no moves left this turn.</p>');
            }
        } else {
            showModal(`<h3>Move blocked</h3><p>${data.message || 'Movement could not be completed.'}</p>`);
        }
    });
});

// ======================= RENDER BOARD =======================

function updateBoard(board, polarities, phase = "setup") {
    const boardDiv = document.getElementById("board");
    currentPhase = phase;
    boardDiv.innerHTML = "";

    const isMainPhase = (phase === "main");

    for (let r = 0; r < board.length; r++) {
        const rowDiv = document.createElement("div");
        rowDiv.classList.add("row");

        for (let c = 0; c < board[r].length; c++) {
            const cell = document.createElement("div");
            cell.classList.add("cell");
            cell.dataset.row = r;
            cell.dataset.col = c;

            const value = board[r][c];
            if (value === 1) cell.classList.add("player1");
            else if (value === 2) cell.classList.add("player2");
            else if (value === 3) cell.classList.add("neutral");

            if (!isMainPhase && c === 7) {
                cell.classList.add("border-cell");
            }

            const polarity = polarities[r][c];
            if (polarity === "+" || polarity === "-" || polarity === "–") {
                const span = document.createElement("span");
                span.textContent = polarity;
                span.classList.add("polarity");
                cell.appendChild(span);
            }

            rowDiv.appendChild(cell);
        }
        boardDiv.appendChild(rowDiv);
    }

    // If we have a snapshot of the previous board, detect converted neutral -> player changes
    if (lastBoard) {
        const converted = [];
        for (let r = 0; r < board.length; r++) {
            for (let c = 0; c < board[r].length; c++) {
                if (lastBoard[r] && lastBoard[r][c] === 3 && board[r][c] !== 3) {
                    // neutral converted to player 1 or 2
                    converted.push([r, c]);
                }
            }
        }
        // animate converted cells
        converted.forEach(([r, c]) => {
            const cell = document.querySelector(`.cell[data-row='${r}'][data-col='${c}']`);
            if (cell) {
                cell.classList.add('converted');
                setTimeout(() => cell.classList.remove('converted'), 700);
            }
        });
        if (converted.length) addHistoryEntry(`Captured ${converted.length} neutral piece(s)`);
    }

    // update lastBoard snapshot
    lastBoard = board.map(row => row.slice());
}


// Show steal options in the modal; targets is array of [r,c]
function showStealOptions(targets) {
    const body = document.getElementById('modalBody');
    if (!body) return;
    // highlight stealable cells on board
    document.querySelectorAll('.cell.stealable').forEach(c => c.classList.remove('stealable'));
    targets.forEach(([r,c]) => {
        const cell = document.querySelector(`.cell[data-row='${r}'][data-col='${c}']`);
        if (cell) cell.classList.add('stealable');
    });

    // build list in modal
    let html = '<h3>Steal Opportunity!</h3>';
    html += '<p>Select a neutral piece to steal (or close to skip):</p>';
    html += '<div class="steal-list">';
    targets.forEach(([r,c]) => {
        html += `<div class="target" data-row="${r}" data-col="${c}">Neutral at (${r}, ${c})</div>`;
    });
    html += '</div>';
    html += '<div class="steal-actions"><button id="stealCloseBtn">Close</button></div>';
    body.innerHTML = html;
    const modal = document.getElementById('modal');
    modal.style.display = 'block';

    // attach handlers
    document.querySelectorAll('.steal-list .target').forEach(el => {
        el.addEventListener('click', async (e) => {
            const r = el.getAttribute('data-row');
            const c = el.getAttribute('data-col');
            // call server to perform steal
            const res = await fetch('/steal', {
                method: 'POST',
                headers: { 'Content-Type':'application/json' },
                body: JSON.stringify({ row: parseInt(r), col: parseInt(c) })
            });
            const data = await res.json();
            // remove highlights
            document.querySelectorAll('.cell.stealable').forEach(cel => cel.classList.remove('stealable'));
            modal.style.display = 'none';
            if (data.success) {
                addHistoryEntry('Stole neutral piece');
                // animate converted cells if server provided them
                if (data.converted && data.converted.length) {
                    data.converted.forEach(([rr, cc]) => {
                        const cell = document.querySelector(`.cell[data-row='${rr}'][data-col='${cc}']`);
                        if (cell) {
                            cell.classList.add('converted');
                            setTimeout(() => cell.classList.remove('converted'), 700);
                        }
                    });
                }
                if (data.board && data.polarities) updateBoard(data.board, data.polarities, data.state?.phase || currentPhase);
                if (data.state) updateStatus(data.state);
            } else {
                showModal(`<h3>Steal failed</h3><p>${data.message || 'No valid steal action available.'}</p>`);
            }
        });
    });

    const closeBtn = document.getElementById('stealCloseBtn');
    if (closeBtn) closeBtn.addEventListener('click', () => {
        document.querySelectorAll('.cell.stealable').forEach(cel => cel.classList.remove('stealable'));
        modal.style.display = 'none';
    });
}

// ======================= STATUS =======================

function updateStatus(state) {
    const status = document.getElementById("status");
    const rollDiceBtn = document.getElementById("rollDiceBtn");
    const endTurnBtn = document.getElementById('endTurnBtn');
    const turnBanner = document.getElementById('turnBanner');
    currentPhase = state.phase;

    // Game ended: freeze UI and show final result
    if (state.phase === "ended") {
        if (state.winner === 1 || state.winner === 2) {
            status.textContent = `Game Over — Player ${state.winner} Wins!`;
            if (turnBanner) {
                turnBanner.textContent = `Winner: Player ${state.winner}`;
                turnBanner.style.background = state.winner === 1
                    ? 'linear-gradient(90deg, #2b6cb0, #2b6cb0)'
                    : 'linear-gradient(90deg, #e53e3e, #e53e3e)';
            }
            showWinnerAnimation(state.winner);
        } else if (state.winner === "draw" || state.winner === "tie" || state.winner == null) {
            status.textContent = `Game Over — It's a Tie!`;
            if (turnBanner) {
                turnBanner.textContent = `Tie Game`;
                turnBanner.style.background = 'linear-gradient(90deg, #4a5568, #2d3748)';
            }
            showWinnerAnimation("tie");
        } else {
            // unknown winner value: fallback to generic game over
            status.textContent = `Game Over`;
            showWinnerAnimation("tie");
        }
        return;
    }

    // update player bubble color based on current player
    const player1Bubble = document.getElementById('player1Bubble');
    if (player1Bubble) {
        player1Bubble.classList.remove('player1', 'player2');
        if (state.current_player === 1) {
            player1Bubble.classList.add('player1');
        } else if (state.current_player === 2) {
            player1Bubble.classList.add('player2');
        }
    }

    if (state.phase === "home_setup") {
        status.textContent = `Player ${state.current_player}'s Turn (Home Setup) — Place your HOME piece on your own side.`;
        if (rollDiceBtn) rollDiceBtn.style.display = "none";
        if (endTurnBtn) endTurnBtn.style.display = 'none';
    } 
    else if (state.phase === "neutral_setup") {
        status.textContent = `Neutral Setup — Neutral pieces are being placed automatically.`;
        if (rollDiceBtn) rollDiceBtn.style.display = "none";
        if (endTurnBtn) endTurnBtn.style.display = 'none';
    } 
    else if (state.phase === "main") {
        const t = state.main_turns || 0;
        const max = state.max_main_turns || 4;
        status.textContent = `Player ${state.current_player}'s Turn (Main Phase) — Turn ${t + 1} of ${max}. Roll dice, click a piece, then move with arrow keys.`;
        if (rollDiceBtn) rollDiceBtn.style.display = "inline-block";
        if (endTurnBtn) endTurnBtn.style.display = 'inline-block';
    } 
    else {
        status.textContent = `Player ${state.current_player}'s Turn (Phase: ${state.phase})`;
        if (rollDiceBtn) rollDiceBtn.style.display = "none";
        if (endTurnBtn) endTurnBtn.style.display = 'none';
    }

    // Mirror status into the Player 1 bubble if present, and ensure text is white
    const player1StatusEl = document.getElementById('player1Status');
    if (player1StatusEl) {
        player1StatusEl.textContent = status.textContent;
        // ensure color set via CSS; if not, force white for readability
        player1StatusEl.style.color = '';
    }

    // If winner declared early (by majority, etc.) while still not marked "ended"
    if (state.winner && state.phase !== "ended") {
        showWinnerAnimation(state.winner);
    }
}

// Move history helper
function addHistoryEntry(text) {
    const history = document.getElementById('moveHistory');
    if (!history) return;
    const div = document.createElement('div');
    div.className = 'entry';
    const t = document.createElement('div');
    t.textContent = `${new Date().toLocaleTimeString()} — ${text}`;
    div.appendChild(t);
    history.prepend(div);
}

// End Turn handler: call server to force end turn
document.addEventListener('DOMContentLoaded', () => {
    const endTurnBtn = document.getElementById('endTurnBtn');
    if (endTurnBtn) {
        endTurnBtn.addEventListener('click', async () => {
            const res = await fetch('/end_turn', { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                updateBoard(data.board, data.polarities, data.state.phase);
                updateStatus(data.state);
                addHistoryEntry('Player ended turn early');
                diceValue = 0;
                const diceResult = document.getElementById('diceResult');
                if (diceResult) diceResult.textContent = '';
            } else {
                showModal('<h3>End turn failed</h3><p>Unable to end the turn. Try again.</p>');
            }
        });
    }
});

// Simple winner animation overlay
function showWinnerAnimation(player) {
    if (document.getElementById('winnerOverlay')) return; // already active

    const colors = {
        1: '#2b6cb0', // blue
        2: '#e53e3e', // red
        tie: '#444444' // neutral grey for tie
    };

    const text = 
        player === 1 ? "Player 1 Wins!" :
        player === 2 ? "Player 2 Wins!" :
        "Tie Game!";

    const overlay = document.createElement('div');
    overlay.id = 'winnerOverlay';
    overlay.style.position = 'fixed';
    overlay.style.top = '0';
    overlay.style.left = '0';
    overlay.style.width = '100%';
    overlay.style.height = '100%';
    overlay.style.display = 'flex';
    overlay.style.alignItems = 'center';
    overlay.style.justifyContent = 'center';
    overlay.style.zIndex = '9999';
    overlay.style.background = 'rgba(0,0,0,0.45)';

    const box = document.createElement('div');
    box.style.padding = '30px 40px';
    box.style.borderRadius = '12px';
    box.style.color = 'white';
    box.style.fontSize = '2rem';
    box.style.fontWeight = '700';
    box.style.textAlign = 'center';
    box.style.background = colors[player] || colors.tie;
    box.textContent = text;

    const br = document.createElement('div');
    br.style.height = '16px';
    box.appendChild(br);

    const resetBtn = document.createElement('button');
    resetBtn.textContent = 'Reset Game';
    resetBtn.style.marginTop = '12px';
    resetBtn.style.padding = '8px 14px';
    resetBtn.style.fontSize = '1rem';
    resetBtn.style.border = 'none';
    resetBtn.style.borderRadius = '8px';
    resetBtn.style.cursor = 'pointer';
    resetBtn.onclick = async () => {
        const res = await fetch('/reset', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            if (overlay.parentNode) overlay.remove();
            updateBoard(data.board, data.polarities, data.state.phase);
            updateStatus(data.state);
        }
    };
    box.appendChild(resetBtn);

    overlay.appendChild(box);
    document.body.appendChild(overlay);
}


// ======================= GHOST PREVIEW =======================

function showGhostPreview(row, col) {
    clearGhostPreview();
    const pieceOffsets = getPieceOffsets(orientation);
    pieceOffsets.forEach(({ dr, dc, symbol }) => {
        const r = row + dr;
        const c = col + dc;
        const cell = document.querySelector(`.cell[data-row='${r}'][data-col='${c}']`);
        if (!cell) return;
        cell.classList.add("ghost");
        if (symbol === "+") cell.classList.add("ghost-plus");
        if (symbol === "–" || symbol === "-") cell.classList.add("ghost-minus");
        ghostCells.push(cell);
    });
}

function clearGhostPreview() {
    ghostCells.forEach(c => c.classList.remove("ghost", "ghost-plus", "ghost-minus"));
    ghostCells = [];
}

function getPieceOffsets(orientation) {
    switch (orientation) {
        case 0: return [{ dr: 0, dc: 0, symbol: '+' }, { dr: 0, dc: 1, symbol: '-' }];
        case 90: return [{ dr: 0, dc: 0, symbol: '+' }, { dr: 1, dc: 0, symbol: '-' }];
        case 180: return [{ dr: 0, dc: 0, symbol: '+' }, { dr: 0, dc: -1, symbol: '-' }];
        case 270: return [{ dr: 0, dc: 0, symbol: '+' }, { dr: -1, dc: 0, symbol: '-' }];
        default: return [];
    }
}

// ======================= HIGHLIGHT =======================

function highlightCluster(cluster) {
    document.querySelectorAll(".cell").forEach(c => c.classList.remove("highlight"));
    cluster.forEach(([r, c]) => {
        const cell = document.querySelector(`.cell[data-row='${r}'][data-col='${c}']`);
        if (cell) cell.classList.add("highlight");
    });
}
