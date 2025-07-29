# Create a file: langgraph_agents/management/commands/test_cccalc.py

from django.core.management.base import BaseCommand
from langgraph_agents.cccalc.cccalc_agent import run_workflow

class Command(BaseCommand):
    """
    To run this test: python manage.py test_cccalc
    """

    help = 'Test the cccalc agent with a sample input'

    def handle(self, *args, **options):
        # Sample input similar to what you used in Jupyter
        initial_state = {
            "messages": [
                {"role": "user", "content": "Hello. I need your help to calculate the CO2 emission of a chemical called SF."}
            ]
        }
        
        result = run_workflow(initial_state)
        
        # Print results
        self.stdout.write(self.style.SUCCESS('Test completed'))
        self.stdout.write('Final messages:')
        for msg in result.get('messages', []):
            if hasattr(msg, 'content') and hasattr(msg, 'type'):
                # LangChain message
                self.stdout.write(f"{msg.type}: {msg.content}")
            elif isinstance(msg, dict):
                # Dict message
                self.stdout.write(f"{msg.get('role', 'unknown')}: {msg.get('content', '')}")