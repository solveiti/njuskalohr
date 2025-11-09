"""
FastAPI application for Njuskalo scraper with Celery integration
"""
import os
import sys
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import asyncio
import json
import hashlib
import secrets

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request, Form, Cookie, Response
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from celery_config import celery_app
from tasks.scraper_tasks import (
    run_full_scrape_task,
    run_auto_moto_only_scrape_task,
    test_scraper_task,
    get_database_stats_task,
    cleanup_old_excel_files_task,
    run_enhanced_tunnel_scrape_task,
    send_dealership_data_to_api_task
)
from database import NjuskaloDatabase

# Create FastAPI app
app = FastAPI(
    title="Njuskalo Scraper API",
    description="API for managing Njuskalo store scraping with Celery and RabbitMQ",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    root_path="/njuskalo"
)

# Create templates directory
templates = Jinja2Templates(directory="templates")

# Custom exception for authentication
class AuthenticationRequired(HTTPException):
    def __init__(self):
        super().__init__(status_code=401, detail="Authentication required")

# Exception handler for authentication redirects
@app.exception_handler(AuthenticationRequired)
async def auth_exception_handler(request: Request, exc: AuthenticationRequired):
    """Redirect unauthenticated users to login page"""
    # For browser requests (HTML), redirect to login
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        return RedirectResponse(url="/njuskalo/login", status_code=302)
    # For API requests (JSON), return 401
    else:
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication required"}
        )

# Authentication configuration
AUTH_USERNAME = os.getenv("AUTH_USERNAME", "admin")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "admin")
SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key-change-this")

# Configurable endpoint paths
LOGIN_ENDPOINT = os.getenv("API_LOGIN_ENDPOINT", "/login")
LOGOUT_ENDPOINT = os.getenv("API_LOGOUT_ENDPOINT", "/logout")

# Session storage (in production, use Redis or database)
active_sessions = {}

def create_session_token() -> str:
    """Create a secure session token"""
    return secrets.token_urlsafe(32)

def verify_credentials(username: str, password: str) -> bool:
    """Verify username and password against environment variables"""
    return username == AUTH_USERNAME and password == AUTH_PASSWORD

def create_session(response: Response) -> str:
    """Create a new session and set cookie"""
    session_token = create_session_token()
    active_sessions[session_token] = {
        "created_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(hours=24)
    }
    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=86400,  # 24 hours
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax"
    )
    return session_token

def verify_session(session_token: Optional[str] = Cookie(None)) -> bool:
    """Verify if session token is valid and not expired"""
    if not session_token or session_token not in active_sessions:
        return False

    session = active_sessions[session_token]
    if datetime.now() > session["expires_at"]:
        # Remove expired session
        del active_sessions[session_token]
        return False

    return True

def require_auth(session_token: Optional[str] = Cookie(None)):
    """Dependency to require authentication"""
    if not verify_session(session_token):
        raise AuthenticationRequired()
    return True

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

class ApiDataRequest(BaseModel):
    scraping_date: Optional[str] = None  # YYYY-MM-DD format, None for today
    min_vehicles: int = 5

class LoginRequest(BaseModel):
    username: str
    password: str


# Login endpoint functions
async def login_form(request: Request):
    """Display login form"""
    context = {
        "request": request,
        "login_endpoint": LOGIN_ENDPOINT
    }
    return templates.TemplateResponse("login.html", context)

