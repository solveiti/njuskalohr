# FastAPI + Celery Integration Guide

## Overview

The Njuskalo scraper has been enhanced with a FastAPI REST API that uses Celery for background task processing and Redis as a message broker. This allows for:

- **Scheduled scraping jobs** running automatically
- **Real-time task monitoring** through a web dashboard
- **RESTful API** for programmatic access
- **Distributed task processing** with multiple workers
- **Web-based management** interface

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   Celery        │    │   Redis         │
│   Web Server    │◄──►│   Worker        │◄──►│   Message       │
│   (Port 8000)   │    │   (Background)  │    │   Broker        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Dashboard │    │   Scheduled     │    │   Task Queue    │
│   (Browser UI)  │    │   Jobs (Beat)   │    │   & Results     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                     ┌─────────────────┐
                     │   PostgreSQL    │
                     │   Database      │
                     └─────────────────┘
```

## Services

### 1. FastAPI Server (api.py)

- **Port**: 8000
- **Purpose**: REST API and web dashboard
- **Features**: Task management, database queries, file downloads

### 2. Celery Worker (start_worker.sh)

- **Purpose**: Execute background scraping tasks
- **Concurrency**: 4 processes by default
- **Features**: Auto-retry, task routing, resource limits

### 3. Celery Beat (start_beat.sh)

- **Purpose**: Schedule periodic tasks
- **Features**: Cron-like scheduling, task distribution
- **Default Jobs**:
  - Daily full scrape (all stores)
  - Hourly test scrape (10 stores)

### 4. Redis

- **Port**: 6379
- **Purpose**: Message broker and result backend
- **Features**: Task queuing, result storage, pub/sub

### 5. Flower (Optional)

- **Port**: 5555
- **Purpose**: Real-time task monitoring
- **Features**: Worker stats, task history, live updates

## API Endpoints

### Task Management

#### Start Scraping Task

```http
POST /scrape/start
Content-Type: application/json

{
  "max_stores": 50,
  "use_database": true
}
```

Response:

```json
{
  "task_id": "abc123-def456",
  "status": "PENDING",
  "message": "Scraping task started with ID: abc123-def456"
}
```

#### Check Task Status

```http
GET /scrape/status/{task_id}
```

Response:

```json
{
  "task_id": "abc123-def456",
  "status": "SUCCESS",
  "message": "Task completed successfully",
  "result": {
    "total_stores_scraped": 50,
    "auto_moto_stores": 12,
    "execution_time_seconds": 245.7,
    "excel_file": "njuskalo_stores_1699123456.xlsx"
  }
}
```

#### Cancel Task

```http
DELETE /scrape/cancel/{task_id}
```

#### Test Scraper

```http
POST /scrape/test
```

### Database Operations

#### Get Database Statistics

```http
GET /database/stats
```

Response:

```json
{
  "total_stores": 1250,
  "valid_stores": 1180,
  "invalid_stores": 70,
  "auto_moto_stores": 245,
  "total_ads": 15420,
  "timestamp": "2024-11-02T21:30:00Z"
}
```

#### List Stores

```http
GET /database/stores?valid_only=true&limit=20&offset=0
```

#### Search Stores

```http
GET /database/search?query=auto&limit=10
```

### System Monitoring

#### Health Check

```http
GET /health
```

Response:

```json
{
  "status": "healthy",
  "celery": "ok",
  "database": "ok",
  "timestamp": "2024-11-02T21:30:00Z"
}
```

#### Worker Status

```http
GET /workers/status
```

#### Recent Tasks

```http
GET /tasks/recent?limit=10
```

### File Management

#### Download Excel File

```http
GET /download/{filename}
```

#### Cleanup Old Files

```http
POST /cleanup/excel-files?days_old=7
```

## Scheduled Jobs

The system includes automatic scheduled jobs managed by Celery Beat:

### Daily Full Scrape

- **Schedule**: Every 24 hours
- **Task**: Complete scraping of all stores
- **Parameters**: No store limit, database enabled

### Hourly Test Scrape

- **Schedule**: Every hour
- **Task**: Limited scraping for monitoring
- **Parameters**: 10 stores max, database enabled

### Custom Schedules

You can modify schedules in `celery_config.py`:

```python
celery_app.conf.beat_schedule = {
    "custom-scrape": {
        "task": "tasks.scraper_tasks.run_full_scrape_task",
        "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM
        "args": (100, True),  # 100 stores, use database
    },
}
```

## Web Dashboard

The dashboard provides a user-friendly interface at http://localhost:8000:

### Features:

- **Real-time statistics** from the database
- **Task control panel** for starting/stopping jobs
- **Live task monitoring** with status updates
- **Quick actions** for testing and cleanup
- **Auto-refresh** every 30 seconds

### Dashboard Sections:

1. **Statistics Cards**: Total/valid/invalid stores, active tasks
2. **Control Panel**: Start scraping, run tests, cleanup files
3. **Recent Tasks**: Live task list with status and controls
4. **Notifications**: Success/error messages

## Deployment Options

### Option 1: Local Development

```bash
# Install dependencies
python setup_api.py

