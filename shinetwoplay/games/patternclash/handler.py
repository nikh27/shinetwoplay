"""
Pattern Clash Game Handler

Both players see the SAME pattern simultaneously.
They have 3s to memorize, then both fill their own grid.
When both submit, server scores: +10 correct, -5 wrong, -2 missed.
Highest score wins the round.
"""

import random
from typing import Dict, List
from games.base import BaseGameHandler
from rooms.redis_client import get_game_state, set_game_state

GRID_SIZE   = 5          # 5x5 = 25 cells
SCORE_CORRECT = 10
SCORE_WRONG   = -5
SCORE_MISSED  = -2


def _make_pattern(round_num: int) -> List[int]:
    """Generate a random pattern. More cells in later rounds."""
    count = min(6 + round_num, 18)
    indices = random.sample(range(GRID_SIZE * GRID_SIZE), count)
    return sorted(indices)


def _calc_score(selection: List[int], pattern: List[int]) -> Dict:
    correct = sum(1 for i in selection if i in pattern)
    wrong   = sum(1 for i in selection if i not in pattern)
    missed  = sum(1 for i in pattern   if i not in selection)
    total   = correct * SCORE_CORRECT + wrong * SCORE_WRONG + missed * SCORE_MISSED
    return {'correct': correct, 'wrong': wrong, 'missed': missed, 'total': total}


class PatternClashHandler(BaseGameHandler):
    game_id    = "patternclash"
    game_name  = "Pattern Clash"
    game_mode  = "turn_based"
    min_players = 2
    max_players = 2

    def initialize(self, room_code: str, players: List[str], total_rounds: int) -> Dict:
        p1, p2 = players[0], players[1]
        pattern = _make_pattern(1)
        state = {
            'players':       {'P1': p1, 'P2': p2},
            'scores':        {p1: 0, p2: 0},
            'round_wins':    {p1: 0, p2: 0},
            'current_round': 1,
            'total_rounds':  total_rounds,
            'pattern':       pattern,
            # phase: 'input' → 'result' → next round
            # (memorize is handled client-side — server always stays in 'input')
            'phase':         'input',
            # submissions: {username: [list of cell indices]}
            'submissions':   {},
            # round scores: {username: {correct, wrong, missed, total}}
            'round_scores':  {},
            'round_winner':  None,
            'game_winner':   None,
            'paused':        False,
            'disconnected_players': [],
        }
        set_game_state(room_code, state)
        return state

    def handle_move(self, room_code: str, player: str, action: str, data: Dict) -> Dict:
        state = get_game_state(room_code)
        if not state:
            return {'error': 'Game not found'}
        if state.get('paused'):
            return {'error': 'Game is paused'}

        # ---- submit: player submits their grid selection ----
        if action == 'submit':
            # Reject only if round already completed
            if state['phase'] == 'result':
                return {'error': 'Round already finished', 'state': state}

            selection = data.get('selection', [])
            if not isinstance(selection, list):
                return {'error': 'Invalid selection'}

            state['submissions'][player] = selection

            p1_name = state['players']['P1']
            p2_name = state['players']['P2']

            # Check if BOTH players have submitted
            if p1_name in state['submissions'] and p2_name in state['submissions']:
                return self._end_round(room_code, state)
            else:
                # Only one player submitted — save state and wait for other
                set_game_state(room_code, state)
                return {
                    'state': state,
                    'player_submitted': player,
                    'waiting_for_opponent': True,
                }

        return {'error': f'Unknown action: {action}', 'state': state}

    def _end_round(self, room_code: str, state: Dict) -> Dict:
        """Score both players, determine round winner."""
        pattern = state['pattern']
        p1_name = state['players']['P1']
        p2_name = state['players']['P2']

        s1 = _calc_score(state['submissions'].get(p1_name, []), pattern)
        s2 = _calc_score(state['submissions'].get(p2_name, []), pattern)

        state['round_scores'] = {p1_name: s1, p2_name: s2}
        state['scores'][p1_name] += s1['total']
        state['scores'][p2_name] += s2['total']

        # Round winner
        if s1['total'] > s2['total']:
            round_winner = p1_name
        elif s2['total'] > s1['total']:
            round_winner = p2_name
        else:
            round_winner = 'draw'

        if round_winner != 'draw':
            state['round_wins'][round_winner] += 1
        state['round_winner'] = round_winner
        state['phase'] = 'result'

        current_round = state['current_round']
        total_rounds  = state['total_rounds']

        if current_round >= total_rounds:
            # Game over
            rw = state['round_wins']
            if rw[p1_name] > rw[p2_name]:
                game_winner = p1_name
            elif rw[p2_name] > rw[p1_name]:
                game_winner = p2_name
            else:
                # Tiebreak by total score
                if state['scores'][p1_name] > state['scores'][p2_name]:
                    game_winner = p1_name
                elif state['scores'][p2_name] > state['scores'][p1_name]:
                    game_winner = p2_name
                else:
                    game_winner = 'draw'

            state['game_winner'] = game_winner
            set_game_state(room_code, state)
            return {
                'state':        state,
                'round_ended':  True,
                'round_winner': round_winner,
                'game_ended':   True,
                'game_winner':  game_winner,
                'final_scores': state['round_wins'],
            }
        else:
            set_game_state(room_code, state)
            return {
                'state':        state,
                'round_ended':  True,
                'round_winner': round_winner,
                'next_round':   current_round + 1,
                'total_rounds': total_rounds,
            }

    def start_next_round(self, room_code: str) -> Dict:
        state = get_game_state(room_code)
        if not state:
            return {'error': 'Game not found'}

        state['current_round'] += 1
        state['pattern']     = _make_pattern(state['current_round'])
        state['phase']       = 'input'   # memorize is client-side only
        state['submissions'] = {}
        state['round_scores'] = {}
        state['round_winner'] = None

        set_game_state(room_code, state)
        return {'state': state, 'round_started': True}
