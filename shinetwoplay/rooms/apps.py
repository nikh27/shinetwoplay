import os
import sys
from django.apps import AppConfig

class RoomsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rooms'

    def ready(self):
        # Prevent the worker from starting during management commands (like migrate, runserver's auto-reload)
        # We only want it running in the actual server instances (daphne or runserver)
        
        # Safely determine if this process is a web server process
        cmd = sys.argv[0] if sys.argv else ""
        is_server = 'daphne' in cmd or 'runserver' in sys.argv or os.environ.get('RUN_MAIN') == 'true'
        
        if is_server:
            try:
                from .analytics_worker import start_worker
                start_worker()
            except Exception as e:
                print(f"Failed to start analytics worker: {e}")
