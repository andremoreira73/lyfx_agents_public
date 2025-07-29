
from django.apps import AppConfig
import logging

logger = logging.getLogger('IM_scanner')

class ImScannerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'IM_scanner'
    
    def ready(self):
        """Initialize API keys when Django starts up"""
        try:
            # uncomment if not using .env + docker
            #from lyfx_agents.initialization_keys import initialize_api_keys
            #initialize_api_keys()
            logger.info("API keys initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize API keys: {e}")
            # Don't fail the app startup if keys can't be loaded