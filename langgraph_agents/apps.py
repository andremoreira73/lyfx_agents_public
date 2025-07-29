
from django.apps import AppConfig
import os
import json
import sys
import logging


## logger instance for this module
logger = logging.getLogger(f'langgraph_agents.apps')



####################################################################
class LanggraphAgentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'langgraph_agents'
    
    def ready(self):
        # Only run initialization when the main server process starts
        # Skip during management commands like migrations
        if os.environ.get('RUN_MAIN') != 'true' and 'runserver' not in sys.argv:
            return

        # Imports
        from django.conf import settings
        from langsmith import Client
            
        # Get OpenAI key
        key_file = getattr(settings, 'OAI_KEY_FILE', '')
        if os.path.exists(key_file):
            with open(key_file, 'r') as file:
                api_data = json.load(file)
                oai_key = api_data.get('key', '')
                os.environ["OPENAI_API_KEY"] = oai_key
        
        # Get LangSmith key
        key_file = getattr(settings, 'LS_KEY_FILE', '')
        if os.path.exists(key_file):
            with open(key_file, 'r') as file:
                api_data = json.load(file)
                ls_key = api_data.get('key', '')
                ls_endpoint = api_data.get('endpoint', '')
                os.environ["LANGSMITH_ENDPOINT"] = ls_endpoint
                os.environ["LANGCHAIN_API_KEY"] = ls_key
        
        # Set LangSmith tracing settings
        langsmith_tracing_bool = getattr(settings, 'LANGCHAIN_TRACING_V2')
        langsmith_project = getattr(settings, 'LANGCHAIN_PROJECT')
        os.environ["LANGCHAIN_TRACING_V2"] = langsmith_tracing_bool
        os.environ["LANGCHAIN_PROJECT"] = langsmith_project

        # Check the connection
        if langsmith_tracing_bool == 'true':  # remember it expects a string...
            try:
                client = Client()
                # Try to list projects (a simple API call)
                projects = list(client.list_projects())  # Convert generator to list - as a way to test the connection
                logger.info(f"Successfully connected to LangSmith. Found {len(projects)} projects.")
                logger.info(f"LangGraph agents initialized with project: {langsmith_project}")

            except Exception as e:
                logger.info(f"Failed to connect to LangSmith API: {e}")
        
        

        #################################################################

    