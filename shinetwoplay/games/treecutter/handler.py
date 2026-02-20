"""
Tree Cutter (Timber Chop) game handler — real-time simultaneous chopping.

Both players race to chop 100 logs. P1 generates the shared branch
pattern and is authoritative for determining the winner.
Server tracks scores, rounds, and game lifecycle.
"""

from typing import Dict, List
from games.base import BaseGameHandler
from rooms.redis_client import get_game_state, set_game_state


class TreeCutterHandler(BaseGameHandler):
    game_id = "treecutter"
    game_name = "Timber Chop"
    game_mode = "real_time"
    min_players = 2
    max_players = 2

    def initialize(self, room_code: str, players: List[str], total_rounds: int) -> Dict:
        state = {
            "players": {"P1": players[0], "P2": players[1]},
            "scores": {"P1": 0, "P2": 0},
            "current_round": 1,
            "total_rounds": total_rounds,
            "round_wins": {"P1": 0, "P2": 0},
            "status": "playing",
            "paused": False,
            "disconnected_players": [],
            "game_mode": "real_time",
        }
        set_game_state(room_code, state)
        return state

    def handle_move(self, room_code: str, player: str, action: str, data: Dict) -> Dict:
        state = get_game_state(room_code)
        if not state:
            return {"error": "Game not found"}

        if action == "score_update":
            if "p1_score" in data:
                state["scores"]["P1"] = data["p1_score"]
            if "p2_score" in data:
                state["scores"]["P2"] = data["p2_score"]
            set_game_state(room_code, state)
            return {"state": state}

        elif action == "round_end":
            winner = data.get("winner")  # "P1" or "P2"
            if winner in ("P1", "P2"):
                state["round_wins"][winner] = state["round_wins"].get(winner, 0) + 1

            state["scores"]["P1"] = data.get("p1_score", state["scores"]["P1"])
            state["scores"]["P2"] = data.get("p2_score", state["scores"]["P2"])

            # Determine round winner name
            round_winner_name = state["players"].get(winner, "draw")

            return self._handle_round_end(room_code, state, round_winner_name)

        return {"state": state}

    def _handle_round_end(self, room_code: str, state: Dict, winner: str) -> Dict:
        """Handle end of a round — check if game is over or start next round."""
        state["current_round"] += 1
        current_round = state["current_round"]
        total_rounds = state["total_rounds"]

        if current_round > total_rounds:
            # All rounds done
            state["status"] = "finished"
            p1w = state["round_wins"]["P1"]
            p2w = state["round_wins"]["P2"]

            if p1w > p2w:
                game_winner = state["players"]["P1"]
            elif p2w > p1w:
                game_winner = state["players"]["P2"]
            else:
                game_winner = "draw"

            set_game_state(room_code, state)

            return {
                "state": state,
                "round_ended": True,
                "round_winner": winner,
                "game_ended": True,
                "game_winner": game_winner,
                "final_scores": state["round_wins"],
            }
        else:
            # More rounds to play
            state["scores"] = {"P1": 0, "P2": 0}
            set_game_state(room_code, state)
            return {
                "state": state,
                "round_ended": True,
                "round_winner": winner,
                "next_round": current_round,
                "total_rounds": total_rounds,
            }

    def start_next_round(self, room_code: str) -> Dict:
        """Start the next round — reset per-round scores."""
        state = get_game_state(room_code)
        if not state:
            return {"error": "Game not found"}

        state["scores"] = {"P1": 0, "P2": 0}
        set_game_state(room_code, state)
        return {"state": state, "round_started": True}

    def handle_input(self, room_code: str, player: str, input_data: Dict) -> None:
        pass

    def tick(self, room_code: str) -> Dict:
        return {}
