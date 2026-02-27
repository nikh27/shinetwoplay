"""
Ludo Game Handler

A turn-based 2-player Ludo game (Red vs Blue).
Each player has 4 pieces that start in the yard (pos=-1).
Roll 6 to enter the board. Navigate the 52-cell path,
5-cell home stretch, then reach the home center (pos=56).
First to bring all 4 pieces home wins the round.
"""
import random
from typing import Dict, List, Optional
from games.base import BaseGameHandler
from rooms.redis_client import get_game_state, set_game_state, clear_game_state


# Full 52-cell circular path (1-indexed row/col, stored for reference only)
PATH = [
    {'r': 7, 'c': 2}, {'r': 7, 'c': 3}, {'r': 7, 'c': 4}, {'r': 7, 'c': 5}, {'r': 7, 'c': 6},
    {'r': 6, 'c': 7}, {'r': 5, 'c': 7}, {'r': 4, 'c': 7}, {'r': 3, 'c': 7}, {'r': 2, 'c': 7}, {'r': 1, 'c': 7},
    {'r': 1, 'c': 8}, {'r': 1, 'c': 9},
    {'r': 2, 'c': 9}, {'r': 3, 'c': 9}, {'r': 4, 'c': 9}, {'r': 5, 'c': 9}, {'r': 6, 'c': 9},
    {'r': 7, 'c': 10}, {'r': 7, 'c': 11}, {'r': 7, 'c': 12}, {'r': 7, 'c': 13}, {'r': 7, 'c': 14}, {'r': 7, 'c': 15},
    {'r': 8, 'c': 15}, {'r': 9, 'c': 15},
    {'r': 9, 'c': 14}, {'r': 9, 'c': 13}, {'r': 9, 'c': 12}, {'r': 9, 'c': 11}, {'r': 9, 'c': 10},
    {'r': 10, 'c': 9}, {'r': 11, 'c': 9}, {'r': 12, 'c': 9}, {'r': 13, 'c': 9}, {'r': 14, 'c': 9}, {'r': 15, 'c': 9},
    {'r': 15, 'c': 8}, {'r': 15, 'c': 7},
    {'r': 14, 'c': 7}, {'r': 13, 'c': 7}, {'r': 12, 'c': 7}, {'r': 11, 'c': 7}, {'r': 10, 'c': 7},
    {'r': 9, 'c': 6}, {'r': 9, 'c': 5}, {'r': 9, 'c': 4}, {'r': 9, 'c': 3}, {'r': 9, 'c': 2}, {'r': 9, 'c': 1},
    {'r': 8, 'c': 1}, {'r': 7, 'c': 1},
]

# Global safe spots (path indices, 0-based)
SAFE_SPOTS = [0, 8, 13, 21, 26, 34, 39, 47]

# Player config
PLAYERS = {
    'red': {
        'start_idx': 0,
        'yard_bases': [{'r': 3, 'c': 3}, {'r': 3, 'c': 4}, {'r': 4, 'c': 3}, {'r': 4, 'c': 4}],
        'home_path': [
            {'r': 8, 'c': 2}, {'r': 8, 'c': 3}, {'r': 8, 'c': 4},
            {'r': 8, 'c': 5}, {'r': 8, 'c': 6}
        ],
        'home_center': {'r': 8, 'c': 7.5},
    },
    'blue': {
        'start_idx': 26,
        'yard_bases': [{'r': 12, 'c': 12}, {'r': 12, 'c': 13}, {'r': 13, 'c': 12}, {'r': 13, 'c': 13}],
        'home_path': [
            {'r': 8, 'c': 14}, {'r': 8, 'c': 13}, {'r': 8, 'c': 12},
            {'r': 8, 'c': 11}, {'r': 8, 'c': 10}
        ],
        'home_center': {'r': 8, 'c': 8.5},
    },
}


