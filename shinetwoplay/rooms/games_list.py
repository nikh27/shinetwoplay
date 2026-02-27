"""
Static list of all available games.
This replaces the database dependency for the games catalog.
"""

GAMES = [
    {
        'game_id': 'ludo',
        'name': 'Ludo',
        'image_url': '/static/games/ludo.png',
        'description': 'Classic Ludo! Roll the dice, move your pieces home. First to bring all 4 home wins!',
        'min_players': 2,
        'max_players': 2,
    },
    {
        'game_id': 'tictactoe',
        'name': 'Tic Tac Toe',
        'image_url': '/static/games/tictactoe.png',
        'description': 'Classic 3x3 grid game. Get 3 in a row to win!',
        'min_players': 2,
        'max_players': 2,
    },
    {
        'game_id': 'paddlearena',
        'name': 'Paddle Arena',
        'image_url': '/static/games/paddlearena.png',
        'description': 'Real-time pong with obstacles. Don\'t miss the ball!',
        'min_players': 2,
        'max_players': 2,
    },
    {
        'game_id': 'connect4',
        'name': 'Connect 4',
        'image_url': '/static/games/connect4.png',
        'description': 'Drop discs to connect 4 in a row. Classic strategy!',
        'min_players': 2,
        'max_players': 2,
    },
    {
        'game_id': 'beachball',
        'name': 'Beach Ball',
        'image_url': '/static/games/beachball.png',
        'description': 'Push the beach ball into your opponent\'s goal! Throw stones in the pool to hit the ball.',
        'min_players': 2,
        'max_players': 2,
    },
    {
        'game_id': 'carrom',
        'name': 'Carrom',
        'image_url': '/static/games/carrom.png',
        'description': 'Classic carrom board game. Pocket all your coins before your opponent!',
        'min_players': 2,
        'max_players': 2,
    },
    {
        'game_id': 'stealthering',
        'name': 'Diamond Heist',
        'image_url': '/static/games/stealthering.png',
        'description': 'Grab the diamond when the case opens! First to 5 wins. Don\'t tap too early!',
        'min_players': 2,
        'max_players': 2,
    },
    {
        'game_id': 'treecutter',
        'name': 'Timber Chop',
        'image_url': '/static/games/treecutter.png',
        'description': 'Race to chop 100 logs! Dodge the branches or get stunned!',
        'min_players': 2,
        'max_players': 2,
    },
    {
        'game_id': 'snakes',
        'name': 'Snakes',
        'image_url': '/static/games/snakes.png',
        'description': 'Real-time 2-player snake battle! Control your snake and outlast your opponent!',
        'min_players': 2,
        'max_players': 2,
    },
    {
        'game_id': 'pulltherope',
        'name': 'Pull The Rope',
        'image_url': '/static/games/pulltherope.png',
        'description': 'Tap as fast as you can! Pull the rope to your side to win!',
        'min_players': 2,
        'max_players': 2,
    },
    {
        'game_id': 'bamboobreaker',
        'name': 'Bamboo Breaker',
        'image_url': '/static/games/bamboobreaker.png',
        'description': 'Panda tile-breaking battle! Move across bamboo tiles that crack under you. Push your opponent into holes!',
        'min_players': 2,
        'max_players': 2,
    }
]

def get_all_games():
    return GAMES

def get_game_by_id(game_id):
    for game in GAMES:
        if game['game_id'] == game_id:
            return game
    return None
