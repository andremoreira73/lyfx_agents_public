from django.contrib import admin
from .models import Agent, UserAgentAccess

@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    #list_display = ('name', 'assistant', 'vector_store', 'chat_type', 'public', 'featured', 'image_filename', 'description')
    list_display = ('name', 'assistant', 'vector_store', 'chat_type', 'public', 'featured', 'image_filename', 'example_message')
    list_filter = ('chat_type', 'public', 'featured')
    list_editable = ('public', 'featured')  # Allow editing statuses directly from the list view
    search_fields = ('name', 'assistant')

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'image_filename')
        }),
        ('Chat Configuration', {
            'fields': ('chat_type', 'assistant', 'vector_store', 'api_endpoint', 'example_message')
        }),
        ('Visibility', {
            'fields': ('public', 'featured')
        }),
    )

@admin.register(UserAgentAccess)
class UserAgentAccessAdmin(admin.ModelAdmin):
    list_display = ('user', 'agent')
    search_fields = ('user__username', 'agent__name')