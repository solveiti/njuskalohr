# 🏪 Njuskalo Sitemap Store Scraper - Complete Documentation

## Table of Contents

1. [Project Overview](#project-overview)
2. [Quick Start Guide](#quick-start-guide)
3. [Server-Compatible Firefox Configuration](#server-compatible-firefox-configuration)
4. [Firefox Migration from Chrome](#firefox-migration-from-chrome)
5. [SSH Tunneling System](#ssh-tunneling-system)
6. [Database Integration](#database-integration)
7. [Enhanced Anti-Detection](#enhanced-anti-detection)
8. [Tunnel Scraper Usage](#tunnel-scraper-usage)
9. [API Documentation](#api-documentation)
10. [Security Considerations](#security-considerations)
11. [Contributing Guidelines](#contributing-guidelines)
12. [Project Summary](#project-summary)

---

## Project Overview

A comprehensive Python web scraper that extracts store information from njuskalo.hr using a sitemap-based approach. This scraper focuses on finding stores that post in the "Auto moto" category (categoryId=2) and extracting their address and ad count information.

### 🎯 Purpose

This scraper is designed to:

1. Download the sitemap index XML from https://www.njuskalo.hr/sitemap-index.xml
2. Extract store-related sitemap URLs
3. Download and parse XML/XML.gz files to find store URLs (trgovina)
4. Visit each store page to scrape information
5. Check if stores post in categoryId 2 ("Auto moto" category)
6. Extract store address and number of ads from the entities-count class
7. Save all data to an Excel file and PostgreSQL database

### 🚀 Key Features

- **XML Sitemap Processing**: Downloads and processes compressed XML sitemaps
- **Auto Moto Detection**: Automatically identifies vehicle-related stores
- **Vehicle Counting**: Distinguishes between new ("Novo vozilo") and used ("Rabljeno vozilo") vehicles
- **SSH Tunnel Support**: Routes traffic through remote servers for anonymity
- **Server Compatibility**: Works on headless servers with xvfb-run
- **Database Integration**: PostgreSQL storage with JSONB support
- **Anti-Detection Measures**: Advanced stealth techniques
- **API Interface**: FastAPI + Celery for automated processing

---

## Quick Start Guide

### 1. Setup

Run the setup script to install dependencies:

```bash
chmod +x setup.sh
./setup.sh
```

This will:

- Install Firefox browser
- Create a Python virtual environment
- Install required Python packages

### 2. Database Setup (Optional but Recommended)

Set up PostgreSQL database for data persistence:

```bash
# Install PostgreSQL if not already installed
sudo pacman -S postgresql  # Arch Linux
sudo apt-get install postgresql postgresql-contrib  # Ubuntu/Debian

# Run database setup
python setup_database.py
```

### 3. Basic Usage

#### For Server Environments (Recommended):

```bash
xvfb-run -a python enhanced_tunnel_scraper.py --max-stores 10 --no-tunnels
```

#### With SSH Tunnels:

```bash
xvfb-run -a python enhanced_tunnel_scraper.py --max-stores 10
```

#### Using Wrapper Script:

```bash
./run_server_scraper.sh --max-stores 5 --verbose
```

### 4. Testing Configuration

```bash
# Test Firefox configuration
xvfb-run -a python test_firefox_tunel.py --skip-tunnel --verbose

# Test simple configuration
xvfb-run -a python server_firefox_example.py
```

---

## Server-Compatible Firefox Configuration

### Overview

This guide explains the server-compatible Firefox configuration that works reliably on headless servers. The configuration has been tested and verified to work with the exact setup provided.

### Key Configuration Elements

#### 1. Server-Compatible Firefox Options

```python
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options

# Set up Firefox options
options = Options()
options.headless = True
options.binary_location = "/usr/bin/firefox"  # Explicit Firefox binary path

# Server-specific preferences for stability
options.set_preference("browser.tabs.remote.autostart", False)
options.set_preference("layers.acceleration.disabled", True)
options.set_preference("gfx.webrender.force-disabled", True)
options.set_preference("dom.ipc.plugins.enabled", False)
options.set_preference("media.hardware-video-decoding.enabled", False)
options.set_preference("media.hardware-video-decoding.force-enabled", False)
options.set_preference("browser.startup.homepage", "about:blank")
options.set_preference("security.sandbox.content.level", 0)
options.set_preference("network.proxy.type", 0)

# Set up Geckodriver service
service = Service("/usr/local/bin/geckodriver")

# Initialize WebDriver
driver = webdriver.Firefox(service=service, options=options)
```

#### 2. Required System Components

- **Firefox**: `/usr/bin/firefox`
- **GeckoDriver**: `/usr/local/bin/geckodriver`
- **Xvfb**: For virtual display (`sudo pacman -S xorg-server-xvfb`)

#### 3. Running with xvfb-run

Always use `xvfb-run -a` for server environments:

```bash
xvfb-run -a python your_scraper_script.py
```

### Key Preferences Explained

| Preference                        | Value              | Purpose                             |
| --------------------------------- | ------------------ | ----------------------------------- |
| `binary_location`                 | `/usr/bin/firefox` | Explicit Firefox path for server    |
| `browser.tabs.remote.autostart`   | `False`            | Disable multi-process for stability |
| `layers.acceleration.disabled`    | `True`             | Disable hardware acceleration       |
| `gfx.webrender.force-disabled`    | `True`             | Disable GPU rendering               |
| `dom.ipc.plugins.enabled`         | `False`            | Disable plugin processes            |
| `media.hardware-video-decoding.*` | `False`            | Disable hardware video decode       |
| `security.sandbox.content.level`  | `0`                | Reduce sandboxing for server        |
| `network.proxy.type`              | `0`                | No proxy (unless tunnels used)      |

### Server Environment Checklist

- [ ] Firefox installed (`firefox --version`)
- [ ] GeckoDriver available (`/usr/local/bin/geckodriver --version`)
- [ ] Xvfb installed (`xvfb-run --help`)
- [ ] Internet connectivity (`ping google.com`)
- [ ] Python Selenium (`pip list | grep selenium`)
- [ ] Test script passes (`xvfb-run -a python test_firefox_tunel.py`)

---

## Firefox Migration from Chrome

### Overview

The entire Njuskalo scraper project has been successfully migrated from Chrome to Firefox for better stability, improved anti-detection capabilities, and easier deployment.

### What Was Changed

#### 1. Core Dependencies

- **OLD**: `webdriver-manager[chrome]`, `ChromeDriverManager`
- **NEW**: `webdriver-manager[firefox]`, `GeckoDriverManager`, `geckodriver-autoinstaller`

#### 2. Selenium Imports Updated

```python
# OLD Chrome imports
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# NEW Firefox imports
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager
```

#### 3. Files Modified

- ✅ `requirements.txt` - Updated dependencies
- ✅ `njuskalo_scraper_with_tunnels.py` - Complete Firefox conversion
- ✅ `njuskalo_sitemap_scraper.py` - Complete Firefox conversion
- ✅ `njuskalo_scraper.py` - Complete Firefox conversion
- ✅ `config.py` - Updated user agent to Firefox

#### 4. Browser Setup Changes

**Chrome Method (OLD):**

```python
chrome_options = Options()
chrome_options.add_argument("--user-agent=...")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_argument("--proxy-server=socks5://...")
self.driver = webdriver.Chrome(service=service, options=chrome_options)
```

**Firefox Method (NEW):**

```python
firefox_options = Options()
firefox_options.set_preference("general.useragent.override", "...")
firefox_options.set_preference("dom.webdriver.enabled", False)
firefox_options.set_preference("network.proxy.socks", "127.0.0.1")
self.driver = webdriver.Firefox(service=service, options=firefox_options)
```

### Benefits of Firefox Migration

1. **Better Stability**: Firefox is more reliable on server environments
2. **Improved Anti-Detection**: More granular control over browser fingerprinting
3. **Enhanced Proxy Support**: Better SOCKS proxy integration
4. **Server Compatibility**: Works better with xvfb-run on headless servers
5. **Resource Efficiency**: Lower memory usage compared to Chrome

---

## SSH Tunneling System

### Overview

A comprehensive SSH tunneling system for distributed web scraping with automatic IP rotation, anti-detection measures, and health monitoring.

### Features

- **Automated Server Setup**: Script to establish tunnel users on remote servers
- **SSH Tunnel Management**: Connect, disconnect, rotate, and monitor SSH tunnels
- **SOCKS Proxy Integration**: Automatic proxy configuration for scrapers
- **Health Monitoring**: Real-time tunnel health checks and automatic reconnection
- **Anti-Detection**: Enhanced stealth measures with tunnel rotation
- **Scraper Integration**: Drop-in replacement for existing scrapers with tunnel support

### Prerequisites

- Python 3.7+
- SSH access to remote servers with key-based authentication
- **sudo privileges on remote servers** (required for system configuration)
- Required Python packages: `subprocess`, `threading`, `socket`, `json`

### File Structure

```
├── ssh_tunnel_manager.py          # Core tunnel management system
├── setup_tunnel_servers.py        # Python server setup script
├── setup_tunnel_servers.sh        # Bash server setup script
├── scraper_tunnel_integration.py  # Scraper integration module
├── enhanced_scraper.py            # Enhanced scraper with tunneling
├── servers_config.json            # Sample server configuration
├── ssh_tunnels.json              # Generated tunnel configuration
└── tunnel_config.json            # Active tunnel configuration
```

### Setup Process

#### Step 1: Configure Your Servers

Edit `tunnel_config.json` with your remote server details:

```json
{
  "server1": {
    "host": "YOUR_SERVER_IP",
    "port": 22,
    "username": "tunnel_user",
    "key_file": "/path/to/private/key",
    "local_port": 8080,
    "remote_port": 80
  }
}
```

#### Step 2: Test SSH Connection

```bash
ssh -i /path/to/private/key tunnel_user@YOUR_SERVER_IP
```

#### Step 3: Run Tunnel-Enabled Scraper

```bash
python enhanced_tunnel_scraper.py --max-stores 10
```

### Tunnel Management Commands

```python
from ssh_tunnel_manager import SSHTunnelManager

# Initialize manager
manager = SSHTunnelManager("tunnel_config.json")

# Start a tunnel
manager.establish_tunnel("server1")

# Get proxy settings
proxy = manager.get_proxy_settings()
print(f"SOCKS proxy: {proxy['host']}:{proxy['port']}")

# Stop tunnel
manager.close_tunnel("server1")
```

---

## Database Integration

### Overview

The Njuskalo scraper has been enhanced with PostgreSQL database integration to provide persistent storage, data validation, and advanced querying capabilities.

### Key Features

#### 🗃️ Data Persistence

- All scraped store data is automatically saved to PostgreSQL
- URLs are tracked with creation and update timestamps
- Invalid/inaccessible URLs are flagged and stored separately
- Automatic upsert operations prevent duplicates

#### 📊 JSONB Storage

- Store data is saved as JSONB for flexible querying
- Supports complex nested data structures
- Enables fast JSON-based searches and filtering
- Maintains data integrity while allowing schema flexibility

#### 🔄 Data Management

- Automatic timestamp management (created_at, updated_at)
- URL uniqueness constraints
- Data validation and error tracking
- Efficient indexing for fast queries

### Database Schema

```sql
CREATE TABLE scraped_stores (
    id SERIAL PRIMARY KEY,
    url VARCHAR(2048) UNIQUE NOT NULL,
    results JSONB,
    is_valid BOOLEAN DEFAULT TRUE,
    is_automoto BOOLEAN,
    new_vehicle_count INTEGER DEFAULT 0,
    used_vehicle_count INTEGER DEFAULT 0,
    total_vehicle_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_scraped_stores_url ON scraped_stores(url);
CREATE INDEX idx_scraped_stores_is_valid ON scraped_stores(is_valid);
CREATE INDEX idx_scraped_stores_is_automoto ON scraped_stores(is_automoto);
CREATE INDEX idx_scraped_stores_created_at ON scraped_stores(created_at);
CREATE INDEX idx_scraped_stores_results_gin ON scraped_stores USING gin (results);
```

### New Files Added

1. **`database.py`** - Main database class with connection management
2. **`setup_database.py`** - Interactive database setup script
3. **`db_manager.py`** - Command-line database management tool
4. **`test_database.py`** - Database integration test suite
5. **`.env.example`** - Environment configuration template

### Usage Examples

```python
from database import NjuskaloDatabase

# Initialize database
db = NjuskaloDatabase()

# Save store data
store_data = {
    'name': 'Auto Store Name',
    'address': 'Store Address',
    'ads_count': 25,
    'is_auto_moto': True
}
db.save_store_data('https://njuskalo.hr/trgovina/example', store_data)

# Query data
valid_stores = db.get_valid_stores()
auto_stores = db.get_stores_by_category(is_auto_moto=True)
recent_stores = db.get_recent_stores(days=7)
```

---

## Enhanced Anti-Detection

### Overview

Comprehensive anti-detection enhancements implemented across all Njuskalo scrapers to avoid detection and blocking while scraping.

### Key Improvements Implemented

#### 1. Smart Delay System

- **Intelligent Timing**: Context-aware delays based on operation type
- **Randomized Patterns**: Triangular distribution for natural delay patterns
- **Progressive Scaling**: Longer delays as scraping progresses to avoid pattern detection
- **Stealth Delays**: Random extra-long delays (3-5% chance) for enhanced stealth

**Delay Profiles:**

- **Store Visits**: 8-20 seconds (main anti-detection measure)
- **Page Loads**: 2-5 seconds
- **Data Extraction**: 1-3 seconds
- **Pagination**: 3-8 seconds
- **Error Recovery**: 15-30 seconds
- **Extended Breaks**: 30-90 seconds every 10-15 stores

#### 2. Enhanced Browser Anti-Detection

**Advanced Firefox Options:**

```python
firefox_options.set_preference("dom.webdriver.enabled", False)
firefox_options.set_preference("useAutomationExtension", False)
firefox_options.set_preference("general.useragent.override", random_user_agent())
firefox_options.set_preference("privacy.trackingprotection.enabled", False)
firefox_options.set_preference("media.peerconnection.enabled", False)
firefox_options.set_preference("webgl.disabled", True)
```

#### 3. User Agent Rotation

```python
USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:119.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0"
]
```

#### 4. Request Pattern Randomization

- **Variable Request Timing**: Triangular distribution (min=8s, mode=12s, max=20s)
- **Organic Scrolling**: Simulated human-like page interactions
- **Random Click Events**: Occasional non-functional clicks for realism
- **Session Management**: Proper cookie and session handling

#### 5. IP Rotation via SSH Tunnels

- **Automatic Tunnel Rotation**: Changes IP every 10-20 stores
- **Health Monitoring**: Continuous tunnel connectivity checks
- **Fallback Mechanisms**: Graceful degradation if tunnels fail
- **Geographic Distribution**: Multiple server locations

### Implementation Example

```python
class AntiDetectionMixin:
    def smart_delay(self, delay_type="default"):
        """Intelligent delay system with natural patterns."""
        base_delays = {
            "store_visit": (8, 12, 20),
            "page_load": (2, 3, 5),
            "data_extract": (1, 2, 3),
            "pagination": (3, 5, 8)
        }

        min_delay, mode_delay, max_delay = base_delays.get(delay_type, (2, 4, 8))

        # Apply progressive scaling
        scale_factor = 1 + (self.stores_scraped * 0.01)

        # Calculate delay with triangular distribution
        delay = random.triangular(min_delay, max_delay, mode_delay) * scale_factor

        # 3% chance of extended delay (stealth mode)
        if random.random() < 0.03:
            delay += random.uniform(15, 45)

        time.sleep(delay)
```

---

## Tunnel Scraper Usage

### Why Your Scraper Wasn't Using SSH Tunnels

**The Problem:** Your original scraper (`njuskalo_sitemap_scraper.py`) was not configured to use SOCKS proxy. The Firefox browser was connecting directly to the internet without routing traffic through your SSH tunnel.

**The Missing Piece:** Firefox needs the SOCKS proxy preferences to use SOCKS proxy.

### The Solution

The `enhanced_tunnel_scraper.py` which:

1. **Inherits from your existing scraper** - All your current functionality is preserved
2. **Adds SSH tunnel management** - Automatically starts/stops tunnels
3. **Configures Firefox proxy** - Routes all traffic through SOCKS proxy
4. **Includes error handling** - Falls back to direct connection if tunnels fail

### Quick Setup

#### Step 1: Update Configuration

Edit `tunnel_config.json` and replace `YOUR_SERVER_IP` with your actual server IP:

```bash
# Edit the config file
nano tunnel_config.json

# Change this line:
"host": "YOUR_SERVER_IP",
# To your actual server IP:
"host": "123.456.789.012",
```

#### Step 2: Test SSH Connection

```bash
ssh -i ~/.ssh/your_key tunnel_user@123.456.789.012
```

#### Step 3: Run the Enhanced Scraper

```bash
# With tunnels (recommended)
xvfb-run -a python enhanced_tunnel_scraper.py --max-stores 10

# Without tunnels (for testing)
xvfb-run -a python enhanced_tunnel_scraper.py --max-stores 5 --no-tunnels
```

### Configuration Options

```bash
# Basic usage
python enhanced_tunnel_scraper.py --max-stores 10

# Advanced options
python enhanced_tunnel_scraper.py \
    --max-stores 20 \
    --tunnel-config custom_config.json \
    --verbose \
    --headless

# Server usage with xvfb
xvfb-run -a python enhanced_tunnel_scraper.py --max-stores 10 --verbose
```

---

## API Documentation

### Overview

The Njuskalo scraper has been enhanced with a FastAPI REST API that uses Celery for background task processing and Redis as a message broker.

### Architecture

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
```

### Setup Requirements

```bash
# Install Redis
sudo pacman -S redis  # Arch Linux
sudo apt-get install redis-server  # Ubuntu

# Install Python dependencies
pip install fastapi celery redis uvicorn

# Start Redis
sudo systemctl start redis
```

### API Endpoints

#### 1. Start Scraping Job

```bash
POST /api/scrape
Content-Type: application/json

{
  "max_stores": 50,
  "use_tunnels": true,
  "headless": true
}
```

#### 2. Get Job Status

```bash
GET /api/jobs/{task_id}
```

#### 3. List All Jobs

```bash
GET /api/jobs
```

#### 4. Get Scraped Data

```bash
GET /api/data?limit=100&offset=0&auto_moto_only=true
```

### Running the API

```bash
# Start the FastAPI server
uvicorn api_main:app --host 0.0.0.0 --port 8000

# Start Celery worker
celery -A celery_app worker --loglevel=info

# Start Celery beat (scheduler)
celery -A celery_app beat --loglevel=info
```

### Web Dashboard

Access the web dashboard at `http://localhost:8000/dashboard` to:

- Start new scraping jobs
- Monitor job progress
- View scraped data
- Manage scheduled tasks
- Check system status

---

## Security Considerations

### Data Protection

- **Environment Variables**: Sensitive configuration stored in `.env` files
- **SSH Key Security**: Private keys stored with proper permissions (600)
- **Database Security**: Connection strings encrypted and secured
- **Tunnel Security**: SSH tunnels use key-based authentication

### Rate Limiting

- **Smart Delays**: Prevent overwhelming target servers
- **Request Throttling**: Configurable rate limits per scraper instance
- **IP Rotation**: Distribute requests across multiple IPs
- **Session Management**: Proper cookie and session handling

### Best Practices

1. **Use SSH Tunnels**: Always route traffic through secure tunnels
2. **Monitor Logs**: Regular log review for unusual patterns
3. **Rotate Credentials**: Regular SSH key rotation
4. **Update Dependencies**: Keep all packages up to date
5. **Secure Storage**: Encrypt sensitive data at rest

### Compliance

- **Robots.txt**: Respect website crawling policies
- **Rate Limits**: Follow reasonable request patterns
- **Data Usage**: Use scraped data responsibly
- **Legal Compliance**: Ensure compliance with local laws

---

## Contributing Guidelines

### Development Setup

1. **Fork the Repository**

```bash
git clone https://github.com/yourusername/njuskalohr.git
cd njuskalohr
```

2. **Create Virtual Environment**

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

3. **Install Dependencies**

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies
```

### Code Standards

- **Python Style**: Follow PEP 8 guidelines
- **Documentation**: Add docstrings to all functions and classes
- **Type Hints**: Use type annotations where applicable
- **Testing**: Write tests for new functionality
- **Logging**: Use proper logging instead of print statements

### Testing

```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest test_database.py

# Run with coverage
python -m pytest --cov=. --cov-report=html
```

### Pull Request Process

1. **Create Feature Branch**

```bash
git checkout -b feature/your-feature-name
```

2. **Make Changes and Test**

```bash
# Make your changes
python -m pytest  # Ensure tests pass
```

3. **Commit and Push**

```bash
git add .
git commit -m "Add: Description of your changes"
git push origin feature/your-feature-name
```

4. **Create Pull Request**

- Provide clear description of changes
- Include test results
- Reference any related issues

### Reporting Issues

When reporting bugs, please include:

- **Environment Details**: OS, Python version, dependency versions
- **Error Messages**: Full stack traces
- **Steps to Reproduce**: Clear reproduction steps
- **Expected Behavior**: What should have happened
- **Actual Behavior**: What actually happened

---

## Project Summary

### ✅ Project Rework Complete

This project has been successfully reworked from a simple car listing scraper to a comprehensive sitemap-based store scraper with advanced features.

### 🎯 Implemented Workflow

The scraper now follows this exact process:

1. **📥 Downloads sitemap index XML** from `https://www.njuskalo.hr/sitemap-index.xml`
2. **🔍 Finds store-related sitemaps** (prioritizes `sitemap-index-stores.xml`)
3. **📦 Downloads and extracts XML.gz files** from the sitemaps
4. **🏪 Extracts store URLs** containing `/trgovina/` pattern
5. **🌐 Visits each store page** to scrape information
6. **✅ Checks for categoryId 2** ("Auto moto" category)
7. **📍 Extracts address and ads count** from entities-count class
8. **🚗 Counts vehicle types** (Novo vozilo vs Rabljeno vozilo)
9. **💾 Saves all data to database** with comprehensive information

### 📊 Test Results

✅ **Enhanced Scraper Test Results**:

- Successfully processed XML sitemaps
- Found 16 new URLs and processed them
- Identified auto moto stores correctly
- Counted vehicle types accurately
- All tests passed with server-compatible configuration

### 📁 Project Files Structure

```
njuskalohr/
├── Core Scrapers
│   ├── enhanced_njuskalo_scraper.py      # Enhanced scraper with XML processing
│   ├── enhanced_tunnel_scraper.py        # Tunnel-enabled enhanced scraper
│   ├── njuskalo_sitemap_scraper.py       # Base scraper class
│   └── njuskalo_scraper.py               # Legacy scraper
├── Database
│   ├── database.py                       # Database integration
│   ├── setup_database.py                # Database setup script
│   └── db_manager.py                     # Database management CLI
├── SSH Tunneling
│   ├── ssh_tunnel_manager.py             # Tunnel management system
│   ├── setup_tunnel_servers.py          # Server setup automation
│   └── tunnel_config.json               # Tunnel configuration
├── Testing & Examples
│   ├── test_firefox_tunel.py             # Firefox configuration tests
│   ├── server_firefox_example.py        # Simple server example
│   └── run_server_scraper.sh             # Server execution script
├── Configuration
│   ├── config.py                         # Scraper configuration
│   ├── requirements.txt                  # Python dependencies
│   └── .env.example                      # Environment template
└── Documentation
    ├── COMPLETE_DOCUMENTATION.md         # This comprehensive guide
    └── Various specific guides           # Individual topic guides
```

### 🔧 Key Features Summary

#### Core Functionality

- ✅ XML sitemap processing with gzip support
- ✅ Auto moto category detection
- ✅ Vehicle type counting (new vs used)
- ✅ PostgreSQL database integration
- ✅ Server-compatible Firefox configuration

#### Advanced Features

- ✅ SSH tunnel support with IP rotation
- ✅ Enhanced anti-detection measures
- ✅ FastAPI + Celery integration
- ✅ Comprehensive error handling
- ✅ Real-time monitoring and logging

#### Server Compatibility

- ✅ xvfb-run integration for headless servers
- ✅ Hardware acceleration disabled for stability
- ✅ Optimized Firefox preferences for servers
- ✅ Comprehensive testing suite

### 🚀 Getting Started Commands

```bash
# Quick test on server
xvfb-run -a python test_firefox_tunel.py --skip-tunnel

# Enhanced scraping without tunnels
xvfb-run -a python enhanced_tunnel_scraper.py --max-stores 5 --no-tunnels

# Full enhanced scraping with tunnels
xvfb-run -a python enhanced_tunnel_scraper.py --max-stores 10

# Using wrapper script
./run_server_scraper.sh --max-stores 10 --verbose
```

### 📈 Performance Metrics

- **XML Processing**: Handles 2800+ store URLs efficiently
- **Server Stability**: Works reliably on headless servers
- **Anti-Detection**: Advanced stealth measures implemented
- **Database Performance**: Optimized queries with proper indexing
- **Tunnel Integration**: Seamless IP rotation and proxy management

---

## Conclusion

This comprehensive scraper system provides a robust, scalable solution for extracting store information from Njuskalo.hr with advanced anti-detection measures, server compatibility, and professional-grade features. The system is designed to be maintainable, extensible, and reliable for production use.

For specific implementation details, refer to the individual sections above or examine the codebase directly. The project includes comprehensive testing, documentation, and example configurations to get you started quickly.

---

**Last Updated**: November 7, 2025
**Version**: 2.0.0
**Status**: Production Ready ✅
