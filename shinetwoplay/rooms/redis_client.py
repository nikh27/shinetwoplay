import redis
import json
import time
from django.conf import settings

# Initialize Redis client
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True
)


# ============= Room State Functions =============

def create_room_cache(room_code, owner, gender):
    """Create room state in Redis cache"""
    avatar = '👨' if gender == 'male' else '👩'
    room_data = {
        'owner': owner,
        'selected_game': '',
        'rounds': '1',
        'status': 'waiting',
        'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'last_activity': time.strftime('%Y-%m-%dT%H:%M:%SZ')
    }
    redis_client.hset(f'room:{room_code}', mapping=room_data)
    redis_client.expire(f'room:{room_code}', 3600)  # 1 hour TTL
    return room_data


def get_room_state(room_code):
    """Get room state from Redis"""
    return redis_client.hgetall(f'room:{room_code}')


def update_room_field(room_code, field, value):
    """Update a specific field in room state"""
    redis_client.hset(f'room:{room_code}', field, value)
    redis_client.hset(f'room:{room_code}', 'last_activity', time.strftime('%Y-%m-%dT%H:%M:%SZ'))
    redis_client.expire(f'room:{room_code}', 3600)  # Refresh TTL


def delete_room_cache(room_code):
    """Delete all room-related cache data"""
    keys_to_delete = [
        f'room:{room_code}',
        f'room:{room_code}:players',
        f'room:{room_code}:messages',
        f'room:{room_code}:typing',
        f'room:{room_code}:online',
        f'ws:connections:{room_code}'
    ]
    redis_client.delete(*keys_to_delete)
    
    # Delete player session data
    players = redis_client.smembers(f'room:{room_code}:players')
    for player in players:
        redis_client.delete(f'player:{player}:{room_code}')


# ============= Player Functions =============

def add_player_to_room(room_code, username, gender):
    """Add player to room in Redis"""
    avatar = '👨' if gender == 'male' else '👩'
    
    # Add to players set
    redis_client.sadd(f'room:{room_code}:players', username)
    redis_client.expire(f'room:{room_code}:players', 3600)
    
    # Create player session
    player_data = {
        'gender': gender,
        'avatar': avatar,
        'is_owner': 'false',
        'is_ready': 'false',
        'is_online': 'true',
        'last_seen': time.strftime('%Y-%m-%dT%H:%M:%SZ')
    }
    redis_client.hset(f'player:{username}:{room_code}', mapping=player_data)
    redis_client.expire(f'player:{username}:{room_code}', 1800)  # 30 min TTL
    
    return player_data


def remove_player_from_room(room_code, username):
    """Remove player from room"""
    redis_client.srem(f'room:{room_code}:players', username)
    redis_client.delete(f'player:{username}:{room_code}')
    redis_client.zrem(f'room:{room_code}:online', username)
    redis_client.srem(f'room:{room_code}:typing', username)


def get_room_players(room_code):
    """Get all players in a room"""
    return redis_client.smembers(f'room:{room_code}:players')


def is_room_full(room_code):
    """Check if room has reached max capacity (2 players)"""
    return redis_client.scard(f'room:{room_code}:players') >= 2


def update_player_status(room_code, username, field, value):
    """Update player status field"""
    redis_client.hset(f'player:{username}:{room_code}', field, value)
    redis_client.hset(f'player:{username}:{room_code}', 'last_seen', time.strftime('%Y-%m-%dT%H:%M:%SZ'))
    redis_client.expire(f'player:{username}:{room_code}', 1800)


def get_player_data(room_code, username):
    """Get player session data"""
    return redis_client.hgetall(f'player:{username}:{room_code}')


# ============= Message Cache Functions =============

def cache_message(room_code, message_data):
    """Cache message in Redis (keep last 100)"""
    message_json = json.dumps(message_data)
    timestamp = int(time.time() * 1000)
    redis_client.zadd(f'room:{room_code}:messages', {message_json: timestamp})
    redis_client.expire(f'room:{room_code}:messages', 86400)  # 24 hours
    
    # Trim to keep only last 100 messages
    redis_client.zremrangebyrank(f'room:{room_code}:messages', 0, -101)


def get_recent_messages(room_code, limit=50):
    """Get recent messages from cache"""
    messages = redis_client.zrevrange(f'room:{room_code}:messages', 0, limit - 1)
    return [json.loads(msg) for msg in messages]


# ============= Typing Indicator Functions =============

def set_typing(room_code, username):
    """Set user as typing"""
    redis_client.sadd(f'room:{room_code}:typing', username)
    redis_client.expire(f'room:{room_code}:typing', 5)  # 5 seconds TTL


def remove_typing(room_code, username):
    """Remove user from typing"""
    redis_client.srem(f'room:{room_code}:typing', username)


def get_typing_users(room_code):
    """Get users currently typing"""
    return redis_client.smembers(f'room:{room_code}:typing')


# ============= Online Status Functions =============

def update_online_status(room_code, username):
    """Update user's online status"""
    timestamp = int(time.time())
    redis_client.zadd(f'room:{room_code}:online', {username: timestamp})
    redis_client.expire(f'room:{room_code}:online', 3600)


def get_online_users(room_code, threshold=30):
    """Get users online in last N seconds"""
    cutoff = int(time.time()) - threshold
    return redis_client.zrangebyscore(f'room:{room_code}:online', cutoff, '+inf')


def remove_offline_users(room_code, threshold=30):
    """Remove users offline for more than N seconds"""
    cutoff = int(time.time()) - threshold
    redis_client.zremrangebyscore(f'room:{room_code}:online', 0, cutoff)


# ============= Rate Limiting Functions =============

def check_rate_limit(key, limit, window):
    """Check if rate limit is exceeded"""
    current = redis_client.get(key)
    
    if current is None:
        redis_client.setex(key, window, 1)
        return True
    
    if int(current) >= limit:
        return False
    
    redis_client.incr(key)
    return True


def get_rate_limit_remaining(key):
    """Get remaining requests for rate limit key"""
    current = redis_client.get(key)
    return int(current) if current else 0


# ============= WebSocket Connection Tracking =============

def add_ws_connection(room_code, username):
    """Add WebSocket connection"""
    redis_client.sadd(f'ws:connections:{room_code}', username)


def remove_ws_connection(room_code, username):
    """Remove WebSocket connection"""
    redis_client.srem(f'ws:connections:{room_code}', username)


def get_active_connections(room_code):
    """Get active WebSocket connections"""
    return redis_client.smembers(f'ws:connections:{room_code}')


# ============= Utility Functions =============

def room_exists(room_code):
    """Check if room exists in Redis"""
    return redis_client.exists(f'room:{room_code}') > 0


def refresh_room_ttl(room_code):
    """Refresh TTL for room and related keys"""
    redis_client.expire(f'room:{room_code}', 3600)
    redis_client.expire(f'room:{room_code}:players', 3600)
    redis_client.expire(f'room:{room_code}:online', 3600)


def get_redis_stats():
    """Get Redis statistics"""
    info = redis_client.info()
    return {
        'total_keys': redis_client.dbsize(),
        'memory_used': info.get('used_memory_human'),
        'connected_clients': info.get('connected_clients'),
    }
