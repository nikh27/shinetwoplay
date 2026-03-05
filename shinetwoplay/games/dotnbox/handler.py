"""
Dots & Boxes — 2-Player Online

Turn-based. Players draw lines between dots.
Complete a box = score a point AND keep your turn.
Game ends when all boxes are filled.
Most boxes wins the round.

Grid sizes:
  short  -> 4 dots = 3×3 = 9  boxes
  medium -> 5 dots = 4×4 = 16 boxes
  long   -> 6 dots = 5×5 = 25 boxes  (default)
"""

from typing import Dict, List
from games.base import BaseGameHandler
from rooms.redis_client import get_game_state, set_game_state

SIZES = {'short': 4, 'medium': 5, 'long': 6}


def _create_board(dots: int) -> Dict:
    """Create h-lines, v-lines, boxes arrays (all zeros)."""
    h_lines = [[0] * (dots - 1) for _ in range(dots)]
    v_lines = [[0] * dots for _ in range(dots - 1)]
    boxes   = [[0] * (dots - 1) for _ in range(dots - 1)]
    return {
        'h_lines': h_lines,
        'v_lines': v_lines,
        'boxes':   boxes,
    }


def _check_boxes(h_lines, v_lines, boxes, player) -> int:
    """Check all boxes. Mark any newly completed ones. Return count scored."""
    scored = 0
    num_rows = len(boxes)
    num_cols = len(boxes[0])
    for r in range(num_rows):
        for c in range(num_cols):
            if boxes[r][c] == 0:
                top    = h_lines[r][c]
                bottom = h_lines[r + 1][c]
                left   = v_lines[r][c]
                right  = v_lines[r][c + 1]
                if top and bottom and left and right:
                    boxes[r][c] = player
                    scored += 1
    return scored


