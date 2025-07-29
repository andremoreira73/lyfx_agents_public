from django.db import models
from django.contrib.auth.models import User

class Agent(models.Model):
    CHAT_TYPES = [
        ('chatapp', 'ChatApp'),
        ('chatapp_plus', 'ChatApp Plus'),
        ('langgraph', 'LangGraph Agent'),
        ('custom', 'Custom Application'),  # for agents that may not be under the umbrella of langgraph agents, etc.
    ]

    name = models.CharField(max_length=100)
    assistant = models.CharField(max_length=150, blank=True)  # Optional for LangGraph
    vector_store = models.CharField(max_length=150, blank=True)  # Optional for LangGraph
    description = models.TextField(blank=True)
    chat_type = models.CharField(
        max_length=20,
        choices=CHAT_TYPES,
        default='chatapp',
    )
    api_endpoint = models.CharField(max_length=255, blank=True, help_text="API endpoint for custom agents; agents under the LangGraph app do not need this explicitly")
    public = models.BooleanField(default=False)
    featured = models.BooleanField(default=False)
    image_filename = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="Custom image filename (without .jpg extension). If blank, uses agent name."
    )
    example_message = models.CharField(
        max_length=255,
        blank=True,
        help_text="Example message to show as placeholder in chat input. If empty, uses generic placeholder."
    )

    def __str__(self):
        return self.name
    
    def get_image_filename(self):
        """Return the image filename to use (with .jpg extension)"""
        if self.image_filename:
            return f"{self.image_filename}.jpg"
        return f"{self.name}.jpg"



class UserAgentAccess(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'agent')

    def __str__(self):
        return f"{self.user.username} access to {self.agent.name}"
