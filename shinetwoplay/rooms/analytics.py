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

        # Skip logging for static, media, internal apis, or websockets if desired
        if request.path.startswith('/static/') or request.path.startswith('/media/') or request.path.startswith('/api/'):
            return response

        try:
            # Extract IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR')

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

            # Push to Redis queue instantly
            redis_client.lpush('shinetwoplay:analytics_queue', json.dumps(data))
        except Exception:
            # Never let analytics crash the main app
            pass

        return response
