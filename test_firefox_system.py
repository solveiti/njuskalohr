#!/usr/bin/env python3
"""
Simple Firefox and GeckoDriver Test Script

This script tests:
1. System GeckoDriver installation at /usr/local/bin/geckodriver
2. Firefox browser functionality
3. SSH tunnel integration (optional)

Usage:
    python test_firefox_system.py
    python test_firefox_system.py --with-tunnel
    python test_firefox_system.py --verbose
"""

import sys
import os
import time
import logging
import argparse
import subprocess
from pathlib import Path
from typing import Optional

# Add current directory to Python path
sys.path.append(str(Path(__file__).parent))

# Selenium imports
try:
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except ImportError as e:
    print(f"❌ Error importing Selenium: {e}")
    print("💡 Install with: pip install selenium")
    sys.exit(1)

def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)

def test_geckodriver_installation():
    """Test if GeckoDriver is installed at expected location"""
    print("🧪 Testing GeckoDriver Installation")
    print("-" * 40)

    geckodriver_path = "/usr/local/bin/geckodriver"

    # Check if file exists
    if not os.path.exists(geckodriver_path):
        print(f"❌ GeckoDriver not found at: {geckodriver_path}")
        print("💡 Install with:")
        print("   wget https://github.com/mozilla/geckodriver/releases/latest/download/geckodriver-v0.34.0-linux64.tar.gz")
        print("   tar -xzf geckodriver-v*.tar.gz")
        print("   sudo mv geckodriver /usr/local/bin/")
        print("   sudo chmod +x /usr/local/bin/geckodriver")
        return False

    # Check if executable
    if not os.access(geckodriver_path, os.X_OK):
        print(f"❌ GeckoDriver exists but not executable: {geckodriver_path}")
        print("💡 Fix with: sudo chmod +x /usr/local/bin/geckodriver")
        return False

    # Test version
    try:
        result = subprocess.run([geckodriver_path, '--version'],
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_info = result.stdout.strip().split('\n')[0]
            print(f"✅ GeckoDriver found: {version_info}")
            print(f"   Location: {geckodriver_path}")
            return True
        else:
            print(f"❌ GeckoDriver version check failed")
            return False
    except Exception as e:
        print(f"❌ Error checking GeckoDriver: {e}")
        return False

def test_firefox_installation():
    """Test if Firefox is installed"""
    print("\n🦊 Testing Firefox Installation")
    print("-" * 40)

    try:
        result = subprocess.run(['firefox', '--version'],
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ Firefox found: {version}")
            return True
        else:
            print("❌ Firefox version check failed")
            return False
    except FileNotFoundError:
        print("❌ Firefox not found in system PATH")
        print("💡 Install with: sudo pacman -S firefox")
        return False
    except Exception as e:
        print(f"❌ Error checking Firefox: {e}")
        return False

def test_firefox_webdriver():
    """Test Firefox WebDriver functionality"""
    print("\n🔧 Testing Firefox WebDriver")
    print("-" * 40)

    driver = None
    try:
        print("Creating Firefox options...")
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        # Anti-detection preferences
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)

        print("Creating Firefox service...")
        service = Service("/usr/local/bin/geckodriver")

        print("Starting Firefox WebDriver...")
        driver = webdriver.Firefox(service=service, options=options)

        print("Testing basic navigation...")
        test_html = """
        <!DOCTYPE html>
        <html>
        <head><title>GeckoDriver Test</title></head>
        <body>
            <h1 id="test-header">Firefox WebDriver Test</h1>
            <p id="test-time">Test Time: """ + str(time.time()) + """</p>
            <button id="test-button" onclick="this.textContent='Clicked!'">Click Me</button>
        </body>
        </html>
        """

        driver.get(f"data:text/html;charset=utf-8,{test_html}")

        # Test element finding
        header = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "test-header"))
        )

        if header.text == "Firefox WebDriver Test":
            print("✅ Element finding: PASSED")
        else:
            print(f"❌ Element finding: FAILED - Expected 'Firefox WebDriver Test', got '{header.text}'")
            return False

        # Test JavaScript execution
        driver.execute_script("document.getElementById('test-button').click();")
        button = driver.find_element(By.ID, "test-button")

        if button.text == "Clicked!":
            print("✅ JavaScript execution: PASSED")
        else:
            print(f"❌ JavaScript execution: FAILED - Button text: '{button.text}'")
            return False

        print("✅ Firefox WebDriver test: PASSED")
        return True

    except Exception as e:
        print(f"❌ Firefox WebDriver test failed: {e}")
        return False
    finally:
        if driver:
            try:
                driver.quit()
                print("🧹 WebDriver cleaned up")
            except:
                pass

