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
            winner = data.get("winner")
            if winner in ("P1", "P2"):
                state["round_wins"][winner] = state["round_wins"].get(winner, 0) + 1

            state["scores"]["P1"] = data.get("p1_score", state["scores"]["P1"])
            state["scores"]["P2"] = data.get("p2_score", state["scores"]["P2"])

            current_round = state.get("current_round", 1)
            total_rounds = state.get("total_rounds", 1)

            if current_round >= total_rounds:
                state["status"] = "finished"
                state["current_round"] = current_round + 1
                set_game_state(room_code, state)

                p1w = state["round_wins"]["P1"]
                p2w = state["round_wins"]["P2"]
                if p1w > p2w:
                    game_winner = "P1"
                elif p2w > p1w:
                    game_winner = "P2"
                else:
                    game_winner = "draw"

                return {
                    "state": state,
                    "round_ended": True,
                    "round_winner": winner,
                    "game_over": True,
                    "game_winner": game_winner,
                    "game_winner_name": state["players"].get(game_winner, "Draw"),
                    "final_scores": state["round_wins"],
                }
            else:
                state["current_round"] = current_round + 1
                state["scores"] = {"P1": 0, "P2": 0}
                set_game_state(room_code, state)
                return {
                    "state": state,
                    "round_ended": True,
                    "round_winner": winner,
                    "game_over": False,
                }

        return {"state": state}

    def handle_input(self, room_code: str, player: str, input_data: Dict) -> None:
        pass

    def tick(self, room_code: str) -> Dict:
        return {}
