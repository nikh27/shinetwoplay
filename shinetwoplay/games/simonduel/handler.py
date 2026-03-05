"""
Simon Duel Game Handler

Turn-based 2-player Simon memory game.

Flow:
  - P1 phase='add': picks one color, pushes to seq
  - P2 phase='repeat': must tap seq[0], seq[1], ... then phase='add-after': adds 1 more
  - Continue alternating. Wrong color → lose a life. 0 lives → round over, opponent wins.
  - Win enough rounds to win the game.
"""

import random
from typing import Dict, List, Optional
from games.base import BaseGameHandler
from rooms.redis_client import get_game_state, set_game_state, clear_game_state

COLORS = ['green', 'red', 'yellow', 'blue']


class SimonDuelHandler(BaseGameHandler):
    """Simon Duel game logic handler"""

    game_id = "simonduel"
    game_name = "Simon Duel"
    game_mode = "turn_based"
    min_players = 2
    max_players = 2

    def initialize(self, room_code: str, players: List[str], total_rounds: int) -> Dict:
        """Initialize a new Simon Duel game session"""
        shuffled = players.copy()
        random.shuffle(shuffled)
        p1, p2 = shuffled[0], shuffled[1]

        state = {
            # Sequence of colors (grows each turn)
            'seq': [],
            # Who acts next: 'P1' or 'P2'
            'current_player': 'P1',
            # 'add'       → pick a color to extend seq
            # 'repeat'    → tap through seq in order (wrong = opponent wins round)
            # 'add-after' → after a perfect repeat, add 1 more
            'phase': 'add',
            # Index into seq during repeat phase
            'repeat_idx': 0,
            # Player mapping
            'players': {'P1': p1, 'P2': p2},
            # Cumulative scores (highest seq length each player achieved)
            'scores': {p1: 0, p2: 0},
            # Round wins
            'round_wins': {p1: 0, p2: 0},
            'current_round': 1,
            'total_rounds': total_rounds,
            'round_winner': None,
            'game_winner': None,
            'paused': False,
            'disconnected_players': [],
        }

        set_game_state(room_code, state)
        return state

    # ------------------------------------------------------------------
    # handle_move
    # ------------------------------------------------------------------
    def handle_move(self, room_code: str, player: str, action: str, data: Dict) -> Dict:
        """Process a player's action"""
        state = get_game_state(room_code)
        if not state:
            return {'error': 'Game not found'}
        if state.get('paused'):
            return {'error': 'Game is paused'}

        cp_key = state['current_player']       # 'P1' or 'P2'
        cp_name = state['players'][cp_key]     # actual username

        if player != cp_name:
            return {'error': 'Not your turn', 'state': state}

        color = data.get('color')
        if color not in COLORS:
            return {'error': f'Invalid color: {color}'}

        phase = state['phase']

        # ---- ADD phase: player appends one color ----
        if phase in ('add', 'add-after'):
            state['seq'].append(color)
            # Update current player's score to current sequence length
            state['scores'][cp_name] = max(state['scores'].get(cp_name, 0), len(state['seq']))

            # Switch to opponent's repeat phase
            opponent_key = 'P2' if cp_key == 'P1' else 'P1'
            state['current_player'] = opponent_key
            state['phase'] = 'repeat'
            state['repeat_idx'] = 0

            set_game_state(room_code, state)
            return {'state': state}

        # ---- REPEAT phase: player taps colors in sequence ----
        elif phase == 'repeat':
            expected = state['seq'][state['repeat_idx']]
            if color != expected:
                # Wrong! Lose a life
                return self._handle_fail(room_code, state)

            # Correct tap
            state['repeat_idx'] += 1

            if state['repeat_idx'] >= len(state['seq']):
                # Finished repeating — now add 1 more
                state['phase'] = 'add-after'
                state['repeat_idx'] = 0
                set_game_state(room_code, state)
                return {'state': state}
            else:
                set_game_state(room_code, state)
                return {'state': state}

        return {'error': f'Unknown phase: {phase}', 'state': state}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _handle_fail(self, room_code: str, state: Dict) -> Dict:
        """Player tapped the wrong color — opponent wins the round immediately."""
        cp_key = state['current_player']
        state['phase'] = 'fail'  # transient marker for client
        opponent_key = 'P2' if cp_key == 'P1' else 'P1'
        opponent_name = state['players'][opponent_key]
        return self._handle_round_end(room_code, state, opponent_name)

    def _handle_round_end(self, room_code: str, state: Dict, winner_name: str) -> Dict:
        """Award the round win and determine if the game is over."""
        if winner_name != 'draw':
            state['round_wins'][winner_name] = state['round_wins'].get(winner_name, 0) + 1
        state['round_winner'] = winner_name

        current_round = state['current_round']
        total_rounds = state['total_rounds']

        if current_round >= total_rounds:
            # Game over
            rw = state['round_wins']
            players = list(rw.keys())
            if rw.get(players[0], 0) > rw.get(players[1], 0):
                game_winner = players[0]
            elif rw.get(players[1], 0) > rw.get(players[0], 0):
                game_winner = players[1]
            else:
                game_winner = 'draw'
            state['game_winner'] = game_winner
            set_game_state(room_code, state)
            return {
                'state': state,
                'fail': True,
                'round_ended': True,
                'round_winner': winner_name,
                'game_ended': True,
                'game_winner': game_winner,
                'final_scores': state['round_wins'],
            }
        else:
            set_game_state(room_code, state)
            return {
                'state': state,
                'fail': True,
                'round_ended': True,
                'round_winner': winner_name,
                'next_round': current_round + 1,
                'total_rounds': total_rounds,
            }

    def start_next_round(self, room_code: str) -> Dict:
        """Reset for the next round."""
        state = get_game_state(room_code)
        if not state:
            return {'error': 'Game not found'}

        # Reset per-round fields
        state['seq'] = []
        state['phase'] = 'add'
        state['repeat_idx'] = 0
        state['round_winner'] = None
        state['current_round'] += 1

        # Alternate who starts
        old_p1 = state['players']['P1']
        old_p2 = state['players']['P2']
        state['players']['P1'] = old_p2
        state['players']['P2'] = old_p1
        state['current_player'] = 'P1'

        set_game_state(room_code, state)
        return {'state': state, 'round_started': True}
