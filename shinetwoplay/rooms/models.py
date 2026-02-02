from django.db import models


class Game(models.Model):
    """
    Static game catalog - stored in database.
    Pre-populated with available games.
    This is the ONLY model we need in the database.
    """
    game_id = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=100)
    image_url = models.CharField(max_length=500)  # Local path or hosted URL
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    min_players = models.IntegerField(default=2)
    max_players = models.IntegerField(default=2)  # Fixed at 2

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'games'
