"""
Base Game Handler

All game handlers must extend this class.
Supports both turn-based and real-time games.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any
import json


class BaseGameHandler(ABC):
    """
    Base class for all game handlers.
    
    Attributes:
        game_id: Unique identifier (must match database Game.game_id)
        game_name: Display name of the game
        game_mode: "turn_based" or "real_time"
        tick_rate: Updates per second (only for real_time games)
        min_players: Minimum players required
        max_players: Maximum players allowed
    """
    
    game_id: str = None
    game_name: str = None
    game_mode: str = "turn_based"  # or "real_time"
    tick_rate: int = 0  # Updates per second (0 = turn-based)
    min_players: int = 2
    max_players: int = 2
    
    def get_template(self) -> str:
        """Load the game.html template from the game's folder"""
        game_folder = Path(__file__).parent / self.game_id
        template_path = game_folder / 'game.html'
        
        if template_path.exists():
            return template_path.read_text(encoding='utf-8')
        else:
            raise FileNotFoundError(f"Template not found: {template_path}")
    
    @abstractmethod
    def initialize(self, room_code: str, players: List[str], total_rounds: int) -> Dict:
        """
        Initialize a new game session.
        
        Args:
            room_code: The room code
            players: List of player usernames
            total_rounds: Number of rounds to play
            
        Returns:
            Initial game state dict
        """
        pass
    
    @abstractmethod
    def handle_move(self, room_code: str, player: str, action: str, data: Dict) -> Dict:
        """
        Process a player's move (turn-based games).
        
        Args:
            room_code: The room code
            player: Username of the player making the move
            action: Action type (e.g., "place", "draw")
            data: Action-specific data
            
        Returns:
            Result dict with 'state' and optionally 'round_ended', 'winner', 'error'
        """
        pass
    
    def handle_input(self, room_code: str, player: str, input_data: Dict) -> None:
        """
        Process continuous player input (real-time games).
        
        Args:
            room_code: The room code
            player: Username of the player
            input_data: Input data (keys pressed, mouse position, etc.)
        """
        # Override in real-time games
        pass
    
    def tick(self, room_code: str) -> Dict:
        """
        Server tick for real-time games (called tick_rate times per second).
        
        Args:
            room_code: The room code
            
        Returns:
            Updated game state
        """
        # Override in real-time games
        return {}
    
    def on_player_disconnect(self, room_code: str, player: str) -> Dict:
        """
        Handle player disconnection during game.
        
        Args:
            room_code: The room code
            player: Username of disconnected player
            
        Returns:
            Updated state with paused=True
        """
        from rooms.redis_client import get_game_state, set_game_state
        import time
        
        state = get_game_state(room_code)
        if state:
            state['paused'] = True
            state['paused_at'] = time.time()
            if 'disconnected_players' not in state:
                state['disconnected_players'] = []
            if player not in state['disconnected_players']:
                state['disconnected_players'].append(player)
            set_game_state(room_code, state)
        return state
    
    def on_player_reconnect(self, room_code: str, player: str) -> Dict:
        """
        Handle player reconnection during game.
        
        Args:
            room_code: The room code  
            player: Username of reconnected player
            
        Returns:
            Updated state (unpaused if all players connected)
        """
        from rooms.redis_client import get_game_state, set_game_state
        
        state = get_game_state(room_code)
        if state and 'disconnected_players' in state:
            if player in state['disconnected_players']:
                state['disconnected_players'].remove(player)
            
            # If no more disconnected players, unpause
            if len(state['disconnected_players']) == 0:
                state['paused'] = False
                state.pop('paused_at', None)
            
            set_game_state(room_code, state)
        return state
    
    def cleanup(self, room_code: str) -> None:
        """
        Clean up game state when game ends.
        
        Args:
            room_code: The room code
        """
        from rooms.redis_client import clear_game_state
        clear_game_state(room_code)
