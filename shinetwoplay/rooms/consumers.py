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
    reconnect_player, clear_disconnection_marker, get_connected_player_count,
    # Game state functions
    get_game_state, set_game_state, clear_game_state, game_state_exists
)

# Game handler imports
try:
    from games import get_handler, GAME_REGISTRY
except ImportError:
    get_handler = lambda x: None
    GAME_REGISTRY = {}


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
            
            # Check if player already exists in room (could be reconnecting)
            existing_player = player_exists(self.room_code, self.username)
            is_reconnecting = False
            player_data = None
            
            if existing_player:
                # Player exists - check if they're in grace period (disconnected but can reconnect)
                if is_player_in_grace_period(self.room_code, self.username):
                    # Reconnection - restore their connection
                    player_data = reconnect_player(self.room_code, self.username)
                    is_reconnecting = True
                else:
                    # Player exists and is connected - duplicate username
                    await self.close(code=4001)  # Duplicate username
                    return
            else:
                # New player - check room capacity
                if is_room_full(self.room_code):
                    await self.close(code=4003)  # Room full
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
                
                # Check if there's an active game
                game_state = get_game_state(self.room_code)
                if game_state:
                    # Remove from disconnected players
                    disconnected = game_state.get('disconnected_players', [])
                    if self.username in disconnected:
                        disconnected.remove(self.username)
                        game_state['disconnected_players'] = disconnected
                    
                    # If no one is disconnected anymore, resume game
                    if len(disconnected) == 0:
                        game_state['paused'] = False
                    
                    set_game_state(self.room_code, game_state)
                    
                    # Get game info
                    room_info = get_room_info(self.room_code)
                    game_id = room_info.get('selected_game', '')
                    total_rounds = int(room_info.get('rounds', 1))
                    
                    # Send game state to reconnecting player
                    handler = get_handler(game_id)
                    if handler:
                        try:
                            game_html = handler.get_template()
                            await self.send(text_data=json.dumps({
                                'event': 'game_loaded',
                                'data': {
                                    'game_id': game_id,
                                    'game_name': handler.game_name,
                                    'game_html': game_html,
                                    'game_state': game_state,
                                    'round': game_state.get('current_round', 1),
                                    'total_rounds': total_rounds
                                }
                            }))
                        except Exception as e:
                            print(f"Error sending game state on reconnect: {e}")
                    
                    # Broadcast game resumed to everyone
                    if not game_state.get('paused'):
                        await self.channel_layer.group_send(
                            self.room_group_name,
                            {
                                'type': 'broadcast_game_resumed',
                                'resumed_by': self.username,
                                'game_state': game_state
                            }
                        )
                
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
        Owner keeps ownership during grace period.
        If in a game, pause the game.
        """
        try:
            if hasattr(self, 'room_group_name') and hasattr(self, 'room_code') and hasattr(self, 'username'):
                # Mark player as disconnected (grace period) instead of removing
                mark_player_disconnected(self.room_code, self.username)
                
                # Add system message for disconnect
                add_system_message(
                    self.room_code,
                    f'{self.username} disconnected',
                    'disconnect'
                )
                
                # Check if in active game - if so, pause it
                game_state = get_game_state(self.room_code)
                if game_state:
                    # Update game state to paused
                    game_state['paused'] = True
                    game_state['disconnected_players'] = game_state.get('disconnected_players', [])
                    if self.username not in game_state['disconnected_players']:
                        game_state['disconnected_players'].append(self.username)
                    set_game_state(self.room_code, game_state)
                    
                    # Notify other player about game pause
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'broadcast_game_paused',
                            'paused_by': self.username,
                            'game_state': game_state,
                            'countdown': 30
                        }
                    )
                
                # Count connected players (excluding those in grace period)
                connected_count = get_connected_player_count(self.room_code)
                
                if connected_count > 0:
                    # Notify remaining players about disconnect (with grace period info)
                    # DO NOT transfer ownership - owner keeps it during grace period
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
                # Game events
                'game_move': self.handle_game_move,
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
        """Handle start game (owner only) - Now uses game handlers"""
        room_info = get_room_info(self.room_code)
        
        # Check owner
        if room_info.get('owner') != self.username:
            await self.send_error('NOT_OWNER', 'Only owner can start game')
            return
        
        # Check game selected
        game_id = room_info.get('selected_game')
        if not game_id:
            await self.send_error('NO_GAME', 'Select a game first')
            return
        
        # Check all players ready
        players = get_players(self.room_code)
        player_list = list(players.keys())
        
        for username, pdata in players.items():
            if username != room_info.get('owner') and not pdata.get('is_ready'):
                await self.send_error('NOT_READY', 'All players must be ready')
                return
        
        # Get game handler
        handler = get_handler(game_id)
        if not handler:
            # Fallback to old redirect behavior
            update_room_info(self.room_code, 'status', 'playing')
            add_system_message(self.room_code, 'Game started!', 'game_started')
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'broadcast_start_game',
                    'game': game_id,
                    'redirect_url': f'/games/{game_id}/{self.room_code}/'
                }
            )
            return
        
        # Initialize game using handler
        total_rounds = int(room_info.get('rounds', 1))
        game_state = handler.initialize(self.room_code, player_list, total_rounds)
        
        # Load game template
        try:
            game_html = handler.get_template()
        except FileNotFoundError as e:
            await self.send_error('GAME_TEMPLATE_ERROR', str(e))
            return
        
        # Update room status
        update_room_info(self.room_code, 'status', 'playing')
        
        # Add system message
        add_system_message(self.room_code, 'Game started!', 'game_started')
        
        # Broadcast game loaded with HTML and initial state
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'broadcast_game_loaded',
                'game_id': game_id,
                'game_name': handler.game_name,
                'game_html': game_html,
                'game_state': game_state,
                'round': 1,
                'total_rounds': total_rounds
            }
        )

    async def handle_game_move(self, data):
        """Handle game move from a player"""
        action = data.get('action')
        move_data = data.get('data', {})
        
        # Get current game state
        game_state = get_game_state(self.room_code)
        if not game_state:
            await self.send_error('NO_GAME', 'No active game')
            return
        
        # Check if game is paused
        if game_state.get('paused'):
            await self.send_error('GAME_PAUSED', 'Game is paused')
            return
        
        # Get room info and handler
        room_info = get_room_info(self.room_code)
        game_id = room_info.get('selected_game')
        handler = get_handler(game_id)
        
        if not handler:
            await self.send_error('NO_HANDLER', f'No handler for game: {game_id}')
            return
        
        # Process the move
        result = handler.handle_move(self.room_code, self.username, action, move_data)
        
        if result.get('error'):
            await self.send_error('INVALID_MOVE', result['error'])
            return
        
        new_state = result.get('state')
        
        import asyncio
        import time

        # Always broadcast the move logic first (so users see the last mark)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'broadcast_game_update',
                'game_state': new_state
            }
        )
        
        # Check for round end
        if result.get('round_ended'):
            # Don't sleep here - send immediately so it reaches everyone
            
            # Add timestamp for synced display
            current_time = int(time.time() * 1000)
            reveal_at = current_time + 1000  # Show 1 second from now
            
            # Broadcast round result
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'broadcast_round_ended',
                    'round_winner': result.get('round_winner'),
                    'scores': new_state.get('scores', {}),
                    'game_state': new_state,
                    'timestamp': current_time,
                    'reveal_at': reveal_at,     # <--- When to show overlay
                    'display_ms': 3000          # Show result for 3 seconds
                }
            )
            
            # Spawn background task for delayed game flow to unblock the consumer
            # This ensures the sender can receive the round_ended message immediately
            asyncio.create_task(self.game_flow_background_task(result, handler))

    async def game_flow_background_task(self, result, handler):
        """
        Handle delayed intervals between rounds/game end.
        Run in background to avoid blocking the WebSocket consumer receive loop.
        """
        try:
            import time
            import asyncio
            # Check for game end
            if result.get('game_ended'):
                # Wait for Reveal (1s) + Display (3s) = 4s total
                await asyncio.sleep(4)
                
                # Game completely ended
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'broadcast_game_ended',
                        'game_winner': result.get('game_winner'),
                        'final_scores': result.get('final_scores', {}),
                        'reason': 'completed',
                        'timestamp': int(time.time() * 1000),
                        'display_ms': 5000  # Show game over for 5 seconds
                    }
                )
                
                # Wait for game over screen
                await asyncio.sleep(5)
                
                # Reset room to waiting state
                update_room_info(self.room_code, 'status', 'waiting')
                
                # Reset player ready states
                players = get_players(self.room_code)
                for username in players.keys():
                    set_player_ready(self.room_code, username, False)
                
                # Clear game state
                clear_game_state(self.room_code)
                
                # Broadcast players not ready
                players = get_players(self.room_code)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'broadcast_players_not_ready',
                        'players': {k: v for k, v in players.items()}
                    }
                )
            else:
                # Start next round after delay
                # Wait for Reveal (1s) + Display (3s) = 4s total
                await asyncio.sleep(4)
                
                next_result = handler.start_next_round(self.room_code)
                next_state = next_result.get('state')
                
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'broadcast_round_started',
                        'round': next_state.get('current_round'),
                        'total_rounds': next_state.get('total_rounds'),
                        'game_state': next_state
                    }
                )
        except Exception as e:
            print(f"Error in game flow background task: {e}")

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
        
        # Add to kicked list (prevents rejoining)
        kick_player(self.room_code, target_user)
        
        # Clear any disconnection marker
        clear_disconnection_marker(self.room_code, target_user)
        
        # Remove player from room immediately
        remove_player(self.room_code, target_user)
        
        # Add system message
        add_system_message(
            self.room_code,
            f'{target_user} was kicked from the room',
            'player_kicked'
        )
        
        # Broadcast kick with updated player list
        players = get_players(self.room_code)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'broadcast_player_kicked',
                'user': target_user,
                'kicked_by': self.username,
                'players': {k: v for k, v in players.items()}
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
                'action': event['action'],
                'old_emoji': event.get('old_emoji')
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

    # ============= Game Broadcast Handlers =============

    async def broadcast_game_loaded(self, event):
        """Send game loaded event with HTML and initial state"""
        await self.send(text_data=json.dumps({
            'event': 'game_loaded',
            'data': {
                'game_id': event['game_id'],
                'game_name': event['game_name'],
                'game_html': event['game_html'],
                'game_state': event['game_state'],
                'round': event['round'],
                'total_rounds': event['total_rounds']
            }
        }))

    async def broadcast_game_update(self, event):
        """Send game state update"""
        await self.send(text_data=json.dumps({
            'event': 'game_update',
            'data': {
                'game_state': event['game_state']
            }
        }))

    async def broadcast_round_ended(self, event):
        """Send round ended event"""
        await self.send(text_data=json.dumps({
            'event': 'round_ended',
            'data': {
                'round_winner': event['round_winner'],
                'scores': event['scores'],
                'game_state': event['game_state'],
                'timestamp': event.get('timestamp'),
                'display_ms': event.get('display_ms', 2000)
            }
        }))

    async def broadcast_round_started(self, event):
        """Send round started event"""
        await self.send(text_data=json.dumps({
            'event': 'round_started',
            'data': {
                'round': event['round'],
                'total_rounds': event['total_rounds'],
                'game_state': event['game_state']
            }
        }))

    async def broadcast_game_ended(self, event):
        """Send game ended event"""
        await self.send(text_data=json.dumps({
            'event': 'game_ended',
            'data': {
                'game_winner': event['game_winner'],
                'final_scores': event['final_scores'],
                'reason': event.get('reason', 'completed'),
                'timestamp': event.get('timestamp'),
                'display_ms': event.get('display_ms', 3000)
            }
        }))

    async def broadcast_players_not_ready(self, event):
        """Send players not ready event after game ends"""
        await self.send(text_data=json.dumps({
            'event': 'players_not_ready',
            'data': {
                'players': event['players']
            }
        }))

    async def broadcast_game_paused(self, event):
        """Send game paused event when player disconnects"""
        await self.send(text_data=json.dumps({
            'event': 'game_paused',
            'data': {
                'paused_by': event['paused_by'],
                'game_state': event['game_state'],
                'countdown': event['countdown']
            }
        }))

    async def broadcast_game_resumed(self, event):
        """Send game resumed event when player reconnects"""
        await self.send(text_data=json.dumps({
            'event': 'game_resumed',
            'data': {
                'resumed_by': event['resumed_by'],
                'game_state': event['game_state']
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
