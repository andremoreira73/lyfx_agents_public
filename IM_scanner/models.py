
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class ScanRun(models.Model):
    """Represents a complete scanning session"""
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    created_at = models.DateTimeField(auto_now_add=True)
    total_jobs_found = models.IntegerField(default=0)
    total_top_picks = models.IntegerField(default=0)
    total_pages_processed = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Scan Run {self.created_at.strftime('%Y-%m-%d %H:%M')} - {self.total_jobs_found} jobs"
    
    @classmethod
    def cleanup_old_runs(cls, weeks=6):
        """Clean up scan runs older than specified weeks"""
        cutoff_date = timezone.now() - timedelta(weeks=weeks)
        old_runs = cls.objects.filter(created_at__lt=cutoff_date)
        count = old_runs.count()
        old_runs.delete()
        return count

class JobPosting(models.Model):
    """Individual job posting found during a scan"""
    scan_run = models.ForeignKey(ScanRun, on_delete=models.CASCADE, related_name='jobs')
    job_title = models.CharField(max_length=300)
    company = models.CharField(max_length=300)
    location = models.CharField(max_length=300)
    description_summary = models.TextField()
    apply_url = models.URLField(max_length=500)
    is_top_pick = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_top_pick', '-created_at']
        indexes = [
            models.Index(fields=['apply_url']),
            models.Index(fields=['scan_run', 'is_top_pick']),
            models.Index(fields=['job_title']),
            models.Index(fields=['company']),
        ]
    
    def __str__(self):
        pick_indicator = " ⭐" if self.is_top_pick else ""
        return f"{self.job_title} at {self.company}{pick_indicator}"
    
    @classmethod
    def url_exists(cls, apply_url):
        """Check if a job with this URL already exists"""
        return cls.objects.filter(apply_url=apply_url).exists()
    
    def get_search_text(self):
        """Return combined text for search functionality"""
        return f"{self.job_title} {self.company} {self.location} {self.description_summary}"