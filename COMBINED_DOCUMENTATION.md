# 🏪 Njuskalo Scraper - Complete System Documentation

## Table of Contents

1. [Project Overview](#project-overview)
2. [Authentication System](#authentication-system)
3. [Configurable API Endpoints](#configurable-api-endpoints)
4. [Configurable Login Endpoints](#configurable-login-endpoints)
5. [Quick Start Guide](#quick-start-guide)
6. [Implementation Summary](#implementation-summary)
7. [Configuration Reference](#configuration-reference)
8. [Security Features](#security-features)
9. [API Documentation](#api-documentation)
10. [Troubleshooting](#troubleshooting)

---

## Project Overview

A comprehensive Python web scraper that extracts store information from njuskalo.hr using a sitemap-based approach. This scraper focuses on finding stores that post in the "Auto moto" category and extracting their address and ad count information.

### 🎯 Purpose

This scraper is designed to:

1. Download the sitemap index XML from https://www.njuskalo.hr/sitemap-index.xml
2. Extract store-related sitemap URLs
3. Download and parse XML/XML.gz files to find store URLs
4. Visit each store page to scrape information
5. Check if stores post in categoryId 2 ("Auto moto" category)
6. Extract store address and number of ads from the entities-count class
7. Save all data to an Excel file and PostgreSQL/MySQL database
8. Send data to external APIs (Dober Avto integration)

### 🚀 Key Features

- **XML Sitemap Processing**: Downloads and processes compressed XML sitemaps
- **Auto Moto Detection**: Automatically identifies vehicle-related stores
- **Vehicle Counting**: Distinguishes between new and used vehicles
- **SSH Tunnel Support**: Routes traffic through remote servers for anonymity
- **Server Compatibility**: Works on headless servers with xvfb-run
- **Database Integration**: MySQL storage with comprehensive data tracking
- **Anti-Detection Measures**: Advanced stealth techniques
- **API Interface**: FastAPI + Celery for automated processing
- **Session Authentication**: Secure login system with configurable endpoints
- **Scheduled Tasks**: Automated weekly scraping and data transmission

---

## Authentication System

The authentication system protects the FastAPI dashboard and all critical API endpoints with a login form that validates credentials against environment variables.

### Configuration

Add the following authentication configuration to your `.env` file:

```bash
# Authentication Configuration
AUTH_USERNAME=admin
AUTH_PASSWORD=njuskalo2025
SECRET_KEY=your-super-secret-key-change-this-in-production
```

### Security Features

#### Session Management

- **Session Tokens**: Secure random tokens generated using `secrets.token_urlsafe(32)`
- **Session Duration**: 24-hour expiry time for all sessions
- **Automatic Cleanup**: Expired sessions are automatically removed
- **HTTP-Only Cookies**: Session tokens stored in HTTP-only cookies for security

#### Protected Endpoints

All critical endpoints now require authentication:

**Dashboard Access:**

- `GET /` - Main dashboard (requires valid session)

**Scraping Operations:**

- `POST /scrape/start` - Start full scraping task
- `POST /scrape/tunnel` - Start tunnel-enabled scraping
- `POST /scrape/test` - Run test scraping task
- `GET /scrape/status/{task_id}` - Get task status

**API Operations:**

- `POST /api/send-data` - Send dealership data to external API

**System Operations:**

- `POST /cleanup/excel-files` - Cleanup old files
- `GET /tasks/recent` - View recent task history

**Public Endpoints:**

- `GET /login` - Login form display
- `POST /login` - Login form processing
- `POST /logout` - User logout
- `GET /health` - Health check endpoint

### Login Process

1. **Access Dashboard**: Navigate to `http://localhost:8080/`
2. **Automatic Redirect**: If not authenticated, automatically redirected to login page
3. **Enter Credentials**: Use configured username and password
4. **Dashboard Access**: Successful login redirects to protected dashboard

### Session Behavior

- **Duration**: Sessions last 24 hours from creation
- **Browser Restart**: Sessions persist across browser restarts via cookies
- **Multiple Tabs**: Single session works across multiple browser tabs

---

## Configurable API Endpoints

The FastAPI dashboard template supports configurable API endpoints through environment variables, allowing you to customize all API URLs.

### Configuration

Add the following to your `.env` file:

```bash
# API Endpoints Configuration (for frontend)
API_BASE_URL=http://localhost:8080
API_LOGIN_ENDPOINT=/login
API_LOGOUT_ENDPOINT=/logout
API_SCRAPE_START_ENDPOINT=/scrape/start
API_SCRAPE_TUNNEL_ENDPOINT=/scrape/tunnel
API_SCRAPE_TEST_ENDPOINT=/scrape/test
API_SCRAPE_STATUS_ENDPOINT=/scrape/status
API_SCRAPE_CANCEL_ENDPOINT=/scrape/cancel
API_CLEANUP_ENDPOINT=/cleanup/excel-files
API_TASKS_RECENT_ENDPOINT=/tasks/recent
API_DATA_SEND_ENDPOINT=/api/send-data
```

### Benefits

1. **Flexibility**: Easily change API endpoints without modifying template code
2. **Environment-Specific Configuration**: Different endpoints for development, staging, and production
3. **Proxy-Friendly**: Support for reverse proxies and custom routing
4. **Maintainability**: Centralized endpoint configuration

### Usage Examples

**Development Environment:**

```bash
API_BASE_URL=http://localhost:8080
API_SCRAPE_START_ENDPOINT=/scrape/start
```

**Production with Reverse Proxy:**

```bash
API_BASE_URL=https://yourdomain.com/api
API_SCRAPE_START_ENDPOINT=/v1/scrape/start
API_SCRAPE_TUNNEL_ENDPOINT=/v1/scrape/tunnel
```

**Custom API Gateway:**

```bash
API_BASE_URL=https://api-gateway.example.com
API_SCRAPE_START_ENDPOINT=/njuskalo/scrape/start
API_SCRAPE_TUNNEL_ENDPOINT=/njuskalo/scrape/tunnel
```

---

## Configurable Login Endpoints

The login endpoints are now fully configurable through environment variables, allowing you to customize the authentication URLs for enhanced security or organizational requirements.

### Configuration

Add these to your `.env` file to customize login endpoints:

```bash
# Authentication Endpoints
API_LOGIN_ENDPOINT=/login          # Login form and authentication
API_LOGOUT_ENDPOINT=/logout        # User logout
```

### Usage Examples

**Standard Configuration (Default):**

```bash
API_LOGIN_ENDPOINT=/login
API_LOGOUT_ENDPOINT=/logout
```

**Custom Endpoints for Security:**

```bash
# Security through obscurity
API_LOGIN_ENDPOINT=/auth/signin
API_LOGOUT_ENDPOINT=/auth/signout

# API versioning
API_LOGIN_ENDPOINT=/v1/auth/login
API_LOGOUT_ENDPOINT=/v1/auth/logout

# Branded paths
API_LOGIN_ENDPOINT=/njuskalo/login
API_LOGOUT_ENDPOINT=/njuskalo/logout
```

**Multi-tenant Setup:**

```bash
# Tenant A
API_LOGIN_ENDPOINT=/tenant-a/login
API_LOGOUT_ENDPOINT=/tenant-a/logout

# Tenant B
API_LOGIN_ENDPOINT=/tenant-b/login
API_LOGOUT_ENDPOINT=/tenant-b/logout
```

### Features

- ✅ **Fully Configurable**: Login GET, Login POST, and Logout POST endpoints
- ✅ **Dynamic Integration**: Templates automatically use configured endpoints
- ✅ **Backward Compatible**: Default endpoints work without configuration
- ✅ **Template Integration**: All forms and redirects use dynamic endpoints

### Implementation Details

Routes are added dynamically based on environment variables:

```python
# Configurable endpoint paths
LOGIN_ENDPOINT = os.getenv("API_LOGIN_ENDPOINT", "/login")
LOGOUT_ENDPOINT = os.getenv("API_LOGOUT_ENDPOINT", "/logout")

# Dynamic route registration
app.add_api_route(LOGIN_ENDPOINT, login_form, methods=["GET"])
app.add_api_route(LOGIN_ENDPOINT, login, methods=["POST"])
app.add_api_route(LOGOUT_ENDPOINT, logout, methods=["POST"])
```

---

## Quick Start Guide

### Setup (First Time)

1. **Configure Credentials** - Edit your `.env` file:

   ```bash
   # Authentication Configuration
   AUTH_USERNAME=admin
   AUTH_PASSWORD=your_secure_password_here
   SECRET_KEY=your-super-secret-key-change-this-in-production
   ```

2. **Generate Secure Secret Key** (recommended):

   ```python
   import secrets
   print(secrets.token_urlsafe(32))
   ```

3. **Start Application**:
   ```bash
   cd /home/srdjan/njuskalohr
   python -m uvicorn api:app --host 0.0.0.0 --port 8080 --reload
   ```

### Web Access

1. **Navigate to Dashboard**: `http://localhost:8080/`
2. **Login**: Use your configured username and password
3. **Dashboard Access**: Full functionality after login
4. **Logout**: Click "Logout" button in header

### Default Credentials

- **Username**: `admin`
- **Password**: `njuskalo2025` (from current .env)

**⚠️ IMPORTANT**: Change the default password in production!

### API Access

For programmatic access, you need a valid session:

```python
import requests

# Login
session = requests.Session()
login_data = {"username": "admin", "password": "njuskalo2025"}
response = session.post("http://localhost:8080/login", data=login_data)

# Use authenticated session for API calls
result = session.post("http://localhost:8080/scrape/start",
                     json={"max_stores": 10})
```

---

## Implementation Summary

### What Was Implemented

**Environment Configuration:**

- Added configurable login/logout endpoints through `API_LOGIN_ENDPOINT` and `API_LOGOUT_ENDPOINT`
- Updated `.env.example` with new configuration options
- Default values: `/login` and `/logout`

**FastAPI Application Changes:**

- Replaced hardcoded route decorators with dynamic route registration
- Added `app.add_api_route()` for flexible endpoint configuration
- Made authentication redirects use configurable endpoints
- Updated context passed to templates with endpoint variables

**Template Updates:**

- **Login Template**: Uses `{{ login_endpoint }}` variable in form action
- **Dashboard Template**: Uses `{{ api_config.endpoints.logout }}` for logout button
- **API Config**: Added login/logout endpoints to JavaScript configuration

**Authentication System:**

- Session-based authentication with 24-hour duration
- HTTP-only cookies for security
- Automatic session cleanup
- Protected all critical API endpoints

**Scheduled Tasks:**

- Weekly tunnel scraper (Monday 2AM)
- Weekly API data sender (Thursday 10AM)
- Celery Beat integration with Redis backend

### Current Configuration

**Environment Variables:**

```bash
# Authentication
AUTH_USERNAME=admin
AUTH_PASSWORD=njuskalo2025
SECRET_KEY=your-super-secret-key-change-this-in-production

# Configurable Endpoints
API_LOGIN_ENDPOINT=/login          # Default: /login
API_LOGOUT_ENDPOINT=/logout        # Default: /logout
API_BASE_URL=http://localhost:8080

# All other API endpoints are configurable...
```

**Routes Created:**

- `GET {LOGIN_ENDPOINT}` → Display login form
- `POST {LOGIN_ENDPOINT}` → Process authentication
- `POST {LOGOUT_ENDPOINT}` → User logout

### Backward Compatibility

- ✅ Existing installations work without changes
- ✅ Default endpoints remain `/login` and `/logout`
- ✅ No breaking changes to existing functionality
- ✅ All authentication features continue working

---

## Configuration Reference

### Complete `.env` Configuration

```bash
# MySQL Database Configuration
DATABASE_HOST=localhost
DATABASE_PORT=3306
DATABASE_NAME=njuskalohr
DATABASE_USER=hellios
DATABASE_PASSWORD=6hell6is6
DATABASE_URL=mysql+pymysql://hellios:6hell6is6@localhost:3306/njuskalohr

# Redis Configuration (for Celery)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_URL=redis://localhost:6379/0

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# FastAPI Configuration
API_HOST=0.0.0.0
API_PORT=8080
API_RELOAD=True

# Authentication Configuration
AUTH_USERNAME=admin
AUTH_PASSWORD=njuskalo2025
SECRET_KEY=your-super-secret-key-change-this-in-production

# API Endpoints Configuration (for frontend)
API_BASE_URL=http://localhost:8080
API_LOGIN_ENDPOINT=/login
API_LOGOUT_ENDPOINT=/logout
API_SCRAPE_START_ENDPOINT=/scrape/start
API_SCRAPE_TUNNEL_ENDPOINT=/scrape/tunnel
API_SCRAPE_TEST_ENDPOINT=/scrape/test
API_SCRAPE_STATUS_ENDPOINT=/scrape/status
API_SCRAPE_CANCEL_ENDPOINT=/scrape/cancel
API_CLEANUP_ENDPOINT=/cleanup/excel-files
API_TASKS_RECENT_ENDPOINT=/tasks/recent
API_DATA_SEND_ENDPOINT=/api/send-data

# Dober Avto API Configuration
DOBER_API_BASE_URL=https://www.doberavto.si/internal-api/v1/
DOBER_API_KEY=prod_key_Um6eeRee5CoG-h6Seikooteequudiwu:031380044
DOBER_API_TIMEOUT=5000
```

---

## Security Features

### Authentication Security

- ✅ **Session-based authentication** (24-hour sessions)
- ✅ **HTTP-only cookies** (XSS protection)
- ✅ **Automatic redirects** (browser-friendly)
- ✅ **Protected API endpoints** (all critical operations)
- ✅ **Environment-based credentials** (secure configuration)
- ✅ **Automatic session cleanup** (expired sessions removed)

### Production Security Recommendations

```bash
# Use HTTPS in production
API_HOST=0.0.0.0
API_PORT=443

# Strong authentication
AUTH_USERNAME=your_admin_user
AUTH_PASSWORD=your_very_secure_password_with_special_chars!
SECRET_KEY=your_cryptographically_secure_secret_key_generated_properly
```

### Security Through Obscurity

```bash
# Custom authentication endpoints
API_LOGIN_ENDPOINT=/x7k9p2/auth
API_LOGOUT_ENDPOINT=/x7k9p2/exit
```

---

## API Documentation

### Authentication Required Endpoints

**Scraping Operations:**

- `POST /scrape/start` - Start full scraping task
  - Parameters: `max_stores` (optional), `use_database` (boolean)
- `POST /scrape/tunnel` - Start tunnel-enabled scraping
  - Enhanced anti-detection and SSH tunnel routing
- `POST /scrape/test` - Run test scraping task
- `GET /scrape/status/{task_id}` - Get task execution status

**API Operations:**

- `POST /api/send-data` - Send dealership data to external API
  - Parameters: `date_filter` (optional), `min_vehicles` (optional)

**System Operations:**

- `POST /cleanup/excel-files` - Cleanup old Excel files
- `GET /tasks/recent` - View recent Celery task history

**Database Operations:**

- `GET /api/users` - List all users with basic information
- `GET /api/ads` - List all ad items with basic information
- `GET /api/pages` - List all pages with basic information
- `GET /api/files` - List all files with basic information
- `GET /api/menus` - List all menu items with basic information

**Publishing Operations:**

- `GET /publish/{uuid}` - Retrieve published ads for user by UUID
  - **Parameters:**
    - `uuid` (path): User UUID identifier
  - **Functionality:**
    - Retrieves user information by UUID
    - Fetches published ads belonging to that user
    - Logs the operation to dedicated log file
  - **Logging:** All requests logged to `/var/log/publish_endpoint.log`
  - **Security:** Authentication required
  - **Response:** JSON with user and ads data or 404 if not found

**Dashboard:**

- `GET /` - Main authenticated dashboard interface

### Public Endpoints

**Authentication:**

- `GET {API_LOGIN_ENDPOINT}` - Display login form
- `POST {API_LOGIN_ENDPOINT}` - Process login credentials
- `POST {API_LOGOUT_ENDPOINT}` - End user session

**Health Check:**

- `GET /health` - Application health status

---

## Publish Endpoint Implementation

### Overview

The `/publish/{uuid}` endpoint provides access to published advertisements for a specific user identified by UUID. This endpoint includes comprehensive logging and error handling.

### Endpoint Details

**URL Pattern:** `GET /publish/{uuid}`

**Authentication:** Required (Session-based)

**Parameters:**

- `uuid` (path parameter): User UUID identifier

### Implementation

```python
@app.get("/publish/{uuid}")
async def get_published_ads(uuid: str, request: Request):
    """
    Retrieve published ads for a user by UUID.

    Args:
        uuid: User UUID identifier
        request: FastAPI request object for authentication

    Returns:
        JSON response with user and ads data
    """
```

### Functionality

1. **User Retrieval**: Fetches user information using provided UUID
2. **Ads Retrieval**: Gets all published ads belonging to the user
3. **Data Formatting**: Processes and formats the response data
4. **Logging**: Records all operations to dedicated log file
5. **Error Handling**: Returns appropriate HTTP status codes

### Response Format

**Success Response (200):**

```json
{
  "user": {
    "uuid": "123e4567-e89b-12d3-a456-426614174000",
    "name": "John Doe",
    "email": "john.doe@example.com",
    "status": "ACTIVE"
  },
  "published_ads": [
    {
      "id": 1,
      "title": "Sample Ad Title",
      "description": "Ad description...",
      "price": 29999,
      "status": "PUBLISHED",
      "created_at": "2025-01-09T10:30:00Z"
    }
  ],
  "total_ads": 1
}
```

**Error Response (404):**

```json
{
  "detail": "User not found"
}
```

### Logging Configuration

**Log File:** `/var/log/publish_endpoint.log`

**Log Format:**

- Timestamp: ISO 8601 format
- Log Level: INFO/ERROR
- User UUID: For tracking requests
- Operation: Action performed
- Result: Success/failure status

**Example Log Entries:**

```
2025-01-09T12:34:56.789Z - INFO - UUID: 123e4567-e89b-12d3-a456-426614174000 - User retrieved successfully
2025-01-09T12:34:56.790Z - INFO - UUID: 123e4567-e89b-12d3-a456-426614174000 - Found 5 published ads
2025-01-09T12:34:56.791Z - INFO - UUID: 123e4567-e89b-12d3-a456-426614174000 - Request completed successfully
```

### Error Handling

- **Invalid UUID Format**: Returns 400 Bad Request
- **User Not Found**: Returns 404 Not Found
- **No Published Ads**: Returns user data with empty ads array
- **Database Errors**: Returns 500 Internal Server Error
- **Authentication Failure**: Returns 401 Unauthorized

### Security Considerations

1. **Authentication Required**: All requests must be authenticated
2. **UUID Validation**: Input validation for UUID format
3. **Data Sanitization**: All output data is properly sanitized
4. **Access Logging**: All access attempts are logged
5. **Error Information**: Minimal error details in responses

### Usage Examples

**cURL Request:**

```bash
curl -X GET "http://localhost:8080/publish/123e4567-e89b-12d3-a456-426614174000" \
     -H "Cookie: session=your_session_cookie"
```

**Python Request:**

```python
import requests

session = requests.Session()
# ... perform login to get session ...

response = session.get(
    "http://localhost:8080/publish/123e4567-e89b-12d3-a456-426614174000"
)
data = response.json()
```

**JavaScript (Frontend):**

```javascript
fetch("/publish/123e4567-e89b-12d3-a456-426614174000", {
  method: "GET",
  credentials: "include", // Include session cookie
})
  .then((response) => response.json())
  .then((data) => console.log(data));
```

### Database Schema Requirements

**Users Table:**

- `uuid` column: VARCHAR(36) or CHAR(36)
- Indexed for optimal performance
- UUID format: Standard UUID v4

**Ads Table:**

- `user_uuid` column: Foreign key to users.uuid
- `status` column: ENUM including 'PUBLISHED' value
- Proper indexing on user_uuid and status

### Performance Considerations

1. **Database Indexing**: Ensure indexes on uuid and status columns
2. **Connection Pooling**: Use connection pooling for database access
3. **Response Caching**: Consider caching for frequently accessed data
4. **Log Rotation**: Configure log rotation for publish endpoint logs

### Monitoring and Maintenance

1. **Log Monitoring**: Monitor `/var/log/publish_endpoint.log` for errors
2. **Performance Metrics**: Track response times and error rates
3. **Database Performance**: Monitor query performance
4. **Disk Space**: Monitor log file growth and implement rotation

---

## Troubleshooting

### Login Issues

**Problem**: Login not working?

**Solutions:**

1. Check `.env` file configuration
2. Verify username and password are correct
3. Ensure `SECRET_KEY` is set
4. Check browser cookies are enabled
5. Restart FastAPI application after `.env` changes

### Custom Endpoints Not Working

**Problem**: Custom login endpoints not responding?

**Solutions:**

1. Verify endpoint paths in `.env` start with `/`
2. Restart application after changing endpoints
3. Check FastAPI logs for route registration
4. Ensure no conflicting routes exist

### Session Expiry

**Problem**: Frequent login requests?

**Solutions:**

1. Sessions last 24 hours - this is by design
2. Check system clock is accurate
3. Browser may be clearing cookies - check settings
4. Multiple users should use different browsers/sessions

### Database Connection Issues

**Problem**: Database errors during scraping?

**Solutions:**

1. Verify MySQL server is running
2. Check database credentials in `.env`
3. Ensure database `njuskalohr` exists
4. Test connection: `mysql -u hellios -p njuskalohr`

### Celery Task Issues

**Problem**: Scheduled tasks not running?

**Solutions:**

1. Ensure Redis server is running
2. Start Celery worker: `celery -A celery_config worker --loglevel=info`
3. Start Celery beat: `celery -A celery_config beat --loglevel=info`
4. Check Redis connection: `redis-cli ping`

### API Data Sender Issues

**Problem**: External API calls failing?

**Solutions:**

1. Verify `DOBER_API_KEY` and `DOBER_API_BASE_URL` in `.env`
2. Check internet connectivity
3. Verify API endpoint is accessible
4. Check for dealership data in database first

### Publish Endpoint Issues

**Problem**: `/publish/{uuid}` returning 404 for valid UUID?

**Solutions:**

1. Verify user exists in database with exact UUID format
2. Check UUID format is valid (36 characters with hyphens)
3. Ensure database connection is working
4. Check user table has proper uuid column

**Problem**: Publish endpoint logging not working?

**Solutions:**

1. Check `/var/log/` directory exists and is writable
2. Verify application has write permissions to log directory
3. Check disk space availability
4. Review log configuration in code
5. Test with: `sudo touch /var/log/publish_endpoint.log && sudo chmod 666 /var/log/publish_endpoint.log`

**Problem**: Published ads not showing up?

**Solutions:**

1. Verify ads table has `status` column with 'PUBLISHED' value
2. Check `user_uuid` foreign key relationship
3. Ensure ads belong to the correct user UUID
4. Verify database indexes on uuid and status columns

**Problem**: Authentication errors on publish endpoint?

**Solutions:**

1. Ensure user is logged in with valid session
2. Check session cookie is being sent with request
3. Verify authentication middleware is working
4. Test other authenticated endpoints first

---

## System Architecture

### Components Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI Web   │    │   Celery Tasks  │    │   MySQL DB      │
│   Dashboard     │◄──►│   (Scraper +    │◄──►│   (Dealership   │
│   (Port 8080)   │    │    API Sender)  │    │    Data)        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │
         │              ┌─────────────────┐
         └─────────────►│   Redis Cache   │
                        │   (Sessions +   │
                        │    Task Queue)  │
                        └─────────────────┘
```

### File Structure

```
njuskalohr/
├── api.py                          # FastAPI application with auth + database endpoints
├── models.py                      # Pydantic models for database schema
├── db_helper.py                   # Simple database connection and queries
├── celery_config.py               # Celery Beat scheduling
├── tasks/
│   └── scraper_tasks.py          # Celery task definitions
├── njuskalo_scraper_chromium.py   # Enhanced tunnel scraper
├── njuskalo_api_data_sender.py    # Database-driven API client
├── templates/
│   ├── dashboard.html            # Authenticated dashboard
│   └── login.html               # Login form
├── requirements.txt              # Python dependencies
├── .env                         # Environment configuration
├── COMBINED_DOCUMENTATION.md      # Complete system documentation
└── run_scraper.py              # Direct scraper execution
```

---

## Maintenance

### Regular Tasks

1. **Monitor Logs**: Check FastAPI and Celery logs regularly
2. **Database Cleanup**: Archive old dealership data periodically
3. **Security Updates**: Keep dependencies updated
4. **Backup Configuration**: Backup `.env` and database regularly

### Performance Optimization

1. **Database Indexing**: Ensure proper indexes on frequently queried columns
2. **Redis Memory**: Monitor Redis memory usage for large task queues
3. **Session Cleanup**: Automatic cleanup runs, but monitor session storage
4. **File Cleanup**: Regular cleanup of generated Excel files

---

_This documentation covers all aspects of the Njuskalo Scraper system including authentication, configuration, API endpoints, and troubleshooting. For specific implementation details, refer to the individual source files._