class DotsBoxesHandler(BaseGameHandler):
    game_id     = "dotnbox"
    game_name   = "Dots & Boxes"
    game_mode   = "turn_based"
    min_players = 2
    max_players = 2

    def initialize(self, room_code: str, players: List[str], total_rounds: int) -> Dict:
        p1, p2 = players[0], players[1]

        # Start with medium (5 dots = 4x4) by default; players pick in first 3s
        dots = SIZES['medium']
        board = _create_board(dots)

        state = {
            'players':        {'P1': p1, 'P2': p2},
            'scores':         {p1: 0, p2: 0},
            'round_wins':     {p1: 0, p2: 0},
            'current_round':  1,
            'total_rounds':   total_rounds,
            'dots':           dots,
            'grid_size':      'medium',
            'h_lines':        board['h_lines'],
            'v_lines':        board['v_lines'],
            'boxes':          board['boxes'],
            'current_player': 'P1',
            'phase':          'choosing',   # 'choosing' | 'playing' | 'result'
            'last_move':      None,
            'last_boxes':     [],
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

        # Grid choice action — allowed during 'choosing' phase by either player
        if action == 'set_grid':
            return self._set_grid(room_code, state, data)

        if state.get('phase') == 'result':
            return {'error': 'Round over'}
        if state.get('phase') == 'choosing':
            return {'error': 'Still choosing grid size'}

        cp_key  = state['current_player']
        cp_name = state['players'][cp_key]
        if player != cp_name:
            return {'error': 'Not your turn', 'state': state}

        if action == 'draw_line':
            return self._draw_line(room_code, state, player, data)

        return {'error': f'Unknown action: {action}', 'state': state}

    def _set_grid(self, room_code: str, state: Dict, data: Dict) -> Dict:
        """Set grid size and switch to playing phase."""
        if state.get('phase') != 'choosing':
            return {'error': 'Grid already chosen', 'state': state}

        size_key = data.get('size', 'medium')
        dots = SIZES.get(size_key, 5)
        board = _create_board(dots)

        state['dots']      = dots
        state['grid_size']  = size_key
        state['h_lines']    = board['h_lines']
        state['v_lines']    = board['v_lines']
        state['boxes']      = board['boxes']
        state['phase']      = 'playing'

        set_game_state(room_code, state)
        return {'state': state, 'grid_set': size_key}

    def _draw_line(self, room_code: str, state: Dict, player: str, data: Dict) -> Dict:
        line_type = data.get('type')  # 'h' or 'v'
        row = data.get('row')
        col = data.get('col')

        if line_type not in ('h', 'v') or row is None or col is None:
            return {'error': 'Invalid line data'}

        lines = state['h_lines'] if line_type == 'h' else state['v_lines']

        if row < 0 or row >= len(lines) or col < 0 or col >= len(lines[0]):
            return {'error': 'Out of range'}

        if lines[row][col] != 0:
            return {'error': 'Line already drawn'}

        # Determine player number (1 or 2)
        p_num = 1 if state['current_player'] == 'P1' else 2
        lines[row][col] = p_num

        # Check for completed boxes
        scored = _check_boxes(state['h_lines'], state['v_lines'], state['boxes'], p_num)

        # Update scores
        p1_name = state['players']['P1']
        p2_name = state['players']['P2']
        if scored > 0:
            state['scores'][player] = state['scores'].get(player, 0) + scored

        # Find completed boxes for animation
        completed = []
        for r in range(len(state['boxes'])):
            for c in range(len(state['boxes'][0])):
                if state['boxes'][r][c] == p_num:
                    completed.append({'r': r, 'c': c})
        state['last_boxes'] = completed if scored > 0 else []
        state['last_move'] = {'type': line_type, 'row': row, 'col': col, 'player': p_num}

        # Check game over
        total_boxes = (state['dots'] - 1) ** 2
        filled = sum(1 for row in state['boxes'] for v in row if v != 0)

        if filled >= total_boxes:
            # Game over for this round
            return self._end_round(room_code, state)

        # If scored, player keeps turn; otherwise switch
        if scored == 0:
            state['current_player'] = 'P2' if state['current_player'] == 'P1' else 'P1'

        set_game_state(room_code, state)
        return {'state': state, 'scored': scored}

    def _end_round(self, room_code: str, state: Dict) -> Dict:
        state['phase'] = 'result'
        p1_name = state['players']['P1']
        p2_name = state['players']['P2']
        s1 = state['scores'].get(p1_name, 0)
        s2 = state['scores'].get(p2_name, 0)

        if s1 > s2:
            round_winner = p1_name
        elif s2 > s1:
            round_winner = p2_name
        else:
            round_winner = 'draw'

        if round_winner != 'draw':
            state['round_wins'][round_winner] = state['round_wins'].get(round_winner, 0) + 1

        current_round = state['current_round']
        total_rounds  = state['total_rounds']

        if current_round >= total_rounds:
            rw = state['round_wins']
            if rw.get(p1_name, 0) > rw.get(p2_name, 0):
                game_winner = p1_name
            elif rw.get(p2_name, 0) > rw.get(p1_name, 0):
                game_winner = p2_name
            else:
                game_winner = p1_name if s1 >= s2 else p2_name

            state['game_winner'] = game_winner
            set_game_state(room_code, state)
            return {
                'state':        state,
                'round_ended':  True,
                'round_winner': round_winner,
                'game_ended':   True,
                'game_winner':  game_winner,
                'final_scores': state['scores'],
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

        p1 = state['players']['P1']
        p2 = state['players']['P2']
        dots = state.get('dots', 6)
        board = _create_board(dots)

        state['current_round'] += 1
        state['h_lines']        = board['h_lines']
        state['v_lines']        = board['v_lines']
        state['boxes']          = board['boxes']
        state['current_player'] = 'P1'
        state['phase']          = 'playing'
        state['scores']         = {p1: 0, p2: 0}
        state['last_move']      = None
        state['last_boxes']     = []

        set_game_state(room_code, state)
        return {'state': state, 'round_started': True}
