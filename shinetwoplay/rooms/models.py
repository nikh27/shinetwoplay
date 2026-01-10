from django.db import models
from django.core.validators import MaxLengthValidator, MinValueValidator, MaxValueValidator

class Room(models.Model):
    code = models.CharField(max_length=4, unique=True, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.CharField(max_length=8)  # Max 8 characters
    selected_game = models.CharField(max_length=50, null=True, blank=True)
    rounds = models.IntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(5)])
    status = models.CharField(max_length=20, default='waiting')  # waiting, playing, finished
    max_players = models.IntegerField(default=2)  # Fixed at 2 players

    def __str__(self):
        return f"Room {self.code} - {self.status}"

    class Meta:
        db_table = 'rooms'


class Player(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='players')
    username = models.CharField(max_length=8)  # Max 8 characters
    gender = models.CharField(max_length=6, choices=GENDER_CHOICES)
    avatar = models.CharField(max_length=10, default='👨')  # Auto-set based on gender
    is_ready = models.BooleanField(default=False)
    is_owner = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)
    is_online = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        # Auto-set avatar based on gender
        if self.gender == 'male':
            self.avatar = '👨'
        elif self.gender == 'female':
            self.avatar = '👩'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} in {self.room.code}"

    class Meta:
        db_table = 'players'
        unique_together = ('room', 'username')


class Message(models.Model):
    MESSAGE_TYPES = [
        ('chat', 'Chat'),
        ('voice', 'Voice'),
        ('image', 'Image'),
        ('system', 'System'),
        ('notification', 'Notification'),
    ]
    
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=8)
    content = models.TextField(blank=True, null=True)  # Null for voice/image messages
    timestamp = models.DateTimeField(auto_now_add=True)
    message_type = models.CharField(max_length=20, default='chat', choices=MESSAGE_TYPES)
    
    # Voice message fields
    voice_url = models.CharField(max_length=500, blank=True, null=True)
    voice_duration = models.IntegerField(blank=True, null=True, validators=[MaxValueValidator(60)])  # Max 60 seconds
    
    # Image message fields
    image_url = models.CharField(max_length=500, blank=True, null=True)
    image_width = models.IntegerField(blank=True, null=True)
    image_height = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"{self.sender}: {self.message_type} in {self.room.code}"

    class Meta:
        db_table = 'messages'
        ordering = ['timestamp']


class MessageReaction(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.CharField(max_length=8)
    emoji = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} reacted {self.emoji} to message {self.message.id}"

    class Meta:
        db_table = 'message_reactions'
        unique_together = ('message', 'user', 'emoji')


class Game(models.Model):
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


class GameSession(models.Model):
    SESSION_STATUS = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
    ]
    
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='game_sessions')
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    current_round = models.IntegerField(default=1)
    total_rounds = models.IntegerField(default=1)
    player1_score = models.IntegerField(default=0)
    player2_score = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    winner = models.CharField(max_length=8, null=True, blank=True)
    status = models.CharField(max_length=20, default='active', choices=SESSION_STATUS)

    def __str__(self):
        return f"{self.game.name} session in {self.room.code}"

    class Meta:
        db_table = 'game_sessions'
