"""
Validation helper functions for API endpoints
"""
import re


def validate_username(username):
    """
    Validate username: 1-8 characters, alphanumeric only
    Returns: (is_valid, error_message)
    """
    if not username:
        return False, "Username is required"
    
    if len(username) > 8:
        return False, "Username must be 8 characters or less"

    if username.strip() == "":
        return False, "Username cannot be empty"

    if not re.match(r'^[a-zA-Z0-9 ]+$', username):
        return False, "Username must contain only letters, numbers, and spaces"

    return True, "Valid username"


def validate_gender(gender):
    """
    Validate gender: must be 'male' or 'female'
    Returns: (is_valid, error_message)
    """
    if not gender:
        return False, "Gender is required"
    
    if gender not in ['male', 'female']:
        return False, "Gender must be 'male' or 'female'"
    
    return True, None


def validate_room_code(code):
    """
    Validate room code: 4 characters, alphanumeric
    Returns: (is_valid, error_message)
    """
    if not code:
        return False, "Room code is required"
    
    if len(code) != 4:
        return False, "Room code must be exactly 4 characters"
    
    if not re.match(r'^[A-Z0-9]+$', code):
        return False, "Invalid room code format"
    
    return True, None


def validate_file_type(file, allowed_types):
    """
    Validate file type
    Returns: (is_valid, error_message)
    """
    if not file:
        return False, "File is required"
    
    file_type = file.content_type
    if file_type not in allowed_types:
        return False, f"Invalid file type. Allowed: {', '.join(allowed_types)}"
    
    return True, None


def validate_file_size(file, max_size_mb):
    """
    Validate file size
    Returns: (is_valid, error_message)
    """
    if not file:
        return False, "File is required"
    
    max_size_bytes = max_size_mb * 1024 * 1024
    if file.size > max_size_bytes:
        return False, f"File too large. Maximum size is {max_size_mb}MB"
    
    return True, None


def validate_message_content(content, max_length=500):
    """
    Validate message content
    Returns: (is_valid, error_message)
    """
    if not content:
        return False, "Message content is required"
    
    if len(content) > max_length:
        return False, f"Message too long. Maximum {max_length} characters"
    
    return True, None


def validate_voice_duration(duration):
    """
    Validate voice message duration
    Returns: (is_valid, error_message)
    """
    if duration is None:
        return False, "Duration is required"
    
    try:
        duration = int(duration)
    except (ValueError, TypeError):
        return False, "Duration must be a number"
    
    if duration <= 0:
        return False, "Duration must be positive"
    
    if duration > 60:
        return False, "Voice message too long. Maximum 60 seconds"
    
    return True, None


def validate_rounds(rounds):
    """
    Validate game rounds
    Returns: (is_valid, error_message)
    """
    if rounds is None:
        return False, "Rounds is required"
    
    try:
        rounds = int(rounds)
    except (ValueError, TypeError):
        return False, "Rounds must be a number"
    
    if rounds not in [1, 3, 5]:
        return False, "Rounds must be 1, 3, or 5"
    
    return True, None
