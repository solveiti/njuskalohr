"""
Celery configuration for Njuskalo scraper
"""
import os
from celery import Celery
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create Celery instance
celery_app = Celery(
    "njuskalo_scraper",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
    include=["tasks.scraper_tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Zagreb",
    enable_utc=True,
    task_track_started=True,
    task_annotations={
        "*": {"rate_limit": "10/m"}  # Rate limit tasks
    },
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    result_expires=3600,  # Results expire after 1 hour
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "scrape-stores-daily": {
        "task": "tasks.scraper_tasks.run_full_scrape_task",
        "schedule": 86400.0,  # Run daily (24 hours)
        "args": (None, True),  # max_stores=None, use_database=True
    },
    "scrape-stores-hourly-test": {
        "task": "tasks.scraper_tasks.run_full_scrape_task",
        "schedule": 3600.0,  # Run hourly for testing
        "args": (10, True),  # max_stores=10, use_database=True
    },
}

if __name__ == "__main__":
    celery_app.start()