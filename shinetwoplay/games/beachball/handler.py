"""
BeachBall Game Handler

A real-time 2-player beach ball game in a pool.
Players throw stones to push the ball into the opponent's goal.
Game logic runs on the clients; server just relays input and manages rounds.
"""
import random
from typing import Dict, List
from games.base import BaseGameHandler
from rooms.redis_client import get_game_state, set_game_state


class BeachBallHandler(BaseGameHandler):
    """BeachBall real-time game handler"""

    game_id = "beachball"
    game_name = "Beach Ball"
    game_mode = "real_time"
    min_players = 2
    max_players = 2

    def initialize(self, room_code: str, players: List[str], total_rounds: int) -> Dict:
        """Initialize a new BeachBall game session"""
        # Owner (first in list) is always P2 (red/bottom)
        # Opponent is always P1 (blue/top)
        owner = players[0]
        opponent = players[1] if len(players) > 1 else players[0]

        state = {
            'players': {
                'P1': opponent,   # Blue player (top)
                'P2': owner,      # Red player (bottom) — room owner
            },
            'current_round': 1,
            'total_rounds': total_rounds,
            'scores': {
                owner: 0,
                opponent: 0,
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

            p1_user = state['players']['P1']
            p2_user = state['players']['P2']
            state['scores'][p1_user] = data.get('p1_score', state['scores'].get(p1_user, 0))
            state['scores'][p2_user] = data.get('p2_score', state['scores'].get(p2_user, 0))

            return self._handle_round_end(room_code, state, state['round_winner'])

        return {'error': f'Unknown action: {action}'}

    def _handle_round_end(self, room_code: str, state: Dict, winner: str) -> Dict:
        """Handle end of a round — first to WIN_ROUNDS wins the game"""
        WIN_ROUNDS = 3
        state['current_round'] += 1
        current_round = state['current_round']
        total_rounds = state['total_rounds']

        scores = state['scores']
        max_score = max(scores.values()) if scores else 0

        # Game ends when someone reaches WIN_ROUNDS wins, or all rounds are done
        if max_score >= WIN_ROUNDS or current_round > total_rounds:
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
                'next_round': current_round,
                'total_rounds': total_rounds,
            }

    def start_next_round(self, room_code: str) -> Dict:
        """Start the next round"""
        state = get_game_state(room_code)
        if not state:
            return {'error': 'Game not found'}

        state['round_winner'] = None
        set_game_state(room_code, state)
        return {'state': state, 'round_started': True}
