from django.urls import path
from . import views

app_name = 'IM_scanner'

urlpatterns = [
    path('', views.scanner_dashboard, name='dashboard'),
    path('scan/<int:run_id>/', views.scan_run_detail, name='scan_detail'),
    path('search/', views.global_search, name='global_search'),
    path('api/stats/', views.api_scan_stats, name='api_stats'),
]