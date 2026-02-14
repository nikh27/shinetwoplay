"""
PaddleArena Game Handler

A real-time 2-player pong game with obstacles.
Game logic runs on the clients; server just relays input and initializes state.
"""
import random
from typing import Dict, List
from games.base import BaseGameHandler
from rooms.redis_client import get_game_state, set_game_state


class PaddleArenaHandler(BaseGameHandler):
    """PaddleArena real-time game handler"""

    game_id = "paddlearena"
    game_name = "Paddle Arena"
    game_mode = "real_time"
    min_players = 2
    max_players = 2

    def initialize(self, room_code: str, players: List[str], total_rounds: int) -> Dict:
        """Initialize a new PaddleArena game session"""
        shuffled = players.copy()
        random.shuffle(shuffled)

        state = {
            'players': {
                'P1': shuffled[0],   # Top paddle
                'P2': shuffled[1],   # Bottom paddle
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
            'game_mode': 'real_time',
        }

        set_game_state(room_code, state)
        return state

    def handle_move(self, room_code: str, player: str, action: str, data: Dict) -> Dict:
        """
        Handle game events from the authoritative client (P1).
        Actions: 'round_end', 'score_update'
        """
        state = get_game_state(room_code)
        if not state:
            return {'error': 'Game not found'}

        if action == 'score_update':
            # P1 reports score changes
            p1_user = state['players']['P1']
            p2_user = state['players']['P2']
            state['scores'][p1_user] = data.get('p1_score', 0)
            state['scores'][p2_user] = data.get('p2_score', 0)
            set_game_state(room_code, state)
            return {'state': state}

        if action == 'round_end':
            winner_role = data.get('winner')  # 'P1', 'P2', or 'draw'
            if winner_role in ('P1', 'P2'):
                winner_user = state['players'][winner_role]
                state['round_winner'] = winner_user
            else:
                state['round_winner'] = 'draw'

            # Use client-reported scores (client is authoritative for PaddleArena)
            p1_user = state['players']['P1']
            p2_user = state['players']['P2']
            state['scores'][p1_user] = data.get('p1_score', state['scores'].get(p1_user, 0))
            state['scores'][p2_user] = data.get('p2_score', state['scores'].get(p2_user, 0))

            return self._handle_round_end(room_code, state, state['round_winner'])

        return {'error': f'Unknown action: {action}'}

    def _handle_round_end(self, room_code: str, state: Dict, winner: str) -> Dict:
        """Handle end of a round"""
        # Increment round counter
        state['current_round'] += 1
        current_round = state['current_round']
        total_rounds = state['total_rounds']

        if current_round > total_rounds:
            scores = state['scores']
            players_list = list(scores.keys())

            if scores[players_list[0]] > scores[players_list[1]]:
                state['game_winner'] = players_list[0]
            elif scores[players_list[1]] > scores[players_list[0]]:
                state['game_winner'] = players_list[1]
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
        """Start the next round — current_round already incremented in _handle_round_end"""
        state = get_game_state(room_code)
        if not state:
            return {'error': 'Game not found'}

        state['round_winner'] = None
        # Don't increment current_round here — already done in _handle_round_end
        # Don't swap P1/P2 — PaddleArena keeps roles fixed

        set_game_state(room_code, state)
        return {'state': state, 'round_started': True}
