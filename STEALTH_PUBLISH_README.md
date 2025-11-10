# Njuskalo Stealth Publish

A sophisticated stealth publish script for Njuskalo.hr using advanced anti-detection techniques from the enhanced tunnel scraper.

## Features

- 🕵️ **Advanced Stealth Configuration**: Uses comprehensive Firefox stealth settings
- 🎭 **Anti-Detection Techniques**: Randomized user agents, screen sizes, and human-like behavior
- 🌐 **SSH Tunnel Support**: Optional SOCKS proxy through SSH tunnels for anonymity
- 🖥️ **Development Mode**: Visible browser for debugging and development
- 📸 **Screenshot Capture**: Automatic screenshots for debugging
- 🔐 **Human-like Interaction**: Realistic typing and mouse movements
- 🚫 **Popup Handling**: Automatically handles advertisement popups by clicking "Prihvati i zatvori"
- � **Device Persistence**: Maintains consistent device identity to avoid "new device" login alerts
- 💾 **Session Management**: Saves and restores cookies and browser data between sessions
- �📊 **Comprehensive Logging**: Detailed logging to files and console

## Installation

1. **Install Python Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

2. **Install GeckoDriver**:

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

3. **Install Firefox**:
   ```bash
   sudo apt-get install firefox
   ```

## Usage

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

### Testing

```bash
# Test in visible mode (recommended for first run)
python test_stealth_publish.py --mode visible

# Test in headless mode
python test_stealth_publish.py --mode headless

# Test both modes
python test_stealth_publish.py --mode both
```

## Configuration

### Environment Variables

Create `.env` file with:

```bash
# Njuskalo configuration
NJUSKALO_BASE_URL=https://www.njuskalo.hr

# SSH Tunnel configuration (optional)
SOCKS_PROXY_HOST=127.0.0.1
SOCKS_PROXY_PORT=1080
```

**Note**: The script automatically uses the correct Croatian login URL (`/prijava`) and looks for Croatian field names ("Korisničko ime" for username and "Lozinka" for password).

### SSH Tunnel Setup (Optional)

For maximum anonymity, you can configure SSH tunnels:

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

## Stealth Features

### Browser Configuration

- **Webdriver Detection Bypass**: Disables `navigator.webdriver` property
- **User Agent Randomization**: Uses realistic Firefox user agents
- **Language Settings**: Configured for Croatian locale (hr-HR)
- **Hardware Fingerprinting**: Disabled WebGL and hardware acceleration
- **Automation Indicators**: Removes Selenium automation markers
- **Cache Disabled**: No disk or memory cache for stealth
- **Proxy Support**: SOCKS5 proxy through SSH tunnels

### Human-like Behavior

- **Realistic Typing**: Random delays between keystrokes (50-150ms)
- **Mouse Movements**: Human-like cursor movements to elements
- **Random Delays**: Thinking pauses and natural interaction timing
- **Screen Size Randomization**: Common resolution patterns
- **Scroll Behavior**: Natural scrolling to bring elements into view

### JavaScript Stealth Injection

- Removes webdriver properties
- Fakes plugin detection
- Spoofs language preferences
- Hides automation indicators
- Patches permissions API

### Consent & Advertisement Popup Handling

The script automatically detects and handles various consent and advertisement popups that may appear on Njuskalo.hr:

- **Didomi Consent Management**: Prioritized handling of `#didomi-notice-agree-button` for GDPR compliance
- **Croatian Button Recognition**: Looks for "Prihvati i zatvori" (Accept and Close) buttons
- **Multiple Detection Strategies**: Uses comprehensive CSS selectors for different popup systems
- **Human-like Interaction**: Clicks popup buttons with realistic mouse movements and delays
- **Non-blocking**: Continues login process even if popup handling fails
- **Dual Timing**: Handles popups both on page load and after login attempts
- **Smart Logging**: Identifies and logs specific popup types (Didomi vs generic)

### Device Persistence & Identity Management

To avoid being detected as a new device on every login, the script implements comprehensive persistence:

- **Persistent Browser Profiles**: Creates and maintains user-specific Firefox profiles
- **Consistent Device Fingerprinting**: Uses username-based seeds for consistent browser characteristics
- **Cookie & Session Management**: Automatically saves and restores login cookies between sessions
- **Local Storage Persistence**: Maintains browser local storage data for device continuity
- **Stable User-Agent**: Uses consistent user agent strings based on device fingerprint
- **Profile Directory Structure**: Organized profile storage in `browser_profiles/` directory
- **Automatic Session Restoration**: Restores previous session data before attempting login

## File Structure

```
njuskalohr/
├── njuskalo_stealth_publish.py  # Main stealth publish script
├── test_stealth_publish.py      # Testing script
├── enhanced_tunnel_scraper.py   # Source of stealth techniques
├── ssh_tunnel_manager.py        # SSH tunnel management (if available)
├── tunnel_config.json           # SSH tunnel configuration (optional)
├── .env                         # Environment variables
├── requirements.txt             # Python dependencies
├── logs/                        # Log files
│   └── njuskalo_stealth_publish.log
└── screenshots/                 # Debug screenshots
    ├── login_page_*.png
    ├── login_success_*.png
    └── login_failed_*.png
```

## Logging

The script creates detailed logs in two formats:

1. **Console Output**: Real-time progress with emoji indicators
2. **Log File**: Detailed logs saved to `logs/njuskalo_stealth_publish.log`

## Error Handling

The script includes comprehensive error handling for:

- GeckoDriver not found
- Firefox installation issues
- Network connectivity problems
- Login form detection failures
- SSH tunnel connection issues
- JavaScript execution errors

## Security Notes

- Uses provided credentials securely (no storage)
- Supports SSH tunnels for IP anonymization
- Implements anti-fingerprinting techniques
- Randomizes identifiable browser characteristics
- Clears browser data after use (in headless mode)

## Troubleshooting

### Common Issues

1. **GeckoDriver not found**:

   ```bash
   # Install GeckoDriver
   sudo apt-get install firefox-geckodriver
   # or download manually to /usr/local/bin/
   ```

2. **Firefox not found**:

   ```bash
   sudo apt-get install firefox
   ```

3. **Login form not detected**:

   - Use visible mode to inspect page structure
   - Check if Njuskalo has updated their login form
   - Review screenshots in `screenshots/` directory

4. **SSH tunnel issues**:
   - Verify `tunnel_config.json` configuration
   - Check SSH key permissions: `chmod 600 /path/to/key`
   - Test SSH connection manually

### Debug Mode

For debugging, use visible mode and check:

```bash
# Run with maximum visibility
python njuskalo_stealth_publish.py --visible

# Check logs
tail -f logs/njuskalo_stealth_publish.log

# Review screenshots
ls -la screenshots/
```

## Advanced Usage

### Integration with Other Scripts

```python
from njuskalo_stealth_publish import NjuskaloStealthPublish

# Create instance
publish = NjuskaloStealthPublish(headless=True)

# Run publish
if publish.run_stealth_publish():
    # Use the logged-in browser session
    driver = publish.driver
    # ... perform actions ...
    driver.quit()
```

### Custom Stealth Configuration

You can extend the stealth configuration by modifying the `setup_stealth_browser()` method to add additional Firefox preferences or JavaScript injections.

## License

This script is for educational and testing purposes. Please respect Njuskalo.hr's terms of service and use responsibly.
