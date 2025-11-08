# 🔐 Authentication Quick Start Guide

## Setup (First Time)

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

3. **Restart Application**:

   ```bash
   # Stop existing FastAPI process
   pkill -f "uvicorn.*api:app"

   # Start with new authentication
   cd /home/srdjan/njuskalohr
   python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
   ```

## Usage

### 🌐 Web Access

1. **Navigate to Dashboard**: `http://localhost:8000/`
2. **Login**: Use your configured username and password
3. **Dashboard Access**: Full functionality after login
4. **Logout**: Click "Logout" button in header

### 🔑 Default Credentials

- **Username**: `admin`
- **Password**: `njuskalo2025` (from current .env)

**⚠️ IMPORTANT**: Change the default password in production!

### 📱 API Access

For programmatic access, you need a valid session:

```python
import requests

# Login
session = requests.Session()
login_data = {"username": "admin", "password": "njuskalo2025"}
response = session.post("http://localhost:8000/login", data=login_data)

# Use authenticated session for API calls
result = session.post("http://localhost:8000/scrape/start",
                     json={"max_stores": 10})
```

## 🛡️ Security Features

- ✅ **Session-based authentication** (24-hour sessions)
- ✅ **HTTP-only cookies** (XSS protection)
- ✅ **Automatic redirects** (browser-friendly)
- ✅ **Protected API endpoints** (all critical operations)
- ✅ **Environment-based credentials** (secure configuration)
- ✅ **Automatic session cleanup** (expired sessions removed)

## 🔧 Configuration Options

### Strong Password Example

```bash
AUTH_USERNAME=scrapadmin
AUTH_PASSWORD=Scr@pe2025!Secure#Pass
SECRET_KEY=ZjB6MWRkNzAtYmExNy00ZDYwLWE1YjMtMzI0ZGE3NGY4YzQx
```

### Production Settings

```bash
# Use HTTPS in production
API_HOST=0.0.0.0
API_PORT=443

# Strong authentication
AUTH_USERNAME=your_admin_user
AUTH_PASSWORD=your_very_secure_password
SECRET_KEY=your_cryptographically_secure_secret_key
```

## 🚨 Troubleshooting

### Login Not Working?

1. **Check .env file**: Verify AUTH_USERNAME and AUTH_PASSWORD are set
2. **Restart app**: Changes require application restart
3. **Clear cookies**: Clear browser cookies if issues persist
4. **Check credentials**: Verify username/password match .env exactly

### Session Expires Quickly?

- Sessions last 24 hours by default
- Check system clock synchronization
- Verify SECRET_KEY is consistent

### API Returns 401?

- Ensure you're authenticated via web login first
- Check session cookie is being sent with requests
- Verify session hasn't expired

## 🎯 Quick Test

```bash
# Test authentication is working
curl -c cookies.txt -d "username=admin&password=njuskalo2025" http://localhost:8000/login
curl -b cookies.txt http://localhost:8000/health
```

## 📚 Full Documentation

See `AUTHENTICATION_GUIDE.md` for complete implementation details and security considerations.

---

**Remember**: Always change default credentials in production environments!
