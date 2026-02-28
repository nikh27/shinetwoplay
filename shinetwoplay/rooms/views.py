"""
Views for ShineTwoPlay - Redis-Only Architecture

API endpoints for room management, file uploads, and game listing.
All room/player data stored in Redis, only games in database.
"""

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from PIL import Image
from io import BytesIO
import json
import os
import time

from django_ratelimit.decorators import ratelimit

from .games_list import get_all_games, get_game_by_id
from .utils import (
    success_response, error_response, generate_room_code, 
    get_avatar_for_gender, get_client_ip
)
from .validators import (
    validate_username, validate_gender, validate_room_code,
    validate_file_type, validate_file_size, validate_voice_duration
)
from .redis_client import (
    create_room, room_exists, get_room_info, get_players,
    is_room_full, player_exists, check_rate_limit, track_media
)


# ============= Template Views =============

@ratelimit(key='ip', rate='60/m', block=True)
def home(request):
    """Home page"""
    return render(request, "home.html")


def room_page(request, room_code):
    """Room page - serves the room.html template"""
    username = request.GET.get("name", "")
    gender = request.GET.get("gender", "male")
    
    # Check if room exists
    if not room_exists(room_code):
        return redirect("/?error=room_not_found")
    
    if not username:
        # Redirect to home with room code so user can enter name and join
        return redirect(f"/?join={room_code}")
    
    # Get active games from static list
    games = get_all_games()

    return render(request, "room.html", {
        "room": room_code,
        "username": username,
        "gender": gender,
        "games": games,
    })


# ============= Room Management API =============

@csrf_exempt
@require_http_methods(["POST"])
@ratelimit(key='ip', rate='30/m', block=True)
def api_create_room(request):
    """
    POST /api/rooms/create/
    Create a new room (Redis only)
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
        
        # Generate unique room code
        room_code = generate_room_code()
        attempts = 0
        while room_exists(room_code) and attempts < 10:
            room_code = generate_room_code()
            attempts += 1
        
        if attempts >= 10:
            return error_response('SERVER_ERROR', 'Could not generate unique room code', status=500)
        
        # Create room in Redis
        create_room(room_code, username, gender)
        
        # Return success with redirect URL
        return success_response({
            'room_code': room_code,
            'redirect_url': f'/rooms/{room_code}/?name={username}&gender={gender}'
        }, status=201)
        
    except json.JSONDecodeError:
        return error_response('INVALID_JSON', 'Invalid JSON in request body')
    except Exception as e:
        return error_response('SERVER_ERROR', str(e), status=500)


@csrf_exempt
@require_http_methods(["POST"])
@ratelimit(key='ip', rate='30/m', block=True)
def api_join_room(request):
    """
    POST /api/rooms/join/
    Join an existing room (Redis validation only)
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
        
        # Check if room exists in Redis
        if not room_exists(room_code):
            return error_response('ROOM_NOT_FOUND', 'Room does not exist', status=404)
        
        # Check if this is a reconnection attempt
        # If player exists and is in grace period, allow them to reconnect
        from .redis_client import is_player_in_grace_period
        
        is_reconnecting = player_exists(room_code, username) and is_player_in_grace_period(room_code, username)
        
        if not is_reconnecting:
            # Not a reconnection - check room capacity and username availability
            
            # Check if room is full
            if is_room_full(room_code):
                return error_response('ROOM_FULL', 'Room is full (2/2 players)', status=403)
            
            # Check if username is taken (by a connected player)
            if player_exists(room_code, username):
                return error_response('USERNAME_TAKEN', 'Username already taken in this room')
        
        # Get room info
        room_info = get_room_info(room_code)
        players = get_players(room_code)
        
        return success_response({
            'room_code': room_code,
            'owner': room_info.get('owner', ''),
            'players': list(players.keys()),
            'redirect_url': f'/rooms/{room_code}/?name={username}&gender={gender}',
            'is_reconnecting': is_reconnecting
        })
        
    except json.JSONDecodeError:
        return error_response('INVALID_JSON', 'Invalid JSON in request body')
    except Exception as e:
        return error_response('SERVER_ERROR', str(e), status=500)


@require_http_methods(["GET"])
def api_get_room(request, room_code):
    """
    GET /api/rooms/{room_code}/
    Get room details from Redis
    """
    try:
        # Validate room code
        is_valid, error_msg = validate_room_code(room_code)
        if not is_valid:
            return error_response('INVALID_ROOM_CODE', error_msg)
        
        # Check if room exists
        if not room_exists(room_code):
            return error_response('ROOM_NOT_FOUND', 'Room does not exist', status=404)
        
        # Get room data from Redis
        room_info = get_room_info(room_code)
        players = get_players(room_code)
        
        # Format players data
        players_data = []
        for username, data in players.items():
            players_data.append({
                'username': username,
                'gender': data.get('gender'),
                'avatar': data.get('avatar'),
                'is_owner': data.get('is_owner', False),
                'is_ready': data.get('is_ready', False)
            })
        
        return success_response({
            'room_code': room_code,
            'owner': room_info.get('owner', ''),
            'players': players_data,
            'selected_game': room_info.get('selected_game', ''),
            'rounds': int(room_info.get('rounds', 1)),
            'status': room_info.get('status', 'waiting'),
            'created_at': room_info.get('created_at', '')
        })
        
    except Exception as e:
        return error_response('SERVER_ERROR', str(e), status=500)


