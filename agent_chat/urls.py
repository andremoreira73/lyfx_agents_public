from django.urls import path
from . import views

app_name = 'agent_chat'

urlpatterns = [
    path('<str:agent_name>/', views.chat_view, name='chat'),
    path('<str:agent_name>/help/', views.help_view, name='help'),
]