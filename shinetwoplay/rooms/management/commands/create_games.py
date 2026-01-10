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
                'game_id': 'pullrope',
                'name': 'Pull Rope',
                'image_url': '/static/games/pullrope.png',
                'description': 'Tap fast to pull the rope and win!',
            },
            {
                'game_id': 'tennis',
                'name': 'Tennis',
                'image_url': '/static/games/tennis.png',
                'description': 'Classic tennis game. Hit the ball back and forth!',
            },
            {
                'game_id': 'ludo',
                'name': 'Ludo',
                'image_url': '/static/games/ludo.png',
                'description': 'Roll the dice and race to the finish!',
            },
            {
                'game_id': 'chess',
                'name': 'Chess',
                'image_url': '/static/games/chess.png',
                'description': 'Strategic board game. Checkmate your opponent!',
            },
            {
                'game_id': 'checkers',
                'name': 'Checkers',
                'image_url': '/static/games/checkers.png',
                'description': 'Jump over opponent pieces to win!',
            },
            {
                'game_id': 'rps',
                'name': 'Rock Paper Scissors',
                'image_url': '/static/games/rps.png',
                'description': 'Classic hand game. Best of 3 rounds!',
            },
            {
                'game_id': 'memory',
                'name': 'Memory Match',
                'image_url': '/static/games/memory.png',
                'description': 'Find matching pairs. Test your memory!',
            },
            {
                'game_id': 'snake',
                'name': 'Snake Race',
                'image_url': '/static/games/snake.png',
                'description': 'Race to collect the most food!',
            },
            {
                'game_id': 'pong',
                'name': 'Pong',
                'image_url': '/static/games/pong.png',
                'description': 'Classic paddle game. Don\'t miss the ball!',
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
