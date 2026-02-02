"""
Redis Client for ShineTwoPlay - Redis-Only Architecture

All room, player, and message data is stored temporarily in Redis.
No database storage except for Game catalog.

Key Schema:
- room:{code}:exists     - Room exists marker (STRING, TTL 1hr)
- room:{code}:info       - Room settings (HASH)
- room:{code}:players    - Players data (HASH: username -> JSON)
- room:{code}:messages   - Chat history (LIST, max 100)
- room:{code}:reactions:{msg_id} - Message reactions (HASH: emoji -> JSON array)
- room:{code}:media      - Media files for cleanup (SET)
"""

import redis
import json
import time
import uuid
import os
from django.conf import settings

# Initialize Redis client
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True
)

ROOM_TTL = 3600  # 1 hour
MAX_MESSAGES = 100


# ============= Room Functions =============

def create_room(code: str, owner: str, gender: str) -> dict:
    """
    Create a new room in Redis.
    Called by API when user creates a room.
    """
    avatar = '👨' if gender == 'male' else '👩'
    created_at = time.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    # Set room exists marker with TTL
    redis_client.setex(f'room:{code}:exists', ROOM_TTL, '1')
    
    # Set room info
    room_info = {
        'owner': owner,
        'selected_game': '',
        'rounds': '3',
        'status': 'waiting',
        'created_at': created_at
    }
    redis_client.hset(f'room:{code}:info', mapping=room_info)
    redis_client.expire(f'room:{code}:info', ROOM_TTL)
    
    return room_info


def room_exists(code: str) -> bool:
    """Check if room exists in Redis"""
    return redis_client.exists(f'room:{code}:exists') > 0


def get_room_info(code: str) -> dict:
    """Get room info from Redis"""
    return redis_client.hgetall(f'room:{code}:info')


def update_room_info(code: str, field: str, value: str):
    """Update a field in room info"""
    redis_client.hset(f'room:{code}:info', field, value)
    refresh_room_ttl(code)


def refresh_room_ttl(code: str):
    """Refresh TTL for all room-related keys"""
    redis_client.expire(f'room:{code}:exists', ROOM_TTL)
    redis_client.expire(f'room:{code}:info', ROOM_TTL)
    redis_client.expire(f'room:{code}:players', ROOM_TTL)
    redis_client.expire(f'room:{code}:messages', ROOM_TTL)


# ============= Player Functions =============

def add_player(code: str, username: str, gender: str, is_owner: bool = False) -> dict:
    """
    Add player to room.
    Called when WebSocket connects.
    """
    avatar = '👨' if gender == 'male' else '👩'
    
    player_data = {
        'gender': gender,
        'avatar': avatar,
        'is_owner': is_owner,
        'is_ready': False
    }
    
    # Store as JSON string in players hash
    redis_client.hset(f'room:{code}:players', username, json.dumps(player_data))
    redis_client.expire(f'room:{code}:players', ROOM_TTL)
    
    # Refresh room TTL
    refresh_room_ttl(code)
    
    return player_data


def remove_player(code: str, username: str):
    """
    Remove player from room.
    Called when WebSocket disconnects.
    """
    redis_client.hdel(f'room:{code}:players', username)


def get_player(code: str, username: str) -> dict:
    """Get single player data"""
    data = redis_client.hget(f'room:{code}:players', username)
    return json.loads(data) if data else None


def get_players(code: str) -> dict:
    """
    Get all players in room.
    Returns: {username: player_data, ...}
    """
    raw = redis_client.hgetall(f'room:{code}:players')
    return {username: json.loads(data) for username, data in raw.items()}


def get_player_count(code: str) -> int:
    """Get number of players in room"""
    return redis_client.hlen(f'room:{code}:players')


def is_room_full(code: str) -> bool:
    """Check if room has 2 players"""
    return get_player_count(code) >= 2


def player_exists(code: str, username: str) -> bool:
    """Check if player exists in room"""
    return redis_client.hexists(f'room:{code}:players', username)


def update_player(code: str, username: str, field: str, value):
    """Update a single field for a player"""
    player = get_player(code, username)
    if player:
        player[field] = value
        redis_client.hset(f'room:{code}:players', username, json.dumps(player))


def set_player_ready(code: str, username: str, is_ready: bool):
    """Set player ready status"""
    update_player(code, username, 'is_ready', is_ready)


# ============= Reconnection Functions =============
# Grace period: 30 seconds for player to reconnect
GRACE_PERIOD = 30

def mark_player_disconnected(code: str, username: str):
    """
    Mark player as disconnected but keep their data for grace period.
    Sets a marker key that expires after GRACE_PERIOD seconds.
    """
    # Set grace period marker
    redis_client.setex(f'room:{code}:disconnected:{username}', GRACE_PERIOD, '1')
    
    # Update player connection status
    update_player(code, username, 'is_connected', False)


def is_player_in_grace_period(code: str, username: str) -> bool:
    """Check if player is in reconnection grace period"""
    return redis_client.exists(f'room:{code}:disconnected:{username}') > 0


