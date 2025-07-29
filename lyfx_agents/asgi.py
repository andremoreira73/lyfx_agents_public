"""
ASGI config for lyfx_agents project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

#import os
#from django.core.asgi import get_asgi_application
#os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lyfx_agents.settings')
#application = get_asgi_application()

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lyfx_agents.settings')
django.setup()

# Import and run initialization
# uncomment if not using .env + docker
#from .initialization_keys import initialize_api_keys
#initialize_api_keys()

# Initialize LangGraph PostgreSQL tables
from .init_langgraph_postgres import initialize_langgraph_tables
initialize_langgraph_tables()

# Get the ASGI application
from django.core.asgi import get_asgi_application
application = get_asgi_application()
