"""
WebSocket Consumer for ShineTwoPlay - Redis-Only Architecture

All room, player, and message data is stored in Redis.
No database queries except for Game catalog.

Key Events:
- chat: Text message
- voice_message: Voice recording
- image_message: Image upload
- typing/stop_typing: Typing indicator
- ready: Player ready toggle
- select_game: Game selection (owner only)
- round_change: Round count change (owner only)
- start_game: Start game (owner only)
- react_message/remove_reaction: Message reactions
- sync_state: Request room state sync
- ping: Heartbeat
"""

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import json
import time
from urllib.parse import parse_qs

from .models import Game
from .redis_client import (
    room_exists, get_room_info, get_players, get_player_count,
    is_room_full, player_exists, add_player, remove_player,
    update_room_info, refresh_room_ttl, set_player_ready,
    add_text_message, add_voice_message, add_image_message,
    add_system_message, get_messages, toggle_reaction,
    destroy_room, set_typing, check_rate_limit, get_player,
    update_player, transfer_ownership, get_next_owner,
    kick_player, is_player_kicked,
    # Reconnection functions
    mark_player_disconnected, is_player_in_grace_period,
    reconnect_player, clear_disconnection_marker, get_connected_player_count
)


class RoomConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for room communication.
    All data stored in Redis - no database queries for room/player/message.
    """

    async def connect(self):
        """Handle WebSocket connection"""
        try:
            # Get room code from URL
            self.room_code = self.scope['url_route']['kwargs']['room_code']
            
            # Parse query string for username and gender
            query_string = self.scope['query_string'].decode()
            params = parse_qs(query_string)
            self.username = params.get('name', ['Guest'])[0]
            self.gender = params.get('gender', ['male'])[0]
            
            # Validate username
            if len(self.username) > 8:
                await self.close(code=4000)  # Username too long
                return
            
            # Check room exists in Redis
            if not room_exists(self.room_code):
                await self.close(code=4004)  # Room not found
                return
            
            # Check if player was kicked from this room
            if is_player_kicked(self.room_code, self.username):
                await self.close(code=4005)  # Player was kicked
                return
            
            # Check if this is a reconnection (player in grace period)
            is_reconnecting = is_player_in_grace_period(self.room_code, self.username)
            
            if is_reconnecting:
                # Reconnection - player exists but was disconnected
                player_data = reconnect_player(self.room_code, self.username)
                if not player_data:
                    # Grace period expired, treat as new connection
                    is_reconnecting = False
            
            if not is_reconnecting:
                # New connection - check room capacity and duplicate username
                if is_room_full(self.room_code):
                    await self.close(code=4003)  # Room full
                    return
                
                # Check duplicate username (only for new connections)
                if player_exists(self.room_code, self.username):
                    await self.close(code=4001)  # Duplicate username
                    return
            
            # Accept connection
            await self.accept()
            
            # Set up room group
            self.room_group_name = f'room_{self.room_code}'
            
            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            
            if is_reconnecting:
                # Reconnection - use existing player data
                is_owner = player_data.get('is_owner', False)
                
                # Add system message for reconnection
                add_system_message(
                    self.room_code,
                    f'{self.username} reconnected',
                    'reconnect'
                )
                
                # Send room state
                await self.send_room_state()
                
                # Notify others about reconnection
                players = get_players(self.room_code)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'broadcast_player_reconnected',
                        'user': self.username,
                        'players': {k: v for k, v in players.items()}
                    }
                )
            else:
                # New connection
                # Check if first player (owner)
                player_count = get_player_count(self.room_code)
                is_owner = player_count == 0
                
                # Add player to Redis
                player_data = add_player(
                    self.room_code,
                    self.username,
                    self.gender,
                    is_owner=is_owner
                )
                
                # Set is_connected flag
                update_player(self.room_code, self.username, 'is_connected', True)
                
                # Add system message for join
                add_system_message(
                    self.room_code,
                    f'{self.username} joined the room',
                    'join'
                )
                
                # Send room state to this user
                await self.send_room_state()
                
                # Notify others about new player
                players = get_players(self.room_code)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'player_join',
                        'user': self.username,
                        'gender': self.gender,
                        'avatar': player_data['avatar'],
                        'is_owner': is_owner,
                        'players': {k: v for k, v in players.items()}
                    }
                )
            
        except Exception as e:
            print(f"Connection error: {e}")
            import traceback
            traceback.print_exc()
            await self.close(code=4500)

    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection with grace period for reconnection.
        Player data is kept for 30 seconds to allow reconnection.
        """
        try:
            if hasattr(self, 'room_group_name') and hasattr(self, 'room_code') and hasattr(self, 'username'):
                # Check if disconnecting player is owner
                room_info = get_room_info(self.room_code)
                is_owner = room_info.get('owner') == self.username
                
                # Mark player as disconnected (grace period) instead of removing
                mark_player_disconnected(self.room_code, self.username)
                
                # Add system message for disconnect (temporary)
                add_system_message(
                    self.room_code,
                    f'{self.username} disconnected',
                    'disconnect'
                )
                
                # Count connected players (excluding those in grace period)
                connected_count = get_connected_player_count(self.room_code)
                
                if connected_count == 0:
                    # No connected players - but don't destroy yet, wait for grace period
                    # Room will be cleaned up by Redis TTL if no one reconnects
                    pass
                else:
                    # Auto-transfer ownership if owner left and other connected player exists
                    if is_owner:
                        new_owner = get_next_owner(self.room_code, self.username)
                        if new_owner:
                            # Check if new owner is actually connected
                            new_owner_data = get_player(self.room_code, new_owner)
                            if new_owner_data and new_owner_data.get('is_connected', True):
                                transfer_ownership(self.room_code, new_owner)
                                
                                # Add system message for ownership transfer
                                add_system_message(
                                    self.room_code,
                                    f'{new_owner} is now the room owner',
                                    'owner_changed'
                                )
                                
                                # Broadcast ownership change
                                players = get_players(self.room_code)
                                await self.channel_layer.group_send(
                                    self.room_group_name,
                                    {
                                        'type': 'broadcast_owner_changed',
                                        'old_owner': self.username,
                                        'new_owner': new_owner,
                                        'players': {k: v for k, v in players.items()}
                                    }
                                )
                    
                    # Notify remaining players about disconnect (with grace period info)
                    players = get_players(self.room_code)
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'broadcast_player_disconnecting',
                            'user': self.username,
                            'grace_period': 30,  # seconds
                            'players': {k: v for k, v in players.items()}
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
            
            # Refresh room TTL on activity
            refresh_room_ttl(self.room_code)
            
            # Route to handler
            handlers = {
                'chat': self.handle_chat,
                'voice_message': self.handle_voice_message,
                'image_message': self.handle_image_message,
                'typing': self.handle_typing,
                'stop_typing': self.handle_stop_typing,
                'ready': self.handle_ready,
                'select_game': self.handle_select_game,
                'round_change': self.handle_round_change,
                'start_game': self.handle_start_game,
                'react_message': self.handle_react_message,
                'remove_reaction': self.handle_remove_reaction,
                'sync_state': self.handle_sync_state,
                'ping': self.handle_ping,
                'recording_voice': self.handle_recording_indicator,
                'uploading_image': self.handle_uploading_indicator,
                # Owner management events
                'transfer_ownership': self.handle_transfer_ownership,
                'kick_player': self.handle_kick_player,
            }
            
            handler = handlers.get(event)
            if handler:
                await handler(data)
            else:
                await self.send_error('INVALID_EVENT', f'Unknown event: {event}')
                
        except json.JSONDecodeError:
            await self.send_error('INVALID_JSON', 'Invalid JSON format')
        except Exception as e:
            print(f"Receive error: {e}")
            await self.send_error('SERVER_ERROR', str(e))

    # ============= Event Handlers =============

    async def handle_chat(self, data):
        """Handle text chat message"""
        content = data.get('msg', '').strip()
        temp_id = data.get('temp_id')
        
        if not content or len(content) > 500:
            await self.send_error('INVALID_MESSAGE', 'Message must be 1-500 characters')
            return
        
        # Rate limit (10 per 10 seconds)
        if not check_rate_limit(f'chat:{self.username}', 10, 10):
            await self.send_error('RATE_LIMIT', 'Too many messages')
            return
        
        # Add message to Redis
        message = add_text_message(self.room_code, self.username, content)
        
        # Send confirmation
        if temp_id:
            await self.send(text_data=json.dumps({
                'event': 'message_confirmed',
                'temp_id': temp_id,
                'message_id': message['id']
            }))
        
        # Broadcast
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'broadcast_chat',
                'message': message
            }
        )

    async def handle_voice_message(self, data):
        """Handle voice message"""
        url = data.get('url')
        duration = data.get('duration', 0)
        
        if not url:
            await self.send_error('INVALID_DATA', 'url required')
            return
        
        if duration > 60:
            await self.send_error('INVALID_DURATION', 'Max 60 seconds')
            return
        
        # Rate limit (5 per minute)
        if not check_rate_limit(f'voice:{self.username}', 5, 60):
            await self.send_error('RATE_LIMIT', 'Too many voice messages')
            return
        
        # Add message to Redis
        message = add_voice_message(self.room_code, self.username, url, duration)
        
        # Broadcast
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'broadcast_voice',
                'message': message
            }
        )

    async def handle_image_message(self, data):
        """Handle image message"""
        url = data.get('url')
        
        if not url:
            await self.send_error('INVALID_DATA', 'url required')
            return
        
        # Rate limit (10 per minute)
        if not check_rate_limit(f'image:{self.username}', 10, 60):
            await self.send_error('RATE_LIMIT', 'Too many images')
            return
        
        # Add message to Redis
        message = add_image_message(self.room_code, self.username, url)
        
        # Broadcast
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'broadcast_image',
                'message': message
            }
        )

    async def handle_typing(self, data):
        """Handle typing indicator"""
        set_typing(self.room_code, self.username)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'broadcast_typing',
                'user': self.username
            }
        )

    async def handle_stop_typing(self, data):
        """Handle stop typing"""
        pass  # Typing auto-expires

    async def handle_ready(self, data):
        """Handle ready state toggle"""
        ready = data.get('ready', False)
        
        # Check if owner (owners don't toggle ready)
        room_info = get_room_info(self.room_code)
        if room_info.get('owner') == self.username:
            await self.send_error('NOT_ALLOWED', 'Owner cannot set ready state')
            return
        
        # Update ready state in Redis
        set_player_ready(self.room_code, self.username, ready)
        
        # Broadcast
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'broadcast_ready',
                'user': self.username,
                'ready': ready
            }
        )

    async def handle_select_game(self, data):
        """Handle game selection (owner only)"""
        game_id = data.get('game')
        
        # Check owner
        room_info = get_room_info(self.room_code)
        if room_info.get('owner') != self.username:
            await self.send_error('NOT_OWNER', 'Only owner can select game')
            return
        
        # Validate game exists in database
        game = await self.get_game(game_id)
        if not game:
            await self.send_error('GAME_NOT_FOUND', 'Game does not exist')
            return
        
        # Update in Redis
        update_room_info(self.room_code, 'selected_game', game_id)
        
        # Add system message
        add_system_message(
            self.room_code,
            f'Game selected: {game["name"]}',
            'game_selected'
        )
        
        # Broadcast
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'broadcast_game_selected',
                'game_id': game_id,
                'game_name': game['name'],
                'image_url': game['image_url']
            }
        )

    async def handle_round_change(self, data):
        """Handle round change (owner only)"""
        rounds = data.get('round')
        
        # Check owner
        room_info = get_room_info(self.room_code)
        if room_info.get('owner') != self.username:
            await self.send_error('NOT_OWNER', 'Only owner can change rounds')
            return
        
        # Validate rounds
        if rounds not in [1, 3, 5]:
            await self.send_error('INVALID_ROUNDS', 'Rounds must be 1, 3, or 5')
            return
        
        # Update in Redis
        update_room_info(self.room_code, 'rounds', str(rounds))
        
        # Broadcast
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'broadcast_round_update',
                'rounds': rounds
            }
        )

    async def handle_start_game(self, data):
        """Handle start game (owner only)"""
        room_info = get_room_info(self.room_code)
        
        # Check owner
        if room_info.get('owner') != self.username:
            await self.send_error('NOT_OWNER', 'Only owner can start game')
            return
        
        # Check game selected
        if not room_info.get('selected_game'):
            await self.send_error('NO_GAME', 'Select a game first')
            return
        
        # Check all players ready
        players = get_players(self.room_code)
        for username, pdata in players.items():
            if username != room_info.get('owner') and not pdata.get('is_ready'):
                await self.send_error('NOT_READY', 'All players must be ready')
                return
        
        # Update status
        update_room_info(self.room_code, 'status', 'playing')
        
        # Add system message
        add_system_message(self.room_code, 'Game started!', 'game_started')
        
        game_id = room_info.get('selected_game')
        
        # Broadcast
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'broadcast_start_game',
                'game': game_id,
                'redirect_url': f'/games/{game_id}/{self.room_code}/'
            }
        )

    async def handle_react_message(self, data):
        """
        Handle message reaction toggle.
        One reaction per user per message:
        - Click emoji: add if none, remove if same, replace if different
        """
        msg_id = data.get('message_id')
        emoji = data.get('emoji')
        
        if not msg_id or not emoji:
            await self.send_error('INVALID_DATA', 'message_id and emoji required')
            return
        
        # Rate limit
        if not check_rate_limit(f'react:{self.username}', 20, 60):
            await self.send_error('RATE_LIMIT', 'Too many reactions')
            return
        
        # Toggle reaction in Redis - returns {action, emoji, old_emoji}
        result = toggle_reaction(self.room_code, msg_id, emoji, self.username)
        
        # Broadcast the reaction change
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'broadcast_reaction',
                'message_id': msg_id,
                'user': self.username,
                'emoji': emoji,
                'action': result['action'],  # 'added', 'removed', or 'replaced'
                'old_emoji': result.get('old_emoji')  # For 'replaced' action
            }
        )

    async def handle_remove_reaction(self, data):
        """
        Handle explicit remove reaction (backward compatibility).
        Just calls toggle_reaction with the same emoji to remove it.
        """
        msg_id = data.get('message_id')
        emoji = data.get('emoji')
        
        if not msg_id or not emoji:
            return
        
        # Toggle will remove if same emoji
        result = toggle_reaction(self.room_code, msg_id, emoji, self.username)
        
        # Broadcast
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'broadcast_reaction',
                'message_id': msg_id,
                'user': self.username,
                'emoji': emoji,
                'action': result['action'],
                'old_emoji': result.get('old_emoji')
            }
        )

    async def handle_sync_state(self, data):
        """Handle state sync request"""
        await self.send_room_state()

    async def handle_ping(self, data):
        """Handle heartbeat"""
        await self.send(text_data=json.dumps({'event': 'pong'}))

    async def handle_recording_indicator(self, data):
        """Handle recording indicator"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'broadcast_recording',
                'user': self.username
            }
        )

    async def handle_uploading_indicator(self, data):
        """Handle uploading indicator"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'broadcast_uploading',
                'user': self.username
            }
        )

    # ============= Owner Management Handlers =============

    async def handle_transfer_ownership(self, data):
        """
        Handle ownership transfer (owner only).
        Transfer room ownership to another player.
        """
        target_user = data.get('target_user')
        
        if not target_user:
            await self.send_error('INVALID_DATA', 'target_user required')
            return
        
        # Check if current user is owner
        room_info = get_room_info(self.room_code)
        if room_info.get('owner') != self.username:
            await self.send_error('NOT_OWNER', 'Only owner can transfer ownership')
            return
        
        # Check target exists
        if not player_exists(self.room_code, target_user):
            await self.send_error('PLAYER_NOT_FOUND', 'Target player not in room')
            return
        
        # Transfer ownership
        if transfer_ownership(self.room_code, target_user):
            # Add system message
            add_system_message(
                self.room_code,
                f'{target_user} is now the room owner',
                'owner_changed'
            )
            
            # Broadcast ownership change
            players = get_players(self.room_code)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'broadcast_owner_changed',
                    'old_owner': self.username,
                    'new_owner': target_user,
                    'players': {k: v for k, v in players.items()}
                }
            )

    async def handle_kick_player(self, data):
        """
        Handle kick player (owner only).
        Kicks player from room - they cannot rejoin.
        """
        target_user = data.get('target_user')
        
        if not target_user:
            await self.send_error('INVALID_DATA', 'target_user required')
            return
        
        # Check if current user is owner
        room_info = get_room_info(self.room_code)
        if room_info.get('owner') != self.username:
            await self.send_error('NOT_OWNER', 'Only owner can kick players')
            return
        
        # Can't kick yourself
        if target_user == self.username:
            await self.send_error('INVALID_ACTION', 'Cannot kick yourself')
            return
        
        # Check target exists
        if not player_exists(self.room_code, target_user):
            await self.send_error('PLAYER_NOT_FOUND', 'Target player not in room')
            return
        
        # Add to kicked list
        kick_player(self.room_code, target_user)
        
        # Add system message
        add_system_message(
            self.room_code,
            f'{target_user} was kicked from the room',
            'player_kicked'
        )
        
        # Broadcast kick (the kicked player's WebSocket will receive this and should disconnect)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'broadcast_player_kicked',
                'user': target_user,
                'kicked_by': self.username
            }
        )

    # ============= Broadcast Handlers =============

    async def player_join(self, event):
        """Send player join event"""
        await self.send(text_data=json.dumps({
            'event': 'player_join',
            'data': {
                'user': event['user'],
                'gender': event['gender'],
                'avatar': event['avatar'],
                'is_owner': event['is_owner'],
                'players': event['players']
            }
        }))

    async def player_disconnect(self, event):
        """Send player disconnect event"""
        await self.send(text_data=json.dumps({
            'event': 'player_disconnect',
            'data': {
                'user': event['user'],
                'players': event['players']
            }
        }))

    async def broadcast_chat(self, event):
        """Send chat message"""
        await self.send(text_data=json.dumps({
            'event': 'chat',
            'data': event['message']
        }))

    async def broadcast_voice(self, event):
        """Send voice message"""
        await self.send(text_data=json.dumps({
            'event': 'voice_message',
            'data': event['message']
        }))

    async def broadcast_image(self, event):
        """Send image message"""
        await self.send(text_data=json.dumps({
            'event': 'image_message',
            'data': event['message']
        }))

    async def broadcast_typing(self, event):
        """Send typing indicator"""
        if event['user'] != self.username:  # Don't send to self
            await self.send(text_data=json.dumps({
                'event': 'typing',
                'data': {'user': event['user']}
            }))

    async def broadcast_ready(self, event):
        """Send ready state update"""
        await self.send(text_data=json.dumps({
            'event': 'ready_state',
            'data': {
                'user': event['user'],
                'ready': event['ready']
            }
        }))

    async def broadcast_game_selected(self, event):
        """Send game selected event"""
        await self.send(text_data=json.dumps({
            'event': 'game_selected',
            'data': {
                'game_id': event['game_id'],
                'game_name': event['game_name'],
                'image_url': event['image_url']
            }
        }))

    async def broadcast_round_update(self, event):
        """Send round update"""
        await self.send(text_data=json.dumps({
            'event': 'round_update',
            'data': {'rounds': event['rounds']}
        }))

    async def broadcast_start_game(self, event):
        """Send start game event"""
        await self.send(text_data=json.dumps({
            'event': 'start_game',
            'data': {
                'game': event['game'],
                'redirect_url': event['redirect_url']
            }
        }))

    async def broadcast_reaction(self, event):
        """Send reaction event"""
        await self.send(text_data=json.dumps({
            'event': 'message_reaction',
            'data': {
                'message_id': event['message_id'],
                'user': event['user'],
                'emoji': event['emoji'],
                'action': event['action']
            }
        }))

    async def broadcast_recording(self, event):
        """Send recording indicator"""
        if event['user'] != self.username:
            await self.send(text_data=json.dumps({
                'event': 'recording_voice',
                'data': {'user': event['user']}
            }))

    async def broadcast_uploading(self, event):
        """Send uploading indicator"""
        if event['user'] != self.username:
            await self.send(text_data=json.dumps({
                'event': 'uploading_image',
                'data': {'user': event['user']}
            }))

    async def broadcast_owner_changed(self, event):
        """Send ownership change event"""
        await self.send(text_data=json.dumps({
            'event': 'owner_changed',
            'data': {
                'old_owner': event['old_owner'],
                'new_owner': event['new_owner'],
                'players': event['players']
            }
        }))

    async def broadcast_player_kicked(self, event):
        """
        Send player kicked event.
        The kicked player should disconnect when they receive this.
        """
        await self.send(text_data=json.dumps({
            'event': 'player_kicked',
            'data': {
                'user': event['user'],
                'kicked_by': event['kicked_by'],
                'should_disconnect': event['user'] == self.username
            }
        }))

    async def broadcast_player_disconnecting(self, event):
        """
        Send player disconnecting event with grace period.
        Frontend can show 'reconnecting...' status for this player.
        """
        if event['user'] != self.username:  # Don't send to the disconnecting user
            await self.send(text_data=json.dumps({
                'event': 'player_disconnecting',
                'data': {
                    'user': event['user'],
                    'grace_period': event['grace_period'],
                    'players': event['players']
                }
            }))

    async def broadcast_player_reconnected(self, event):
        """
        Send player reconnected event.
        Frontend can update player status from 'reconnecting' to 'connected'.
        """
        await self.send(text_data=json.dumps({
            'event': 'player_reconnected',
            'data': {
                'user': event['user'],
                'players': event['players']
            }
        }))

    # ============= Helper Methods =============

    async def send_room_state(self):
        """Send complete room state to client"""
        room_info = get_room_info(self.room_code)
        players = get_players(self.room_code)
        messages = get_messages(self.room_code, 50)
        
        await self.send(text_data=json.dumps({
            'event': 'room_state',
            'data': {
                'room': {
                    'code': self.room_code,
                    'owner': room_info.get('owner', ''),
                    'selected_game': room_info.get('selected_game', ''),
                    'rounds': int(room_info.get('rounds', 3)),
                    'status': room_info.get('status', 'waiting')
                },
                'players': players,
                'messages': messages
            }
        }))

    async def send_error(self, code, message):
        """Send error message"""
        await self.send(text_data=json.dumps({
            'event': 'error',
            'error': {
                'code': code,
                'message': message
            }
        }))

    @database_sync_to_async
    def get_game(self, game_id):
        """Get game from database (static catalog)"""
        try:
            game = Game.objects.get(game_id=game_id, is_active=True)
            return {
                'game_id': game.game_id,
                'name': game.name,
                'image_url': game.image_url,
                'description': game.description
            }
        except Game.DoesNotExist:
            return None
