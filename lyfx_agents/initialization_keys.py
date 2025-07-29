import os
import json
from django.conf import settings

import logging

## logger instance for this module
logger = logging.getLogger(f'keys_initializer')

def initialize_api_keys():
    """Initialize API keys once at server startup"""

    logger.info("Initializing API keys...")

    # Get OpenAI key
    key_file = getattr(settings, 'OAI_KEY_FILE', '')
    if os.path.exists(key_file):
        try:
            with open(key_file, 'r') as file:
                api_data = json.load(file)
                os.environ["OPENAI_API_KEY"] = api_data.get('key', '')
                logger.info(f"Set OpenAI API key from {key_file}")
        except Exception as e:
            logger.error(f"Error loading OpenAI API key: {e}")
    
    # LangSmith keys and params
    key_file = getattr(settings, 'LS_KEY_FILE', '')
    if os.path.exists(key_file):
        try:
            with open(key_file, 'r') as file:
                api_data = json.load(file)
                os.environ["LANGSMITH_ENDPOINT"] = api_data.get('endpoint', '')
                os.environ["LANGCHAIN_API_KEY"] = api_data.get('key', '')
                logger.info(f"Set LangSmith API key from {key_file}")
        except Exception as e:
            logger.error(f"Error loading LangSmith API key: {e}")

    # Set LangSmith tracing settings - use getattr with defaults
    langsmith_tracing_bool = getattr(settings, 'LANGCHAIN_TRACING_V2', 'false')
    langsmith_project = getattr(settings, 'LANGCHAIN_PROJECT', 'default_project')
    
    os.environ["LANGCHAIN_TRACING_V2"] = langsmith_tracing_bool
    os.environ["LANGCHAIN_PROJECT"] = langsmith_project
    logger.info(f"Set LangSmith project: {langsmith_project}, tracing: {langsmith_tracing_bool}")

    # Get Scraping Bee key
    key_file = getattr(settings, 'SCRAPING_BEE_FILE', '')
    if os.path.exists(key_file):
        try:
            with open(key_file, 'r') as file:
                api_data = json.load(file)
                os.environ["SCRAPINGBEE_API_KEY"] = api_data.get('key', '')
                os.environ["SCRAPINGBEE_ENDPOINT"] = api_data.get('endpoint', '')
                logger.info(f"Set Scraping Bee API key and endpoint from {key_file}")
        except Exception as e:
            logger.error(f"Error loading Scraping Bee API key and endpoint: {e}")
    
    # Get email key (lyfx.ai gmail)
    key_file = getattr(settings, 'LYFX_EMAIL_FILE', '')
    if os.path.exists(key_file):
        try:
            with open(key_file, 'r') as file:
                api_data = json.load(file)
                os.environ["LYFX_EMAIL_KEY"] = api_data.get('key', '')
                logger.info(f"Set lyfX.ai email key from {key_file}")
        except Exception as e:
            logger.error(f"Error loading lyfX.ai email key: {e}")

    return