"""
Celery application configuration.

This module sets up the Celery app for running background tasks
like OCR processing, notifications, and ML training.
"""
from celery import Celery
from .config import settings

# Create Celery app
celery_app = Celery(
    "blessings_tasks",
    broker=settings.celery_broker_url,
    backend=settings.redis_url
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        'app.tasks.*': {'queue': 'blessings_queue'},
    },
    worker_log_color=False,
)