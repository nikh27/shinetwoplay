"""
Bingo Game Handler — 2-Player Online

Each player gets their OWN 5×5 card (different numbers).
Numbers called auto (3.5 s) from shared pool 1-75.
Players mark numbers on their own card.
First to complete a row / column / diagonal and press BINGO wins.
If BINGO is false → penalty (no action, just shamed).
Round system with scores.
"""

import random
from typing import Dict, List
from games.base import BaseGameHandler
from rooms.redis_client import get_game_state, set_game_state

COLS = [(1, 15), (16, 30), (31, 45), (46, 60), (61, 75)]
HEADER = ['B', 'I', 'N', 'G', 'O']


def _generate_card() -> List[List[int]]:
    """5×5 bingo card; center is FREE (0)."""
    card = [[0]*5 for _ in range(5)]
    for c in range(5):
        lo, hi = COLS[c]
        pool = list(range(lo, hi + 1))
        random.shuffle(pool)
        for r in range(5):
            card[r][c] = pool[r]
    card[2][2] = 0  # FREE
    return card


def _check_win(marked: List[List[bool]]) -> bool:
    # Rows
    for r in range(5):
        if all(marked[r]):
            return True
    # Columns
    for c in range(5):
        if all(marked[r][c] for r in range(5)):
            return True
    # Diagonals
    if all(marked[i][i] for i in range(5)):
        return True
    if all(marked[i][4 - i] for i in range(5)):
        return True
    return False


def _create_marked() -> List[List[bool]]:
    m = [[False]*5 for _ in range(5)]
    m[2][2] = True  # FREE
    return m


class BingoHandler(BaseGameHandler):
    game_id     = "bingo"
    game_name   = "Bingo"
    game_mode   = "turn_based"
    min_players = 2
    max_players = 2

    def initialize(self, room_code: str, players: List[str], total_rounds: int) -> Dict:
        p1, p2 = players[0], players[1]

        # Shared call pool (shuffled 1-75)
        pool = list(range(1, 76))
        random.shuffle(pool)

        state = {
            'players':        {'P1': p1, 'P2': p2},
            'scores':         {p1: 0, p2: 0},
            'round_wins':     {p1: 0, p2: 0},
            'current_round':  1,
            'total_rounds':   total_rounds,
            # Each player has their OWN card
            'cards':          {p1: _generate_card(), p2: _generate_card()},
            'marked':         {p1: _create_marked(), p2: _create_marked()},
            'call_pool':      pool,         # remaining numbers to call
            'called_numbers': [],           # numbers already called (newest first)
            'current_number': None,         # latest called number
            'call_index':     0,            # how many numbers have been called
            'phase':          'playing',    # 'playing' | 'result'
            'winner':         None,         # username who won this round
            'false_bingo':    None,         # username who called false bingo
            'paused':         False,
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
        if state.get('winner'):
            return {'error': 'Round already won'}

        if action == 'call_number':
            return self._call_number(room_code, state)
        elif action == 'mark':
            return self._mark_cell(room_code, state, player, data)
        elif action == 'bingo':
            return self._declare_bingo(room_code, state, player)

        return {'error': f'Unknown action: {action}', 'state': state}

    def _call_number(self, room_code: str, state: Dict) -> Dict:
        """Call the next number from the pool."""
        pool = state['call_pool']
        if not pool:
            return {'error': 'All numbers called', 'state': state}

        num = pool.pop()
        state['current_number'] = num
        state['called_numbers'].insert(0, num)
        state['call_index'] += 1
        state['false_bingo'] = None  # clear any old false bingo

        set_game_state(room_code, state)
        return {'state': state, 'number_called': num}

    def _mark_cell(self, room_code: str, state: Dict, player: str, data: Dict) -> Dict:
        """Player marks a number on their OWN card."""
        r = data.get('row')
        c = data.get('col')
        if r is None or c is None:
            return {'error': 'Missing row/col'}
        if not (0 <= r < 5 and 0 <= c < 5):
            return {'error': 'Invalid position'}

        card = state['cards'].get(player)
        marked = state['marked'].get(player)
        if not card or not marked:
            return {'error': 'Player not found'}

        val = card[r][c]
        if val == 0:
            return {'error': 'Cannot mark FREE cell'}
        if marked[r][c]:
            return {'error': 'Already marked'}
        if val not in state['called_numbers']:
            return {'error': 'Number not called yet'}

        marked[r][c] = True
        state['marked'][player] = marked

        set_game_state(room_code, state)
        return {'state': state, 'marked_by': player, 'row': r, 'col': c}

    def _declare_bingo(self, room_code: str, state: Dict, player: str) -> Dict:
        """Player declares BINGO. Check if valid."""
        marked = state['marked'].get(player)
        if not marked:
            return {'error': 'Player not found'}

        if _check_win(marked):
            # Valid bingo!
            state['winner'] = player
            state['phase'] = 'result'
            state['scores'][player] = state['scores'].get(player, 0) + 10

            # Round wins
            state['round_wins'][player] = state['round_wins'].get(player, 0) + 1

            current_round = state['current_round']
            total_rounds = state['total_rounds']

            if current_round >= total_rounds:
                # Game over
                p1 = state['players']['P1']
                p2 = state['players']['P2']
                rw = state['round_wins']
                if rw.get(p1, 0) > rw.get(p2, 0):
                    game_winner = p1
                elif rw.get(p2, 0) > rw.get(p1, 0):
                    game_winner = p2
                else:
                    s = state['scores']
                    game_winner = p1 if s.get(p1, 0) >= s.get(p2, 0) else p2

                state['game_winner'] = game_winner
                set_game_state(room_code, state)
                return {
                    'state':        state,
                    'round_ended':  True,
                    'round_winner': player,
                    'game_ended':   True,
                    'game_winner':  game_winner,
                    'final_scores': state['scores'],
                }
            else:
                set_game_state(room_code, state)
                return {
                    'state':        state,
                    'round_ended':  True,
                    'round_winner': player,
                    'next_round':   current_round + 1,
                    'total_rounds': total_rounds,
                }
        else:
            # False bingo!
            state['false_bingo'] = player
            set_game_state(room_code, state)
            return {'state': state, 'false_bingo': player}

    def start_next_round(self, room_code: str) -> Dict:
        state = get_game_state(room_code)
        if not state:
            return {'error': 'Game not found'}

        p1 = state['players']['P1']
        p2 = state['players']['P2']

        pool = list(range(1, 76))
        random.shuffle(pool)

        state['current_round'] += 1
        state['cards']          = {p1: _generate_card(), p2: _generate_card()}
        state['marked']         = {p1: _create_marked(), p2: _create_marked()}
        state['call_pool']      = pool
        state['called_numbers'] = []
        state['current_number'] = None
        state['call_index']     = 0
        state['phase']          = 'playing'
        state['winner']         = None
        state['false_bingo']    = None

        set_game_state(room_code, state)
        return {'state': state, 'round_started': True}
