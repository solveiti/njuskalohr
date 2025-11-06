# 🦊 Firefox Migration Guide

## Overview

The entire Njuskalo scraper project has been successfully migrated from Chrome to Firefox for better stability, improved anti-detection capabilities, and easier deployment.

## 🔄 What Was Changed

### 1. **Core Dependencies**

- **OLD**: `webdriver-manager[chrome]`, `ChromeDriverManager`
- **NEW**: `webdriver-manager[firefox]`, `GeckoDriverManager`, `geckodriver-autoinstaller`

### 2. **Selenium Imports Updated**

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

### 3. **Files Modified**

- ✅ `requirements.txt` - Updated dependencies
- ✅ `njuskalo_scraper_with_tunnels.py` - Complete Firefox conversion
- ✅ `njuskalo_sitemap_scraper.py` - Complete Firefox conversion
- ✅ `njuskalo_scraper.py` - Complete Firefox conversion
- ✅ `config.py` - Updated user agent to Firefox

### 4. **Browser Setup Changes**

#### Chrome Method (OLD):

```python
chrome_options = Options()
chrome_options.add_argument("--user-agent=...")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_argument("--proxy-server=socks5://...")
self.driver = webdriver.Chrome(service=service, options=chrome_options)
```

#### Firefox Method (NEW):

```python
firefox_options = Options()
firefox_options.set_preference("general.useragent.override", "...")
firefox_options.set_preference("dom.webdriver.enabled", False)
firefox_options.set_preference("network.proxy.type", 1)  # For SOCKS proxy
firefox_options.set_preference("network.proxy.socks", "127.0.0.1")
self.driver = webdriver.Firefox(service=service, options=firefox_options)
```

### 5. **User Agent Strings Updated**

- **OLD**: Chrome-based user agents (`Chrome/120.0.0.0 Safari/537.36`)
- **NEW**: Firefox-based user agents (`rv:120.0 Gecko/20100101 Firefox/120.0`)

### 6. **SOCKS Proxy Configuration**

- **Chrome**: Used `--proxy-server=socks5://127.0.0.1:8081`
- **Firefox**: Uses preference-based configuration:
  ```python
  firefox_options.set_preference("network.proxy.type", 1)
  firefox_options.set_preference("network.proxy.socks", "127.0.0.1")
  firefox_options.set_preference("network.proxy.socks_port", 8081)
  firefox_options.set_preference("network.proxy.socks_version", 5)
  ```

## 🚀 Installation & Setup

### For Manjaro/Arch Linux:

```bash
# Run the setup script
./setup_firefox_manjaro.sh
```

### Manual Installation:

```bash
# Install Firefox
sudo pacman -S firefox  # Manjaro/Arch
sudo apt-get install firefox  # Ubuntu/Debian

# Install Python dependencies
source .venv/bin/activate
pip install -r requirements.txt
```

## 🧪 Testing the Migration

### 1. Test Basic Functionality:

```bash
cd /home/srdjan/njuskalohr
source .venv/bin/activate
python test_scraper_suite.py
```

### 2. Test Tunnel Integration:

```bash
# Test without tunnels
python njuskalo_scraper_with_tunnels.py --no-tunnels --max-stores 3

# Test with tunnels (requires SSH key setup)
python njuskalo_scraper_with_tunnels.py --max-stores 3
```

### 3. Test Scripts:

```bash
# Basic scraping
python run_scraper.py

# Tunnel-enabled scraping
./run_scraper_with_tunnels.sh --max-stores 5
```

## ✅ Benefits of Firefox Migration

1. **Better Stealth**: Firefox has superior anti-detection capabilities
2. **Stable Proxy Support**: More reliable SOCKS proxy implementation
3. **Resource Efficiency**: Generally uses less memory than Chrome
4. **Open Source**: Better community support and transparency
5. **Less Detection**: Many sites don't specifically target Firefox automation

## 🔧 Usage Examples

### Basic Scraping:

```python
from njuskalo_sitemap_scraper import NjuskaloSitemapScraper

scraper = NjuskaloSitemapScraper(headless=True)
stores = scraper.run_full_scrape(max_stores=10)
```

### With Tunnels:

```python
from njuskalo_scraper_with_tunnels import TunnelEnabledNjuskaloScraper

scraper = TunnelEnabledNjuskaloScraper(
    headless=True,
    use_tunnels=True,
    tunnel_config_path='tunnel_config.json'
)
stores = scraper.run_full_scrape(max_stores=10)
```

## 🚨 Important Notes

1. **Tunnel Configuration**: The tunnel config format is correct (`tunnel_config.json`)
2. **SSH Key Setup**: Still needed for tunnel functionality
3. **All Scripts Updated**: Both Python and Bash scripts support Firefox
4. **Backward Compatibility**: No Chrome code remains - complete migration

## 🎯 Next Steps

1. Install Firefox on your system using the provided setup script
2. Test the basic scraper functionality
3. Complete SSH key setup for tunnel functionality
4. Run production scraping with Firefox

The migration is complete and ready for production use! 🎉
