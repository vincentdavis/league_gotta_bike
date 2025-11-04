"""APScheduler configuration for membership background tasks.

This module sets up APScheduler to trigger django-tasks on a schedule.
It ensures the scheduler only runs once, avoiding duplicates in:
- Django auto-reloader subprocess
- Background worker processes
- Management commands
"""

import os
import sys
import atexit
import logfire
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger


# Global scheduler instance (singleton)
_scheduler = None


def should_start_scheduler():
    """
    Determine if the scheduler should start in this process.

    Returns False if:
    - Running in Django auto-reloader subprocess (RUN_MAIN != 'true')
    - Running management commands (migrate, shell, etc.)
    - Running background worker (db_worker)

    Returns:
        bool: True if scheduler should start, False otherwise
    """
    # Check if running via Django's auto-reloader
    # RUN_MAIN is set by Django's runserver when auto-reload is active
    # - Not set: Production or direct ASGI server (daphne, gunicorn) - OK to run
    # - Set to 'true': Main Django process in dev server - OK to run
    # - Set but not 'true': Parent watcher process - SKIP
    run_main = os.environ.get('RUN_MAIN')
    if run_main is not None and run_main != 'true':
        logfire.debug("Scheduler: Skipping - in Django auto-reloader parent process")
        return False

    # Skip if running specific management commands (but allow runserver and ASGI servers)
    if len(sys.argv) > 1:
        command = sys.argv[1]

        # Skip these management commands
        skip_commands = [
            'migrate', 'makemigrations', 'shell', 'dbshell',
            'test', 'check', 'collectstatic', 'createsuperuser',
            'db_worker',  # Background task worker
            'tailwind',   # Tailwind CSS compilation
        ]

        if command in skip_commands:
            logfire.debug(f"Scheduler: Skipping - running management command '{command}'")
            return False

    # Allow scheduler to run in:
    # - Django runserver (manage.py runserver)
    # - ASGI servers (daphne, uvicorn, gunicorn)
    # - Production deployments
    return True


def trigger_membership_sync():
    """
    Job function that APScheduler calls to trigger the membership sync task.

    This enqueues the task in django-tasks, which will be processed by db_worker.
    """
    try:
        from apps.membership.tasks import sync_membership_status_with_seasons

        logfire.info("APScheduler: Triggering membership/season sync task")

        # Enqueue the task using django-tasks
        result = sync_membership_status_with_seasons.enqueue()

        logfire.info(
            "APScheduler: Task enqueued successfully",
            task_id=result.id if hasattr(result, 'id') else None
        )

    except Exception as e:
        logfire.error(
            "APScheduler: Failed to enqueue membership sync task",
            error=str(e),
            exc_info=True
        )


def start_scheduler():
    """
    Initialize and start the APScheduler BackgroundScheduler.

    Configures the scheduler to trigger membership sync task every 12 hours.
    Only starts if should_start_scheduler() returns True.
    """
    global _scheduler

    # Check if we should start the scheduler
    if not should_start_scheduler():
        return

    # Prevent duplicate scheduler instances
    if _scheduler is not None:
        logfire.warn("APScheduler: Scheduler already running, skipping initialization")
        return

    try:
        logfire.info("APScheduler: Initializing scheduler")

        # Create BackgroundScheduler
        # - BackgroundScheduler runs in a background thread
        # - timezone='UTC' ensures consistent scheduling across environments
        _scheduler = BackgroundScheduler(timezone='UTC')

        # Add job to trigger every 12 hours
        _scheduler.add_job(
            func=trigger_membership_sync,
            trigger=IntervalTrigger(hours=12),
            id='membership_season_sync',
            name='Sync membership status with active seasons',
            replace_existing=True,
            max_instances=1,  # Only allow one instance to run at a time
            misfire_grace_time=60,  # Allow 60 seconds grace time for misfires
        )

        # Start the scheduler
        _scheduler.start()

        logfire.info(
            "APScheduler: Scheduler started successfully",
            job_id='membership_season_sync',
            interval_hours=12
        )

        # Register shutdown handler to stop scheduler gracefully
        atexit.register(shutdown_scheduler)

    except Exception as e:
        logfire.error(
            "APScheduler: Failed to start scheduler",
            error=str(e),
            exc_info=True
        )


def shutdown_scheduler():
    """
    Gracefully shutdown the scheduler.

    Called automatically via atexit when the process exits.
    """
    global _scheduler

    if _scheduler is not None:
        logfire.info("APScheduler: Shutting down scheduler")
        _scheduler.shutdown(wait=False)
        _scheduler = None
