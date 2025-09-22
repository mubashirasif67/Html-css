"""
Celery application configuration for the Blessings Donation System.

This module configures Celery for background task processing including
OCR processing, email notifications, and ML model training.
"""

from celery import Celery
from celery.schedules import crontab
import structlog

from .config import settings

logger = structlog.get_logger(__name__)

# Create Celery application
celery_app = Celery(
    "blessings_donation_system",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks",
        "app.ml.tasks",
        "app.notifications.tasks"
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task routing
    task_routes={
        "app.tasks.process_receipt_ocr": {"queue": "ocr"},
        "app.tasks.send_donation_receipt_email": {"queue": "notifications"},
        "app.ml.tasks.train_eligibility_model": {"queue": "ml"},
        "app.ml.tasks.train_fraud_model": {"queue": "ml"},
        "app.ml.tasks.analyze_donation_fraud": {"queue": "ml"},
        "app.notifications.tasks.send_email": {"queue": "notifications"},
        "app.notifications.tasks.send_sms": {"queue": "notifications"},
    },
    
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    
    # Task execution settings
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,       # 10 minutes
    task_max_retries=3,
    task_default_retry_delay=60,  # 1 minute
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_persistent=True,
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Beat schedule for periodic tasks
    beat_schedule={
        # Clean up expired tokens every hour
        "cleanup-expired-tokens": {
            "task": "app.tasks.cleanup_expired_tokens",
            "schedule": crontab(minute=0),  # Every hour
        },
        
        # Generate daily donation statistics
        "generate-daily-stats": {
            "task": "app.tasks.generate_donation_stats",
            "schedule": crontab(hour=1, minute=0),  # Daily at 1 AM
        },
        
        # Retrain ML models weekly
        "retrain-ml-models": {
            "task": "app.ml.tasks.retrain_models",
            "schedule": crontab(day_of_week=0, hour=2, minute=0),  # Sunday at 2 AM
        },
        
        # Send weekly reports
        "send-weekly-reports": {
            "task": "app.tasks.send_weekly_reports",
            "schedule": crontab(day_of_week=1, hour=9, minute=0),  # Monday at 9 AM
        },
        
        # Clean up old files
        "cleanup-old-files": {
            "task": "app.tasks.cleanup_old_files",
            "schedule": crontab(day_of_week=0, hour=3, minute=0),  # Sunday at 3 AM
        },
        
        # Health check for external services
        "health-check-services": {
            "task": "app.tasks.health_check_services",
            "schedule": crontab(minute="*/15"),  # Every 15 minutes
        },
    },
    
    # Queue configuration
    task_default_queue="default",
    task_create_missing_queues=True,
    
    # Security settings
    worker_hijack_root_logger=False,
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s",
)

# Configure logging
@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery configuration."""
    print(f"Request: {self.request!r}")
    return "Debug task completed successfully"


# Task failure handler
@celery_app.task(bind=True)
def task_failure_handler(self, task_id, error, traceback):
    """Handle task failures with logging and notifications."""
    logger.error(
        "Task failed",
        task_id=task_id,
        error=str(error),
        traceback=traceback
    )
    
    # Send notification to admins for critical failures
    if self.request.retries >= self.max_retries:
        from .notifications.tasks import send_admin_notification
        send_admin_notification.delay(
            subject="Critical Task Failure",
            message=f"Task {task_id} failed after maximum retries: {error}",
            level="error"
        )


# Custom task base class
class CallbackTask(celery_app.Task):
    """Custom task class with callbacks and error handling."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails."""
        logger.error(
            "Task failed",
            task_name=self.name,
            task_id=task_id,
            exception=str(exc),
            args=args,
            kwargs=kwargs
        )
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried."""
        logger.warning(
            "Task retrying",
            task_name=self.name,
            task_id=task_id,
            exception=str(exc),
            retry_count=self.request.retries
        )
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds."""
        logger.info(
            "Task completed successfully",
            task_name=self.name,
            task_id=task_id,
            result=str(retval)[:100]  # Truncate long results
        )


# Set default task base class
celery_app.Task = CallbackTask


# Celery signals
@celery_app.signals.worker_ready.connect
def worker_ready_handler(sender, **kwargs):
    """Called when worker is ready."""
    logger.info("Celery worker ready", worker=sender.hostname)


@celery_app.signals.worker_shutdown.connect
def worker_shutdown_handler(sender, **kwargs):
    """Called when worker shuts down."""
    logger.info("Celery worker shutting down", worker=sender.hostname)


@celery_app.signals.task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Called before task execution."""
    logger.debug(
        "Task starting",
        task_name=task.name if task else "unknown",
        task_id=task_id
    )


@celery_app.signals.task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Called after task execution."""
    logger.debug(
        "Task finished",
        task_name=task.name if task else "unknown",
        task_id=task_id,
        state=state
    )


# Health check function
def health_check():
    """Check Celery health status."""
    try:
        # Check if broker is accessible
        inspector = celery_app.control.inspect()
        stats = inspector.stats()
        
        if stats:
            active_workers = len(stats)
            return {
                "status": "healthy",
                "active_workers": active_workers,
                "broker_url": settings.celery_broker_url,
                "backend_url": settings.celery_result_backend
            }
        else:
            return {
                "status": "unhealthy",
                "error": "No active workers found",
                "broker_url": settings.celery_broker_url,
                "backend_url": settings.celery_result_backend
            }
    
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "broker_url": settings.celery_broker_url,
            "backend_url": settings.celery_result_backend
        }


# Export the app for use in other modules
__all__ = ["celery_app", "health_check"]