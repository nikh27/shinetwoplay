import logging

from django.http import HttpResponseForbidden

logger = logging.getLogger(__name__)

# Known bot strings to block (case-insensitive checking later)
BLOCKED_KEYWORDS = [
    "curl",
    "python-requests",
    "aiohttp",
    "Go-http-client",
    "axios",
    "zgrab",
    "ssl-scanner",
    "AhrefsBot",
    "Censys",
    "BitSightBot",
    "RankrBot",
]

# Known good bots to allow
ALLOWED_GOOGLE = [
    "Googlebot",
    "AdsBot-Google",
]

class BotBlockMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        
        # 1. Allow Known Good Bots immediately
        if any(bot in user_agent for bot in ALLOWED_GOOGLE):
            return self.get_response(request)

        # 2. Block Known Bad Bots
        if any(keyword.lower() in user_agent.lower() for keyword in BLOCKED_KEYWORDS):
            logger.warning(f"Blocked User-Agent match: {user_agent}")
            return HttpResponseForbidden("Bot Blocked")

        return self.get_response(request)
