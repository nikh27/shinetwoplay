import json
import logging
import redis
import time
from django.conf import settings

analytics_logger = logging.getLogger('shinetwoplay.analytics.errors')

class AnalyticsMiddleware:
    """
    Fast, zero-latency analytics middleware.
    
    - Only tracks home page (/) and room pages (/rooms/.../). 
    - Deduplicates per IP+page using a 10-minute Redis TTL key.
    - Pushes to separate Redis queues for home and room pages.
    - Swallows all errors gracefully so analytics NEVER affect the user.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Lazy Redis client — created once and reused
        try:
            self._redis = redis.Redis(
                host=getattr(settings, 'REDIS_HOST', '127.0.0.1'),
                port=getattr(settings, 'REDIS_PORT', 6379),
                db=getattr(settings, 'REDIS_DB', 0),
                decode_responses=True,
                socket_connect_timeout=1,  # Fail fast if Redis is down
                socket_timeout=1,
            )
        except Exception as e:
            print(f"[Analytics] Redis connection failed on startup: {e}")
            self._redis = None

    def __call__(self, request):
        response = self.get_response(request)

        # Only track two specific paths
        is_home = (request.path == '/')
        is_room = request.path.startswith('/rooms/')

        if not (is_home or is_room):
            return response

        # Don't slow down failed responses or redirects
        if response.status_code not in (200, 201):
            return response

        try:
            self._track(request, response, is_home, is_room)
        except Exception as e:
            # Log the error but NEVER let analytics crash the site
            print(f"[Analytics] Error tracking {request.path}: {e}")

        return response

    def _track(self, request, response, is_home, is_room):
        if not self._redis:
            return

        # --- Extract Real IP ---
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'Unknown')

        # --- Deduplication Check (10 minutes) ---
        # Key is based on IP only (not full path), so a user switching
        # from home page to room is still tracked on BOTH but not spammed.
        # We use ip + page TYPE (home vs room) for deduplication.
        page_type = 'home' if is_home else f"room:{request.path}"
        cache_key = f"analytics:seen:{ip}:{page_type}"

        try:
            if self._redis.get(cache_key):
                return  # Already tracked this visitor recently
            self._redis.setex(cache_key, 600, '1')
        except redis.RedisError as e:
            # Redis unavailable — skip dedup check and track anyway
            print(f"[Analytics] Redis dedup check failed: {e}")

        # --- Build Payload ---
        data = {
            'timestamp': time.time(),
            'ip': ip,
            'path': request.path,
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'referer': request.META.get('HTTP_REFERER', ''),
            'status_code': response.status_code,
        }

        # --- Push to Correct Queue ---
        try:
            if is_home:
                self._redis.lpush('shinetwoplay:analytics_home', json.dumps(data))
            elif is_room:
                data['name'] = request.GET.get('name', 'Unknown')
                data['gender'] = request.GET.get('gender', 'Unknown')
                self._redis.lpush('shinetwoplay:analytics_room', json.dumps(data))
        except redis.RedisError as e:
            print(f"[Analytics] Redis push failed: {e}")
