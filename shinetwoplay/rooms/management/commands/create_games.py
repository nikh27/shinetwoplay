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