def test_external_site():
    """Test accessing external website"""
    print("\n🌐 Testing External Site Access")
    print("-" * 40)

    driver = None
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        # Set a realistic user agent
        options.set_preference("general.useragent.override",
                             "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0")

        service = Service("/usr/local/bin/geckodriver")
        driver = webdriver.Firefox(service=service, options=options)
        driver.set_page_load_timeout(30)

        print("Accessing httpbin.org...")
        driver.get("http://httpbin.org/user-agent")

        # Wait for page to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "pre"))
        )

        page_source = driver.page_source
        if "user-agent" in page_source.lower() and "firefox" in page_source.lower():
            print("✅ External site access: PASSED")
            print("   Successfully accessed httpbin.org with Firefox user agent")
            return True
        else:
            print("❌ External site access: FAILED")
            print(f"   Page source preview: {page_source[:200]}...")
            return False

    except Exception as e:
        print(f"❌ External site test failed: {e}")
        return False
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def test_with_tunnel():
    """Test Firefox with SSH tunnel"""
    print("\n🚇 Testing Firefox with SSH Tunnel")
    print("-" * 40)

    try:
        from ssh_tunnel_manager import SSHTunnelManager
    except ImportError:
        print("❌ ssh_tunnel_manager not available - skipping tunnel test")
        return False

    tunnel_manager = None
    driver = None

    try:
        # Load tunnel configuration
        config_path = "tunnel_config.json"
        if not os.path.exists(config_path):
            print(f"❌ Tunnel config not found: {config_path}")
            return False

        print("Loading tunnel configuration...")
        tunnel_manager = SSHTunnelManager(config_path)
        tunnels = tunnel_manager.list_tunnels()

        if not tunnels:
            print("❌ No tunnels configured")
            return False

        tunnel_name = tunnels[0]
        print(f"Starting tunnel: {tunnel_name}")

        success = tunnel_manager.start_tunnel(tunnel_name)
        if not success:
            print("❌ Failed to start tunnel")
            return False

        socks_port = tunnel_manager.get_tunnel_port(tunnel_name)
        print(f"✅ Tunnel active on port: {socks_port}")

        # Test Firefox with SOCKS proxy
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        # Configure SOCKS proxy
        options.set_preference("network.proxy.type", 1)
        options.set_preference("network.proxy.socks", "127.0.0.1")
        options.set_preference("network.proxy.socks_port", socks_port)
        options.set_preference("network.proxy.socks_version", 5)
        options.set_preference("network.proxy.socks_remote_dns", True)

        service = Service("/usr/local/bin/geckodriver")
        driver = webdriver.Firefox(service=service, options=options)
        driver.set_page_load_timeout(30)

        print("Testing proxy functionality...")
        driver.get("http://httpbin.org/ip")

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "pre"))
        )

        print("✅ Firefox + SSH tunnel test: PASSED")
        return True

    except Exception as e:
        print(f"❌ Tunnel test failed: {e}")
        return False
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
        if tunnel_manager and 'tunnel_name' in locals():
            try:
                tunnel_manager.close_tunnel(tunnel_name)
                print("🧹 Tunnel closed")
            except:
                pass

def main():
    """Main test function"""
    parser = argparse.ArgumentParser(description="Firefox System GeckoDriver Test")
    parser.add_argument("--with-tunnel", action="store_true",
                       help="Include SSH tunnel tests")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        setup_logging(True)

    print("🚀 Firefox System GeckoDriver Test Suite")
    print("=" * 50)

    tests = [
        test_geckodriver_installation,
        test_firefox_installation,
        test_firefox_webdriver,
        test_external_site
    ]

    if args.with_tunnel:
        tests.append(test_with_tunnel)

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
            time.sleep(1)  # Brief pause between tests
        except KeyboardInterrupt:
            print("\n⚠️  Tests interrupted by user")
            break
        except Exception as e:
            print(f"❌ Test failed with unexpected error: {e}")

    print(f"\n📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Firefox with system GeckoDriver is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)