def reconnect_player(code: str, username: str) -> dict:
    """
    Reconnect a player who is in grace period.
    Returns the player data if successful, None if not in grace period.
    """
    # Check if player is in grace period
    if not is_player_in_grace_period(code, username):
        return None
    
    # Clear the disconnection marker
    redis_client.delete(f'room:{code}:disconnected:{username}')
    
    # Update player connection status
    update_player(code, username, 'is_connected', True)
    
    # Return player data
    return get_player(code, username)


def clear_disconnection_marker(code: str, username: str):
    """Clear the disconnection marker (used when fully removing player)"""
    redis_client.delete(f'room:{code}:disconnected:{username}')


def get_connected_player_count(code: str) -> int:
    """Get count of actually connected players (not in grace period)"""
    players = get_players(code)
    return sum(1 for p in players.values() if p.get('is_connected', True))


# ============= Owner Management Functions =============

def transfer_ownership(code: str, new_owner: str) -> bool:
    """
    Transfer room ownership to another player.
    Updates room info and player flags.
    Returns True if successful.
    """
    # Get current owner
    room_info = get_room_info(code)
    old_owner = room_info.get('owner')
    
    # Check new owner exists
    if not player_exists(code, new_owner):
        return False
    
    # Update room info
    update_room_info(code, 'owner', new_owner)
    
    # Update player flags
    if old_owner and player_exists(code, old_owner):
        update_player(code, old_owner, 'is_owner', False)
    update_player(code, new_owner, 'is_owner', True)
    
    return True


def get_next_owner(code: str, exclude_username: str = None) -> str:
    """
    Find a connected player to be new owner (exclude current owner).
    Returns username or None if no suitable player.
    """
    players = get_players(code)
    
    for username, data in players.items():
        if username != exclude_username:
            # Prefer connected players
            if data.get('is_connected', True):  # Default True for backward compat
                return username
    
    # If no connected player found, return any player (except excluded)
    for username in players.keys():
        if username != exclude_username:
            return username
    
    return None


def kick_player(code: str, username: str):
    """
    Add player to kicked list.
    Kicked players cannot rejoin this room.
    """
    redis_client.sadd(f'room:{code}:kicked', username)
    redis_client.expire(f'room:{code}:kicked', ROOM_TTL)


def is_player_kicked(code: str, username: str) -> bool:
    """Check if player was kicked from this room"""
    return redis_client.sismember(f'room:{code}:kicked', username)


def unkick_player(code: str, username: str):
    """Remove player from kicked list"""
    redis_client.srem(f'room:{code}:kicked', username)


# ============= Message Functions =============

def generate_message_id() -> str:
    """Generate unique message ID"""
    return f"msg_{uuid.uuid4().hex[:12]}"


def add_message(code: str, msg_type: str, sender: str, **kwargs) -> dict:
    """
    Add message to room.
    
    Types: text, voice, image, system
    
    For text: content="Hello"
    For voice: url="/media/...", duration=5.2
    For image: url="/media/..."
    For system: content="User joined", subtype="join"
    """
    msg_id = generate_message_id()
    timestamp = time.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    message = {
        'id': msg_id,
        'type': msg_type,
        'sender': sender,
        'timestamp': timestamp,
        'reactions': {}
    }
    
    # Add type-specific fields
    if msg_type == 'text':
        message['content'] = kwargs.get('content', '')
    elif msg_type == 'voice':
        message['url'] = kwargs.get('url', '')
        message['duration'] = kwargs.get('duration', 0)
    elif msg_type == 'image':
        message['url'] = kwargs.get('url', '')
    elif msg_type == 'system':
        message['content'] = kwargs.get('content', '')
        message['subtype'] = kwargs.get('subtype', '')
        message['sender'] = None  # System messages have no sender
    
    # Push to list (newest first)
    redis_client.lpush(f'room:{code}:messages', json.dumps(message))
    
    # Trim to max messages
    redis_client.ltrim(f'room:{code}:messages', 0, MAX_MESSAGES - 1)
    
    redis_client.expire(f'room:{code}:messages', ROOM_TTL)
    
    return message


def get_messages(code: str, count: int = 50) -> list:
    """
    Get recent messages from room.
    Returns newest first.
    """
    raw = redis_client.lrange(f'room:{code}:messages', 0, count - 1)
    messages = [json.loads(msg) for msg in raw]
    
    # Add reactions to each message
    for msg in messages:
        reactions = get_reactions(code, msg['id'])
        msg['reactions'] = reactions
    
    return messages


def add_text_message(code: str, sender: str, content: str) -> dict:
    """Convenience function for text messages"""
    return add_message(code, 'text', sender, content=content)


def add_voice_message(code: str, sender: str, url: str, duration: float) -> dict:
    """Convenience function for voice messages"""
    return add_message(code, 'voice', sender, url=url, duration=duration)


