"""
Game Template Loader

Utility functions for loading game HTML templates.
"""
from pathlib import Path
from typing import Optional


def load_game_template(game_id: str) -> Optional[str]:
    """
    Load a game's HTML template.
    
    Args:
        game_id: The game identifier
        
    Returns:
        HTML template string or None if not found
    """
    games_dir = Path(__file__).parent
    template_path = games_dir / game_id / 'game.html'
    
    if template_path.exists():
        return template_path.read_text(encoding='utf-8')
    return None


def get_game_asset_url(game_id: str, asset_name: str) -> str:
    """
    Get the URL for a game asset.
    
    Args:
        game_id: The game identifier
        asset_name: Name of the asset file
        
    Returns:
        URL path to the asset
    """
    return f'/static/games/{game_id}/assets/{asset_name}'
