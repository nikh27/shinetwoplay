from django.core.management.base import BaseCommand
from rooms.models import Game


class Command(BaseCommand):
    help = 'Create initial games in the database'

    def handle(self, *args, **kwargs):
        games_data = [
            {
                'game_id': 'tictactoe',
                'name': 'Tic Tac Toe',
                'image_url': '/static/games/tictactoe.png',
                'description': 'Classic 3x3 grid game. Get 3 in a row to win!',
            },
            {
                'game_id': 'paddlearena',
                'name': 'Paddle Arena',
                'image_url': '/static/games/paddlearena.png',
                'description': 'Real-time pong with obstacles. Don\'t miss the ball!',
            },
            {
                'game_id': 'connect4',
                'name': 'Connect 4',
                'image_url': '/static/games/connect4.png',
                'description': 'Drop discs to connect 4 in a row. Classic strategy!',
            },
            {
                'game_id': 'beachball',
                'name': 'Beach Ball',
                'image_url': '/static/games/beachball.png',
                'description': 'Push the beach ball into your opponent\'s goal! Throw stones in the pool to hit the ball.',
            },
            {
                'game_id': 'carrom',
                'name': 'Carrom',
                'image_url': '/static/games/carrom.png',
                'description': 'Classic carrom board game. Pocket all your coins before your opponent!',
            },
            {
                'game_id': 'stealthering',
                'name': 'Diamond Heist',
                'image_url': '/static/games/stealthering.png',
                'description': 'Grab the diamond when the case opens! First to 5 wins. Don\'t tap too early!',
            },
            {
                'game_id': 'treecutter',
                'name': 'Timber Chop',
                'image_url': '/static/games/treecutter.png',
                'description': 'Race to chop 100 logs! Dodge the branches or get stunned!',
            },
        ]

        created_count = 0
        updated_count = 0

        for game_data in games_data:
            game, created = Game.objects.update_or_create(
                game_id=game_data['game_id'],
                defaults=game_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created game: {game.name}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated game: {game.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSummary: {created_count} games created, {updated_count} games updated'
            )
        )
