let orientation = 0;
const orientations = [0, 90, 180, 270];
let orientationIndex = 0;
let ghostCells = [];
let selectedCluster = [];
let diceValue = 0;
let currentPhase = "home_setup";

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
                <li>Then place neutral pieces on your opponent's half.</li>
                <li>In the main phase, roll the dice to move your magnetic clusters.</li>
                <li>Opposite polarities (+/–) attract, same repel.</li>
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

    // --- ROTATE BUTTON ---
    rotateBtn.addEventListener("click", () => {
        orientationIndex = (orientationIndex + 1) % orientations.length;
        orientation = orientations[orientationIndex];
        orientationLabel.textContent = `${orientation}°`;
        clearGhostPreview();
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
                alert("Roll the dice first!");
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
                alert(data.message || "Invalid placement!");
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
        const res = await fetch("/roll_dice", { method: "POST" });
        const data = await res.json();
        if (data.success) {
            diceValue = data.dice;
            diceResult.textContent = `🎲 You rolled a ${diceValue}`;
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
            body: JSON.stringify({ cluster: selectedCluster, dr, dc }),
        });
        const data = await res.json();
        if (data.success) {
            updateBoard(data.board, data.polarities, data.state?.phase || "main");
            selectedCluster = data.new_cluster || selectedCluster.map(([r, c]) => [r + dr, c + dc]);
            highlightCluster(selectedCluster);
            diceValue -= 1;
            diceResult.textContent = `🎲 Moves left: ${diceValue}`;
            if (diceValue <= 0) {
                selectedCluster = [];
                alert("Out of moves!");
            }
        } else {
            alert(data.message);
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
}

// ======================= STATUS =======================

function updateStatus(state) {
    const status = document.getElementById("status");
    const rollDiceBtn = document.getElementById("rollDiceBtn");
    currentPhase = state.phase;

    if (state.phase === "home_setup") {
        status.textContent = `Player ${state.current_player}'s Turn (Home Setup) — Place your HOME piece on your own side.`;
        rollDiceBtn.style.display = "none";
    } 
    else if (state.phase === "neutral_setup") {
        status.textContent = `Player ${state.current_player}'s Turn (Neutral Setup) — Place NEUTRAL pieces on your opponent's half.`;
        rollDiceBtn.style.display = "none";
    } 
    else if (state.phase === "main") {
        status.textContent = `Player ${state.current_player}'s Turn (Main Phase) — Roll dice, Click on piece, and move with arrow keys.`;
        rollDiceBtn.style.display = "inline-block";
    } 
    else {
        status.textContent = `Player ${state.current_player}'s Turn (Phase: ${state.phase})`;
        rollDiceBtn.style.display = "none";
    }
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
