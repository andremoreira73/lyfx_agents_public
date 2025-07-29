# langgraph_api_1/models.py
import uuid
from django.db import models

class Thread(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Thread {self.id}"

class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=50)  # 'user' or 'assistant'
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}"
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'thread_id': str(self.thread.id),
            'role': self.role,
            'content': self.content,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'object': 'message'
        }

class Run(models.Model):
    STATUSES = (
        ('queued', 'Queued'),
        ('in_progress', 'In Progress'),
        ('requires_action', 'Requires Action'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name='runs')
    assistant_id = models.CharField(max_length=100)  # Identifier for the LangGraph agent
    status = models.CharField(max_length=20, choices=STATUSES, default='queued')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Run {self.id} ({self.status})"
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'thread_id': str(self.thread.id),
            'assistant_id': self.assistant_id,
            'status': self.status,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'object': 'run'
        }
