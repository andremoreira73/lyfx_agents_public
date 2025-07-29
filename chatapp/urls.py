from django.urls import path
from . import views, async_views

#urlpatterns = [
#    path('', views.chat_view, name='chat'),
#]

app_name = 'chatapp'

urlpatterns = [
    path('chat/', views.chat_view, name='chat'),
    path('chat_async/', async_views.chat_async, name='chat_async'),
    path('check_status/', async_views.check_status_async, name='check_status'),
    path('cancel_request/', async_views.cancel_request, name='cancel_request'),
]