# Start all services
./start_all.sh
```

### Option 2: Docker Compose

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Option 3: Production (Systemd)

```bash
# Create service files
python setup_api.py

# Install services
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable njuskalo-worker njuskalo-beat njuskalo-api
sudo systemctl start njuskalo-worker njuskalo-beat njuskalo-api
```

## Configuration

### Environment Variables (.env)

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/njuskalohr

# Redis
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# API
API_HOST=0.0.0.0
API_PORT=8000
```

### Celery Configuration (celery_config.py)

- **Serialization**: JSON format
- **Timezone**: Europe/Zagreb
- **Rate Limiting**: 10 tasks per minute
- **Result Expiry**: 1 hour
- **Worker Prefetch**: 1 task at a time

## Monitoring & Troubleshooting

### Logs

```bash
# View real-time logs
tail -f celery_worker.log celery_beat.log

# API logs (if running in background)
tail -f api.log
```

### Redis Monitoring

```bash
# Connect to Redis CLI
redis-cli

# Monitor commands
redis-cli monitor

# Check memory usage
redis-cli info memory
```

### Task Debugging

```bash
# List active tasks
celery -A celery_config inspect active

# List scheduled tasks
celery -A celery_config inspect scheduled

# Purge all tasks
celery -A celery_config purge
```

### Common Issues

1. **Redis Connection Error**

   - Check if Redis is running: `redis-cli ping`
   - Start Redis: `sudo systemctl start redis-server`

2. **Worker Not Processing Tasks**

   - Check worker logs: `tail -f celery_worker.log`
   - Restart worker: `./stop_all.sh && ./start_all.sh`

3. **Database Connection Error**

   - Verify .env configuration
   - Test connection: `python test_database.py`

4. **Port Already in Use**
   - Change API_PORT in .env
   - Kill existing processes: `pkill -f "python api.py"`

## Performance Tuning

### Worker Scaling

```bash
# Start multiple workers
celery -A celery_config worker --concurrency=8

# Start workers on different queues
celery -A celery_config worker -Q scraping,cleanup
```

### Resource Limits

```python
# In celery_config.py
celery_app.conf.update(
    worker_prefetch_multiplier=1,
    task_soft_time_limit=3600,  # 1 hour
    task_time_limit=7200,       # 2 hours
)
```

### Redis Optimization

```bash
# In redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
```

## Security Considerations

1. **Environment Variables**: Never commit .env files
2. **API Access**: Consider adding authentication for production
3. **Network Security**: Use firewall rules for Redis/PostgreSQL
4. **Resource Limits**: Set appropriate memory/CPU limits
5. **Monitoring**: Set up alerts for failed tasks

## Integration Examples

### Python Client

```python
import requests

# Start scraping
response = requests.post("http://localhost:8000/scrape/start",
                        json={"max_stores": 20})
task_id = response.json()["task_id"]

# Check status
status = requests.get(f"http://localhost:8000/scrape/status/{task_id}")
print(status.json())
```

### Webhook Integration

```python
# In your application
def notify_completion(task_id, result):
    # Send notification when task completes
    webhook_url = "https://your-app.com/webhook"
    requests.post(webhook_url, json={"task_id": task_id, "result": result})
```

### Scheduled Reports

```python
# Custom task for daily reports
@celery_app.task
def generate_daily_report():
    with NjuskaloDatabase() as db:
        stats = db.get_database_stats()
        send_email_report(stats)
```
