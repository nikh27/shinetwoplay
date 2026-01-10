"""
Utility functions for API responses and common operations
"""
from django.http import JsonResponse
import random
import string


def success_response(data=None, message="", status=200):
    """
    Standard success response format
    """
    response = {
        "success": True,
        "message": message
    }
    if data is not None:
        response["data"] = data
    
    return JsonResponse(response, status=status)


def error_response(code, message, details=None, status=400):
    """
    Standard error response format
    """
    response = {
        "success": False,
        "error": {
            "code": code,
            "message": message
        }
    }
    if details:
        response["error"]["details"] = details
    
    return JsonResponse(response, status=status)


def generate_room_code(length=4):
    """
    Generate a random room code
    """
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def get_avatar_for_gender(gender):
    """
    Get avatar emoji based on gender
    """
    return '👨' if gender == 'male' else '👩'


def get_client_ip(request):
    """
    Get client IP address from request
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
