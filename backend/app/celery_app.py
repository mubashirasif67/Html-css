"""
Celery configuration and initialization
"""

from celery import Celery
from app.config import settings

# Create Celery app
celery_app = Celery(
    "blessings_fyp",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Task routing
celery_app.conf.task_routes = {
    "app.tasks.process_ocr": {"queue": "ocr"},
    "app.tasks.send_email": {"queue": "notifications"},
    "app.tasks.send_sms": {"queue": "notifications"},
    "app.tasks.train_models": {"queue": "ml"},
}

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "retrain-models-weekly": {
        "task": "app.tasks.retrain_models",
        "schedule": 604800.0,  # Weekly (in seconds)
    },
    "cleanup-old-files-daily": {
        "task": "app.tasks.cleanup_old_files",
        "schedule": 86400.0,  # Daily
    },
}