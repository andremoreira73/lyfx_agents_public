# Create file: langgraph_agents/management/commands/setup_checkpointer.py

from django.core.management.base import BaseCommand
from django.conf import settings
from langgraph.checkpoint.postgres import PostgresSaver
import os

class Command(BaseCommand):
    help = 'Setup LangGraph PostgreSQL checkpoint tables'

    def handle(self, *args, **options):
        # Get database settings
        db_settings = settings.DATABASES['default']
        
        if 'NAME' in db_settings:
            DB_URI = (
                f"postgresql://{db_settings['USER']}:{db_settings['PASSWORD']}"
                f"@{db_settings['HOST']}:{db_settings['PORT']}/{db_settings['NAME']}"
                f"?sslmode=disable"
            )
        else:
            DB_URI = os.environ.get('DATABASE_URL')
        
        self.stdout.write(f"Connecting to database...")
        
        # Create checkpointer and run setup
        checkpointer = PostgresSaver.from_conn_string(DB_URI)
        checkpointer.setup()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created LangGraph checkpoint tables')
        )