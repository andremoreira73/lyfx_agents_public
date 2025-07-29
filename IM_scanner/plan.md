# Directory Structure Setup

You'll need to create these directories and files for the Django management command to work:

```
IM_scanner/
├── management/
│   ├── __init__.py          # Empty file
│   └── commands/
│       ├── __init__.py      # Empty file
│       └── run_scanner.py   # The management command file (already created)
├── migrations/
│   ├── __init__.py          # Should already exist
│   └── 0001_initial.py      # The migration file (already created)
├── templates/
│   └── IM_scanner/
│       ├── dashboard.html           # Main dashboard template
│       ├── scan_detail.html         # Scan detail template
│       ├── search.html              # Global search template
│       ├── access_denied.html       # Access denied template
│       └── partials/
│           ├── job_list.html        # Job list partial for HTMX
│           └── search_results.html  # Search results partial for HTMX
├── models.py            # Database models (already created)
├── views.py             # Views (already created)
├── urls.py              # URL configuration (already created)
├── admin.py             # Admin configuration (already created)
├── apps.py              # Should already exist
└── __init__.py          # Should already exist
```

## Commands to create the structure:

```bash
# From your project root directory
mkdir -p IM_scanner/management/commands
touch IM_scanner/management/__init__.py
touch IM_scanner/management/commands/__init__.py

mkdir -p IM_scanner/templates/IM_scanner/partials
```

## Next Steps:

1. **Run migrations:**

   ```bash
   python manage.py makemigrations IM_scanner
   python manage.py makemigrations agents
   python manage.py migrate
   ```

2. **Test the management command:**

   ```bash
   python manage.py run_scanner --dry-run
   ```

3. **Create a superuser if needed and assign IM Scanner access:**

   ```bash
   python manage.py createsuperuser
   ```

4. **Access the IM Scanner:**

   - Go to `/admin/` and add users to the IM Scanner agent access
   - Or create an "AccessAllAgents" group and add users to it
   - Visit `/im-scanner/` to see the dashboard

5. **Set up cron job:**
   ```bash
   # Add to crontab (twice weekly - Tuesdays and Fridays at 6 AM)
   0 6 * * 2,5 /path/to/your/venv/bin/python /path/to/your/project/manage.py run_scanner --cleanup
   ```
