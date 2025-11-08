# Authentication System Documentation

This document describes the session-based authentication system implemented for the Njuskalo Scraper FastAPI dashboard.

## Overview

The authentication system protects the FastAPI dashboard and all critical API endpoints with a login form that validates credentials against environment variables.

## Configuration

### Environment Variables

Add the following authentication configuration to your `.env` file:

```bash
# Authentication Configuration
AUTH_USERNAME=admin
AUTH_PASSWORD=your_secure_password_here
SECRET_KEY=your-super-secret-key-change-this-in-production
```

### Configuration Details

- **`AUTH_USERNAME`**: Username for dashboard access (default: "admin")
- **`AUTH_PASSWORD`**: Password for dashboard access (default: "admin" - **change this!**)
- **`SECRET_KEY`**: Secret key for session management (change in production)

## Security Features

### Session Management

- **Session Tokens**: Secure random tokens generated using `secrets.token_urlsafe(32)`
- **Session Duration**: 24-hour expiry time for all sessions
- **Automatic Cleanup**: Expired sessions are automatically removed
- **HTTP-Only Cookies**: Session tokens stored in HTTP-only cookies for security

### Protected Endpoints

All critical endpoints now require authentication:

#### Dashboard Access

- `GET /` - Main dashboard (requires valid session)

#### Scraping Operations

- `POST /scrape/start` - Start full scraping task
- `POST /scrape/tunnel` - Start tunnel-enabled scraping
- `POST /scrape/auto-moto` - Start auto-moto scraping
- `POST /scrape/test` - Run test scraping task
- `GET /scrape/status/{task_id}` - Get task status

#### API Operations

- `POST /api/send-data` - Send dealership data to external API

#### System Operations

- `POST /cleanup/excel-files` - Cleanup old files
- `GET /tasks/recent` - View recent task history

#### Public Endpoints

The following endpoints remain public:

- `GET /login` - Login form display
- `POST /login` - Login form processing
- `POST /logout` - User logout
- `GET /health` - Health check endpoint

## Usage

### Login Process

1. **Access Dashboard**: Navigate to `http://localhost:8000/`
2. **Automatic Redirect**: If not authenticated, automatically redirected to `/login`
3. **Enter Credentials**: Use configured username and password
4. **Dashboard Access**: Successful login redirects to protected dashboard

### Logout Process

1. **Logout Button**: Click "Logout" button in dashboard header
2. **Confirmation**: Confirm logout in browser dialog
3. **Session Cleanup**: Session token invalidated and cookie removed
4. **Redirect**: Automatically redirected to login page

### Session Behavior

- **Duration**: Sessions last 24 hours from creation
- **Inactivity**: No automatic logout on inactivity (24-hour fixed expiry)
- **Browser Restart**: Sessions persist across browser restarts via cookies
- **Multiple Tabs**: Single session works across multiple browser tabs

## Implementation Details

### Authentication Flow

```
User Request → Check Session Cookie → Valid? → Allow Access
                      ↓                   ↓
              Invalid/Missing         Redirect to Login
                      ↓                       ↓
              Redirect to Login       Enter Credentials
                                             ↓
                                     Verify Against .env
                                             ↓
                                     Create Session Cookie
                                             ↓
                                     Redirect to Dashboard
```

### Code Structure

#### Session Management Functions

- `create_session_token()`: Generate secure session tokens
- `verify_credentials()`: Validate username/password against environment
- `create_session()`: Create new session and set cookie
- `verify_session()`: Check session validity and expiration
- `require_auth()`: FastAPI dependency for endpoint protection

#### Storage

- **Development**: In-memory session storage (`active_sessions` dictionary)
- **Production Recommendation**: Use Redis or database for session storage

### Security Considerations

#### Development vs Production

**Development (Current):**

- HTTP-only cookies (secure=False)
- In-memory session storage
- Basic username/password authentication

**Production Recommendations:**

1. **HTTPS**: Set `secure=True` for cookies in production
2. **Redis/Database**: Use persistent session storage
3. **Strong Passwords**: Use complex passwords and consider 2FA
4. **Rate Limiting**: Implement login attempt rate limiting
5. **Session Rotation**: Consider implementing session rotation

## Troubleshooting

### Common Issues

#### 1. Login Loop (Redirects back to login)

**Cause**: Session creation failing or cookies not being set
**Solution**:

- Check browser cookie settings
- Verify SECRET_KEY is set in .env
- Check browser developer tools for cookie issues

#### 2. "Authentication required" on API calls

**Cause**: Frontend making API calls without valid session
**Solution**:

- Ensure user is logged in through web interface
- Check session cookie is present in requests
- Verify session hasn't expired

#### 3. Credentials not working

**Cause**: Environment variables not loaded or incorrect values
**Solution**:

- Verify .env file contains AUTH_USERNAME and AUTH_PASSWORD
- Restart FastAPI application after .env changes
- Check for typos in credentials

### Debugging

Enable debug logging to troubleshoot authentication issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Migration Guide

### For Existing Installations

1. **Add Authentication Variables**: Add AUTH_USERNAME, AUTH_PASSWORD, and SECRET_KEY to .env
2. **Restart Application**: Restart FastAPI server to load new configuration
3. **First Login**: Use configured credentials to access dashboard
4. **Update Bookmarks**: Update any bookmarks to account for login requirement

### Upgrading Security

1. **Change Default Password**: Immediately change from default "admin" password
2. **Generate Strong Secret**: Use cryptographically secure random string for SECRET_KEY
3. **Consider HTTPS**: Enable HTTPS in production environments
4. **Regular Rotation**: Periodically rotate passwords and secret keys

## API Integration

For programmatic access to protected endpoints, include session cookie:

```python
import requests

# Login to get session
login_data = {"username": "admin", "password": "your_password"}
response = requests.post("http://localhost:8000/login", data=login_data)
cookies = response.cookies

# Use session for API calls
api_response = requests.post(
    "http://localhost:8000/scrape/start",
    json={"max_stores": 10},
    cookies=cookies
)
```

## Monitoring

### Session Metrics

Monitor the `active_sessions` dictionary for:

- Number of active sessions
- Session creation rate
- Expired session cleanup

### Security Events

Log the following events:

- Successful logins
- Failed login attempts
- Session expirations
- Logout events

This provides audit trail and helps detect security issues.
