from django.contrib import admin
from .models import ScanRun, JobPosting

@admin.register(ScanRun)
class ScanRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'status', 'total_jobs_found', 'total_top_picks', 'total_pages_processed')
    list_filter = ('status', 'created_at')
    readonly_fields = ('created_at',)
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('created_at', 'status')
        }),
        ('Results', {
            'fields': ('total_jobs_found', 'total_top_picks', 'total_pages_processed')
        }),
        ('Error Info', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )

@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ('job_title', 'company', 'location', 'is_top_pick', 'scan_run', 'created_at')
    list_filter = ('is_top_pick', 'company', 'scan_run__created_at', 'created_at')
    search_fields = ('job_title', 'company', 'location', 'description_summary')
    list_editable = ('is_top_pick',)
    readonly_fields = ('created_at',)
    ordering = ['-is_top_pick', '-created_at']
    
    fieldsets = (
        ('Job Details', {
            'fields': ('job_title', 'company', 'location', 'apply_url')
        }),
        ('Content', {
            'fields': ('description_summary',)
        }),
        ('Metadata', {
            'fields': ('scan_run', 'is_top_pick', 'created_at')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('scan_run')