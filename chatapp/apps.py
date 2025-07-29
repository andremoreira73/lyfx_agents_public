from django.apps import AppConfig
import importlib
import sys

class ChatappPlusConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chatapp'
    
    def ready(self):
        # Only run when server is starting, not during management commands
        if 'runserver' in sys.argv or 'uvicorn' in sys.argv:
            try:
                # Import async_views here to avoid AppRegistryNotReady error
                async_views = importlib.import_module('chatapp.async_views')
            except ImportError:
                pass