"""
Memory Card Game Handler

Shared 4×6 board (24 cards = 12 pairs). Turn-based.
- Player flips 2 cards per turn via 'flip' action
- If they match  → player scores a point and KEEPS their turn
- If they don't  → cards flip back, turn passes to opponent
- Game ends when all 12 pairs are found
- Most pairs wins the round
"""

import random
from typing import Dict, List, Optional
from games.base import BaseGameHandler
from rooms.redis_client import get_game_state, set_game_state

SYMBOLS = ["♠", "♦", "♣", "♥", "★", "♛", "♞", "♜", "⚡", "✿", "♫", "☀"]
PAIR_COUNT = len(SYMBOLS)   # 12 pairs = 24 cards


def _make_deck() -> List[Dict]:
    """Create and shuffle 24 cards (12 symbol pairs)."""
    cards = []
    for ci, sym in enumerate(SYMBOLS):
        cards.append({'id': ci * 2,     'symbol': sym, 'ci': ci})
        cards.append({'id': ci * 2 + 1, 'symbol': sym, 'ci': ci})
    random.shuffle(cards)
    return cards


class MemoryHandler(BaseGameHandler):
    game_id     = "memory"
    game_name   = "Memory"
    game_mode   = "turn_based"
    min_players = 2
    max_players = 2

    def initialize(self, room_code: str, players: List[str], total_rounds: int) -> Dict:
        p1, p2 = players[0], players[1]
        state = {
            'players':       {'P1': p1, 'P2': p2},
            'scores':        {p1: 0, p2: 0},
            'round_wins':    {p1: 0, p2: 0},
            'current_round': 1,
            'total_rounds':  total_rounds,
            # The deck: list of {id, symbol, ci}
            'deck':          _make_deck(),
            # match_owner: {card_id: username} for matched pairs
            'match_owner':   {},
            # current turn state
            'current_player': 'P1',
            'flipped':        [],    # list of card indices currently exposed (max 2)
            'phase':          'pick',  # 'pick' | 'reveal' | 'result'
            'streak':         {p1: 0, p2: 0},
            'last_flip':      None,  # {index, matched: bool}
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

        # Validate it's this player's turn
        cp_key = state['current_player']
        cp_name = state['players'][cp_key]
        if player != cp_name:
            return {'error': 'Not your turn', 'state': state}

        if action == 'flip':
            return self._handle_flip(room_code, state, player, data)

        return {'error': f'Unknown action: {action}', 'state': state}

    def _handle_flip(self, room_code: str, state: Dict, player: str, data: Dict) -> Dict:
        idx = data.get('index')
        if idx is None or not isinstance(idx, int):
            return {'error': 'Invalid index', 'state': state}

        deck = state['deck']
        if idx < 0 or idx >= len(deck):
            return {'error': 'Index out of range', 'state': state}

        card = deck[idx]
        card_key = str(card['id'])   # ALWAYS use string keys for match_owner

        # Can't flip an already matched card
        if card_key in state['match_owner']:
            return {'error': 'Card already matched', 'state': state}

        # Can't flip a card already face-up this turn
        if idx in state['flipped']:
            return {'error': 'Card already flipped', 'state': state}

        state['flipped'].append(idx)

        if len(state['flipped']) == 1:
            # First card of the pair — clear stale last_flip
            state['last_flip'] = None
            state['phase'] = 'pick'
            set_game_state(room_code, state)
            return {'state': state, 'waiting_for_second': True}

        # Second card flipped — check for match
        a_idx, b_idx = state['flipped'][0], state['flipped'][1]
        card_a = deck[a_idx]
        card_b = deck[b_idx]

        p1_name = state['players']['P1']
        p2_name = state['players']['P2']

        if card_a['symbol'] == card_b['symbol']:
            # MATCH — always use string keys!
            state['match_owner'][str(card_a['id'])] = player
            state['match_owner'][str(card_b['id'])] = player
            state['scores'][player] += 1
            state['streak'][player] = state['streak'].get(player, 0) + 1
            # Reset opponent streak
            opp = p2_name if player == p1_name else p1_name
            state['streak'][opp] = 0
            state['flipped'] = []
            state['phase'] = 'pick'
            state['last_flip'] = {'a': a_idx, 'b': b_idx, 'matched': True}
            # Player keeps turn!

            # Check game over
            total_matched = len(state['match_owner'])
            if total_matched >= PAIR_COUNT * 2:
                return self._end_round(room_code, state)

            set_game_state(room_code, state)
            return {'state': state, 'matched': True, 'scorer': player,
                    'streak': state['streak'][player]}
        else:
            # NO MATCH — switch turn, flash the two cards then hide
            state['last_flip'] = {'a': a_idx, 'b': b_idx, 'matched': False}
            state['streak'][player] = 0
            state['phase'] = 'pick'
            # Switch turn
            if state['current_player'] == 'P1':
                state['current_player'] = 'P2'
            else:
                state['current_player'] = 'P1'
            # Clear flipped immediately — client uses last_flip for reveal anim
            state['flipped'] = []
            set_game_state(room_code, state)
            return {'state': state, 'matched': False,
                    'reveal_cards': [a_idx, b_idx]}

    def _end_round(self, room_code: str, state: Dict) -> Dict:
        p1_name = state['players']['P1']
        p2_name = state['players']['P2']
        s1 = state['scores'][p1_name]
        s2 = state['scores'][p2_name]

        if s1 > s2:
            round_winner = p1_name
        elif s2 > s1:
            round_winner = p2_name
        else:
            round_winner = 'draw'

        if round_winner != 'draw':
            state['round_wins'][round_winner] += 1
        state['phase'] = 'result'

        current_round = state['current_round']
        total_rounds  = state['total_rounds']

        if current_round >= total_rounds:
            rw = state['round_wins']
            if rw[p1_name] > rw[p2_name]:
                game_winner = p1_name
            elif rw[p2_name] > rw[p1_name]:
                game_winner = p2_name
            else:
                # Tiebreak by total score
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

        p1_name = state['players']['P1']
        p2_name = state['players']['P2']
        state['current_round'] += 1
        state['deck']          = _make_deck()
        state['match_owner']   = {}
        state['flipped']       = []
        state['phase']         = 'pick'
        state['scores']        = {p1_name: 0, p2_name: 0}
        state['streak']        = {p1_name: 0, p2_name: 0}
        state['current_player'] = 'P1'
        state['last_flip']     = None

        set_game_state(room_code, state)
        return {'state': state, 'round_started': True}
