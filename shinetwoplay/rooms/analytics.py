import json
import redis
import time
from django.conf import settings

# Initialize Redis connection
redis_client = redis.Redis(
    host=getattr(settings, 'REDIS_HOST', '127.0.0.1'),
    port=getattr(settings, 'REDIS_PORT', 6379),
    db=getattr(settings, 'REDIS_DB', 0),
    decode_responses=True
)

class AnalyticsMiddleware:
    """
    Fast middleware to log basic visitor data to a Redis queue without slowing down the page load.
    A background worker will process the queue to do slow location lookups.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # We perfectly ONLY track / or /rooms/...
        # All other paths (SEO routes, APIs, media, static) are ignored entirely.
        is_home = (request.path == '/')
        is_room = request.path.startswith('/rooms/')
        
        if not (is_home or is_room):
            return response

        try:
            # Extract IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR')
                
            # Deduplication Check (10 minutes = 600 seconds)
            # This ensures multiple refreshes don't spam the logs.
            cache_key = f"seen:{ip}:{request.path}"
            if redis_client.get(cache_key):
                # We've seen this IP visit this path recently. Ignore.
                return response
                
            # Mark them as seen for the next 10 minutes
            redis_client.setex(cache_key, 600, "1")

            # Extract User Agent and Referer
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            referer = request.META.get('HTTP_REFERER', '')

            # Build minimal payload for the background worker
            data = {
                'timestamp': time.time(),
                'ip': ip,
                'path': request.path,
                'method': request.method,
                'user_agent': user_agent,
                'referer': referer,
                'status_code': response.status_code
            }

            if is_home:
                redis_client.lpush('shinetwoplay:analytics_home', json.dumps(data))
            elif is_room:
                # Get specific data provided in Room URL (like ?name=Bob&gender=Male)
                data['name'] = request.GET.get('name', 'Unknown')
                data['gender'] = request.GET.get('gender', 'Unknown')
                redis_client.lpush('shinetwoplay:analytics_room', json.dumps(data))
                
        except Exception:
            # Never let analytics crash the main app
            pass

        return response
