"""
Game Handler Auto-Discovery and Registry

This module automatically discovers all game handlers in subdirectories
and provides a registry to access them by game_id.
"""
import os
import importlib
from pathlib import Path

# Game registry - populated on import
GAME_REGISTRY = {}


def discover_games():
    """
    Auto-discover all game handlers in subdirectories.
    Each game folder must have:
    - __init__.py
    - handler.py (with a class extending BaseGameHandler)
    - game.html (UI template)
    """
    games_dir = Path(__file__).parent
    
    for item in games_dir.iterdir():
        if item.is_dir() and not item.name.startswith('_'):
            # Check if it's a game folder (has handler.py)
            handler_file = item / 'handler.py'
            if handler_file.exists():
                try:
                    # Import the handler module
                    module = importlib.import_module(f'games.{item.name}.handler')
                    
                    # Find the handler class (first class with game_id attribute)
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            hasattr(attr, 'game_id') and 
                            attr.game_id is not None and
                            attr.__name__ != 'BaseGameHandler'):
                            # Register the handler
                            handler_instance = attr()
                            GAME_REGISTRY[handler_instance.game_id] = handler_instance
                            print(f"[Games] Registered: {handler_instance.game_id} -> {handler_instance.game_name}")
                            break
                except Exception as e:
                    print(f"[Games] Error loading {item.name}: {e}")


def get_handler(game_id):
    """Get a game handler by its game_id"""
    return GAME_REGISTRY.get(game_id)


def get_all_games():
    """Get all registered game handlers"""
    return GAME_REGISTRY


# Auto-discover games on module import
discover_games()
