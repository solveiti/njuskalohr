"""
FastAPI application for Njuskalo scraper with Celery integration
"""
import os
import sys
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio
import json

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from celery_config import celery_app
from tasks.scraper_tasks import run_full_scrape_task, test_scraper_task, get_database_stats_task, cleanup_old_excel_files_task
from database import NjuskaloDatabase

# Create FastAPI app
app = FastAPI(
    title="Njuskalo Scraper API",
    description="API for managing Njuskalo store scraping with Celery and RabbitMQ",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Create templates directory
templates = Jinja2Templates(directory="templates")

# Pydantic models
class ScrapeRequest(BaseModel):
    max_stores: Optional[int] = None
    use_database: bool = True
    headless: bool = True

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

class ScrapeResult(BaseModel):
    task_id: str
    status: str
    total_stores_scraped: Optional[int] = None
    auto_moto_stores: Optional[int] = None
    execution_time_seconds: Optional[float] = None
    excel_file: Optional[str] = None
    database_stats: Optional[Dict] = None
    error: Optional[str] = None

class ScheduleRequest(BaseModel):
    task_name: str
    cron_expression: str
    max_stores: Optional[int] = None
    use_database: bool = True


# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Main dashboard page"""
    try:
        # Get database stats
        with NjuskaloDatabase() as db:
            db_stats = db.get_database_stats()
    except Exception:
        db_stats = {"total_stores": 0, "valid_stores": 0, "invalid_stores": 0}

    # Get active tasks
    active_tasks = celery_app.control.inspect().active()
    scheduled_tasks = celery_app.control.inspect().scheduled()

    context = {
        "request": request,
        "db_stats": db_stats,
        "active_tasks": active_tasks or {},
        "scheduled_tasks": scheduled_tasks or {},
        "timestamp": datetime.now().isoformat()
    }

    return templates.TemplateResponse("dashboard.html", context)


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Celery
        celery_status = celery_app.control.inspect().ping()
        celery_ok = bool(celery_status)

        # Check database
        try:
            with NjuskaloDatabase() as db:
                db.get_database_stats()
            db_ok = True
        except Exception:
            db_ok = False

        return {
            "status": "healthy" if (celery_ok and db_ok) else "degraded",
            "celery": "ok" if celery_ok else "error",
            "database": "ok" if db_ok else "error",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


# Start scraping task
@app.post("/scrape/start", response_model=TaskResponse)
async def start_scraping(request: ScrapeRequest):
    """Start a new scraping task"""
    try:
        task = run_full_scrape_task.delay(
            max_stores=request.max_stores,
            use_database=request.use_database
        )

        return TaskResponse(
            task_id=task.id,
            status="PENDING",
            message=f"Scraping task started with ID: {task.id}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start scraping task: {str(e)}")


# Get task status
@app.get("/scrape/status/{task_id}")
async def get_task_status(task_id: str):
    """Get the status of a scraping task"""
    try:
        task = celery_app.AsyncResult(task_id)

        if task.state == "PENDING":
            response = {
                "task_id": task_id,
                "status": "PENDING",
                "message": "Task is waiting to be processed"
            }
        elif task.state == "PROGRESS":
            response = {
                "task_id": task_id,
                "status": "PROGRESS",
                "message": "Task is in progress",
                "progress": task.info
            }
        elif task.state == "SUCCESS":
            response = {
                "task_id": task_id,
                "status": "SUCCESS",
                "message": "Task completed successfully",
                "result": task.result
            }
        elif task.state == "FAILURE":
            response = {
                "task_id": task_id,
                "status": "FAILURE",
                "message": "Task failed",
                "error": str(task.info)
            }
        else:
            response = {
                "task_id": task_id,
                "status": task.state,
                "message": f"Task is in state: {task.state}"
            }

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")


# Cancel task
@app.delete("/scrape/cancel/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a running task"""
    try:
        celery_app.control.revoke(task_id, terminate=True)
        return {"task_id": task_id, "status": "CANCELLED", "message": "Task cancelled successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel task: {str(e)}")


# Test scraper
@app.post("/scrape/test", response_model=TaskResponse)
async def test_scraper():
    """Run a test scraping task"""
    try:
        task = test_scraper_task.delay()
        return TaskResponse(
            task_id=task.id,
            status="PENDING",
            message=f"Test task started with ID: {task.id}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start test task: {str(e)}")


# Database stats
@app.get("/database/stats")
async def get_database_stats():
    """Get database statistics"""
    try:
        task = get_database_stats_task.delay()
        result = task.get(timeout=10)  # Wait up to 10 seconds
        return result
    except Exception as e:
        # Fallback to direct database query
        try:
            with NjuskaloDatabase() as db:
                stats = db.get_database_stats()
                return {**stats, "timestamp": datetime.now().isoformat()}
        except Exception as db_error:
            raise HTTPException(status_code=500, detail=f"Failed to get database stats: {str(db_error)}")


# List stores
@app.get("/database/stores")
async def list_stores(valid_only: bool = True, limit: int = 50, offset: int = 0):
    """List stores from database"""
    try:
        with NjuskaloDatabase() as db:
            if valid_only:
                stores = db.get_all_valid_stores()
            else:
                all_valid = db.get_all_valid_stores()
                all_invalid = db.get_invalid_stores()
                stores = all_valid + all_invalid

            # Apply pagination
            total = len(stores)
            paginated_stores = stores[offset:offset + limit]

            return {
                "stores": paginated_stores,
                "total": total,
                "limit": limit,
                "offset": offset,
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list stores: {str(e)}")


# Search stores
@app.get("/database/search")
async def search_stores(query: str, limit: int = 20):
    """Search stores by name or URL"""
    try:
        with NjuskaloDatabase() as db:
            stores = db.get_all_valid_stores()

            # Filter stores based on query
            matching_stores = []
            query_lower = query.lower()

            for store in stores:
                results = store.get('results', {})
                name = results.get('name', '').lower()
                url = store['url'].lower()

                if query_lower in name or query_lower in url:
                    matching_stores.append(store)

            # Apply limit
            limited_stores = matching_stores[:limit]

            return {
                "stores": limited_stores,
                "total_matches": len(matching_stores),
                "query": query,
                "limit": limit,
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search stores: {str(e)}")


# Worker status
@app.get("/workers/status")
async def get_worker_status():
    """Get Celery worker status"""
    try:
        inspect = celery_app.control.inspect()

        stats = inspect.stats()
        active = inspect.active()
        scheduled = inspect.scheduled()
        reserved = inspect.reserved()

        return {
            "stats": stats or {},
            "active_tasks": active or {},
            "scheduled_tasks": scheduled or {},
            "reserved_tasks": reserved or {},
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get worker status: {str(e)}")


# List recent tasks
@app.get("/tasks/recent")
async def get_recent_tasks(limit: int = 10):
    """Get recent tasks"""
    try:
        inspect = celery_app.control.inspect()

        # Get active tasks
        active = inspect.active() or {}

        # Get reserved tasks
        reserved = inspect.reserved() or {}

        # Combine and format
        all_tasks = []

        for worker, tasks in active.items():
            for task in tasks:
                all_tasks.append({
                    "worker": worker,
                    "status": "ACTIVE",
                    **task
                })

        for worker, tasks in reserved.items():
            for task in tasks:
                all_tasks.append({
                    "worker": worker,
                    "status": "RESERVED",
                    **task
                })

        # Sort by time and limit
        all_tasks.sort(key=lambda x: x.get('time_start', 0), reverse=True)
        limited_tasks = all_tasks[:limit]

        return {
            "tasks": limited_tasks,
            "total": len(all_tasks),
            "limit": limit,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent tasks: {str(e)}")


# Cleanup old files
@app.post("/cleanup/excel-files")
async def cleanup_excel_files(days_old: int = 7):
    """Clean up old Excel files"""
    try:
        task = cleanup_old_excel_files_task.delay(days_old=days_old)
        return TaskResponse(
            task_id=task.id,
            status="PENDING",
            message=f"Cleanup task started with ID: {task.id}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start cleanup task: {str(e)}")


# Download Excel file
@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download generated Excel files"""
    try:
        file_path = os.path.join(os.getcwd(), filename)
        if os.path.exists(file_path) and filename.endswith('.xlsx'):
            return FileResponse(
                path=file_path,
                filename=filename,
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        else:
            raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")


if __name__ == "__main__":
    # Configuration from environment
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    reload = os.getenv("API_RELOAD", "True").lower() == "true"

    uvicorn.run(app, host=host, port=port, reload=reload)