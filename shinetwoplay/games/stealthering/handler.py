"""
Stealthering (Diamond Heist) game handler — real-time reflex game.

Both players compete to grab a diamond when the case opens.
P1 is authoritative: generates timing, determines who grabbed first.
Server tracks scores, rounds, and game lifecycle.

Each round = first to 3 points. Whoever wins more rounds wins the game.
"""

from typing import Dict, List
from games.base import BaseGameHandler
from rooms.redis_client import get_game_state, set_game_state


class StealtheringHandler(BaseGameHandler):
    game_id = "stealthering"
    game_name = "Diamond Heist"
    game_mode = "real_time"
    min_players = 2
    max_players = 2

    POINTS_PER_ROUND = 3

    def initialize(self, room_code: str, players: List[str], total_rounds: int) -> Dict:
        state = {
            "players": {"P1": players[0], "P2": players[1]},
            "scores": {"P1": 0, "P2": 0},          # per-round scores (reset each round)
            "round_wins": {"P1": 0, "P2": 0},       # how many rounds each player won
            "current_round": 1,
            "total_rounds": total_rounds,
            "round_winner": None,
            "game_winner": None,
            "paused": False,
            "disconnected_players": [],
            "game_mode": "real_time",
            "status": "playing",
        }
        set_game_state(room_code, state)
        return state

    def handle_move(self, room_code: str, player: str, action: str, data: Dict) -> Dict:
        state = get_game_state(room_code)
        if not state:
            return {"error": "Game not found"}

        if action == "score_update":
            # P1 reports intermediate score changes
            state["scores"]["P1"] = data.get("p1_score", state["scores"]["P1"])
            state["scores"]["P2"] = data.get("p2_score", state["scores"]["P2"])
            set_game_state(room_code, state)
            return {"state": state}

        if action == "round_end":
            # A player reached POINTS_PER_ROUND — round is over
            winner_role = data.get("winner")      # "P1" or "P2"

            # Update scores from client
            state["scores"]["P1"] = data.get("p1_score", state["scores"]["P1"])
            state["scores"]["P2"] = data.get("p2_score", state["scores"]["P2"])

            # Record round winner
            if winner_role in ("P1", "P2"):
                state["round_wins"][winner_role] = state["round_wins"].get(winner_role, 0) + 1
                state["round_winner"] = state["players"][winner_role]
            else:
                state["round_winner"] = "draw"

            return self._handle_round_end(room_code, state, state["round_winner"])

        return {"error": f"Unknown action: {action}"}

    def _handle_round_end(self, room_code: str, state: Dict, winner: str) -> Dict:
        """Handle end of a round — check if game is over or start next round."""
        state["current_round"] += 1
        current_round = state["current_round"]
        total_rounds = state["total_rounds"]

        if current_round > total_rounds:
            # All rounds done — determine game winner
            p1w = state["round_wins"]["P1"]
            p2w = state["round_wins"]["P2"]

            if p1w > p2w:
                state["game_winner"] = state["players"]["P1"]
            elif p2w > p1w:
                state["game_winner"] = state["players"]["P2"]
            else:
                state["game_winner"] = "draw"

            set_game_state(room_code, state)

            return {
                "state": state,
                "round_ended": True,
                "round_winner": winner,
                "game_ended": True,
                "game_winner": state["game_winner"],
                "final_scores": state["round_wins"],
            }
        else:
            # More rounds to play
            set_game_state(room_code, state)
            return {
                "state": state,
                "round_ended": True,
                "round_winner": winner,
                "next_round": current_round,
                "total_rounds": total_rounds,
            }

    def start_next_round(self, room_code: str) -> Dict:
        """Start the next round — reset per-round scores, keep round_wins."""
        state = get_game_state(room_code)
        if not state:
            return {"error": "Game not found"}

        state["round_winner"] = None
        state["scores"] = {"P1": 0, "P2": 0}  # reset per-round scores

        set_game_state(room_code, state)
        return {"state": state, "round_started": True}

    def handle_input(self, room_code: str, player: str, input_data: Dict) -> None:
        pass

    def tick(self, room_code: str) -> Dict:
        return {}
