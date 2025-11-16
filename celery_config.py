"""
Celery configuration for Njuskalo scraper
"""
import os
import sys

# Ensure we're running in the virtual environment
if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    # Try to load VENV_PATH from .env file
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    venv_path = '.venv'  # Default value

    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if line.strip() and not line.strip().startswith('#'):
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        if key.strip() == 'VENV_PATH':
                            venv_path = value.strip()
                            break

    venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), venv_path, 'bin', 'python3')
    if os.path.exists(venv_python):
        print(f"Restarting script in virtual environment: {venv_python}")
        os.execv(venv_python, [venv_python] + sys.argv)
    else:
        print(f"Warning: Virtual environment not found at {venv_python}")

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