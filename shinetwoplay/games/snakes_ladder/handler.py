"""
Snakes & Ladders Game Handler

A turn-based 2-player Snakes & Ladders game (Red vs Blue).
Players start at position 0 (off the board).
Roll the dice to move forward on a 10x10 board (1-100).
Land on a ladder bottom → climb up. Land on a snake head → slide down.
First player to reach exactly 100 wins the round.
"""
import random
from typing import Dict, List
from games.base import BaseGameHandler
from rooms.redis_client import get_game_state, set_game_state, clear_game_state


# ── Snake positions: head → tail ──
SNAKES = {
    99: 78, 97: 79, 93: 73, 90: 70, 84: 63, 76: 56, 74: 53,
    71: 51, 66: 45, 59: 38, 52: 31, 47: 26, 39: 22, 34: 13, 18: 6
}

# ── Ladder positions: bottom → top ──
LADDERS = {
    2: 23, 8: 29, 17: 37, 21: 42, 25: 46, 36: 55, 44: 65,
    54: 73, 62: 82, 64: 85, 68: 89, 81: 98
}


class SnakesLadderHandler(BaseGameHandler):
    """Snakes & Ladders game logic handler"""

    game_id = "snakes_ladder"
    game_name = "Snakes & Ladders"
    game_mode = "turn_based"
    min_players = 2
    max_players = 2

    def initialize(self, room_code: str, players: List[str], total_rounds: int) -> Dict:
        """Initialize a new Snakes & Ladders game session"""
        shuffled = players.copy()
        random.shuffle(shuffled)

        state = {
            'players': {
                'red': shuffled[0],
                'blue': shuffled[1],
            },
            'positions': {
                'red': 1,   # Start at tile 1
                'blue': 1,
            },
            'turn': 'red',
            'phase': 'ROLL',        # ROLL only (no MOVE phase — dice auto-moves)
            'dice_value': None,
            'last_roll_by': None,    # Track who rolled for animation
            'move_data': None,       # Animation data: {from, to, slide_to, slide_type}
            'stats': {
                'red': {'moves': 0, 'snakes_hit': 0, 'ladders_climbed': 0},
                'blue': {'moves': 0, 'snakes_hit': 0, 'ladders_climbed': 0},
            },
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
        """Process a player action: 'roll'"""
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
        else:
            return {'error': f'Unknown action: {action}'}

    def _handle_roll(self, room_code: str, state: Dict, player: str, player_color: str) -> Dict:
        """Handle dice roll — automatically moves the piece"""
        if state['turn'] != player_color:
            return {'error': 'Not your turn', 'state': state}

        if state['phase'] != 'ROLL':
            return {'error': 'Not in ROLL phase', 'state': state}

        dice_value = random.randint(1, 6)
        state['dice_value'] = dice_value
        state['last_roll_by'] = player_color
        state['stats'][player_color]['moves'] += 1

        current_pos = state['positions'][player_color]
        new_pos = current_pos + dice_value

        # Build move_data for animation
        move_data = {
            'player': player_color,
            'dice': dice_value,
            'from_pos': current_pos,
            'to_pos': None,
            'slide_to': None,
            'slide_type': None,  # 'snake' or 'ladder'
        }

        # If first move is from 1, just move normally.
        # Removing the special 0 starting logic.
        if new_pos > 100:
            # Need exact number to win — turn passed
            move_data['to_pos'] = current_pos
            state['move_data'] = move_data
            state['turn'] = 'blue' if player_color == 'red' else 'red'
            state['dice_value'] = dice_value
            set_game_state(room_code, state)
            return {'state': state, 'rolled': dice_value, 'too_high': True}

        else:
            move_data['to_pos'] = new_pos

        # Apply the base move
        landed_pos = move_data['to_pos']

        # Check for snake or ladder
        if landed_pos in SNAKES:
            slide_dest = SNAKES[landed_pos]
            move_data['slide_to'] = slide_dest
            move_data['slide_type'] = 'snake'
            state['stats'][player_color]['snakes_hit'] += 1
            landed_pos = slide_dest

        elif landed_pos in LADDERS:
            slide_dest = LADDERS[landed_pos]
            move_data['slide_to'] = slide_dest
            move_data['slide_type'] = 'ladder'
            state['stats'][player_color]['ladders_climbed'] += 1
            landed_pos = slide_dest

        # Update final position
        state['positions'][player_color] = landed_pos
        state['move_data'] = move_data

        # Check win
        if landed_pos == 100:
            state['scores'][player] += 1
            state['round_winner'] = player
            state['phase'] = 'ROLL'
            return self._handle_round_end(room_code, state, player)

        # Switch turn
        state['turn'] = 'blue' if player_color == 'red' else 'red'
        state['phase'] = 'ROLL'

        set_game_state(room_code, state)
        return {'state': state, 'rolled': dice_value}

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
        """Start the next round with fresh positions"""
        state = get_game_state(room_code)
        if not state:
            return {'error': 'Game not found'}

        # Reset positions to 1
        state['positions'] = {'red': 1, 'blue': 1}
        state['current_round'] += 1
        state['round_winner'] = None
        state['dice_value'] = None
        state['last_roll_by'] = None
        state['move_data'] = None
        state['phase'] = 'ROLL'

        # Reset stats for new round
        state['stats'] = {
            'red': {'moves': 0, 'snakes_hit': 0, 'ladders_climbed': 0},
            'blue': {'moves': 0, 'snakes_hit': 0, 'ladders_climbed': 0},
        }

        # Alternate who starts (swap red/blue assignments)
        p = state['players']
        state['players'] = {'red': p['blue'], 'blue': p['red']}
        state['turn'] = 'red'

        set_game_state(room_code, state)
        return {'state': state, 'round_started': True}
