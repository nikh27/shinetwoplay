from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from PIL import Image
import json
import os
import time
from datetime import datetime

from .models import Room, Player, Message, MessageReaction, Game, GameSession
from .utils import (
    success_response, error_response, generate_room_code, 
    get_avatar_for_gender, get_client_ip
)
from .validators import (
    validate_username, validate_gender, validate_room_code,
    validate_file_type, validate_file_size, validate_message_content,
    validate_voice_duration, validate_rounds
)
from .redis_client import (
    create_room_cache, add_player_to_room, is_room_full,
    get_room_state, get_room_players, check_rate_limit
)


# ============= Template Views (Existing) =============

def home(request):
    """Home page"""
    return render(request, "home.html")


def create_room_view(request):
    """Create room (old template-based view)"""
    name = request.GET.get("name", "Guest")
    code = generate_room_code()
    return redirect(f"/rooms/{code}/?name={name}")


def room_page(request, code):
    """Room page"""
    name = request.GET.get("name", "")
    
    if not name:
        return redirect("/")
    
    return render(request, "room.html", {
        "room": code,
        "username": name
    })


# ============= Room Management API =============

@csrf_exempt
@require_http_methods(["POST"])
def api_create_room(request):
    """
    POST /api/rooms/create
    Create a new room
    """
    try:
        data = json.loads(request.body)
        username = data.get('username')
        gender = data.get('gender')
        
        # Validate username
        is_valid, error_msg = validate_username(username)
        if not is_valid:
            return error_response('INVALID_USERNAME', error_msg)
        
        # Validate gender
        is_valid, error_msg = validate_gender(gender)
        if not is_valid:
            return error_response('INVALID_GENDER', error_msg)
        
        # Check rate limit (5 per hour per IP)
        ip = get_client_ip(request)
        if not check_rate_limit(f'ratelimit:create_room:{ip}', 5, 3600):
            return error_response('RATE_LIMIT_EXCEEDED', 'Too many room creations. Please try again later.', status=429)
        
        # Generate unique room code
        room_code = generate_room_code()
        while Room.objects.filter(code=room_code).exists():
            room_code = generate_room_code()
        
        # Create room in database
        room = Room.objects.create(
            code=room_code,
            owner=username,
            status='waiting'
        )
        
        # Create owner as player
        avatar = get_avatar_for_gender(gender)
        Player.objects.create(
            room=room,
            username=username,
            gender=gender,
            avatar=avatar,
            is_owner=True
        )
        
        # Create room in Redis cache
        create_room_cache(room_code, username, gender)
        add_player_to_room(room_code, username, gender)
        
        return success_response({
            'room_code': room_code,
            'owner': username,
            'created_at': room.created_at.isoformat(),
            'redirect_url': f'/rooms/{room_code}/?name={username}'
        }, status=201)
        
    except json.JSONDecodeError:
        return error_response('INVALID_JSON', 'Invalid JSON in request body')
    except Exception as e:
        return error_response('SERVER_ERROR', str(e), status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_join_room(request):
    """
    POST /api/rooms/join
    Join an existing room
    """
    try:
        data = json.loads(request.body)
        room_code = data.get('room_code')
        username = data.get('username')
        gender = data.get('gender')
        
        # Validate room code
        is_valid, error_msg = validate_room_code(room_code)
        if not is_valid:
            return error_response('INVALID_ROOM_CODE', error_msg)
        
        # Validate username
        is_valid, error_msg = validate_username(username)
        if not is_valid:
            return error_response('INVALID_USERNAME', error_msg)
        
        # Validate gender
        is_valid, error_msg = validate_gender(gender)
        if not is_valid:
            return error_response('INVALID_GENDER', error_msg)
        
        # Check if room exists
        try:
            room = Room.objects.get(code=room_code)
        except Room.DoesNotExist:
            return error_response('ROOM_NOT_FOUND', 'Room does not exist', status=404)
        
        # Check if room is full
        if is_room_full(room_code) or room.players.count() >= 2:
            return error_response('ROOM_FULL', 'Room is full (2/2 players)', status=403)
        
        # Check if username is taken
        if room.players.filter(username=username).exists():
            return error_response('USERNAME_TAKEN', 'Username already taken in this room')
        
        # Add player to database
        avatar = get_avatar_for_gender(gender)
        Player.objects.create(
            room=room,
            username=username,
            gender=gender,
            avatar=avatar,
            is_owner=False
        )
        
        # Add player to Redis
        add_player_to_room(room_code, username, gender)
        
        # Get all players
        players = list(room.players.values_list('username', flat=True))
        
        return success_response({
            'room_code': room_code,
            'owner': room.owner,
            'players': players,
            'selected_game': room.selected_game,
            'rounds': room.rounds,
            'redirect_url': f'/rooms/{room_code}/?name={username}'
        })
        
    except json.JSONDecodeError:
        return error_response('INVALID_JSON', 'Invalid JSON in request body')
    except Exception as e:
        return error_response('SERVER_ERROR', str(e), status=500)


@require_http_methods(["GET"])
def api_get_room(request, room_code):
    """
    GET /api/rooms/{room_code}
    Get room details
    """
    try:
        # Validate room code
        is_valid, error_msg = validate_room_code(room_code)
        if not is_valid:
            return error_response('INVALID_ROOM_CODE', error_msg)
        
        # Check if room exists
        try:
            room = Room.objects.get(code=room_code)
        except Room.DoesNotExist:
            return error_response('ROOM_NOT_FOUND', 'Room does not exist', status=404)
        
        # Get players
        players_data = []
        for player in room.players.all():
            players_data.append({
                'username': player.username,
                'gender': player.gender,
                'avatar': player.avatar,
                'is_owner': player.is_owner,
                'is_ready': player.is_ready,
                'is_online': player.is_online
            })
        
        return success_response({
            'room_code': room.code,
            'owner': room.owner,
            'players': players_data,
            'selected_game': room.selected_game,
            'rounds': room.rounds,
            'status': room.status,
            'created_at': room.created_at.isoformat()
        })
        
    except Exception as e:
        return error_response('SERVER_ERROR', str(e), status=500)


@require_http_methods(["GET"])
def api_get_share_link(request, room_code):
    """
    GET /api/rooms/{room_code}/share
    Get shareable room link
    """
    try:
        # Check if room exists
        try:
            room = Room.objects.get(code=room_code)
        except Room.DoesNotExist:
            return error_response('ROOM_NOT_FOUND', 'Room does not exist', status=404)
        
        # Generate share URL
        host = request.get_host()
        protocol = 'https' if request.is_secure() else 'http'
        share_url = f'{protocol}://{host}/r/{room_code}'
        
        return success_response({
            'share_url': share_url,
            'qr_code': None  # TODO: Generate QR code if needed
        })
        
    except Exception as e:
        return error_response('SERVER_ERROR', str(e), status=500)


# ============= Message Operations API =============

@require_http_methods(["GET"])
def api_get_messages(request, room_code):
    """
    GET /api/rooms/{room_code}/messages
    Get message history with pagination
    """
    try:
        # Check if room exists
        try:
            room = Room.objects.get(code=room_code)
        except Room.DoesNotExist:
            return error_response('ROOM_NOT_FOUND', 'Room does not exist', status=404)
        
        # Get pagination parameters
        limit = int(request.GET.get('limit', 50))
        before = request.GET.get('before')  # Message ID
        
        # Query messages
        messages_query = room.messages.all()
        if before:
            messages_query = messages_query.filter(id__lt=before)
        
        messages = messages_query[:limit]
        
        # Format messages
        messages_data = []
        for msg in messages:
            msg_data = {
                'id': msg.id,
                'sender': msg.sender,
                'message_type': msg.message_type,
                'timestamp': msg.timestamp.isoformat()
            }
            
            if msg.message_type == 'chat':
                msg_data['content'] = msg.content
            elif msg.message_type == 'voice':
                msg_data['voice_url'] = msg.voice_url
                msg_data['voice_duration'] = msg.voice_duration
            elif msg.message_type == 'image':
                msg_data['image_url'] = msg.image_url
                msg_data['width'] = msg.image_width
                msg_data['height'] = msg.image_height
            
            # Get reactions
            reactions = {}
            for reaction in msg.reactions.all():
                if reaction.emoji not in reactions:
                    reactions[reaction.emoji] = []
                reactions[reaction.emoji].append(reaction.user)
            
            msg_data['reactions'] = [
                {'emoji': emoji, 'users': users}
                for emoji, users in reactions.items()
            ]
            
            messages_data.append(msg_data)
        
        return success_response({
            'messages': messages_data,
            'has_more': room.messages.filter(id__lt=messages[-1].id if messages else 0).exists()
        })
        
    except Exception as e:
        return error_response('SERVER_ERROR', str(e), status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_react_message(request, room_code):
    """
    POST /api/rooms/{room_code}/messages/react
    Add reaction to message
    """
    try:
        data = json.loads(request.body)
        message_id = data.get('message_id')
        emoji = data.get('emoji')
        user = data.get('user')
        
        # Check rate limit (20 per minute)
        if not check_rate_limit(f'ratelimit:react:{user}', 20, 60):
            return error_response('RATE_LIMIT_EXCEEDED', 'Too many reactions. Please slow down.', status=429)
        
        # Check if message exists
        try:
            message = Message.objects.get(id=message_id, room__code=room_code)
        except Message.DoesNotExist:
            return error_response('MESSAGE_NOT_FOUND', 'Message does not exist', status=404)
        
        # Create or get reaction
        reaction, created = MessageReaction.objects.get_or_create(
            message=message,
            user=user,
            emoji=emoji
        )
        
        return success_response({
            'message_id': message_id,
            'emoji': emoji,
            'user': user,
            'created': created
        })
        
    except json.JSONDecodeError:
        return error_response('INVALID_JSON', 'Invalid JSON in request body')
    except Exception as e:
        return error_response('SERVER_ERROR', str(e), status=500)


# ============= Media Upload API =============

@csrf_exempt
@require_http_methods(["POST"])
def api_upload_voice(request):
    """
    POST /api/upload/voice
    Upload voice message
    """
    try:
        # Get form data
        audio_file = request.FILES.get('audio')
        room_code = request.POST.get('room_code')
        duration = request.POST.get('duration')
        
        if not audio_file:
            return error_response('FILE_REQUIRED', 'Audio file is required')
        
        # Validate file type
        allowed_types = ['audio/webm', 'audio/mpeg', 'audio/ogg', 'audio/mp3']
        is_valid, error_msg = validate_file_type(audio_file, allowed_types)
        if not is_valid:
            return error_response('INVALID_FILE_TYPE', error_msg, status=415)
        
        # Validate file size (5MB)
        is_valid, error_msg = validate_file_size(audio_file, 5)
        if not is_valid:
            return error_response('FILE_TOO_LARGE', error_msg, status=413)
        
        # Validate duration
        is_valid, error_msg = validate_voice_duration(duration)
        if not is_valid:
            return error_response('INVALID_DURATION', error_msg)
        
        # Generate filename
        timestamp = int(time.time())
        ext = audio_file.name.split('.')[-1]
        filename = f'{room_code}_{timestamp}.{ext}'
        filepath = f'voice/{filename}'
        
        # Save file
        path = default_storage.save(filepath, ContentFile(audio_file.read()))
        file_url = default_storage.url(path)
        
        return success_response({
            'voice_url': file_url,
            'duration': int(duration),
            'file_size': audio_file.size
        })
        
    except Exception as e:
        return error_response('SERVER_ERROR', str(e), status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_upload_image(request):
    """
    POST /api/upload/image
    Upload image with auto-resize and EXIF stripping
    """
    try:
        # Get form data
        image_file = request.FILES.get('image')
        room_code = request.POST.get('room_code')
        
        if not image_file:
            return error_response('FILE_REQUIRED', 'Image file is required')
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        is_valid, error_msg = validate_file_type(image_file, allowed_types)
        if not is_valid:
            return error_response('INVALID_FILE_TYPE', error_msg, status=415)
        
        # Validate file size (10MB)
        is_valid, error_msg = validate_file_size(image_file, 10)
        if not is_valid:
            return error_response('FILE_TOO_LARGE', error_msg, status=413)
        
        # Open image with PIL
        img = Image.open(image_file)
        
        # Strip EXIF data
        if hasattr(img, '_getexif'):
            img = img.copy()
        
        # Get original dimensions
        width, height = img.size
        
        # Resize if larger than 2048x2048
        max_size = 2048
        if width > max_size or height > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            width, height = img.size
        
        # Generate filename
        timestamp = int(time.time())
        ext = image_file.name.split('.')[-1]
        filename = f'{room_code}_{timestamp}.{ext}'
        filepath = f'images/{filename}'
        
        # Save processed image
        from io import BytesIO
        buffer = BytesIO()
        img_format = 'JPEG' if ext.lower() in ['jpg', 'jpeg'] else ext.upper()
        img.save(buffer, format=img_format, quality=85)
        buffer.seek(0)
        
        path = default_storage.save(filepath, ContentFile(buffer.read()))
        file_url = default_storage.url(path)
        
        # Generate thumbnail (300x300)
        img.thumbnail((300, 300), Image.Resampling.LANCZOS)
        thumb_buffer = BytesIO()
        img.save(thumb_buffer, format=img_format, quality=80)
        thumb_buffer.seek(0)
        
        thumb_filename = f'{room_code}_{timestamp}_thumb.{ext}'
        thumb_filepath = f'images/{thumb_filename}'
        thumb_path = default_storage.save(thumb_filepath, ContentFile(thumb_buffer.read()))
        thumb_url = default_storage.url(thumb_path)
        
        return success_response({
            'image_url': file_url,
            'width': width,
            'height': height,
            'file_size': image_file.size,
            'thumbnail_url': thumb_url
        })
        
    except Exception as e:
        return error_response('SERVER_ERROR', str(e), status=500)


# ============= Game Operations API =============

@require_http_methods(["GET"])
def api_list_games(request):
    """
    GET /api/games
    List all available games
    """
    try:
        games = Game.objects.filter(is_active=True)
        games_data = []
        
        for game in games:
            games_data.append({
                'game_id': game.game_id,
                'name': game.name,
                'image_url': game.image_url,
                'description': game.description,
                'min_players': game.min_players,
                'max_players': game.max_players,
                'is_active': game.is_active
            })
        
        return success_response({'games': games_data})
        
    except Exception as e:
        return error_response('SERVER_ERROR', str(e), status=500)


@require_http_methods(["GET"])
def api_get_game(request, game_id):
    """
    GET /api/games/{game_id}
    Get game details
    """
    try:
        try:
            game = Game.objects.get(game_id=game_id)
        except Game.DoesNotExist:
            return error_response('GAME_NOT_FOUND', 'Game does not exist', status=404)
        
        return success_response({
            'game_id': game.game_id,
            'name': game.name,
            'image_url': game.image_url,
            'description': game.description,
            'min_players': game.min_players,
            'max_players': game.max_players,
            'is_active': game.is_active
        })
        
    except Exception as e:
        return error_response('SERVER_ERROR', str(e), status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_start_game(request, room_code):
    """
    POST /api/rooms/{room_code}/game/start
    Start game (owner only)
    """
    try:
        data = json.loads(request.body)
        game_id = data.get('game_id')
        rounds = data.get('rounds', 1)
        user = data.get('user')  # Username of requester
        
        # Check if room exists
        try:
            room = Room.objects.get(code=room_code)
        except Room.DoesNotExist:
            return error_response('ROOM_NOT_FOUND', 'Room does not exist', status=404)
        
        # Check if user is owner
        if room.owner != user:
            return error_response('NOT_OWNER', 'Only the room owner can start the game', status=403)
        
        # Check if game is selected
        if not room.selected_game:
            return error_response('GAME_NOT_SELECTED', 'Please select a game first')
        
        # Validate rounds
        is_valid, error_msg = validate_rounds(rounds)
        if not is_valid:
            return error_response('INVALID_ROUNDS', error_msg)
        
        # Check if all players are ready (or just owner if alone)
        player_count = room.players.count()
        if player_count > 1:
            not_ready = room.players.filter(is_ready=False, is_owner=False)
            if not_ready.exists():
                return error_response('PLAYERS_NOT_READY', 'All players must be ready')
        
        # Create game session
        game = Game.objects.get(game_id=room.selected_game)
        session = GameSession.objects.create(
            room=room,
            game=game,
            total_rounds=rounds,
            status='active'
        )
        
        # Update room status
        room.status = 'playing'
        room.save()
        
        return success_response({
            'session_id': session.id,
            'game_id': game.game_id,
            'rounds': rounds,
            'redirect_url': f'/games/{game.game_id}/{room_code}/'
        })
        
    except json.JSONDecodeError:
        return error_response('INVALID_JSON', 'Invalid JSON in request body')
    except Exception as e:
        return error_response('SERVER_ERROR', str(e), status=500)