"""
Celery configuration for Njuskalo scraper
"""
import os
from celery import Celery
from celery.schedules import crontab
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
    "scrape-stores-weekly-tunnel": {
        "task": "tasks.scraper_tasks.run_enhanced_tunnel_scrape_task",
        "schedule": crontab(hour=2, minute=0, day_of_week=1),  # Run every Monday at 2:00 AM
        "args": (None, True),  # max_stores=None, use_database=True
    },
    "send-api-data-weekly": {
        "task": "tasks.scraper_tasks.send_dealership_data_to_api_task",
        "schedule": crontab(hour=10, minute=0, day_of_week=4),  # Run every Thursday at 10:00 AM
        "args": (None, 5),  # scraping_date=None (today), min_vehicles=5
    },
}

if __name__ == "__main__":
    celery_app.start()