def add_image_message(code: str, sender: str, url: str) -> dict:
    """Convenience function for image messages"""
    return add_message(code, 'image', sender, url=url)


def add_system_message(code: str, content: str, subtype: str) -> dict:
    """Convenience function for system messages"""
    return add_message(code, 'system', None, content=content, subtype=subtype)


# ============= Reaction Functions =============
# Schema: room:{code}:reactions:{msg_id} - HASH: username -> emoji (one reaction per user)

def toggle_reaction(code: str, msg_id: str, emoji: str, username: str) -> dict:
    """
    Toggle reaction for a user on a message.
    Each user can only have ONE reaction per message.
    
    Returns: {action: 'added'|'removed'|'replaced', emoji: str, old_emoji: str|None}
    """
    key = f'room:{code}:reactions:{msg_id}'
    
    # Get user's current reaction on this message
    current_emoji = redis_client.hget(key, username)
    
    if current_emoji is None:
        # No reaction - add new one
        redis_client.hset(key, username, emoji)
        redis_client.expire(key, ROOM_TTL)
        return {'action': 'added', 'emoji': emoji, 'old_emoji': None}
    
    elif current_emoji == emoji:
        # Same emoji - remove reaction
        redis_client.hdel(key, username)
        return {'action': 'removed', 'emoji': emoji, 'old_emoji': emoji}
    
    else:
        # Different emoji - replace reaction
        old_emoji = current_emoji
        redis_client.hset(key, username, emoji)
        redis_client.expire(key, ROOM_TTL)
        return {'action': 'replaced', 'emoji': emoji, 'old_emoji': old_emoji}


def get_user_reaction(code: str, msg_id: str, username: str) -> str:
    """Get user's reaction on a message, or None if no reaction"""
    key = f'room:{code}:reactions:{msg_id}'
    return redis_client.hget(key, username)


def get_reactions(code: str, msg_id: str) -> dict:
    """
    Get all reactions for a message.
    Returns: {emoji: [usernames], ...} format for frontend compatibility
    """
    key = f'room:{code}:reactions:{msg_id}'
    raw = redis_client.hgetall(key)  # {username: emoji, ...}
    
    # Transform to {emoji: [users], ...} for frontend
    reactions = {}
    for username, emoji in raw.items():
        if emoji not in reactions:
            reactions[emoji] = []
        reactions[emoji].append(username)
    
    return reactions


# Keep legacy functions for backward compatibility but mark as deprecated
def add_reaction(code: str, msg_id: str, emoji: str, username: str):
    """DEPRECATED: Use toggle_reaction instead"""
    toggle_reaction(code, msg_id, emoji, username)


def remove_reaction(code: str, msg_id: str, emoji: str, username: str):
    """DEPRECATED: Use toggle_reaction instead"""
    key = f'room:{code}:reactions:{msg_id}'
    current = redis_client.hget(key, username)
    if current == emoji:
        redis_client.hdel(key, username)


# ============= Media Tracking =============

def track_media(code: str, filepath: str):
    """Track media file for cleanup when room is destroyed"""
    redis_client.sadd(f'room:{code}:media', filepath)
    redis_client.expire(f'room:{code}:media', ROOM_TTL)


def get_media_files(code: str) -> set:
    """Get all media files for a room"""
    return redis_client.smembers(f'room:{code}:media')


# ============= Room Destruction =============

def destroy_room(code: str):
    """
    Destroy room and clean up all data.
    Called when last player disconnects.
    """
    # Get media files to delete
    media_files = get_media_files(code)
    
    # Delete media files from disk
    for filepath in media_files:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            print(f"Error deleting media file {filepath}: {e}")
    
    # Get all reaction keys for this room
    reaction_keys = redis_client.keys(f'room:{code}:reactions:*')
    
    # Delete all room keys
    keys_to_delete = [
        f'room:{code}:exists',
        f'room:{code}:info',
        f'room:{code}:players',
        f'room:{code}:messages',
        f'room:{code}:media'
    ]
    keys_to_delete.extend(reaction_keys)
    
    if keys_to_delete:
        redis_client.delete(*keys_to_delete)
    
    print(f"Room {code} destroyed, deleted {len(media_files)} media files")


# ============= Typing Indicator (Optional) =============

def set_typing(code: str, username: str):
    """Set user as typing (expires in 3 seconds)"""
    redis_client.setex(f'room:{code}:typing:{username}', 3, '1')


def is_typing(code: str, username: str) -> bool:
    """Check if user is typing"""
    return redis_client.exists(f'room:{code}:typing:{username}') > 0


# ============= Rate Limiting =============

def check_rate_limit(key: str, limit: int, window: int) -> bool:
    """
    Check if rate limit is exceeded.
    Returns True if within limit, False if exceeded.
    """
    current = redis_client.get(key)
    
    if current is None:
        redis_client.setex(key, window, 1)
        return True
    
    if int(current) >= limit:
        return False
    
    redis_client.incr(key)
    return True
