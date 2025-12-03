"""
AI Player Implementation for FluxWars
Supports three difficulty levels:
- Easy: Heuristic-based rule system
- Normal: Monte Carlo Tree Search (MCTS)
- Expert: LLM-based reasoning
"""

import random
import copy
from typing import Tuple, List, Optional, Dict, Any


# ==============================================================
#   EASY: HEURISTIC-BASED AI
# ==============================================================

def easy_ai_move():
    """
    Simple heuristic-based AI that follows good general rules:
    1. Prioritize converting neutral clusters
    2. Move toward opponent territory
    3. Avoid leaving pieces isolated
    4. Prefer moves that increase cluster size
    """
    from board import (find_cluster, move_cluster_cells, get_dice, BOARD_SIZE, 
                       get_board, get_polarities, get_state, roll_dice, next_player)
    import board as board_module
    
    # Get current game state
    board = get_board()
    polarities = get_polarities()
    game_state = get_state()
    player = game_state.get("ai_player", 2)
    
    # Roll dice if needed
    if get_dice() <= 0:
        roll_dice()
    
    if get_dice() <= 0:
        next_player()
        return False
    
    # Find all player-owned clusters
    visited = set()
    clusters = []
    
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] == player and (r, c) not in visited:
                cluster = find_cluster(r, c)
                if cluster:
                    clusters.append(cluster)
                    visited.update(tuple(pos) for pos in cluster)
    
    if not clusters:
        next_player()
        return False
    
    # Make all available moves
    moves_made = 0
    while get_dice() > 0 and moves_made < 20:  # Safety limit
        # Score each possible move for each cluster
        best_move = None
        best_score = -float('inf')
        
        for cluster in clusters:
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                # Try this move
                score = evaluate_move_heuristic(board, polarities, cluster, dr, dc, player)
                if score > best_score:
                    best_score = score
                    best_move = (cluster, dr, dc)
        
        if not best_move or best_score <= -1000:
            print(f"AI: No valid moves found (best score: {best_score})")
            break  # No valid moves
        
        # Execute the best move
        cluster, dr, dc = best_move
        print(f"AI attempting move: cluster size={len(cluster)}, direction=({dr},{dc})")
        success, message, new_cluster = move_cluster_cells(cluster, dr, dc, actor_player=player)
        
        if not success:
            print(f"AI move failed: {message}")
            break
        
        # Decrement dice manually (dice_value is module-level in board.py)
        board_module.dice_value -= 1
        print(f"AI move successful. Dice remaining: {board_module.dice_value}")
        
        moves_made += 1
        
        # Update clusters after move
        visited = set()
        clusters = []
        board = get_board()  # Refresh board state
        polarities = get_polarities()
        
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if board[r][c] == player and (r, c) not in visited:
                    cluster = find_cluster(r, c)
                    if cluster:
                        clusters.append(cluster)
                        visited.update(tuple(pos) for pos in cluster)
    
    # After all moves, switch to next player
    print(f"AI completed {moves_made} moves")
    next_player()
    return True


def evaluate_move_heuristic(board, polarities, cluster, dr, dc, player):
    """Evaluate a move using simple heuristics"""
    score = 0
    
    # Check if move is valid
    cluster_set = {tuple(c) for c in cluster}
    for r, c in cluster:
        nr, nc = r + dr, c + dc
        if not (0 <= nr < len(board) and 0 <= nc < len(board[0])):
            return -1000  # Out of bounds
        if board[nr][nc] != 0 and (nr, nc) not in cluster_set:
            return -1000  # Blocked
    
    # Score based on nearby neutrals with opposite polarity
    neutrals_adjacent = 0
    for r, c in cluster:
        nr, nc = r + dr, c + dc
        pol = polarities[r][c]  # polarities is always a 2D list in board.py
        
        # Check adjacent cells to new position
        for ar, ac in [(nr+1, nc), (nr-1, nc), (nr, nc+1), (nr, nc-1)]:
            if 0 <= ar < len(board) and 0 <= ac < len(board[0]):
                if board[ar][ac] == 3:  # Neutral
                    adj_pol = polarities[ar][ac]
                    if adj_pol in ('+', '-') and adj_pol != pol:
                        neutrals_adjacent += 1
    
    score += neutrals_adjacent * 10  # Prioritize conversion opportunities
    
    # Prefer moving toward center
    center_r, center_c = len(board) // 2, len(board[0]) // 2
    avg_dist_before = sum(abs(r - center_r) + abs(c - center_c) for r, c in cluster) / len(cluster)
    avg_dist_after = sum(abs(r + dr - center_r) + abs(c + dc - center_c) for r, c in cluster) / len(cluster)
    score += (avg_dist_before - avg_dist_after) * 2  # Reward moving toward center
    
    return score


