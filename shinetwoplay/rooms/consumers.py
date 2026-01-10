from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import json
from datetime import datetime

from .models import Room, Player, Message, MessageReaction, Game, GameSession
from .redis_client import (
    add_player_to_room, remove_player_from_room, get_room_players,
    is_room_full, update_player_status, get_player_data,
    cache_message, get_recent_messages, set_typing, remove_typing,
    update_online_status, add_ws_connection, remove_ws_connection,
    check_rate_limit, get_room_state as get_redis_room_state
)


class RoomConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for room communication
    Handles all real-time events for 2-player game rooms
    """

    async def connect(self):
        """Handle WebSocket connection"""
        try:
            # Get room code and username from URL
            self.room_code = self.scope['url_route']['kwargs']['room_code']
            
            # Extract username from query string
            query_string = self.scope['query_string'].decode()
            params = dict(param.split('=') for param in query_string.split('&') if '=' in param)
            self.username = params.get('name', 'Guest')
            
            # Validate username length (max 8 characters)
            if len(self.username) > 8:
                await self.close(code=4000)
                return
            
            # Check if room exists
            room_exists = await self.check_room_exists(self.room_code)
            if not room_exists:
                await self.close(code=4004)  # Room not found
                return
            
            # Check if room is full
            if is_room_full(self.room_code):
                player_count = await self.get_player_count(self.room_code)
                if player_count >= 2:
                    await self.close(code=4003)  # Room full
                    return
            
            # Check if username is already taken
            existing_players = get_room_players(self.room_code)
            if self.username in existing_players:
                await self.close(code=4009)  # Username taken
                return
            
            # Set room group name
            self.room_group_name = f'room_{self.room_code}'
            
            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            
            # Accept connection
            await self.accept()
            
            # Get player data from database
            player_data = await self.get_or_create_player()
            
            # Add to Redis
            add_ws_connection(self.room_code, self.username)
            update_online_status(self.room_code, self.username)
            
            # Send initial room state to this user
            await self.send_room_state()
            
            # Notify others about new player
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'player_join',
                    'user': self.username,
                    'gender': player_data['gender'],
                    'avatar': player_data['avatar'],
                    'players': list(get_room_players(self.room_code))
                }
            )
            
        except Exception as e:
            print(f"Connection error: {e}")
            await self.close(code=4500)

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        try:
            # Remove from Redis
            remove_ws_connection(self.room_code, self.username)
            remove_typing(self.room_code, self.username)
            
            # Update player status in database
            await self.update_player_online_status(False)
            
            # Notify others
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'player_disconnect',
                    'user': self.username,
                    'reason': 'connection_lost'
                }
            )
            
            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            
        except Exception as e:
            print(f"Disconnect error: {e}")

    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            event = data.get('event')
            
            # Update online status on any activity
            update_online_status(self.room_code, self.username)
            
            # Route to appropriate handler
            if event == 'chat':
                await self.handle_chat(data)
            elif event == 'voice_message':
                await self.handle_voice_message(data)
            elif event == 'image_message':
                await self.handle_image_message(data)
            elif event == 'typing':
                await self.handle_typing()
            elif event == 'stop_typing':
                await self.handle_stop_typing()
            elif event == 'ready':
                await self.handle_ready(data)
            elif event == 'select_game':
                await self.handle_select_game(data)
            elif event == 'round_change':
                await self.handle_round_change(data)
            elif event == 'start_game':
                await self.handle_start_game()
            elif event == 'react_message':
                await self.handle_react_message(data)
            elif event == 'remove_reaction':
                await self.handle_remove_reaction(data)
            elif event == 'sync_state':
                await self.send_room_state()
            elif event == 'ping':
                await self.handle_ping()
            elif event == 'recording_voice':
                await self.handle_recording_indicator()
            elif event == 'stopped_recording':
                await self.handle_stopped_recording()
            elif event == 'uploading_image':
                await self.handle_uploading_indicator()
            else:
                await self.send_error('INVALID_EVENT', 'Unknown event type')
                
        except json.JSONDecodeError:
            await self.send_error('INVALID_JSON', 'Invalid JSON format')
        except Exception as e:
            print(f"Receive error: {e}")
            await self.send_error('SERVER_ERROR', str(e))

    # ============= Event Handlers =============

    async def handle_chat(self, data):
        """Handle chat message"""
        msg = data.get('msg', '')
        temp_id = data.get('temp_id')
        
        # Validate message
        if not msg or len(msg) > 500:
            await self.send_error('MESSAGE_TOO_LONG', 'Message must be 1-500 characters')
            return
        
        # Check rate limit (10 messages per 10 seconds)
        if not check_rate_limit(f'ratelimit:chat:{self.username}', 10, 10):
            await self.send_error('RATE_LIMIT_EXCEEDED', 'Too many messages. Please slow down.')
            return
        
        # Save to database
        message = await self.save_message('chat', content=msg)
        
        # Cache in Redis
        message_data = {
            'id': message.id,
            'sender': self.username,
            'content': msg,
            'message_type': 'chat',
            'timestamp': message.timestamp.isoformat()
        }
        cache_message(self.room_code, message_data)
        
        # Send confirmation to sender
        if temp_id:
            await self.send(text_data=json.dumps({
                'event': 'message_confirmed',
                'temp_id': temp_id,
                'message_id': message.id
            }))
        
        # Broadcast to room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message_id': message.id,
                'sender': self.username,
                'msg': msg,
                'timestamp': message.timestamp.isoformat(),
                'message_type': 'chat'
            }
        )

    async def handle_voice_message(self, data):
        """Handle voice message"""
        voice_url = data.get('voice_url')
        duration = data.get('duration')
        
        # Validate
        if not voice_url or not duration:
            await self.send_error('INVALID_DATA', 'voice_url and duration required')
            return
        
        if duration > 60:
            await self.send_error('INVALID_DURATION', 'Voice message too long. Max 60 seconds')
            return
        
        # Check rate limit (5 per minute)
        if not check_rate_limit(f'ratelimit:voice:{self.username}', 5, 60):
            await self.send_error('RATE_LIMIT_EXCEEDED', 'Too many voice messages')
            return
        
        # Save to database
        message = await self.save_message('voice', voice_url=voice_url, voice_duration=duration)
        
        # Broadcast to room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'voice_message',
                'message_id': message.id,
                'sender': self.username,
                'voice_url': voice_url,
                'duration': duration,
                'timestamp': message.timestamp.isoformat(),
                'message_type': 'voice'
            }
        )

    async def handle_image_message(self, data):
        """Handle image message"""
        image_url = data.get('image_url')
        width = data.get('width')
        height = data.get('height')
        
        # Validate
        if not image_url:
            await self.send_error('INVALID_DATA', 'image_url required')
            return
        
        # Check rate limit (10 per minute)
        if not check_rate_limit(f'ratelimit:image:{self.username}', 10, 60):
            await self.send_error('RATE_LIMIT_EXCEEDED', 'Too many images')
            return
        
        # Save to database
        message = await self.save_message('image', image_url=image_url, image_width=width, image_height=height)
        
        # Broadcast to room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'image_message',
                'message_id': message.id,
                'sender': self.username,
                'image_url': image_url,
                'width': width,
                'height': height,
                'timestamp': message.timestamp.isoformat(),
                'message_type': 'image'
            }
        )

    async def handle_typing(self):
        """Handle typing indicator"""
        set_typing(self.room_code, self.username)
        
        # Broadcast to others (not self)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user': self.username
            }
        )

    async def handle_stop_typing(self):
        """Handle stop typing"""
        remove_typing(self.room_code, self.username)

    async def handle_ready(self, data):
        """Handle ready state change"""
        ready = data.get('ready', False)
        
        # Check if user is owner (owners don't need to be ready)
        is_owner = await self.is_room_owner()
        if is_owner:
            await self.send_error('NOT_ALLOWED', 'Room owner cannot set ready state')
            return
        
        # Update in database
        await self.update_player_ready_status(ready)
        
        # Update in Redis
        update_player_status(self.room_code, self.username, 'is_ready', str(ready).lower())
        
        # Broadcast
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'ready_state',
                'user': self.username,
                'ready': ready
            }
        )

    async def handle_select_game(self, data):
        """Handle game selection (owner only)"""
        game_id = data.get('game')
        
        # Check if user is owner
        is_owner = await self.is_room_owner()
        if not is_owner:
            await self.send_error('NOT_OWNER', 'Only room owner can select games')
            return
        
        # Validate game exists
        game_exists = await self.check_game_exists(game_id)
        if not game_exists:
            await self.send_error('GAME_NOT_FOUND', 'Game does not exist')
            return
        
        # Update room
        await self.update_room_game(game_id)
        
        # Get game details
        game_data = await self.get_game_details(game_id)
        
        # Broadcast
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'game_selected',
                'game': game_id,
                'game_name': game_data['name'],
                'image_url': game_data['image_url']
            }
        )

    async def handle_round_change(self, data):
        """Handle round change (owner only)"""
        rounds = data.get('round')
        
        # Check if user is owner
        is_owner = await self.is_room_owner()
        if not is_owner:
            await self.send_error('NOT_OWNER', 'Only room owner can change rounds')
            return
        
        # Validate rounds
        if rounds not in [1, 3, 5]:
            await self.send_error('INVALID_ROUNDS', 'Rounds must be 1, 3, or 5')
            return
        
        # Update room
        await self.update_room_rounds(rounds)
        
        # Broadcast
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'round_update',
                'round': rounds
            }
        )

    async def handle_start_game(self):
        """Handle start game (owner only)"""
        # Check if user is owner
        is_owner = await self.is_room_owner()
        if not is_owner:
            await self.send_error('NOT_OWNER', 'Only room owner can start game')
            return
        
        # Get room data
        room_data = await self.get_room_data()
        
        # Check if game is selected
        if not room_data['selected_game']:
            await self.send_error('GAME_NOT_SELECTED', 'Please select a game first')
            return
        
        # Check if players are ready
        players_ready = await self.check_all_players_ready()
        if not players_ready:
            await self.send_error('PLAYERS_NOT_READY', 'All players must be ready')
            return
        
        # Create game session
        session_id = await self.create_game_session(room_data['selected_game'], room_data['rounds'])
        
        # Broadcast
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'start_game',
                'game': room_data['selected_game'],
                'room': self.room_code,
                'session_id': session_id,
                'redirect_url': f'/games/{room_data["selected_game"]}/{self.room_code}/'
            }
        )

    async def handle_react_message(self, data):
        """Handle message reaction"""
        message_id = data.get('message_id')
        emoji = data.get('emoji')
        
        # Check rate limit (20 per minute)
        if not check_rate_limit(f'ratelimit:react:{self.username}', 20, 60):
            await self.send_error('RATE_LIMIT_EXCEEDED', 'Too many reactions')
            return
        
        # Create reaction
        created = await self.create_reaction(message_id, emoji)
        
        # Broadcast
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'message_reaction',
                'message_id': message_id,
                'user': self.username,
                'emoji': emoji,
                'action': 'add'
            }
        )

    async def handle_remove_reaction(self, data):
        """Handle remove reaction"""
        message_id = data.get('message_id')
        emoji = data.get('emoji')
        
        # Remove reaction
        await self.delete_reaction(message_id, emoji)
        
        # Broadcast
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'message_reaction',
                'message_id': message_id,
                'user': self.username,
                'emoji': emoji,
                'action': 'remove'
            }
        )

    async def handle_ping(self):
        """Handle heartbeat ping"""
        update_online_status(self.room_code, self.username)
        await self.send(text_data=json.dumps({'event': 'pong'}))

    async def handle_recording_indicator(self):
        """Handle voice recording indicator"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'recording_voice',
                'user': self.username
            }
        )

    async def handle_stopped_recording(self):
        """Handle stopped recording indicator"""
        # Just notify, no need to broadcast
        pass

    async def handle_uploading_indicator(self):
        """Handle image uploading indicator"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'uploading_image',
                'user': self.username
            }
        )

    # ============= Server → Client Event Handlers =============

    async def player_join(self, event):
        """Send player join event"""
        await self.send(text_data=json.dumps({
            'event': 'player_join',
            'data': {
                'user': event['user'],
                'gender': event.get('gender'),
                'avatar': event.get('avatar'),
                'players': event['players']
            }
        }))

    async def player_disconnect(self, event):
        """Send player disconnect event"""
        await self.send(text_data=json.dumps({
            'event': 'player_disconnect',
            'data': {
                'user': event['user'],
                'reason': event.get('reason', 'unknown')
            }
        }))

    async def chat_message(self, event):
        """Send chat message event"""
        await self.send(text_data=json.dumps({
            'event': 'chat',
            'data': {
                'message_id': event['message_id'],
                'sender': event['sender'],
                'msg': event['msg'],
                'timestamp': event['timestamp'],
                'message_type': event['message_type']
            }
        }))

    async def voice_message(self, event):
        """Send voice message event"""
        await self.send(text_data=json.dumps({
            'event': 'voice_message',
            'data': {
                'message_id': event['message_id'],
                'sender': event['sender'],
                'voice_url': event['voice_url'],
                'duration': event['duration'],
                'timestamp': event['timestamp'],
                'message_type': event['message_type']
            }
        }))

    async def image_message(self, event):
        """Send image message event"""
        await self.send(text_data=json.dumps({
            'event': 'image_message',
            'data': {
                'message_id': event['message_id'],
                'sender': event['sender'],
                'image_url': event['image_url'],
                'width': event.get('width'),
                'height': event.get('height'),
                'timestamp': event['timestamp'],
                'message_type': event['message_type']
            }
        }))

    async def typing_indicator(self, event):
        """Send typing indicator event"""
        # Don't send to self
        if event['user'] != self.username:
            await self.send(text_data=json.dumps({
                'event': 'typing',
                'data': {'user': event['user']}
            }))

    async def ready_state(self, event):
        """Send ready state event"""
        await self.send(text_data=json.dumps({
            'event': 'ready_state',
            'data': {
                'user': event['user'],
                'ready': event['ready']
            }
        }))

    async def game_selected(self, event):
        """Send game selected event"""
        await self.send(text_data=json.dumps({
            'event': 'game_selected',
            'data': {
                'game': event['game'],
                'game_name': event['game_name'],
                'image_url': event['image_url']
            }
        }))

    async def round_update(self, event):
        """Send round update event"""
        await self.send(text_data=json.dumps({
            'event': 'round_update',
            'data': {'round': event['round']}
        }))

    async def start_game(self, event):
        """Send start game event"""
        await self.send(text_data=json.dumps({
            'event': 'start_game',
            'data': {
                'game': event['game'],
                'room': event['room'],
                'session_id': event['session_id'],
                'redirect_url': event['redirect_url']
            }
        }))

    async def message_reaction(self, event):
        """Send message reaction event"""
        await self.send(text_data=json.dumps({
            'event': 'message_reaction',
            'data': {
                'message_id': event['message_id'],
                'user': event['user'],
                'emoji': event['emoji'],
                'action': event['action']
            }
        }))

    async def recording_voice(self, event):
        """Send recording indicator event"""
        # Don't send to self
        if event['user'] != self.username:
            await self.send(text_data=json.dumps({
                'event': 'recording_voice',
                'data': {'user': event['user']}
            }))

    async def uploading_image(self, event):
        """Send uploading indicator event"""
        # Don't send to self
        if event['user'] != self.username:
            await self.send(text_data=json.dumps({
                'event': 'uploading_image',
                'data': {'user': event['user']}
            }))

    # ============= Helper Methods =============

    async def send_room_state(self):
        """Send complete room state to client"""
        room_data = await self.get_room_data()
        players_data = await self.get_all_players_data()
        recent_messages = get_recent_messages(self.room_code, 50)
        
        await self.send(text_data=json.dumps({
            'event': 'room_state',
            'data': {
                'room': {
                    'code': self.room_code,
                    'owner': room_data['owner'],
                    'selected_game': room_data['selected_game'],
                    'rounds': room_data['rounds'],
                    'status': room_data['status'],
                    'created_at': room_data['created_at']
                },
                'players': players_data,
                'recent_messages': recent_messages
            }
        }))

    async def send_error(self, code, message):
        """Send error message to client"""
        await self.send(text_data=json.dumps({
            'event': 'error',
            'error': {
                'code': code,
                'message': message
            }
        }))

    # ============= Database Operations =============

    @database_sync_to_async
    def check_room_exists(self, room_code):
        return Room.objects.filter(code=room_code).exists()

    @database_sync_to_async
    def get_player_count(self, room_code):
        return Player.objects.filter(room__code=room_code).count()

    @database_sync_to_async
    def get_or_create_player(self):
        room = Room.objects.get(code=self.room_code)
        player, created = Player.objects.get_or_create(
            room=room,
            username=self.username,
            defaults={'gender': 'male', 'is_owner': room.owner == self.username}
        )
        return {
            'gender': player.gender,
            'avatar': player.avatar,
            'is_owner': player.is_owner
        }

    @database_sync_to_async
    def update_player_online_status(self, is_online):
        Player.objects.filter(room__code=self.room_code, username=self.username).update(is_online=is_online)

    @database_sync_to_async
    def save_message(self, message_type, content=None, voice_url=None, voice_duration=None, image_url=None, image_width=None, image_height=None):
        room = Room.objects.get(code=self.room_code)
        return Message.objects.create(
            room=room,
            sender=self.username,
            message_type=message_type,
            content=content,
            voice_url=voice_url,
            voice_duration=voice_duration,
            image_url=image_url,
            image_width=image_width,
            image_height=image_height
        )

    @database_sync_to_async
    def is_room_owner(self):
        room = Room.objects.get(code=self.room_code)
        return room.owner == self.username

    @database_sync_to_async
    def update_player_ready_status(self, ready):
        Player.objects.filter(room__code=self.room_code, username=self.username).update(is_ready=ready)

    @database_sync_to_async
    def check_game_exists(self, game_id):
        return Game.objects.filter(game_id=game_id, is_active=True).exists()

    @database_sync_to_async
    def update_room_game(self, game_id):
        Room.objects.filter(code=self.room_code).update(selected_game=game_id)

    @database_sync_to_async
    def update_room_rounds(self, rounds):
        Room.objects.filter(code=self.room_code).update(rounds=rounds)

    @database_sync_to_async
    def get_room_data(self):
        room = Room.objects.get(code=self.room_code)
        return {
            'owner': room.owner,
            'selected_game': room.selected_game,
            'rounds': room.rounds,
            'status': room.status,
            'created_at': room.created_at.isoformat()
        }

    @database_sync_to_async
    def get_all_players_data(self):
        players = Player.objects.filter(room__code=self.room_code)
        return {
            player.username: {
                'gender': player.gender,
                'avatar': player.avatar,
                'is_owner': player.is_owner,
                'is_ready': player.is_ready,
                'is_online': player.is_online
            }
            for player in players
        }

    @database_sync_to_async
    def get_game_details(self, game_id):
        game = Game.objects.get(game_id=game_id)
        return {
            'name': game.name,
            'image_url': game.image_url
        }

    @database_sync_to_async
    def check_all_players_ready(self):
        # Get all non-owner players
        not_ready = Player.objects.filter(
            room__code=self.room_code,
            is_owner=False,
            is_ready=False
        )
        return not not_ready.exists()

    @database_sync_to_async
    def create_game_session(self, game_id, rounds):
        room = Room.objects.get(code=self.room_code)
        game = Game.objects.get(game_id=game_id)
        session = GameSession.objects.create(
            room=room,
            game=game,
            total_rounds=rounds
        )
        # Update room status
        room.status = 'playing'
        room.save()
        return session.id

    @database_sync_to_async
    def create_reaction(self, message_id, emoji):
        message = Message.objects.get(id=message_id)
        reaction, created = MessageReaction.objects.get_or_create(
            message=message,
            user=self.username,
            emoji=emoji
        )
        return created

    @database_sync_to_async
    def delete_reaction(self, message_id, emoji):
        MessageReaction.objects.filter(
            message_id=message_id,
            user=self.username,
            emoji=emoji
        ).delete()