async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Process login form"""
    if verify_credentials(username, password):
        # Create redirect response and set cookie on it
        redirect_response = RedirectResponse(url="/njuskalo/", status_code=302)
        session_token = create_session_token()
        active_sessions[session_token] = {
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(hours=24)
        }
        redirect_response.set_cookie(
            key="session_token",
            value=session_token,
            max_age=86400,  # 24 hours
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax"
        )
        return redirect_response
    else:
        # Return to login with error
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "login_endpoint": LOGIN_ENDPOINT,
                "error": "Invalid username or password"
            }
        )

async def logout(response: Response, session_token: Optional[str] = Cookie(None)):
    """Logout user by invalidating session"""
    if session_token and session_token in active_sessions:
        del active_sessions[session_token]

    response.delete_cookie("session_token")
    return RedirectResponse(url=LOGIN_ENDPOINT, status_code=302)

# Add configurable login endpoints dynamically
app.add_api_route(LOGIN_ENDPOINT, login_form, methods=["GET"], response_class=HTMLResponse)
app.add_api_route(LOGIN_ENDPOINT, login, methods=["POST"])
app.add_api_route(LOGOUT_ENDPOINT, logout, methods=["POST"])

"""
# Root endpoint (protected)
@app.get("/", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
async def read_root(request: Request):

    try:
        # Get database stats
        with NjuskaloDatabase() as db:
            db_stats = db.get_database_stats()
    except Exception:
        db_stats = {"total_stores": 0, "valid_stores": 0, "invalid_stores": 0}

    # Get active tasks
    active_tasks = celery_app.control.inspect().active()
    scheduled_tasks = celery_app.control.inspect().scheduled()

    # API endpoints configuration from environment
    api_config = {
        "base_url": os.getenv("API_BASE_URL", "http://localhost:8000"),
        "endpoints": {
            "login": os.getenv("API_LOGIN_ENDPOINT", "/login"),
            "logout": os.getenv("API_LOGOUT_ENDPOINT", "/logout"),
            "scrape_start": os.getenv("API_SCRAPE_START_ENDPOINT", "/scrape/start"),
            "scrape_tunnel": os.getenv("API_SCRAPE_TUNNEL_ENDPOINT", "/scrape/tunnel"),
            "scrape_test": os.getenv("API_SCRAPE_TEST_ENDPOINT", "/scrape/test"),
            "scrape_status": os.getenv("API_SCRAPE_STATUS_ENDPOINT", "/scrape/status"),
            "scrape_cancel": os.getenv("API_SCRAPE_CANCEL_ENDPOINT", "/scrape/cancel"),
            "cleanup": os.getenv("API_CLEANUP_ENDPOINT", "/cleanup/excel-files"),
            "tasks_recent": os.getenv("API_TASKS_RECENT_ENDPOINT", "/tasks/recent"),
            "api_send_data": os.getenv("API_DATA_SEND_ENDPOINT", "/api/send-data")
        }
    }

    context = {
        "request": request,
        "db_stats": db_stats,
        "active_tasks": active_tasks or {},
        "scheduled_tasks": scheduled_tasks or {},
        "timestamp": datetime.now().isoformat(),
        "api_config": api_config
    }

    return templates.TemplateResponse("dashboard.html", context)

"""
@app.get("/njuskalo/", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
async def njuskalo_dashboard(request: Request):
    """Dashboard accessible via /njuskalo/ path"""
    # Reuse the same logic as the root route
    try:
        # Get database stats
        with NjuskaloDatabase() as db:
            db_stats = db.get_database_stats()
    except Exception:
        db_stats = {"total_stores": 0, "valid_stores": 0, "invalid_stores": 0}

    # Get active tasks
    active_tasks = celery_app.control.inspect().active()
    scheduled_tasks = celery_app.control.inspect().scheduled()

    # API endpoints configuration from environment
    api_config = {
        "base_url": os.getenv("API_BASE_URL", "http://localhost:8000"),
        "endpoints": {
            "login": os.getenv("API_LOGIN_ENDPOINT", "/login"),
            "logout": os.getenv("API_LOGOUT_ENDPOINT", "/logout"),
            "scrape_start": os.getenv("API_SCRAPE_START_ENDPOINT", "/scrape/start"),
            "scrape_tunnel": os.getenv("API_SCRAPE_TUNNEL_ENDPOINT", "/scrape/tunnel"),
            "scrape_test": os.getenv("API_SCRAPE_TEST_ENDPOINT", "/scrape/test"),
            "scrape_status": os.getenv("API_SCRAPE_STATUS_ENDPOINT", "/scrape/status"),
            "scrape_cancel": os.getenv("API_SCRAPE_CANCEL_ENDPOINT", "/scrape/cancel"),
            "cleanup": os.getenv("API_CLEANUP_ENDPOINT", "/cleanup/excel-files"),
            "tasks_recent": os.getenv("API_TASKS_RECENT_ENDPOINT", "/tasks/recent"),
            "api_send_data": os.getenv("API_DATA_SEND_ENDPOINT", "/api/send-data")
        }
    }

    context = {
        "request": request,
        "db_stats": db_stats,
        "active_tasks": active_tasks or {},
        "scheduled_tasks": scheduled_tasks or {},
        "timestamp": datetime.now().isoformat(),
        "api_config": api_config
    }

    return templates.TemplateResponse("dashboard.html", context)


# Also add a route for /njuskalo (without trailing slash) to redirect to /njuskalo/
@app.get("/njuskalo")
async def njuskalo_redirect():
    """Redirect /njuskalo to /njuskalo/ (root dashboard)"""
    return RedirectResponse(url="/njuskalo/", status_code=301)

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
@app.post("/scrape/start", response_model=TaskResponse, dependencies=[Depends(require_auth)])
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


@app.post("/scrape/auto-moto", response_model=TaskResponse, dependencies=[Depends(require_auth)])
async def start_auto_moto_scraping(request: ScrapeRequest):
    """Start auto moto only scraping task (most efficient for car data)"""
    try:
        task = run_auto_moto_only_scrape_task.delay(
            max_stores=request.max_stores
        )

        return TaskResponse(
            task_id=task.id,
            status="PENDING",
            message=f"Auto moto scraping task started with ID: {task.id}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start auto moto scraping task: {str(e)}")


@app.post("/scrape/tunnel", response_model=TaskResponse, dependencies=[Depends(require_auth)])
async def start_tunnel_scraping(request: ScrapeRequest):
    """Start enhanced tunnel-enabled scraping task (most secure and feature-rich)"""
    try:
        task = run_enhanced_tunnel_scrape_task.delay(
            max_stores=request.max_stores,
            use_database=request.use_database
        )

        return TaskResponse(
            task_id=task.id,
            status="PENDING",
            message=f"Enhanced tunnel scraping task started with ID: {task.id}. Using SSH tunnels for anonymity and enhanced features."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start tunnel scraping task: {str(e)}")


@app.post("/api/send-data", response_model=TaskResponse, dependencies=[Depends(require_auth)])
async def send_dealership_data_to_api(request: ApiDataRequest):
    """Send dealership data to Dober Avto API"""
    try:
        task = send_dealership_data_to_api_task.delay(
            scraping_date=request.scraping_date,
            min_vehicles=request.min_vehicles
        )

        date_msg = request.scraping_date if request.scraping_date else "today"
        return TaskResponse(
            task_id=task.id,
            status="PENDING",
            message=f"API data sender task started with ID: {task.id}. Sending dealership data for {date_msg} (min vehicles: {request.min_vehicles})."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start API data sender task: {str(e)}")


# Get task status
@app.get("/scrape/status/{task_id}", dependencies=[Depends(require_auth)])
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
@app.post("/scrape/test", response_model=TaskResponse, dependencies=[Depends(require_auth)])
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
@app.get("/tasks/recent", dependencies=[Depends(require_auth)])
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
@app.post("/cleanup/excel-files", dependencies=[Depends(require_auth)])
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
    """Download generated Excel files from datadump directory"""
    try:
        # Look for files in datadump directory
        datadump_dir = "datadump"
        file_path = os.path.join(datadump_dir, filename)

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

    if reload:
        # Use import string for reload mode
        uvicorn.run("api:app", host=host, port=port, reload=reload)
    else:
        # Use app object for non-reload mode
        uvicorn.run(app, host=host, port=port, reload=reload)