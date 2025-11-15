# 🏪 Njuskalo HR - Complete System Documentation

**A comprehensive Python system for automated interaction with Njuskalo.hr using advanced stealth techniques, database-driven content management, and intelligent form filling capabilities.**

---

## 📑 Table of Contents

1. [Project Overview](#project-overview)
2. [UUID Architecture](#uuid-architecture)
3. [Installation & Setup](#installation--setup)
4. [Usage & Examples](#usage--examples)
5. [System Architecture](#system-architecture)
6. [Stealth & Security Features](#stealth--security-features)
7. [Form Filling Implementation](#form-filling-implementation)
8. [Ad Status Validation](#ad-status-validation)
9. [Configuration Reference](#configuration-reference)
10. [Error Handling & Troubleshooting](#error-handling--troubleshooting)
11. [Advanced Features](#advanced-features)
12. [File Structure](#file-structure)
13. [Future Extensions](#future-extensions)

---

## Project Overview

### 🎯 Purpose

This system provides:

1. **Stealth Publishing**: Automated content publishing with advanced anti-detection measures
2. **Form Filling Automation**: Database-driven ad submission with intelligent field mapping
3. **Status Validation**: Comprehensive ad validation before publishing
4. **Session Management**: UUID-based persistent browser sessions with device continuity
5. **Two-Factor Authentication**: Automated 2FA handling for secure login
6. **Anti-Detection**: Advanced browser fingerprinting and stealth techniques
7. **SSH Tunnel Support**: Anonymous traffic routing through remote servers

### 🚀 Key Features

- 🕵️ **Advanced Stealth Configuration**: Comprehensive Firefox stealth settings
- 🎭 **Anti-Detection Techniques**: Randomized user agents, screen sizes, human-like behavior
- 🤖 **Intelligent Form Filling**: Database-driven content with smart field detection
- 🔐 **Human-like Interaction**: Realistic typing and mouse movements
- 📊 **Status Validation**: Ensures only properly prepared ads are published
- 🌐 **SSH Tunnel Support**: Optional SOCKS proxy for anonymity
- 💾 **Session Persistence**: Maintains device identity across sessions
- 🔑 **Dual UUID Architecture**: Proper separation of ads and user sessions
- 📸 **Debug Capabilities**: Screenshot capture and comprehensive logging

---

## UUID Architecture

### 🏗️ Architecture Overview

The system uses a two-step UUID lookup system that properly separates ad identification from user sessions while maintaining data relationships.

#### Before (Single UUID)

```
user_uuid → Firefox sessions + Form data + User credentials
```

#### After (Dual UUID System)

```
ad_uuid → adItem.user → user_uuid → Firefox sessions + User credentials
ad_uuid → adItem.content → Form data
```

### 📊 Database Schema Requirements

#### Required Tables

**1. adItem table**

- `uuid` (BINARY(16)) - Primary ad identifier
- `user` (BINARY(16)) - Reference to users.uuid
- `content` (JSON) - Ad form data
- `status` (VARCHAR) - Must be 'PUBLISHED'
- `publishNjuskalo` (BOOLEAN) - Must be TRUE

**2. users table**

- `uuid` (BINARY(16)) - Primary user identifier
- `njuskalo`/`profile`/`avtonet` (JSON) - Contains credentials and 2FA codes

#### Example Data Structure

```sql
-- adItem table
INSERT INTO adItem (uuid, user, content, status, publishNjuskalo) VALUES
(UNHEX(REPLACE('ad-uuid-here', '-', '')),
 UNHEX(REPLACE('user-uuid-here', '-', '')),
 '{"price": 5000, "description": "Car description..."}',
 'PUBLISHED',
 TRUE);

-- users table
INSERT INTO users (uuid, njuskalo) VALUES
(UNHEX(REPLACE('user-uuid-here', '-', '')),
 '[{"username": "user123", "password": "pass123", "code": "123456"}]');
```

### 🔍 Validation Flow

1. **Input**: Provide ad_uuid (required)
2. **Lookup**: Find user from adItem.user field
3. **Resolve**: Get user credentials from users table
4. **Validate**: Check both ad_uuid and user_uuid exist
5. **Session**: Use user_uuid for Firefox profiles
6. **Form**: Use ad_uuid for ad content retrieval
7. **Publish**: Submit with proper user authentication

### 📝 Benefits

- **Proper Data Relationships**: Ad and user data properly separated
- **Automatic Resolution**: Only need ad UUID - user data resolved automatically
- **Session Persistence**: User UUID used for Firefox profiles and 2FA
- **Flexible Overrides**: Can override user or credentials when needed
- **Backward Compatible**: Existing scripts continue to work
- **Clear Separation**: Ad content vs user session data clearly separated

---

## Installation & Setup

### 1. Python Dependencies

```bash
pip install -r requirements.txt
```

**Required packages:**

- selenium
- pymysql
- python-dotenv
- webdriver-manager (optional)

### 2. GeckoDriver Installation

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

### 3. Firefox Installation

```bash
sudo apt-get install firefox
```

### 4. Environment Configuration

Create `.env` file with:

```bash
# Njuskalo configuration
NJUSKALO_BASE_URL=https://www.njuskalo.hr

# Database configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_username
DB_PASSWORD=your_password
DB_NAME=njuskalo_database

# SSH Tunnel configuration (optional)
SOCKS_PROXY_HOST=127.0.0.1
SOCKS_PROXY_PORT=1080

# Stealth Configuration
USER_AGENT_RANDOMIZATION=true
DEVICE_PERSISTENCE=true
JAVASCRIPT_STEALTH=true
```

### 5. SSH Tunnel Setup (Optional)

For maximum anonymity, create `tunnel_config.json`:

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

---

## Usage & Examples

### Basic Usage (Recommended)

```bash
# Only need ad UUID - everything else is resolved automatically
python njuskalo_stealth_publish.py --ad-uuid 12345678-1234-1234-1234-123456789abc --submit-ad

# Development mode with visible Firefox
python njuskalo_stealth_publish.py --ad-uuid your-ad-uuid --visible

# Headless production mode
python njuskalo_stealth_publish.py --ad-uuid your-ad-uuid --submit-ad

# With SSH tunnel for anonymity
python njuskalo_stealth_publish.py --ad-uuid your-ad-uuid --submit-ad --tunnel
```

### Advanced Usage

```bash
# Override user UUID for specific user session
python njuskalo_stealth_publish.py \
  --ad-uuid ad-uuid-here \
  --user-uuid user-uuid-here \
  --submit-ad

# Custom credentials override
python njuskalo_stealth_publish.py \
  --ad-uuid your-ad-uuid \
  --username "your_user" \
  --password "your_pass" \
  --submit-ad

# Disable device persistence (appear as new device)
python njuskalo_stealth_publish.py \
  --ad-uuid your-ad-uuid \
  --submit-ad \
  --no-persistent

# Test mode with manual input
python njuskalo_stealth_publish.py --test-mode --submit-ad --visible
```

### Backward Compatibility

```bash
# Legacy --uuid parameter still works (maps to --ad-uuid)
python njuskalo_stealth_publish.py --uuid ad-uuid-here --submit-ad
```

### Testing Scripts

```bash
# Test in visible mode (recommended for first run)
python test_stealth_publish.py --mode visible

# Test in headless mode
python test_stealth_publish.py --mode headless

# Test both modes sequentially
python test_stealth_publish.py --mode both

# Test UUID resolution architecture
python tests/test_uuid_architecture.py

# See usage examples
python tests/usage_examples_new_architecture.py
```

### Command Line Arguments

```bash
# Core Arguments
--ad-uuid UUID           # Specific ad UUID to process (NEW)
--uuid UUID              # Legacy parameter (maps to --ad-uuid)
--user-uuid UUID         # Override user UUID
--username USERNAME      # Njuskalo login username override
--password PASSWORD      # Njuskalo login password override
--visible                # Run in visible mode (not headless)
--headless               # Force headless mode
--submit-ad              # Enable form submission
--test-mode              # Enable test mode with manual UUID input

# Advanced Arguments
--tunnel                 # Use SSH tunnel for anonymity
--no-persistent          # Disable device persistence
--debug                  # Enable debug logging
--screenshot-dir DIR     # Custom screenshot directory
--profile-dir DIR        # Custom browser profile directory
```

---

## System Architecture

### Data Flow Overview

```
Database (adItem) → UUID Resolution → Status Validation → Content Extraction → Form Mapping → Human Simulation → Submission
```

### Core Components

1. **NjuskaloStealthPublish**: Main orchestrator class
2. **UUID Resolution System**: Two-step ad → user lookup
3. **Database Integration**: MySQL with status validation
4. **Form Filling Engine**: Intelligent field detection and mapping
5. **Stealth Browser**: Advanced anti-detection configuration
6. **Session Management**: Persistent device identity and restoration
7. **2FA Handler**: Database-driven two-factor authentication

### Key Methods

#### Constructor

```python
def __init__(self,
    ad_uuid: str = None,           # NEW: Primary ad identifier
    user_uuid: str = None,         # Optional user override
    username: str = None,          # Optional credential override
    password: str = None,          # Optional credential override
    headless: bool = True,
    tunnel_enabled: bool = False,
    persistent: bool = True,
    ...
):
```

#### New UUID Resolution Methods

- `_resolve_user_from_ad()` - Resolves user from ad UUID
- `_validate_required_uuids()` - Validates required UUIDs

#### Updated Methods

- `_get_ad_data_from_database()` - Uses ad_uuid instead of user_uuid
- `_get_2fa_code_from_database()` - Uses user_uuid for 2FA lookup
- `run_stealth_publish()` - Added UUID validation step

---

## Stealth & Security Features

### Advanced Stealth Configuration

#### Webdriver Detection Bypass

```python
# Disables navigator.webdriver property
options.set_preference("dom.webdriver.enabled", False)
options.set_preference("useAutomationExtension", False)

# Remove automation indicators
options.set_preference("marionette", False)
```

#### User Agent Randomization

```python
# Consistent but randomized based on device fingerprint
device_seed = hashlib.md5(username.encode()).hexdigest()[:8]
user_agents = [
    "Mozilla/5.0 (X11; Linux x86_64; rv:91.0) Gecko/20100101 Firefox/91.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:95.0) Gecko/20100101 Firefox/95.0"
]
selected_ua = user_agents[int(device_seed[4:6], 16) % len(user_agents)]
```

#### JavaScript Stealth Injection

```javascript
// Remove webdriver properties
Object.defineProperty(navigator, "webdriver", { get: () => undefined });

// Fake plugin detection
Object.defineProperty(navigator, "plugins", {
  get: () => [1, 2, 3, 4, 5].map(() => "Plugin"),
});

// Spoof language preferences
Object.defineProperty(navigator, "languages", {
  get: () => ["hr-HR", "hr", "en-US", "en"],
});

// Hide automation indicators
[
  "__webdriver_evaluate",
  "__selenium_evaluate",
  "__webdriver_script_function",
].forEach((prop) => {
  window[prop] = undefined;
});
```

### Device Persistence & Identity Management

```python
# Persistent browser profiles based on user UUID
profile_dir = f"browser_profiles/{user_uuid}_profile"

# Consistent device fingerprinting
device_seed = hashlib.md5(user_uuid.encode()).hexdigest()[:8]
screen_width = 1366 + int(device_seed[:2], 16) % 100
screen_height = 768 + int(device_seed[2:4], 16) % 100
```

**Features:**

- **Persistent Browser Profiles**: Creates and maintains user-specific Firefox profiles
- **Consistent Device Fingerprinting**: Uses user UUID-based seeds for browser characteristics
- **Cookie & Session Management**: Automatically saves and restores login sessions
- **Local Storage Persistence**: Maintains browser data for device continuity
- **Stable User-Agent**: Consistent user agent strings based on device fingerprint

### Human-like Behavior Simulation

```python
def _human_like_typing(self, element, text: str, min_delay=0.05, max_delay=0.15):
    """Simulate realistic human typing patterns"""
    for char in text:
        element.send_keys(char)
        # Random typing delays
        time.sleep(random.uniform(min_delay, max_delay))

        # Occasional thinking pauses (10% chance)
        if random.random() < 0.1:
            time.sleep(random.uniform(0.5, 1.5))
```

**Behavioral Features:**

- **Realistic Typing**: Random delays between keystrokes (50-150ms)
- **Mouse Movements**: Human-like cursor movements to elements
- **Random Delays**: Natural thinking pauses and interaction timing
- **Screen Size Randomization**: Common resolution patterns
- **Scroll Behavior**: Natural scrolling to bring elements into view

### Didomi Consent Handling

```python
# Didomi consent management selectors
didomi_selectors = [
    "#didomi-notice-agree-button",
    "[data-didomi-id='agree']",
    ".didomi-notice-component-button[aria-labelledby*='agree']",
    ".didomi-button-agree",
    ".didomi-continue-without-agreeing",
    "button[id*='didomi-notice-agree']",
    "button[class*='didomi-notice-agree']",
    "button.didomi-components-button"
]
```

**Consent Management:**

- **Didomi Consent Detection**: Prioritized GDPR compliance handling
- **Human-like Interaction**: Realistic click timing and mouse movements
- **Non-blocking Operation**: Continues even if consent handling fails
- **Dual Timing**: Handles consent on page load and after login

### Network Security

- **SSH Tunnel Support**: SOCKS5 proxy through encrypted tunnels
- **IP Randomization**: Different IP addresses per session
- **DNS over HTTPS**: Encrypted DNS resolution
- **Certificate Validation**: Full SSL certificate verification

---

## Form Filling Implementation

### Architecture Overview

The form filling system provides comprehensive automation for Njuskalo.hr ad submission with database-driven content and intelligent field mapping.

### Core Method: `_fill_ad_form()`

```python
def _fill_ad_form(self) -> bool:
    """Main orchestrator for form filling process"""
    # 1. Status validation and data retrieval
    ad_content = self._get_ad_data_from_database()
    if not ad_content:
        return False

    # 2. Fill form sections
    self._fill_basic_ad_info(ad_content)
    self._fill_vehicle_details(ad_content)
    self._fill_contact_info(ad_content)
    self._fill_vehicle_features(ad_content)

    # 3. Prepare for submission
    return True
```

### Form Filling Components

#### Basic Ad Information (`_fill_basic_ad_info`)

Handles fundamental ad data:

```python
# Price handling
price_selectors = [
    'input[name*="price"]',
    'input[id*="price"]',
    'input[placeholder*="cijena"]'
]

# Description filling with cleanup
description_clean = re.sub(r'\s+', ' ', ad_content.get('description', '')).strip()
```

**Supported Fields:**

- **Price**: Numeric price with currency handling
- **Description**: Text cleanup and formatting
- **Price Type**: Normal/negotiable options

#### Vehicle Details (`_fill_vehicle_details`)

Comprehensive vehicle specification automation:

```python
# Smart fuel type mapping
fuel_mapping = {
    'DIESEL': ['Diesel', 'DIESEL', 'diesel'],
    'PETROL': ['Benzin', 'PETROL', 'petrol', 'benzin'],
    'HYBRID': ['Hibrid', 'HYBRID', 'hybrid'],
    'ELECTRIC': ['Električni', 'ELECTRIC', 'electric']
}

# Transmission type mapping
transmission_mapping = {
    'Automatic': ['Automatski', 'Automatic', 'automatski'],
    'Manual': ['Ručni', 'Manual', 'Manualni', 'ručni']
}
```

**Supported Vehicle Data:**

- Make/Manufacturer (`vehicleManufacturerName`)
- Model (`vehicleBaseModelName`)
- Year (`vehicleTrimYear`)
- Engine displacement (`vehicleEngineDisplacement`)
- Power in kW (`vehicleEnginePower`)
- Mileage (`vehicleCurrentOdometer`)
- Fuel type (`vehicleFuelType`) with Croatian mapping
- Transmission (`vehicleTransmissionType`) with Croatian mapping
- VIN number (`vin`)

#### Contact Information (`_fill_contact_info`)

Handles contact data with smart array processing:

```python
# Contact data structure
{
  "contact": {
    "name": "Contact Name",
    "phone": ["123456789", "", "", ""],
    "email": ["email@example.com", "", "", ""],
    "location": "City Name"
  }
}

# Smart array value extraction
def _get_first_valid_value(data):
    if isinstance(data, list):
        return next((item for item in data if item and str(item).strip()), "")
    return str(data) if data else ""
```

#### Vehicle Features (`_fill_vehicle_features`)

Advanced checkbox automation for Croatian vehicle equipment:

```python
# Multi-strategy feature detection
search_strategies = [
    f"//label[contains(text(), '{feature_name}')]//input[@type='checkbox']",
    f"//input[@type='checkbox'][@value='{feature_name}']",
    f"//input[@type='checkbox'][contains(@id, '{feature_name.lower()}')]",
    f"//input[@type='checkbox'][following-sibling::text()[contains(., '{feature_name}')]]"
]

# Croatian feature examples
features = [
    "ABS", "Airbag", "Bluetooth", "Klimatska naprava",
    "Električni prozori", "Centralno zaključavanje",
    "Tempomat", "Kožni unutrašnjost"
]
```

### Field Detection Engine

#### `_find_form_field(selectors: list)`

Robust multi-strategy field detection:

```python
def _find_form_field(self, selectors: list):
    """Find form field using multiple selector strategies"""
    for selector in selectors:
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                if element.is_displayed() and element.is_enabled():
                    return element
        except Exception as e:
            continue
    return None
```

**Detection Strategies:**

1. **Name attribute matching** (most reliable)
2. **ID attribute matching** (common)
3. **Placeholder text matching** (user-friendly)
4. **Class name matching** (CSS-based)
5. **XPath text matching** (content-based)

#### `_select_dropdown_option(select_element, options)`

Intelligent dropdown selection with fuzzy matching:

```python
def _select_dropdown_option(self, select_element, options):
    """Select dropdown option with fuzzy matching support"""
    select_obj = Select(select_element)

    # Try exact match first
    for option in options:
        try:
            select_obj.select_by_visible_text(option)
            return True
        except:
            continue

    # Try partial match
    available_options = [opt.text for opt in select_obj.options]
    for target_option in options:
        for available_option in available_options:
            if target_option.lower() in available_option.lower():
                select_obj.select_by_visible_text(available_option)
                return True

    return False
```

---

## Ad Status Validation

### Overview

Comprehensive validation system ensures only properly prepared ads proceed to form filling.

### Validation Method: `_get_ad_data_from_database()`

```python
def _get_ad_data_from_database(self):
    """Validate ad status and retrieve content"""

    # Database query using ad_uuid
    query = """
    SELECT uuid, content, status, publishNjuskalo
    FROM adItem
    WHERE uuid = %s
    LIMIT 1
    """

    # Status validation
    if status_col != "PUBLISHED":
        self.logger.error(f"❌ Ad status is '{status_col}', expected 'PUBLISHED'")
        return None

    # Njuskalo flag validation
    if not publish_njuskalo_col:
        self.logger.error(f"❌ publishNjuskalo is '{publish_njuskalo_col}', expected True")
        return None

    return json.loads(content_col)
```

### Validation Logic

| Scenario        | Status        | publishNjuskalo | Result                          |
| --------------- | ------------- | --------------- | ------------------------------- |
| ❌ Draft Ad     | `"DRAFT"`     | `True`          | Error: Status not PUBLISHED     |
| ❌ Unpublished  | `"PUBLISHED"` | `False`         | Error: publishNjuskalo not True |
| ❌ Both Invalid | `"DRAFT"`     | `False`         | Error: Both conditions fail     |
| ✅ Valid Ad     | `"PUBLISHED"` | `True`          | Success: Form filling proceeds  |

### Benefits

- 🛡️ **Data Integrity**: Only published ads with njuskalo flag proceed
- 🔍 **Clear Feedback**: Detailed error messages for failed validation
- 🧪 **Test Support**: Manual UUID input for development/testing
- 📊 **Database Driven**: Uses existing adItem table structure
- ⚡ **Early Exit**: Stops process immediately if validation fails

---

## Configuration Reference

### Environment Variables (.env)

```bash
# Core Njuskalo Configuration
NJUSKALO_BASE_URL=https://www.njuskalo.hr

# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_username
DB_PASSWORD=your_password
DB_NAME=njuskalo_database

# SSH Tunnel Configuration (Optional)
SOCKS_PROXY_HOST=127.0.0.1
SOCKS_PROXY_PORT=1080

# Stealth Configuration
USER_AGENT_RANDOMIZATION=true
DEVICE_PERSISTENCE=true
JAVASCRIPT_STEALTH=true
```

**Note**: The script automatically uses the correct Croatian login URL (`/prijava`) and looks for Croatian field names.

---

## Error Handling & Troubleshooting

### Comprehensive Error Management

#### Form Filling Errors

```python
# Field detection failure (non-fatal)
self.logger.warning(f"⚠️ Could not find field with selectors: {selectors}")

# Feature selection errors (logged individually)
self.logger.warning(f"⚠️ Feature checkbox not found: {feature_name}")

# Critical form validation errors
self.logger.error("❌ Failed to fill basic ad information - cannot proceed")
```

#### Status Validation Errors

```python
# Ad status validation failures
"❌ Ad status is 'DRAFT', expected 'PUBLISHED'"
"❌ publishNjuskalo is 'False', expected True"
"❌ No ad found with UUID: [uuid]"
"❌ Failed to retrieve valid ad data - cannot proceed with form filling"
```

#### UUID Resolution Errors

```python
"❌ No user found for ad UUID: [ad_uuid]"
"❌ Failed to resolve user from ad - cannot proceed"
"❌ Both ad_uuid and user_uuid are required but not provided"
```

### Common Issues & Solutions

#### 1. GeckoDriver Issues

```bash
# Problem: GeckoDriver not found
# Solution: Install GeckoDriver
sudo apt-get install firefox-geckodriver

# Alternative: Manual installation
wget https://github.com/mozilla/geckodriver/releases/download/v0.33.0/geckodriver-v0.33.0-linux64.tar.gz
tar -xzf geckodriver-v0.33.0-linux64.tar.gz
sudo mv geckodriver /usr/local/bin/
sudo chmod +x /usr/local/bin/geckodriver
```

#### 2. Firefox Installation

```bash
# Problem: Firefox not found
# Solution: Install Firefox
sudo apt-get install firefox
```

#### 3. Database Connection Issues

```bash
# Check database connectivity
mysql -h localhost -u username -p database_name

# Verify table structure
DESCRIBE adItem;
DESCRIBE users;

# Test ad UUID lookup
SELECT uuid, user, status, publishNjuskalo FROM adItem
WHERE uuid = UNHEX(REPLACE('your-ad-uuid', '-', ''));

# Test user resolution
SELECT u.uuid, u.njuskalo FROM users u
JOIN adItem a ON a.user = u.uuid
WHERE a.uuid = UNHEX(REPLACE('your-ad-uuid', '-', ''));
```

#### 4. Login Form Detection

```bash
# Debug with visible mode
python njuskalo_stealth_publish.py --ad-uuid your-uuid --visible --debug

# Check screenshots
ls -la screenshots/login_*.png

# Review detailed logs
tail -f logs/njuskalo_stealth_publish.log
```

#### 5. SSH Tunnel Problems

```bash
# Test SSH connection manually
ssh -i /path/to/key username@server.com

# Check key permissions
chmod 600 /path/to/private/key

# Test SOCKS proxy
curl --socks5 127.0.0.1:1080 http://httpbin.org/ip
```

### Debug Mode Features

```bash
# Maximum debugging visibility
python njuskalo_stealth_publish.py --ad-uuid your-uuid --visible --debug --screenshot-dir ./debug_screenshots

# Log analysis
tail -f logs/njuskalo_stealth_publish.log | grep -E "(ERROR|WARNING)"

# Screenshot review
find screenshots/ -name "*.png" -mtime -1 | sort
```

---

## Advanced Features

### Integration Capabilities

#### API Integration

```python
from njuskalo_stealth_publish import NjuskaloStealthPublish

# Create instance with custom configuration
publish = NjuskaloStealthPublish(
    ad_uuid="your-ad-uuid",
    headless=True,
    tunnel_enabled=True,
    persistent_device=True
)

# Run with specific ad
success = publish.run_stealth_publish()

if success:
    # Continue with browser session
    driver = publish.driver
    # Perform additional actions
    driver.quit()
```

#### Batch Processing

```python
# Process multiple ads
ad_uuids = ["uuid1", "uuid2", "uuid3"]

for uuid in ad_uuids:
    try:
        publisher = NjuskaloStealthPublish(ad_uuid=uuid)
        success = publisher.run_stealth_publish()

        if success:
            print(f"✅ Successfully published ad: {uuid}")
        else:
            print(f"❌ Failed to publish ad: {uuid}")

    except Exception as e:
        print(f"⚠️ Error processing {uuid}: {e}")
    finally:
        if 'publisher' in locals():
            publisher.cleanup()
```

### Custom Field Mapping

```python
# Extend field mapping for custom forms
custom_selectors = {
    'custom_price': [
        'input[name="custom_price"]',
        '#price_field_custom',
        '.price-input-custom'
    ],
    'special_description': [
        'textarea[name="special_desc"]',
        '#custom_description'
    ]
}

# Integrate custom mapping
publish._custom_field_selectors = custom_selectors
```

---

## File Structure

```
njuskalohr/
├── njuskalo_stealth_publish.py      # Main stealth publish system
├── README.md                        # This comprehensive documentation
├── config.py                        # Configuration management
├── requirements.txt                 # Python dependencies
├── setup.sh                         # Environment setup script
├── .env                             # Environment variables
├── tunnel_config.json               # SSH tunnel configuration (optional)
├── tests/                           # Test files directory
│   ├── __init__.py
│   ├── README.md
│   ├── test_stealth_publish.py
│   ├── test_form_filling.py
│   ├── test_uuid_architecture.py
│   ├── usage_examples_new_architecture.py
│   ├── demo_form_filling_complete.py
│   └── demo_ad_status_validation.py
├── logs/                            # Log files directory
│   ├── njuskalo_stealth_publish.log
│   ├── form_filling.log
│   └── debug.log
├── screenshots/                     # Debug screenshots
│   ├── login_page_*.png
│   ├── form_filled_*.png
│   ├── login_success_*.png
│   └── error_*.png
├── browser_profiles/                # Persistent browser profiles (gitignored)
│   ├── user_uuid_1_profile/
│   ├── user_uuid_2_profile/
│   └── ...
└── __pycache__/                     # Python cache files
```

---

## Future Extensions

### Planned Enhancements

#### Image Upload Automation

```python
# Future: Automated image upload
def _upload_ad_images(self, ad_content):
    """Upload images from database or file system"""
    images = ad_content.get('images', [])

    for i, image_data in enumerate(images):
        # Download image from URL or database
        image_path = self._prepare_image(image_data)

        # Find upload input
        upload_input = self._find_upload_field(f"image_{i}")
        upload_input.send_keys(image_path)

        # Wait for upload completion
        self._wait_for_upload_complete(i)
```

#### Multi-language Support

```python
# Future: Dynamic language detection
def _detect_form_language(self):
    """Detect form language and adapt field mapping"""

    # Check page language
    html_lang = self.driver.find_element(By.TAG_NAME, "html").get_attribute("lang")

    if html_lang.startswith("hr"):
        return self._load_croatian_mapping()
    elif html_lang.startswith("en"):
        return self._load_english_mapping()
    else:
        return self._load_default_mapping()
```

#### Machine Learning Field Detection

```python
# Future: AI-powered field detection
def _ai_field_detection(self, field_type):
    """Use ML to identify form fields"""

    # Capture page screenshot
    screenshot = self.driver.get_screenshot_as_png()

    # Use computer vision to identify fields
    field_locations = self.ml_model.detect_fields(screenshot, field_type)

    # Convert coordinates to WebElements
    elements = []
    for location in field_locations:
        element = self.driver.execute_script(
            "return document.elementFromPoint(arguments[0], arguments[1]);",
            location['x'], location['y']
        )
        elements.append(element)

    return elements
```

### Integration Opportunities

#### External Services

- **Image Hosting Services**: Automated image upload and URL generation
- **OCR Integration**: Form field recognition through optical character recognition
- **Translation Services**: Multi-language form content adaptation
- **Analytics Integration**: Performance tracking and optimization
- **Notification Services**: Real-time alerts and status updates

#### API Extensions

- **REST API Wrapper**: HTTP API for remote ad publishing
- **Webhook Support**: Event-driven processing triggers
- **Queue Management**: Asynchronous job processing
- **Monitoring Dashboard**: Web-based status and analytics interface

### Scalability Improvements

#### Distributed Processing

```python
# Future: Distributed ad processing
class DistributedPublisher:
    def __init__(self, worker_nodes=["node1", "node2", "node3"]):
        self.workers = worker_nodes
        self.task_queue = RedisQueue("ad_publishing")

    def distribute_ads(self, ad_list):
        """Distribute ads across worker nodes"""
        for i, ad_uuid in enumerate(ad_list):
            worker = self.workers[i % len(self.workers)]
            self.task_queue.enqueue(worker, ad_uuid)
```

---

## License & Legal

This system is developed for educational and legitimate automation purposes. Users must:

- **Respect Terms of Service**: Comply with Njuskalo.hr's terms and conditions
- **Use Responsibly**: Avoid excessive requests or disruptive behavior
- **Data Privacy**: Handle personal data according to GDPR and local regulations
- **Authentication**: Use only legitimate credentials and authorized access
- **Rate Limiting**: Implement appropriate delays and request throttling

**Disclaimer**: This software is provided as-is for educational purposes. Users are responsible for ensuring compliance with applicable laws and website terms of service.

---

## Summary

✅ **Implementation Status**: Complete and Production Ready
🔧 **Last Updated**: November 2025
📚 **Compatibility**: Njuskalo.hr Croatian automotive marketplace
🏗️ **Architecture**: Modular, scalable, dual UUID design
🛡️ **Security**: Advanced anti-detection and privacy protection
📊 **Database**: MySQL integration with comprehensive validation
🚀 **Performance**: Optimized for reliability and efficiency
🔑 **UUID System**: Proper ad/user separation with automatic resolution
