"""
Production settings for shinetwoplay.
Usage: Set env var DJANGO_SETTINGS_MODULE=shinetwoplay.settings_prod
"""
import os
from .settings import *

# ──── Security ────
DEBUG = False
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'CHANGE-ME-to-a-random-64-char-string-in-production')
ALLOWED_HOSTS = [
    'shinetwoplay.online',
    'www.shinetwoplay.online',
    '13.235.50.170',  # EC2 IP
    '_',              # Catch-all Nginx proxy host
    'localhost',      # Local connections
]

# ──── CSRF / HTTPS ────
CSRF_TRUSTED_ORIGINS = [
    'https://shinetwoplay.online',
    'https://www.shinetwoplay.online',
]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ──── Middleware (override for ASGI compatibility) ────
# Remove SecurityMiddleware and CorsMiddleware — Nginx handles these.
# These cause 'coroutine' object errors under Django ASGI + Channels.
MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

# ──── No database needed ────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/opt/shinetwoplay/shinetwoplay/db.sqlite3',
    }
}

# ──── Static files ────
STATIC_URL = '/static/'
STATIC_ROOT = '/opt/shinetwoplay/shinetwoplay/staticfiles'

# ──── Media files ────
MEDIA_URL = '/media/'
MEDIA_ROOT = '/opt/shinetwoplay/shinetwoplay/media'

# ──── Redis (same machine) ────
REDIS_HOST = os.environ.get('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
REDIS_DB = 0

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(REDIS_HOST, REDIS_PORT)],
        },
    },
}

# ──── Logging ────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {module}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/shinetwoplay/django.log',
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': '/var/log/shinetwoplay/error.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'error_file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.channels': {
            'handlers': ['file', 'error_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
