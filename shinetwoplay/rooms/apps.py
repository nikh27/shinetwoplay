import os
import sys
from django.apps import AppConfig

class RoomsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rooms'

    def ready(self):
        # Only start the analytics background worker in PRODUCTION.
        # It is completely disabled during local development.
        settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', '')
        is_production = 'settings_prod' in settings_module
        
        if not is_production:
            return  # Do nothing in local dev

        # In production, only spin up the worker when Daphne actually starts
        cmd = sys.argv[0] if sys.argv else ""
        is_daphne = 'daphne' in cmd or 'daphne' in sys.argv
        is_runserver = 'runserver' in sys.argv or os.environ.get('RUN_MAIN') == 'true'

        if is_daphne or is_runserver:
            try:
                from .analytics_worker import start_worker
                start_worker()
            except Exception as e:
                print(f"Failed to start analytics worker: {e}")

