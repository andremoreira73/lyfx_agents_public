import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from IM_scanner.models import ScanRun, JobPosting
from IM_scanner.core.IM_scanner_runs import run_IM_scanner

logger = logging.getLogger('IM_scanner.management')

class Command(BaseCommand):
    help = 'Run the IM Scanner and save results to database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up old scan runs (6+ weeks old)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run scanner but don\'t save to database',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(
                f'Starting IM Scanner at {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}'
            )
        )

        # Handle cleanup if requested
        if options['cleanup']:
            self.cleanup_old_runs()

        # Create new scan run
        scan_run = ScanRun.objects.create(status='running')
        
        try:
            # Run the actual scanner
            self.stdout.write('Running IM Scanner workflow...')
            results = run_IM_scanner()
            
            # Process results
            new_jobs_count, total_jobs_count = self.save_results(scan_run, results, options['dry_run'])
            
            # Update scan run with final stats
            if not options['dry_run']:
                scan_run.total_jobs_found = total_jobs_count
                scan_run.total_top_picks = len(results.get('jobs_top_picks_ll', []))
                scan_run.total_pages_processed = len(results.get('processed_urls_ll', []))
                scan_run.status = 'completed'
                scan_run.save()

            # Report results
            if new_jobs_count == 0:
                self.stdout.write(
                    self.style.WARNING(
                        f'No new jobs found. Total processed: {len(results.get("processed_urls_ll", []))} pages'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully found {new_jobs_count} new jobs out of {total_jobs_count} total jobs'
                    )
                )
                
        except Exception as e:
            logger.error(f"IM Scanner failed: {str(e)}")
            if not options['dry_run']:
                scan_run.status = 'failed'
                scan_run.error_message = str(e)
                scan_run.save()
            
            self.stdout.write(
                self.style.ERROR(f'IM Scanner failed: {str(e)}')
            )
            raise

    def save_results(self, scan_run, results, dry_run=False):
        """Save scanner results to database"""
        jobs_found_ll = results.get('jobs_found_ll', [])
        jobs_top_picks_ll = results.get('jobs_top_picks_ll', [])
        
        # Get apply_urls of top picks for easy lookup
        top_pick_urls = {job.apply_url for job in jobs_top_picks_ll}
        
        new_jobs_count = 0
        total_jobs_count = len(jobs_found_ll)
        
        for job in jobs_found_ll:
            # Check if job already exists
            if JobPosting.url_exists(job.apply_url):
                self.stdout.write(f'Skipping duplicate job: {job.job_title} at {job.company}')
                continue
            
            if dry_run:
                self.stdout.write(f'[DRY RUN] Would save: {job.job_title} at {job.company}')
                new_jobs_count += 1
                continue
            
            # Create new job posting
            JobPosting.objects.create(
                scan_run=scan_run,
                job_title=job.job_title,
                company=job.company,
                location=job.location,
                description_summary=job.description_summary,
                apply_url=job.apply_url,
                is_top_pick=job.apply_url in top_pick_urls
            )
            new_jobs_count += 1
            
        return new_jobs_count, total_jobs_count

    def cleanup_old_runs(self):
        """Clean up old scan runs"""
        count = ScanRun.cleanup_old_runs(weeks=6)
        self.stdout.write(
            self.style.SUCCESS(f'Cleaned up {count} old scan runs')
        )