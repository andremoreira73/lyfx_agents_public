"""
URL configuration for lyfx_agents project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    # Admin and auth
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    
    # Main apps
    path('agents/', include('agents.urls', namespace='agents')),
    
    # Legacy chat interfaces
    path('chat/', include('chatapp.urls', namespace='chatapp')),
    path('chat_plus/', include('chatapp_plus.urls', namespace='chatapp_plus')),
    
    # New modern chat interface for LangGraph agents
    path('agent/', include('agent_chat.urls', namespace='agent_chat')),

    # IM Scanner
    path('im-scanner/', include('IM_scanner.urls', namespace='IM_scanner')),
    
    # API endpoints
    path('', include('langgraph_api_1.urls')),
    
    # Root redirect
    path('', RedirectView.as_view(url='agents/home/', permanent=True)),
]

# Add static URL mapping in DEBUG mode
#if settings.DEBUG:
#    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()


