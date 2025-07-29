"""
WSGI config for lyfx_agents project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

#import os
#from django.core.wsgi import get_wsgi_application
#os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lyfx_agents.settings')
#application = get_wsgi_application()


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

# Get the WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()