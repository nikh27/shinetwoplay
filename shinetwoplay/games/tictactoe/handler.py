"""
TicTacToe Game Handler

A simple turn-based TicTacToe game for 2 players.
"""
import random
from typing import Dict, List, Optional
from games.base import BaseGameHandler
from rooms.redis_client import get_game_state, set_game_state, clear_game_state


class TicTacToeHandler(BaseGameHandler):
    """TicTacToe game logic handler"""
    
    game_id = "tictactoe"
    game_name = "Tic Tac Toe"
    game_mode = "turn_based"
    min_players = 2
    max_players = 2
    
    # All possible winning patterns (indices)
    WIN_PATTERNS = [
        [0, 1, 2],  # Row 1
        [3, 4, 5],  # Row 2
        [6, 7, 8],  # Row 3
        [0, 3, 6],  # Column 1
        [1, 4, 7],  # Column 2
        [2, 5, 8],  # Column 3
        [0, 4, 8],  # Diagonal 1
        [2, 4, 6],  # Diagonal 2
    ]
    
    def initialize(self, room_code: str, players: List[str], total_rounds: int) -> Dict:
        """Initialize a new TicTacToe game session"""
        # Randomly assign X and O to players
        shuffled = players.copy()
        random.shuffle(shuffled)
        
        state = {
            'board': [None] * 9,  # 3x3 board as flat array
            'players': {
                'X': shuffled[0],
                'O': shuffled[1]
            },
            'current_mark': 'X',  # X always starts
            'current_round': 1,
            'total_rounds': total_rounds,
            'scores': {
                shuffled[0]: 0,
                shuffled[1]: 0
            },
            'round_winner': None,
            'game_winner': None,
            'paused': False,
            'disconnected_players': []
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
        
        if action != 'place':
            return {'error': f'Unknown action: {action}'}
        
        cell = data.get('cell')
        if cell is None or not (0 <= cell <= 8):
            return {'error': 'Invalid cell index'}
        
        # Validate it's this player's turn
        current_mark = state['current_mark']
        expected_player = state['players'][current_mark]
        
        if player != expected_player:
            return {'error': 'Not your turn', 'state': state}
        
        # Validate cell is empty
        if state['board'][cell] is not None:
            return {'error': 'Cell already taken', 'state': state}
        
        # Place the mark
        state['board'][cell] = current_mark
        
        # Check for winner
        winner_mark = self._check_winner(state['board'])
        
        if winner_mark:
            # Someone won this round
            winner_username = state['players'][winner_mark]
            state['scores'][winner_username] += 1
            state['round_winner'] = winner_username
            
            return self._handle_round_end(room_code, state, winner_username)
        
        # Check for draw
        if all(cell is not None for cell in state['board']):
            # Draw - no one wins this round
            state['round_winner'] = 'draw'
            return self._handle_round_end(room_code, state, 'draw')
        
        # Switch turn
        state['current_mark'] = 'O' if current_mark == 'X' else 'X'
        
        set_game_state(room_code, state)
        return {'state': state}
    
    def _check_winner(self, board: List) -> Optional[str]:
        """Check if there's a winner on the board"""
        for pattern in self.WIN_PATTERNS:
            a, b, c = pattern
            if board[a] and board[a] == board[b] == board[c]:
                return board[a]  # Return 'X' or 'O'
        return None
    
    def _handle_round_end(self, room_code: str, state: Dict, winner: str) -> Dict:
        """Handle end of a round"""
        current_round = state['current_round']
        total_rounds = state['total_rounds']
        
        if current_round >= total_rounds:
            # Game over - determine overall winner
            scores = state['scores']
            players = list(scores.keys())
            
            if scores[players[0]] > scores[players[1]]:
                state['game_winner'] = players[0]
            elif scores[players[1]] > scores[players[0]]:
                state['game_winner'] = players[1]
            else:
                state['game_winner'] = 'draw'
            
            set_game_state(room_code, state)
            
            return {
                'state': state,
                'round_ended': True,
                'round_winner': winner,
                'game_ended': True,
                'game_winner': state['game_winner'],
                'final_scores': state['scores']
            }
        else:
            # More rounds to go - prepare next round
            set_game_state(room_code, state)
            
            return {
                'state': state,
                'round_ended': True,
                'round_winner': winner,
                'next_round': current_round + 1,
                'total_rounds': total_rounds
            }
    
    def start_next_round(self, room_code: str) -> Dict:
        """Start the next round with a fresh board"""
        state = get_game_state(room_code)
        
        if not state:
            return {'error': 'Game not found'}
        
        # Reset board
        state['board'] = [None] * 9
        state['current_round'] += 1
        state['round_winner'] = None
        
        # Alternate who starts (swap X and O players)
        players = state['players']
        state['players'] = {
            'X': players['O'],
            'O': players['X']
        }
        state['current_mark'] = 'X'
        
        set_game_state(room_code, state)
        return {'state': state, 'round_started': True}