# ==============================================================
#   NORMAL: MONTE CARLO TREE SEARCH (MCTS)
# ==============================================================

class MCTSNode:
    def __init__(self, board, polarities, game_state, parent=None, move=None):
        self.board = [row[:] for row in board]  # Deep copy
        self.polarities = [row[:] for row in polarities]  # Deep copy
        self.game_state = game_state.copy()  # Shallow copy sufficient for dict
        self.parent = parent
        self.move = move  # (cluster, dr, dc) that led to this state
        self.children = []
        self.wins = 0
        self.visits = 0
        self.untried_moves = None
        self.player = game_state.get("current_player")
    
    def uct_value(self, exploration=1.41):
        if self.visits == 0:
            return float('inf')
        return self.wins / self.visits + exploration * ((2 * self.parent.visits) ** 0.5 / self.visits)
    
    def get_possible_moves(self):
        """Get all legal moves from current state"""
        from board import find_cluster, BOARD_SIZE
        
        moves = []
        visited = set()
        player = self.game_state.get("current_player")
        
        # Find all clusters for current player
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if self.board[r][c] == player and (r, c) not in visited:
                    cluster = self._find_cluster_in_state(r, c)
                    if cluster:
                        visited.update(tuple(pos) for pos in cluster)
                        # Try all four directions
                        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                            if self._is_valid_move(cluster, dr, dc):
                                moves.append((cluster, dr, dc))
        
        return moves
    
    def _find_cluster_in_state(self, start_r, start_c):
        """Find cluster in this node's state"""
        from collections import deque
        
        player = self.board[start_r][start_c]
        if player not in (1, 2):
            return []
        
        cluster = []
        visited = set()
        queue = deque([(start_r, start_c)])
        visited.add((start_r, start_c))
        
        while queue:
            r, c = queue.popleft()
            cluster.append([r, c])
            
            start_pol = self.polarities[start_r][start_c]
            curr_pol = self.polarities[r][c]
            
            # Check adjacent cells
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nr, nc = r + dr, c + dc
                if (nr, nc) in visited:
                    continue
                if not (0 <= nr < len(self.board) and 0 <= nc < len(self.board[0])):
                    continue
                
                neighbor_owner = self.board[nr][nc]
                neighbor_pol = self.polarities[nr][nc]
                
                # Player-owned with alternating polarity
                if neighbor_owner == player and neighbor_pol in ('+', '-'):
                    if neighbor_pol != curr_pol:
                        visited.add((nr, nc))
                        queue.append((nr, nc))
                # Neutral with opposite polarity can join
                elif neighbor_owner == 3 and neighbor_pol in ('+', '-'):
                    if neighbor_pol != start_pol:
                        visited.add((nr, nc))
                        queue.append((nr, nc))
        
        return cluster
    
    def _is_valid_move(self, cluster, dr, dc):
        """Check if move is valid in this state"""
        cluster_set = {tuple(c) for c in cluster}
        for r, c in cluster:
            nr, nc = r + dr, c + dc
            if not (0 <= nr < len(self.board) and 0 <= nc < len(self.board[0])):
                return False
            if self.board[nr][nc] != 0 and (nr, nc) not in cluster_set:
                return False
        return True
    
    def apply_move(self, cluster, dr, dc):
        """Apply move and return new node"""
        import copy
        
        # Create new state
        new_board = [row[:] for row in self.board]
        new_polarities = [row[:] for row in self.polarities]
        new_game_state = self.game_state.copy()
        
        # Move cluster
        cluster_set = {tuple(c) for c in cluster}
        moving_positions = []
        
        for r, c in cluster:
            moving_positions.append((r, c))
        
        # Clear old positions
        for r, c in moving_positions:
            new_board[r][c] = 0
            new_polarities[r][c] = ""
        
        # Place at new positions
        for r, c in moving_positions:
            nr, nc = r + dr, c + dc
            new_board[nr][nc] = self.board[r][c]
            new_polarities[nr][nc] = self.polarities[r][c]
        
        # Simple conversion check (one adjacent neutral)
        player = new_game_state.get("current_player")
        for r, c in moving_positions:
            nr, nc = r + dr, c + dc
            pol = new_polarities[nr][nc]
            for ar, ac in [(nr+1, nc), (nr-1, nc), (nr, nc+1), (nr, nc-1)]:
                if 0 <= ar < len(new_board) and 0 <= ac < len(new_board[0]):
                    if new_board[ar][ac] == 3 and new_polarities[ar][ac] in ('+', '-'):
                        if new_polarities[ar][ac] != pol:
                            new_board[ar][ac] = player
                            break  # Only one conversion per move
        
        # Switch player
        new_game_state["current_player"] = 2 if player == 1 else 1
        
        return MCTSNode(new_board, new_polarities, new_game_state, parent=self, move=(cluster, dr, dc))
    
    def is_terminal(self):
        """Check if game is over"""
        return self.game_state.get("phase") == "ended"
    
    def get_winner(self):
        """Determine winner (simple heuristic: most pieces)"""
        p1_count = sum(row.count(1) for row in self.board)
        p2_count = sum(row.count(2) for row in self.board)
        
        if p1_count > p2_count:
            return 1
        elif p2_count > p1_count:
            return 2
        else:
            return 0  # Draw


