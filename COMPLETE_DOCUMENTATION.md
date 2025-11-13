# 🏪 Njuskalo HR - Complete System Documentation

## Table of Contents

1. [Project Overview](#project-overview)
2. [Stealth Publish System](#stealth-publish-system)
3. [Two-Factor Authentication (2FA)](#two-factor-authentication-2fa)
4. [UUID Session Management](#uuid-session-management)
5. [Installation & Setup](#installation--setup)
6. [Usage Examples](#usage-examples)
7. [Configuration Reference](#configuration-reference)
8. [API Documentation](#api-documentation)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Features](#advanced-features)

---

## Project Overview

A comprehensive Python system for interacting with Njuskalo.hr using advanced stealth techniques and automation. The system includes web scraping, stealth publishing, and comprehensive anti-detection measures.

### 🎯 Purpose

This system is designed to:

1. **Stealth Publishing**: Automated content publishing with anti-detection
2. **Session Management**: UUID-based persistent browser sessions
3. **Two-Factor Authentication**: Automated 2FA handling (test & production modes)
4. **Anti-Detection**: Advanced browser fingerprinting and stealth techniques
5. **SSH Tunnel Support**: Anonymous traffic routing through remote servers
6. **Database Integration**: MySQL/PostgreSQL with comprehensive data tracking
7. **API Interface**: FastAPI + Celery for automated processing

### 🚀 Key Features

- **Advanced Stealth Configuration**: Comprehensive Firefox anti-detection
- **Human-like Behavior**: Realistic typing, mouse movements, and delays
- **Device Persistence**: Maintains consistent device identity across sessions
- **2FA Automation**: Handles verification codes (manual & database modes)
- **UUID Sessions**: Persistent Firefox profiles to avoid confirmation codes
- **Popup Handling**: Automatically handles consent and advertisement popups
- **SSH Tunnel Support**: SOCKS proxy through SSH tunnels for anonymity
- **Screenshot Capture**: Automatic debugging screenshots
- **Comprehensive Logging**: Detailed logs to files and console

---

## Stealth Publish System

### Overview

The Njuskalo Stealth Publish system provides sophisticated automation for Njuskalo.hr with advanced anti-detection techniques.

### Core Features

#### 🕵️ Anti-Detection Techniques

- **Webdriver Detection Bypass**: Disables `navigator.webdriver` property
- **User Agent Randomization**: Uses realistic Firefox user agents
- **Language Settings**: Configured for Croatian locale (hr-HR)
- **Hardware Fingerprinting**: Disabled WebGL and hardware acceleration
- **Automation Indicators**: Removes Selenium automation markers
- **JavaScript Stealth Injection**: Patches browser APIs to appear human

#### 🎭 Human-like Behavior

- **Realistic Typing**: Random delays between keystrokes (50-150ms)
- **Mouse Movements**: Human-like cursor movements to elements
- **Random Delays**: Thinking pauses and natural interaction timing
- **Screen Size Randomization**: Common resolution patterns
- **Scroll Behavior**: Natural scrolling to bring elements into view

#### 💾 Device Persistence & Identity Management

To avoid being detected as a new device on every login:

- **Persistent Browser Profiles**: Creates user-specific Firefox profiles
- **Consistent Device Fingerprinting**: Username-based seeds for browser characteristics
- **Cookie & Session Management**: Saves and restores login cookies between sessions
- **Local Storage Persistence**: Maintains browser local storage for device continuity
- **Stable User-Agent**: Consistent user agent strings based on device fingerprint

#### 🚫 Popup Handling

Automatically detects and handles various consent and advertisement popups:

- **Didomi Consent Management**: Prioritized handling for GDPR compliance
- **Croatian Button Recognition**: Looks for "Prihvati i zatvori" (Accept and Close)
- **Multiple Detection Strategies**: Comprehensive CSS selectors for different popup systems
- **Human-like Interaction**: Realistic mouse movements and delays
- **Non-blocking**: Continues process even if popup handling fails

---

## Two-Factor Authentication (2FA)

### Overview

The system supports automatic two-factor authentication with handling for both test and production environments.

### How it Works

#### 1. Login Process

1. User enters username and password
2. System clicks login button
3. System checks if 2FA is required by looking for the "Next Step" button

#### 2. 2FA Detection

The system looks for the 2FA step button with class:

```css
.form-action.form-action--submit.button-standard.button-standard--alpha.button-standard--full.TwoFactorAuthentication-stepNextAction
```

#### 3. 2FA Handling Modes

##### Test Mode (Manual Input)

- Clicks the "Next Step" button to request verification code
- Waits for user to manually enter the code in the browser
- User presses Enter in terminal when code is entered
- System clicks the submit button

##### Production Mode (Database Retrieval)

- Clicks the "Next Step" button to request verification code
- Waits up to 15 minutes for code to appear in database users table
- Automatically enters the code when found
- Clicks the submit button

#### 4. Submit Button

After code entry, system clicks the submit button with class:

```css
.form-action.form-action--submit.button-standard.button-standard--alpha.button-standard--full.TwoFactorAuthentication-submitAction
```

### 2FA Implementation Details

#### Test Environment Detection

The system determines test mode by:

1. Explicit `test_mode=True` parameter
2. Fallback to username check (`test`, `srdjanmsd`, `testuser`)

#### Database Integration (Production Mode)

To implement database code retrieval, update the `_get_2fa_code_from_database()` method:

```python
def _get_2fa_code_from_database(self) -> str:
    import pymysql

    connection = pymysql.connect(
        host='your_host',
        user='your_user',
        password='your_password',
        database='your_database'
    )

    with connection.cursor() as cursor:
        sql = "SELECT verification_code FROM users WHERE username = %s AND verification_code IS NOT NULL ORDER BY created_at DESC LIMIT 1"
        cursor.execute(sql, (self.username,))
        result = cursor.fetchone()
        if result:
            return result[0]

    connection.close()
    return None
```

---

## UUID Session Management

### Overview

UUID-based Firefox sessions provide persistent browser profiles that avoid new device detection and reduce the need for confirmation codes.

### How UUID Sessions Work

#### Session Creation

1. **UUID Validation**: Validates provided UUID format or generates new one
2. **Directory Structure**: Creates `firefoxsessions/{uuid}` directory
3. **Profile Setup**: Initializes persistent Firefox profile in session directory
4. **Fingerprint Generation**: Creates consistent device fingerprint based on UUID
5. **Metadata Storage**: Saves session info as JSON with creation/usage timestamps

#### Session Benefits

- **Persistent Login State**: Browser remembers login across script executions
- **Device Recognition**: Appears as same device to reduce security prompts
- **2FA Reduction**: Established sessions may bypass 2FA requirements
- **API Integration**: UUID parameter allows external systems to manage sessions
- **Session Tracking**: Metadata tracks usage patterns and session health

#### Session Directory Structure

```
firefoxsessions/
├── {uuid-1}/
│   ├── session_info.json     # Session metadata
│   ├── cookies.sqlite        # Firefox cookies
│   ├── sessionstore.jsonlz4  # Firefox session data
│   └── ...                   # Other Firefox profile files
├── {uuid-2}/
│   └── ...
└── .gitkeep                  # Keeps directory in git
```

#### Session Metadata Format

```json
{
  "uuid": "12345678-1234-5678-9abc-123456789012",
  "username": "example_user",
  "created": 1699788123.456,
  "last_used": 1699788456.789,
  "fingerprint": "a1b2c3d4e5f6..."
}
```

---

## Installation & Setup

### Prerequisites

- **Python 3.8+**
- **Firefox Browser**
- **GeckoDriver**

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install GeckoDriver

```bash
# Option 1: Download from GitHub releases
wget https://github.com/mozilla/geckodriver/releases/download/v0.33.0/geckodriver-v0.33.0-linux64.tar.gz
tar -xzf geckodriver-v0.33.0-linux64.tar.gz
sudo mv geckodriver /usr/local/bin/
sudo chmod +x /usr/local/bin/geckodriver

# Option 2: Using package manager (Ubuntu/Debian)
sudo apt-get install firefox-geckodriver

# Option 3: Using webdriver-manager (automatic)
pip install webdriver-manager
```

### 3. Install Firefox

```bash
sudo apt-get install firefox
```

### 4. Environment Configuration

Create `.env` file with:

```bash
# Njuskalo configuration
NJUSKALO_BASE_URL=https://www.njuskalo.hr

# SSH Tunnel configuration (optional)
SOCKS_PROXY_HOST=127.0.0.1
SOCKS_PROXY_PORT=1080
```

### 5. SSH Tunnel Setup (Optional)

For maximum anonymity, configure SSH tunnels:

1. Create `tunnel_config.json`:

   ```json
   {
     "tunnel1": {
       "ssh_host": "your-server.com",
       "ssh_port": 22,
       "ssh_user": "username",
       "ssh_key": "/path/to/private/key",
       "local_port": 1080,
       "remote_host": "localhost",
       "remote_port": 1080
     }
   }
   ```

2. Use with tunnel:
   ```bash
   python njuskalo_stealth_publish.py --tunnel
   ```

---

## Usage Examples

### Basic Usage

```bash
# Development mode with visible Firefox
python njuskalo_stealth_publish.py --visible

# Headless mode (production)
python njuskalo_stealth_publish.py

# With SSH tunnel (if configured)
python njuskalo_stealth_publish.py --tunnel

# Custom credentials
python njuskalo_stealth_publish.py --username "your_user" --password "your_pass"

# Disable device persistence (appear as new device each time)
python njuskalo_stealth_publish.py --no-persistent
```

### UUID Session Examples

```bash
# Auto-generate UUID session
python njuskalo_stealth_publish.py --visible

# Use specific UUID (API integration)
python njuskalo_stealth_publish.py --uuid "12345678-1234-5678-9abc-123456789012"

# UUID session with 2FA test mode
python njuskalo_stealth_publish.py --visible --test-mode --uuid "12345678-1234-5678-9abc-123456789012"
```

### 2FA Usage Examples

#### Test Mode (Manual Code Entry)

```bash
# Using test script
python3 test_stealth_publish.py --uuid "12345678-1234-5678-9abc-123456789012" --mode visible

# Using main script
python3 njuskalo_stealth_publish.py --visible --test-mode --uuid "12345678-1234-5678-9abc-123456789012"
```

#### Production Mode (Database Code Retrieval)

```bash
# Main script will automatically use production mode
python3 njuskalo_stealth_publish.py --uuid "12345678-1234-5678-9abc-123456789012"
```

### Testing

```bash
# Test in visible mode (recommended for first run)
python test_stealth_publish.py --mode visible

# Test with UUID session
python test_stealth_publish.py --uuid "12345678-1234-5678-9abc-123456789012" --mode visible

# Test in headless mode
python test_stealth_publish.py --mode headless

# Test both modes
python test_stealth_publish.py --mode both
```

---

## Configuration Reference

### Command Line Arguments

| Argument          | Type   | Default               | Description                         |
| ----------------- | ------ | --------------------- | ----------------------------------- |
| `--visible`       | flag   | False                 | Run in visible mode (not headless)  |
| `--tunnel`        | flag   | False                 | Use SSH tunnel for anonymity        |
| `--username`      | string | "MilkicHalo"          | Njuskalo username                   |
| `--password`      | string | "rvp2mqu@xye1JRC0fjt" | Njuskalo password                   |
| `--no-persistent` | flag   | False                 | Disable persistent profile          |
| `--uuid`          | string | None                  | UUID for persistent Firefox session |
| `--test-mode`     | flag   | False                 | Enable test mode for 2FA            |

### Constructor Parameters

```python
NjuskaloStealthPublish(
    headless=True,          # Run browser in headless mode
    use_tunnel=False,       # Enable SSH tunnel support
    username=None,          # Njuskalo username
    password=None,          # Njuskalo password
    persistent=True,        # Use persistent browser profile
    user_uuid=None,         # UUID for session management
    test_mode=False         # Enable test mode for 2FA
)
```

### Environment Variables

```bash
# Required
NJUSKALO_BASE_URL=https://www.njuskalo.hr

# Optional - SSH Tunnel
SOCKS_PROXY_HOST=127.0.0.1
SOCKS_PROXY_PORT=1080
```

---

## API Documentation

### Integration Example

```python
from njuskalo_stealth_publish import NjuskaloStealthPublish

# Create instance with UUID session
publish = NjuskaloStealthPublish(
    headless=True,
    username="your_user",
    password="your_pass",
    user_uuid="12345678-1234-5678-9abc-123456789012"
)

# Run stealth publish
success = publish.run_stealth_publish()

if success:
    print("✅ Login successful!")
    # Use the logged-in browser session
    driver = publish.driver
    # ... perform additional actions ...
    driver.quit()
else:
    print("❌ Login failed!")
```

### Session Management API

```python
# List existing sessions
from pathlib import Path
import json

sessions_dir = Path("firefoxsessions")
for session_dir in sessions_dir.iterdir():
    if session_dir.is_dir():
        session_file = session_dir / "session_info.json"
        if session_file.exists():
            with open(session_file, 'r') as f:
                info = json.load(f)
            print(f"UUID: {info['uuid']}, User: {info['username']}")
```

---

## Troubleshooting

### Common Issues

#### 1. GeckoDriver not found

```bash
# Install GeckoDriver
sudo apt-get install firefox-geckodriver
# or download manually to /usr/local/bin/
```

#### 2. Firefox not found

```bash
sudo apt-get install firefox
```

#### 3. Login form not detected

- Use visible mode to inspect page structure
- Check if Njuskalo has updated their login form
- Review screenshots in `screenshots/` directory

#### 4. SSH tunnel issues

- Verify `tunnel_config.json` configuration
- Check SSH key permissions: `chmod 600 /path/to/key`
- Test SSH connection manually

#### 5. 2FA Issues

1. **2FA button not found**: Check CSS selector classes on Njuskalo.hr
2. **Code input field not found**: Verify input field selectors
3. **Database timeout**: Ensure database connection and table structure
4. **UUID format error**: Use proper UUID format (e.g., from `uuid.uuid4()`)

#### 6. UUID Session Issues

- **Invalid UUID format**: Use proper UUID format
- **Session directory permissions**: Check write permissions
- **Firefox profile corruption**: Delete session directory and recreate

### Debug Mode

For debugging, use visible mode and check:

```bash
# Run with maximum visibility
python njuskalo_stealth_publish.py --visible

# Check logs
tail -f logs/njuskalo_stealth_publish.log

# Review screenshots
ls -la screenshots/

# Test 2FA flow
python test_stealth_publish.py --uuid "test-uuid" --mode visible
```

### File Structure

```
njuskalohr/
├── njuskalo_stealth_publish.py  # Main stealth publish script
├── test_stealth_publish.py      # Testing script
├── uuid_session_example.py      # UUID session examples
├── ssh_tunnel_manager.py        # SSH tunnel management (optional)
├── tunnel_config.json           # SSH tunnel configuration (optional)
├── .env                         # Environment variables
├── requirements.txt             # Python dependencies
├── logs/                        # Log files
│   └── njuskalo_stealth_publish.log
├── screenshots/                 # Debug screenshots
│   ├── login_page_*.png
│   ├── login_success_*.png
│   └── login_failed_*.png
├── firefoxsessions/            # UUID-based Firefox sessions
│   ├── {uuid-1}/
│   ├── {uuid-2}/
│   └── .gitkeep
└── browser_profiles/           # Username-based profiles (legacy)
    └── njuskalo_profile_*/
```

---

## Advanced Features

### Custom Stealth Configuration

You can extend the stealth configuration by modifying the `setup_stealth_browser()` method to add additional Firefox preferences or JavaScript injections.

### Session Fingerprinting

The system generates consistent device fingerprints based on:

- Username or UUID seed
- Base URL domain
- System identifiers
- Browser characteristics

### Anti-Detection Measures

- **JavaScript Stealth Injection**: Removes webdriver properties, fakes plugin detection, spoofs language preferences
- **Hardware Fingerprinting**: Disables WebGL, canvas fingerprinting, hardware acceleration
- **Network Behavior**: Randomized request timing, realistic connection patterns
- **Behavioral Patterns**: Human-like interaction delays and mouse movements

### Production Deployment

#### Database Configuration

For production 2FA, implement database connection in `_get_2fa_code_from_database()`:

```python
# Example MySQL/PostgreSQL implementation
connection = pymysql.connect(
    host=os.getenv('DB_HOST'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME')
)
```

#### Session Management

- Monitor session health with metadata tracking
- Implement session cleanup for old/unused sessions
- Use UUID-based sessions for API integration
- Set up session rotation policies

#### Security Considerations

- Store sensitive credentials in environment variables
- Use SSH tunnels for IP anonymization
- Implement rate limiting for login attempts
- Monitor for detection patterns and adapt techniques
- Regular updates to anti-detection methods

### Error Handling

The script includes comprehensive error handling for:

- GeckoDriver not found
- Firefox installation issues
- Network connectivity problems
- Login form detection failures
- SSH tunnel connection issues
- JavaScript execution errors
- 2FA timeout scenarios
- UUID session corruption

## License

This script is for educational and testing purposes. Please respect Njuskalo.hr's terms of service and use responsibly.