# ============= Media Upload API =============

@csrf_exempt
@require_http_methods(["POST"])
@ratelimit(key='ip', rate='10/m', block=True)
def api_upload_voice(request):
    """
    POST /api/upload/voice/
    Upload voice message, track for cleanup
    """
    try:
        audio_file = request.FILES.get('audio')
        room_code = request.POST.get('room_code')
        duration = request.POST.get('duration', 0)
        
        if not audio_file:
            return error_response('FILE_REQUIRED', 'Audio file is required')
        
        if not room_code:
            return error_response('ROOM_REQUIRED', 'Room code is required')
        
        # Validate room exists
        if not room_exists(room_code):
            return error_response('ROOM_NOT_FOUND', 'Room does not exist', status=404)
        
        # Validate file type
        allowed_types = ['audio/webm', 'audio/mpeg', 'audio/ogg', 'audio/mp3', 'audio/wav']
        is_valid, error_msg = validate_file_type(audio_file, allowed_types)
        if not is_valid:
            return error_response('INVALID_FILE_TYPE', error_msg, status=415)
        
        # Validate file size (5MB)
        is_valid, error_msg = validate_file_size(audio_file, 5)
        if not is_valid:
            return error_response('FILE_TOO_LARGE', error_msg, status=413)
        
        # Generate filename
        timestamp = int(time.time() * 1000)
        ext = audio_file.name.split('.')[-1] if '.' in audio_file.name else 'webm'
        filename = f'voice_{room_code}_{timestamp}.{ext}'
        filepath = f'rooms/{room_code}/{filename}'
        
        # Save file
        path = default_storage.save(filepath, ContentFile(audio_file.read()))
        file_url = default_storage.url(path)
        
        # Get absolute path for cleanup tracking
        absolute_path = os.path.join(settings.MEDIA_ROOT, path)
        track_media(room_code, absolute_path)
        
        return success_response({
            'url': file_url,
            'duration': float(duration) if duration else 0,
            'file_size': audio_file.size
        })
        
    except Exception as e:
        return error_response('SERVER_ERROR', str(e), status=500)


@csrf_exempt
@require_http_methods(["POST"])
@ratelimit(key='ip', rate='10/m', block=True)
def api_upload_image(request):
    """
    POST /api/upload/image/
    Upload image with auto-resize, track for cleanup
    """
    try:
        image_file = request.FILES.get('image')
        room_code = request.POST.get('room_code')
        
        if not image_file:
            return error_response('FILE_REQUIRED', 'Image file is required')
        
        if not room_code:
            return error_response('ROOM_REQUIRED', 'Room code is required')
        
        # Validate room exists
        if not room_exists(room_code):
            return error_response('ROOM_NOT_FOUND', 'Room does not exist', status=404)
        
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
        
        # Strip EXIF data by copying
        if hasattr(img, '_getexif') and img._getexif():
            data = list(img.getdata())
            img_no_exif = Image.new(img.mode, img.size)
            img_no_exif.putdata(data)
            img = img_no_exif
        
        # Get original dimensions
        width, height = img.size
        
        # Resize if larger than 1920px
        max_size = 1920
        if width > max_size or height > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            width, height = img.size
        
        # Generate filename
        timestamp = int(time.time() * 1000)
        ext = image_file.name.split('.')[-1] if '.' in image_file.name else 'jpg'
        filename = f'image_{room_code}_{timestamp}.{ext}'
        filepath = f'rooms/{room_code}/{filename}'
        
        # Save processed image
        buffer = BytesIO()
        img_format = 'JPEG' if ext.lower() in ['jpg', 'jpeg'] else ext.upper()
        if img_format == 'JPEG' and img.mode == 'RGBA':
            img = img.convert('RGB')
        img.save(buffer, format=img_format, quality=85)
        buffer.seek(0)
        
        path = default_storage.save(filepath, ContentFile(buffer.read()))
        file_url = default_storage.url(path)
        
        # Get absolute path for cleanup tracking
        absolute_path = os.path.join(settings.MEDIA_ROOT, path)
        track_media(room_code, absolute_path)
        
        return success_response({
            'url': file_url,
            'width': width,
            'height': height,
            'file_size': image_file.size
        })
        
    except Exception as e:
        return error_response('SERVER_ERROR', str(e), status=500)


# ============= Game API (Database - Static) =============

@require_http_methods(["GET"])
def api_list_games(request):
    """
    GET /api/games/
    List all available games (from static list)
    """
    try:
        games = get_all_games()
        return success_response({'games': games})
        
    except Exception as e:
        return error_response('SERVER_ERROR', str(e), status=500)


@require_http_methods(["GET"])
def api_get_game(request, game_id):
    """
    GET /api/games/{game_id}/
    Get game details (from static list)
    """
    try:
        game = get_game_by_id(game_id)
        if not game:
            return error_response('GAME_NOT_FOUND', 'Game does not exist', status=404)
        
        return success_response(game)
        
    except Exception as e:
        return error_response('SERVER_ERROR', str(e), status=500)