def normal_ai_move(simulations=100):
    """
    MCTS-based AI that simulates games to find the best move
    """
    from board import get_board, get_polarities, get_state, get_dice, roll_dice, move_cluster_cells, next_player, BOARD_SIZE
    import board as board_module
    import random
    
    # Get current state
    board = get_board()
    polarities = get_polarities()
    game_state = get_state()
    player = game_state.get("ai_player", 2)
    
    # Roll dice if needed
    if get_dice() <= 0:
        roll_dice()
    
    if get_dice() <= 0:
        next_player()
        return False
    
    print(f"MCTS: Starting with {simulations} simulations")
    
    # Create root node
    root = MCTSNode(board, polarities, game_state)
    root.untried_moves = root.get_possible_moves()
    
    if not root.untried_moves:
        print("MCTS: No legal moves available")
        next_player()
        return False
    
    # Run MCTS simulations
    for i in range(simulations):
        node = root
        
        # Selection: traverse tree using UCT
        while not node.untried_moves and node.children:
            node = max(node.children, key=lambda n: n.uct_value())
        
        # Expansion: add new child node
        if node.untried_moves:
            move = random.choice(node.untried_moves)
            node.untried_moves.remove(move)
            cluster, dr, dc = move
            child = node.apply_move(cluster, dr, dc)
            child.untried_moves = child.get_possible_moves()
            node.children.append(child)
            node = child
        
        # Simulation: play out randomly
        sim_node = node
        depth = 0
        while not sim_node.is_terminal() and depth < 10:
            possible_moves = sim_node.get_possible_moves()
            if not possible_moves:
                break
            move = random.choice(possible_moves)
            cluster, dr, dc = move
            sim_node = sim_node.apply_move(cluster, dr, dc)
            depth += 1
        
        # Get result
        winner = sim_node.get_winner()
        reward = 1 if winner == player else (0.5 if winner == 0 else 0)
        
        # Backpropagation
        while node:
            node.visits += 1
            node.wins += reward
            node = node.parent
    
    # Choose best move
    if not root.children:
        print("MCTS: No children expanded, using first available move")
        best_move = root.untried_moves[0] if root.untried_moves else None
    else:
        best_child = max(root.children, key=lambda n: n.visits)
        best_move = best_child.move
        print(f"MCTS: Best move has {best_child.visits} visits, {best_child.wins:.1f} wins")
    
    if not best_move:
        next_player()
        return False
    
    # Execute moves until dice runs out
    moves_made = 0
    while board_module.dice_value > 0 and moves_made < 20:
        cluster, dr, dc = best_move
        
        print(f"MCTS executing move: cluster size={len(cluster)}, direction=({dr},{dc})")
        success, message, new_cluster = move_cluster_cells(cluster, dr, dc, actor_player=player)
        
        if not success:
            print(f"MCTS move failed: {message}")
            break
        
        board_module.dice_value -= 1
        print(f"MCTS move successful. Dice remaining: {board_module.dice_value}")
        moves_made += 1
        
        if board_module.dice_value <= 0:
            break
        
        # For subsequent moves, pick another high-value move
        board = get_board()
        polarities = get_polarities()
        root = MCTSNode(board, polarities, get_state())
        moves = root.get_possible_moves()
        
        if not moves:
            break
        
        # Quick evaluation for remaining moves
        best_score = -float('inf')
        for m in moves:
            c, d_r, d_c = m
            score = evaluate_move_heuristic(board, polarities, c, d_r, d_c, player)
            if score > best_score:
                best_score = score
                best_move = m
    
    print(f"MCTS completed {moves_made} moves")
    next_player()
    return True


