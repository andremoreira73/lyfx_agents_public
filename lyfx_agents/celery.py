import os
from celery import Celery

# Create Celery app
app = Celery('lyfx_agents')

# Configure Celery using settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()