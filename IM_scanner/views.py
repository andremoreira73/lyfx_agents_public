from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta
from agents.models import Agent, UserAgentAccess
from .models import ScanRun, JobPosting
import json

def check_im_scanner_access(user):
    """Check if user has access to IM Scanner agent"""
    try:
        # Check if user is in AccessAllAgents group
        if user.groups.filter(name='AccessAllAgents').exists():
            return True
        
        # Check for specific IM Scanner agent access
        im_scanner_agent = Agent.objects.get(name='IM Scanner')
        return (im_scanner_agent.public or 
                UserAgentAccess.objects.filter(user=user, agent=im_scanner_agent).exists())
    except Agent.DoesNotExist:
        return False

@login_required
def scanner_dashboard(request):
    """Main dashboard showing scan runs"""
    if not check_im_scanner_access(request.user):
        return render(request, 'IM_scanner/access_denied.html')
    
    # Get recent scan runs with stats
    scan_runs = ScanRun.objects.all()[:20]  # Last 20 runs
    
    # Get overall stats
    total_jobs = JobPosting.objects.count()
    total_runs = ScanRun.objects.filter(status='completed').count()
    recent_jobs = JobPosting.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=7)
    ).count()
    
    # Get top companies
    top_companies = JobPosting.objects.values('company').annotate(
        job_count=Count('id')
    ).order_by('-job_count')[:5]
    
    context = {
        'scan_runs': scan_runs,
        'total_jobs': total_jobs,
        'total_runs': total_runs,
        'recent_jobs': recent_jobs,
        'top_companies': top_companies,
    }
    
    return render(request, 'IM_scanner/dashboard.html', context)

@login_required
def scan_run_detail(request, run_id):
    """Detail view for a specific scan run"""
    if not check_im_scanner_access(request.user):
        return render(request, 'IM_scanner/access_denied.html')
    
    scan_run = get_object_or_404(ScanRun, id=run_id)
    
    # Get jobs for this run
    jobs_query = scan_run.jobs.all()
    
    # Handle search
    search_query = request.GET.get('search', '').strip()
    if search_query:
        jobs_query = jobs_query.filter(
            Q(job_title__icontains=search_query) |
            Q(company__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(description_summary__icontains=search_query)
        )
    
    # Handle filter by top picks
    show_top_picks = request.GET.get('top_picks') == 'true'
    if show_top_picks:
        jobs_query = jobs_query.filter(is_top_pick=True)
    
    # Pagination
    paginator = Paginator(jobs_query, 10)
    page_number = request.GET.get('page')
    jobs = paginator.get_page(page_number)
    
    # For HTMX requests, return partial template
    if request.headers.get('HX-Request'):
        return render(request, 'IM_scanner/partials/job_list.html', {
            'jobs': jobs,
            'search_query': search_query,
            'show_top_picks': show_top_picks,
        })
    
    context = {
        'scan_run': scan_run,
        'jobs': jobs,
        'search_query': search_query,
        'show_top_picks': show_top_picks,
    }
    
    return render(request, 'IM_scanner/scan_detail.html', context)

@login_required
def global_search(request):
    """Global search across all job postings"""
    if not check_im_scanner_access(request.user):
        return render(request, 'IM_scanner/access_denied.html')
    
    search_query = request.GET.get('search', '').strip()
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    company_filter = request.GET.get('company')
    
    jobs_query = JobPosting.objects.all()
    
    # Apply filters
    if search_query:
        jobs_query = jobs_query.filter(
            Q(job_title__icontains=search_query) |
            Q(company__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(description_summary__icontains=search_query)
        )
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            jobs_query = jobs_query.filter(created_at__date__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            jobs_query = jobs_query.filter(created_at__date__lte=date_to_obj)
        except ValueError:
            pass
    
    if company_filter:
        jobs_query = jobs_query.filter(company__icontains=company_filter)
    
    # Order by top picks first, then by date
    jobs_query = jobs_query.order_by('-is_top_pick', '-created_at')
    
    # Pagination
    paginator = Paginator(jobs_query, 15)
    page_number = request.GET.get('page')
    jobs = paginator.get_page(page_number)
    
    # Get companies for filter dropdown
    companies = JobPosting.objects.values_list('company', flat=True).distinct().order_by('company')
    
    # For HTMX requests, return partial template
    if request.headers.get('HX-Request'):
        return render(request, 'IM_scanner/partials/search_results.html', {
            'jobs': jobs,
            'search_query': search_query,
        })
    
    context = {
        'jobs': jobs,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'company_filter': company_filter,
        'companies': companies,
    }
    
    return render(request, 'IM_scanner/search.html', context)

@login_required
def api_scan_stats(request):
    """API endpoint for dashboard stats (for HTMX updates)"""
    if not check_im_scanner_access(request.user):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    # Get latest scan run
    latest_run = ScanRun.objects.filter(status='completed').first()
    
    stats = {
        'latest_run_date': latest_run.created_at.isoformat() if latest_run else None,
        'latest_run_jobs': latest_run.total_jobs_found if latest_run else 0,
        'total_jobs': JobPosting.objects.count(),
        'this_week_jobs': JobPosting.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count(),
    }
    
    return JsonResponse(stats)