class LudoHandler(BaseGameHandler):
    """Ludo game logic handler"""

    game_id = "ludo"
    game_name = "Ludo"
    game_mode = "turn_based"
    min_players = 2
    max_players = 2

    def initialize(self, room_code: str, players: List[str], total_rounds: int) -> Dict:
        """Initialize a new Ludo game session"""
        shuffled = players.copy()
        random.shuffle(shuffled)

        # Build 8 pieces (4 per player), pos=-1 = in yard
        pieces = []
        for pid in range(4):
            pieces.append({'player': 'red', 'id': pid, 'pos': -1})
        for pid in range(4):
            pieces.append({'player': 'blue', 'id': pid, 'pos': -1})

        state = {
            'players': {
                'red': shuffled[0],
                'blue': shuffled[1],
            },
            'pieces': pieces,
            'turn': 'red',          # whose turn it is
            'phase': 'ROLL',        # ROLL | MOVE | ANIMATING
            'dice_value': None,
            'current_round': 1,
            'total_rounds': total_rounds,
            'scores': {
                shuffled[0]: 0,
                shuffled[1]: 0,
            },
            'round_winner': None,
            'game_winner': None,
            'paused': False,
            'disconnected_players': [],
        }

        set_game_state(room_code, state)
        return state

    def handle_move(self, room_code: str, player: str, action: str, data: Dict) -> Dict:
        """Process a player action: 'roll' or 'move'"""
        state = get_game_state(room_code)

        if not state:
            return {'error': 'Game not found'}

        if state.get('paused'):
            return {'error': 'Game is paused'}

        # Determine this player's color
        player_color = None
        for color, username in state['players'].items():
            if username == player:
                player_color = color
                break

        if player_color is None:
            return {'error': 'Player not in this game'}

        if action == 'roll':
            return self._handle_roll(room_code, state, player, player_color)
        elif action == 'move':
            piece_id = data.get('piece_id')
            if piece_id is None:
                return {'error': 'piece_id required'}
            return self._handle_move_piece(room_code, state, player, player_color, int(piece_id))
        else:
            return {'error': f'Unknown action: {action}'}

    def _handle_roll(self, room_code: str, state: Dict, player: str, player_color: str) -> Dict:
        """Handle dice roll action"""
        if state['turn'] != player_color:
            return {'error': 'Not your turn', 'state': state}

        if state['phase'] != 'ROLL':
            return {'error': 'Not in ROLL phase', 'state': state}

        dice_value = random.randint(1, 6)
        state['dice_value'] = dice_value

        # Check if any valid moves exist
        if self._has_valid_moves(state, player_color, dice_value):
            state['phase'] = 'MOVE'
        else:
            # No valid moves — switch turn
            state['phase'] = 'ROLL'
            state['turn'] = 'blue' if player_color == 'red' else 'red'
            # Do NOT clear dice_value yet, let client see what was rolled

        set_game_state(room_code, state)
        return {'state': state, 'rolled': dice_value, 'no_moves': state['phase'] == 'ROLL' and state['turn'] != player_color}

    def _handle_move_piece(self, room_code: str, state: Dict, player: str, player_color: str, piece_id: int) -> Dict:
        """Handle a piece move action"""
        if state['turn'] != player_color:
            return {'error': 'Not your turn', 'state': state}

        if state['phase'] != 'MOVE':
            return {'error': 'Not in MOVE phase', 'state': state}

        dice_value = state['dice_value']
        if dice_value is None:
            return {'error': 'No dice value', 'state': state}

        # Find the piece
        piece = None
        for p in state['pieces']:
            if p['player'] == player_color and p['id'] == piece_id:
                piece = p
                break

        if piece is None:
            return {'error': 'Piece not found', 'state': state}

        if not self._is_valid_move(piece, dice_value):
            return {'error': 'Invalid move for this piece', 'state': state}

        # Calculate new position
        old_pos = piece['pos']
        if old_pos == -1:
            new_pos = 0
        else:
            new_pos = old_pos + dice_value

        piece['pos'] = new_pos

        # Check for capture (only on main path, not home path)
        cut_occurred = False
        if new_pos >= 0 and new_pos <= 50:
            abs_pos = (PLAYERS[player_color]['start_idx'] + new_pos) % 52
            if abs_pos not in SAFE_SPOTS:
                opp_color = 'blue' if player_color == 'red' else 'red'
                for opp in state['pieces']:
                    if opp['player'] == opp_color and opp['pos'] >= 0 and opp['pos'] <= 50:
                        opp_abs = (PLAYERS[opp_color]['start_idx'] + opp['pos']) % 52
                        if opp_abs == abs_pos:
                            opp['pos'] = -1  # Send back to yard
                            cut_occurred = True

        # Determine bonus turn
        bonus = (dice_value == 6) or cut_occurred or (new_pos == 56)

        # Check win: all 4 pieces at home center (pos=56)
        home_count = sum(1 for p in state['pieces'] if p['player'] == player_color and p['pos'] == 56)
        if home_count == 4:
            state['scores'][player] += 1
            state['round_winner'] = player
            state['phase'] = 'ROLL'
            state['dice_value'] = None
            return self._handle_round_end(room_code, state, player)

        # Switch turn or give bonus
        if bonus:
            state['phase'] = 'ROLL'
            # keep state['turn'] = player_color (same player rolls again)
        else:
            state['turn'] = 'blue' if player_color == 'red' else 'red'
            state['phase'] = 'ROLL'

        state['dice_value'] = None
        set_game_state(room_code, state)

        return {
            'state': state,
            'cut': cut_occurred,
            'bonus': bonus,
            'moved_piece': {'player': player_color, 'id': piece_id, 'from': old_pos, 'to': new_pos},
        }

    def _has_valid_moves(self, state: Dict, player_color: str, dice_value: int) -> bool:
        """Check if the player has at least one valid move"""
        for p in state['pieces']:
            if p['player'] == player_color:
                if self._is_valid_move(p, dice_value):
                    return True
        return False

    def _is_valid_move(self, piece: Dict, dice_value: int) -> bool:
        """Check if a specific piece can move"""
        if piece['pos'] == -1:
            return dice_value == 6
        if piece['pos'] + dice_value > 56:
            return False
        return True

    def _handle_round_end(self, room_code: str, state: Dict, winner: str) -> Dict:
        """Handle end of a round"""
        current_round = state['current_round']
        total_rounds = state['total_rounds']

        if current_round >= total_rounds:
            # Determine game winner
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

        # Reset pieces
        pieces = []
        for pid in range(4):
            pieces.append({'player': 'red', 'id': pid, 'pos': -1})
        for pid in range(4):
            pieces.append({'player': 'blue', 'id': pid, 'pos': -1})

        state['pieces'] = pieces
        state['current_round'] += 1
        state['round_winner'] = None
        state['dice_value'] = None
        state['phase'] = 'ROLL'

        # Alternate who starts
        p = state['players']
        state['players'] = {'red': p['blue'], 'blue': p['red']}
        state['turn'] = 'red'

        set_game_state(room_code, state)
        return {'state': state, 'round_started': True}
