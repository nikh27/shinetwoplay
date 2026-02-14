"""
Connect4 Game Handler

A turn-based Connect 4 game for 2 players.
6 rows × 7 columns. First to get 4 in a row wins the round.
"""
import random
from typing import Dict, List, Optional
from games.base import BaseGameHandler
from rooms.redis_client import get_game_state, set_game_state, clear_game_state

ROWS = 6
COLS = 7


class Connect4Handler(BaseGameHandler):
    """Connect4 game logic handler"""

    game_id = "connect4"
    game_name = "Connect 4"
    game_mode = "turn_based"
    min_players = 2
    max_players = 2

    def initialize(self, room_code: str, players: List[str], total_rounds: int) -> Dict:
        """Initialize a new Connect4 game session"""
        shuffled = players.copy()
        random.shuffle(shuffled)

        state = {
            'board': [[None] * COLS for _ in range(ROWS)],  # 6x7 grid
            'players': {
                'red': shuffled[0],
                'blue': shuffled[1],
            },
            'current_color': 'red',  # red always starts
            'current_round': 1,
            'total_rounds': total_rounds,
            'scores': {
                shuffled[0]: 0,
                shuffled[1]: 0,
            },
            'round_winner': None,
            'game_winner': None,
            'last_move': None,       # {row, col} of last placed piece
            'win_cells': None,       # list of [row,col] if someone won
            'paused': False,
            'disconnected_players': [],
        }

        set_game_state(room_code, state)
        return state

    def handle_move(self, room_code: str, player: str, action: str, data: Dict) -> Dict:
        """Process a player's move"""
        state = get_game_state(room_code)

        if not state:
            return {'error': 'Game not found'}

        if state.get('paused'):
            return {'error': 'Game is paused'}

        if action != 'drop':
            return {'error': f'Unknown action: {action}'}

        col = data.get('col')
        if col is None or not (0 <= col < COLS):
            return {'error': 'Invalid column'}

        # Validate it's this player's turn
        current_color = state['current_color']
        expected_player = state['players'][current_color]

        if player != expected_player:
            return {'error': 'Not your turn', 'state': state}

        # Find lowest empty row in this column
        board = state['board']
        row = self._get_lowest_row(board, col)

        if row == -1:
            return {'error': 'Column is full', 'state': state}

        # Place the piece
        board[row][col] = current_color
        state['last_move'] = {'row': row, 'col': col}

        # Check for winner
        win_cells = self._check_win(board, row, col, current_color)

        if win_cells:
            winner_username = state['players'][current_color]
            state['scores'][winner_username] += 1
            state['round_winner'] = winner_username
            state['win_cells'] = win_cells
            return self._handle_round_end(room_code, state, winner_username)

        # Check for draw (board full)
        if self._is_board_full(board):
            state['round_winner'] = 'draw'
            state['win_cells'] = None
            return self._handle_round_end(room_code, state, 'draw')

        # Switch turn
        state['current_color'] = 'blue' if current_color == 'red' else 'red'

        set_game_state(room_code, state)
        return {'state': state}

    def _get_lowest_row(self, board: List, col: int) -> int:
        """Find the lowest empty row in a column, returns -1 if full"""
        for row in range(ROWS - 1, -1, -1):
            if board[row][col] is None:
                return row
        return -1

    def _check_win(self, board: List, row: int, col: int, color: str) -> Optional[List]:
        """Check if placing at (row,col) creates 4 in a row. Returns winning cells or None."""
        directions = [
            [(0, 1), (0, -1)],    # Horizontal
            [(1, 0), (-1, 0)],    # Vertical
            [(1, 1), (-1, -1)],   # Diagonal \
            [(1, -1), (-1, 1)],   # Diagonal /
        ]

        for dir_pair in directions:
            cells = [[row, col]]
            for dr, dc in dir_pair:
                r, c = row + dr, col + dc
                while 0 <= r < ROWS and 0 <= c < COLS and board[r][c] == color:
                    cells.append([r, c])
                    r += dr
                    c += dc
            if len(cells) >= 4:
                return cells

        return None

    def _is_board_full(self, board: List) -> bool:
        """Check if top row is completely filled"""
        return all(cell is not None for cell in board[0])

    def _handle_round_end(self, room_code: str, state: Dict, winner: str) -> Dict:
        """Handle end of a round"""
        current_round = state['current_round']
        total_rounds = state['total_rounds']

        if current_round >= total_rounds:
            # Game over - determine overall winner
            scores = state['scores']
            player_list = list(scores.keys())

            if scores[player_list[0]] > scores[player_list[1]]:
                state['game_winner'] = player_list[0]
            elif scores[player_list[1]] > scores[player_list[0]]:
                state['game_winner'] = player_list[1]
            else:
                state['game_winner'] = 'draw'

            set_game_state(room_code, state)

            return {
                'state': state,
                'round_ended': True,
                'round_winner': winner,
                'game_ended': True,
                'game_winner': state['game_winner'],
                'final_scores': state['scores'],
            }
        else:
            set_game_state(room_code, state)

            return {
                'state': state,
                'round_ended': True,
                'round_winner': winner,
                'next_round': current_round + 1,
                'total_rounds': total_rounds,
            }

    def start_next_round(self, room_code: str) -> Dict:
        """Start the next round with a fresh board"""
        state = get_game_state(room_code)

        if not state:
            return {'error': 'Game not found'}

        # Reset board
        state['board'] = [[None] * COLS for _ in range(ROWS)]
        state['current_round'] += 1
        state['round_winner'] = None
        state['last_move'] = None
        state['win_cells'] = None

        # Alternate who starts (swap red and blue players)
        p = state['players']
        state['players'] = {
            'red': p['blue'],
            'blue': p['red'],
        }
        state['current_color'] = 'red'

        set_game_state(room_code, state)
        return {'state': state, 'round_started': True}