# ==============================================================
#   EXPERT: LLM-BASED AI
# ==============================================================

def serialize_game_state_for_llm(board, polarities, game_state, player):
    """Convert game state to text format for LLM"""
    lines = []
    lines.append("=== FLUXWARS GAME STATE ===\n")
    lines.append(f"You are Player {player} (AI)")
    lines.append(f"Current Turn: {game_state.get('main_turns', 0) + 1}")
    lines.append(f"Phase: {game_state.get('phase')}\n")
    
    # Board visualization
    lines.append("BOARD (15x15):")
    lines.append("Legend: 1=Player1(Blue), 2=Player2(Red/AI), 3=Neutral, 0=Empty")
    lines.append("Polarities: +=Positive, -=Negative\n")
    
    # Create compact board representation
    lines.append("   " + "".join(f"{c:2d}" for c in range(15)))
    for r in range(15):
        row_pieces = []
        row_pols = []
        for c in range(15):
            val = board[r][c]
            pol = polarities[r][c]
            row_pieces.append(str(val) if val != 0 else ".")
            row_pols.append(pol if pol else " ")
        lines.append(f"{r:2d} {' '.join(row_pieces)}")
        lines.append(f"   {' '.join(row_pols)}")
    
    # Piece counts
    p1_count = sum(row.count(1) for row in board)
    p2_count = sum(row.count(2) for row in board)
    neutral_count = sum(row.count(3) for row in board)
    
    lines.append(f"\nPiece Counts: Player1={p1_count}, Player2(You)={p2_count}, Neutral={neutral_count}")
    
    # Find clusters
    from board import find_cluster, BOARD_SIZE
    
    lines.append(f"\nYour Clusters (Player {player}):")
    visited = set()
    cluster_num = 1
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] == player and (r, c) not in visited:
                cluster = []
                # Simple BFS for cluster
                from collections import deque
                queue = deque([(r, c)])
                temp_visited = set()
                temp_visited.add((r, c))
                
                while queue:
                    cr, cc = queue.popleft()
                    cluster.append((cr, cc))
                    for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                        nr, nc = cr + dr, cc + dc
                        if (0 <= nr < 15 and 0 <= nc < 15 and 
                            (nr, nc) not in temp_visited and
                            board[nr][nc] == player):
                            temp_visited.add((nr, nc))
                            queue.append((nr, nc))
                
                visited.update(temp_visited)
                lines.append(f"  Cluster {cluster_num}: {len(cluster)} pieces at {cluster[:5]}{'...' if len(cluster) > 5 else ''}")
                cluster_num += 1
    
    return "\n".join(lines)


