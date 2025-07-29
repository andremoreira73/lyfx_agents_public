from django.urls import path
from . import views

app_name = 'agents'

urlpatterns = [
    path('', views.agent_dashboard, name='dashboard'),
    path('home/', views.home, name='home'),
]
