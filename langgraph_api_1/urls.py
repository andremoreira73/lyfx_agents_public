# langgraph_api_1/urls.py
from django.urls import path
from . import api

urlpatterns = [
    # Core API endpoints
    path('api/', api.api_info, name='api_info'),
    path('api/threads', api.threads, name='threads'),
    path('api/threads/<uuid:thread_id>/messages', api.thread_messages, name='thread_messages'),
    path('api/threads/<uuid:thread_id>/runs', api.thread_runs, name='thread_runs'),
    path('api/threads/<uuid:thread_id>/runs/<uuid:run_id>', api.run_detail, name='run_detail'),
    path('api/threads/<uuid:thread_id>/runs/<uuid:run_id>/events', api.run_events, name='run_events'),
    path('api/runs/<uuid:run_id>/submit_tool_outputs', api.submit_tool_outputs, name='submit_tool_outputs'),
]