def parse_llm_response(response_text, board, player):
    """Extract move commands from LLM response"""
    from board import find_cluster, BOARD_SIZE
    
    # Look for move patterns in response
    # Expected format: "MOVE cluster_at(row,col) direction(dr,dc)"
    # Or: "MOVE (r,c) UP/DOWN/LEFT/RIGHT"
    
    import re
    
    # Try to find coordinate patterns
    coord_pattern = r'\((\d+)\s*,\s*(\d+)\)'
    direction_pattern = r'(UP|DOWN|LEFT|RIGHT|up|down|left|right)'
    
    coords = re.findall(coord_pattern, response_text)
    directions = re.findall(direction_pattern, response_text)
    
    if not coords:
        return None
    
    # Use first coordinate as starting point
    r, c = int(coords[0][0]), int(coords[0][1])
    
    # Validate coordinate is player's piece
    if not (0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE):
        return None
    if board[r][c] != player:
        return None
    
    # Get cluster at that position
    cluster = find_cluster(r, c)
    if not cluster:
        return None
    
    # Parse direction
    dr, dc = 0, 0
    if directions:
        dir_str = directions[0].upper()
        if dir_str == "UP":
            dr, dc = -1, 0
        elif dir_str == "DOWN":
            dr, dc = 1, 0
        elif dir_str == "LEFT":
            dr, dc = 0, -1
        elif dir_str == "RIGHT":
            dr, dc = 0, 1
    else:
        # Try to infer from text
        text_lower = response_text.lower()
        if "up" in text_lower or "north" in text_lower:
            dr, dc = -1, 0
        elif "down" in text_lower or "south" in text_lower:
            dr, dc = 1, 0
        elif "left" in text_lower or "west" in text_lower:
            dr, dc = 0, -1
        elif "right" in text_lower or "east" in text_lower:
            dr, dc = 0, 1
        else:
            # Default to moving toward center
            center_r, center_c = 7, 7
            if r < center_r:
                dr, dc = 1, 0
            elif r > center_r:
                dr, dc = -1, 0
            elif c < center_c:
                dr, dc = 0, 1
            else:
                dr, dc = 0, -1
    
    return (cluster, dr, dc)


def call_llm_api(prompt, api_key=None, model="gpt-4", provider="openai"):
    """Call LLM API with the game state prompt"""
    import os
    import json
    
    # Get API key from environment if not provided
    if not api_key:
        if provider == "openai":
            api_key = os.environ.get("OPENAI_API_KEY")
        elif provider == "anthropic":
            api_key = os.environ.get("ANTHROPIC_API_KEY")
    
    if not api_key:
        print(f"LLM: No API key found for {provider}. Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable.")
        return None
    
    try:
        if provider == "openai":
            import openai
            client = openai.OpenAI(api_key=api_key)
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert FluxWars player. Analyze the board and suggest the best move. Use format: MOVE (row,col) DIRECTION where DIRECTION is UP/DOWN/LEFT/RIGHT."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        elif provider == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            
            response = client.messages.create(
                model=model if "claude" in model else "claude-3-sonnet-20240229",
                max_tokens=500,
                messages=[
                    {"role": "user", "content": f"You are an expert FluxWars player. {prompt}\n\nSuggest your move using format: MOVE (row,col) DIRECTION where DIRECTION is UP/DOWN/LEFT/RIGHT."}
                ]
            )
            
            return response.content[0].text
            
    except ImportError as e:
        print(f"LLM: Missing library for {provider}. Install with: pip install {provider}")
        return None
    except Exception as e:
        print(f"LLM: API call failed: {e}")
        return None


def expert_ai_move():
    """
    LLM-based AI that uses language model reasoning
    Requires API key and model configuration (OPENAI_API_KEY or ANTHROPIC_API_KEY)
    Falls back to MCTS if LLM unavailable
    """
    from board import (get_board, get_polarities, get_state, get_dice, roll_dice, 
                       move_cluster_cells, next_player, BOARD_SIZE)
    import board as board_module
    import os
    
    # Get current state
    board = get_board()
    polarities = get_polarities()
    game_state = get_state()
    player = game_state.get("ai_player", 2)
    
    # Roll dice if needed
    if get_dice() <= 0:
        roll_dice()
    
    if get_dice() <= 0:
        next_player()
        return False
    
    print("LLM: Analyzing game state...")
    
    # Serialize game state for LLM
    prompt = serialize_game_state_for_llm(board, polarities, game_state, player)
    prompt += "\n\nSTRATEGIC CONSIDERATIONS:"
    prompt += "\n- Magnetic pieces have + and - polarities that must alternate in clusters"
    prompt += "\n- You can convert adjacent neutral pieces with opposite polarity"
    prompt += "\n- Moving toward center provides more conversion opportunities"
    prompt += "\n- Larger clusters are more powerful but harder to maneuver"
    prompt += "\n- Protect your pieces from being stolen by opponent"
    prompt += f"\n\nYou have {get_dice()} moves remaining. Suggest your best move."
    
    # Try to get LLM response
    llm_response = call_llm_api(
        prompt,
        model=os.environ.get("LLM_MODEL", "gpt-4"),
        provider=os.environ.get("LLM_PROVIDER", "openai")
    )
    
    if llm_response:
        print(f"LLM: Response received: {llm_response[:100]}...")
        
        # Parse the response
        move = parse_llm_response(llm_response, board, player)
        
        if move:
            cluster, dr, dc = move
            print(f"LLM: Parsed move - cluster size={len(cluster)}, direction=({dr},{dc})")
            
            # Execute moves until dice runs out
            moves_made = 0
            while board_module.dice_value > 0 and moves_made < 20:
                print(f"LLM executing move: cluster size={len(cluster)}, direction=({dr},{dc})")
                success, message, new_cluster = move_cluster_cells(cluster, dr, dc, actor_player=player)
                
                if not success:
                    print(f"LLM move failed: {message}")
                    break
                
                board_module.dice_value -= 1
                print(f"LLM move successful. Dice remaining: {board_module.dice_value}")
                moves_made += 1
                
                if board_module.dice_value <= 0:
                    break
                
                # For subsequent moves, use heuristics
                board = get_board()
                polarities = get_polarities()
                from board import find_cluster
                
                # Find new clusters and pick best heuristic move
                visited = set()
                best_move = None
                best_score = -float('inf')
                
                for r in range(BOARD_SIZE):
                    for c in range(BOARD_SIZE):
                        if board[r][c] == player and (r, c) not in visited:
                            cl = find_cluster(r, c)
                            if cl:
                                visited.update(tuple(pos) for pos in cl)
                                for d_r, d_c in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                                    score = evaluate_move_heuristic(board, polarities, cl, d_r, d_c, player)
                                    if score > best_score:
                                        best_score = score
                                        best_move = (cl, d_r, d_c)
                
                if not best_move:
                    break
                
                cluster, dr, dc = best_move
            
            print(f"LLM completed {moves_made} moves")
            next_player()
            return True
        else:
            print("LLM: Failed to parse valid move from response")
    else:
        print("LLM: API call failed")
    
    # Fallback to MCTS if LLM fails
    print("LLM: Falling back to MCTS")
    return normal_ai_move(simulations=100)


# ==============================================================
#   MAIN AI DISPATCHER
# ==============================================================

def get_ai_move(difficulty="normal"):
    """
    Get the AI's move based on difficulty setting
    Returns: function reference
    """
    
    if difficulty == "easy":
        return easy_ai_move
    elif difficulty == "normal":
        return normal_ai_move
    elif difficulty == "expert":
        return expert_ai_move
    else:
        return easy_ai_move
