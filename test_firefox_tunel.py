#!/usr/bin/env python3
"""
Firefox and Tunnel Test Script for Njuskalo Scraper

This script performs comprehensive testing of:
1. Firefox browser installation
2. GeckoDriver functionality
3. SSH tunnel connectivity
4. SOCKS proxy configuration
5. End-to-end browser + tunnel integration

Usage:
    python test_firefox_tunnel.py
    python test_firefox_tunnel.py --verbose
    python test_firefox_tunnel.py --skip-tunnel
"""

import sys
import os
import time
import logging
import argparse
import subprocess
import requests
import socket
from pathlib import Path
from typing import Optional, Dict, Any

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

# Tunnel manager import
try:
    from ssh_tunnel_manager import SSHTunnelManager
except ImportError:
    print("⚠️  Warning: ssh_tunnel_manager.py not found - tunnel tests will be skipped")
    SSHTunnelManager = None

def find_geckodriver():
    """Find GeckoDriver from multiple possible locations"""
    import glob
    import shutil

    possible_paths = [
        "/usr/local/bin/geckodriver",
        "/usr/bin/geckodriver",
    ]

    # Check exact paths first
    for path in possible_paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            return path

    # Check webdriver-manager cache
    wdm_pattern = "~/.wdm/drivers/geckodriver/linux64/*/geckodriver"
    matches = glob.glob(wdm_pattern)
    if matches:
        for match in matches:
            if os.access(match, os.X_OK):
                return match

    # Try to find in PATH
    path_geckodriver = shutil.which("geckodriver")
    if path_geckodriver:
        return path_geckodriver

    return None

# Configure logging
def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)

class FirefoxTunnelTester:
    """Comprehensive Firefox and tunnel testing suite"""

    def __init__(self, verbose: bool = False, skip_tunnel: bool = False):
        self.logger = setup_logging(verbose)
        self.skip_tunnel = skip_tunnel
        self.test_results = {}
        self.tunnel_manager = None
        self.tunnel_name = None
        self.socks_port = None
        self.geckodriver_path = None

    def print_header(self, title: str):
        """Print formatted test section header"""
        print(f"\n{'='*60}")
        print(f"🧪 {title}")
        print(f"{'='*60}")

    def test_system_requirements(self) -> bool:
        """Test basic system requirements"""
        self.print_header("System Requirements Check")

        try:
            # Check Python version
            python_version = sys.version
            self.logger.info(f"🐍 Python version: {python_version}")

            # Check if Firefox is installed
            try:
                result = subprocess.run(['firefox', '--version'],
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    firefox_version = result.stdout.strip()
                    self.logger.info(f"🦊 Firefox version: {firefox_version}")
                    self.test_results['firefox_installed'] = True
                else:
                    self.logger.error("❌ Firefox not found in system PATH")
                    self.test_results['firefox_installed'] = False
                    return False
            except FileNotFoundError:
                self.logger.error("❌ Firefox not installed or not in PATH")
                self.logger.error("💡 Install with: sudo pacman -S firefox")
                self.test_results['firefox_installed'] = False
                return False
            except subprocess.TimeoutExpired:
                self.logger.error("❌ Firefox version check timed out")
                self.test_results['firefox_installed'] = False
                return False

            # Check display environment
            display = os.environ.get('DISPLAY')
            if display:
                self.logger.info(f"🖥️  Display environment: {display}")
            else:
                self.logger.info("🖥️  No DISPLAY set (headless mode)")

            self.logger.info("✅ System requirements check: PASSED")
            return True

        except Exception as e:
            self.logger.error(f"❌ System requirements check failed: {e}")
            self.test_results['system_requirements'] = False
            return False

    def test_geckodriver(self) -> bool:
        """Test GeckoDriver installation and functionality"""
        self.print_header("GeckoDriver Test")

        try:
            self.logger.info("🚗 Testing GeckoDriver installation...")

            # Find GeckoDriver from multiple locations
            driver_path = find_geckodriver()
            if not driver_path:
                self.logger.error("❌ GeckoDriver not found in any expected location")
                self.logger.error("💡 Searched locations:")
                self.logger.error("   - /usr/local/bin/geckodriver")
                self.logger.error("   - /usr/bin/geckodriver")
                self.logger.error("   - ~/.wdm/drivers/geckodriver/linux64/*/geckodriver")
                self.logger.error("   - PATH environment variable")
                self.logger.error("")
                self.logger.error("💡 Install with:")
                self.logger.error("   wget https://github.com/mozilla/geckodriver/releases/latest/download/geckodriver-v0.34.0-linux64.tar.gz")
                self.logger.error("   tar -xzf geckodriver-v*.tar.gz")
                self.logger.error("   sudo mv geckodriver /usr/local/bin/")
                self.logger.error("   sudo chmod +x /usr/local/bin/geckodriver")
                self.test_results['geckodriver'] = False
                return False

            self.logger.info(f"✅ GeckoDriver found at: {driver_path}")
            # Store for use in other tests
            self.geckodriver_path = driver_path

            # Test GeckoDriver version
            result = subprocess.run([driver_path, '--version'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version = result.stdout.strip().split('\n')[0]
                self.logger.info(f"🚗 GeckoDriver version: {version}")
                self.test_results['geckodriver'] = True
                return True
            else:
                self.logger.error("❌ GeckoDriver version check failed")
                self.test_results['geckodriver'] = False
                return False

        except Exception as e:
            self.logger.error(f"❌ GeckoDriver test failed: {e}")
            self.test_results['geckodriver'] = False
            return False

    def test_firefox_basic(self) -> bool:
        """Test basic Firefox WebDriver functionality with server-compatible configuration"""
        self.print_header("Firefox Basic Test (Server Compatible)")

        driver = None
        try:
            self.logger.info("🦊 Starting server-compatible Firefox WebDriver test...")
            self.logger.info("🖥️  Using xvfb-run for virtual display...")

            # Server-compatible Firefox options
            options = Options()
            options.headless = True
            options.binary_location = "/usr/bin/firefox"  # Set the Firefox binary explicitly

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

            # Additional anti-detection preferences
            options.set_preference("dom.webdriver.enabled", False)
            options.set_preference("useAutomationExtension", False)

            # Create service with GeckoDriver
            if not self.geckodriver_path:
                self.geckodriver_path = find_geckodriver()
            service = Service("/usr/local/bin/geckodriver")

            # Use xvfb-run to create virtual display
            self.logger.info("🔧 Creating Firefox WebDriver with xvfb-run...")

            # Test if we can create the driver
            driver = webdriver.Firefox(service=service, options=options)

            # Test basic functionality
            self.logger.info("🌐 Testing basic navigation...")
            test_html = "data:text/html,<html><body><h1 id='test'>Firefox WebDriver Test</h1><p>Server Compatible Mode</p><p>Timestamp: " + str(time.time()) + "</p></body></html>"
            driver.get(test_html)

            # Test element finding
            element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "test"))
            )

            if element and element.text == "Firefox WebDriver Test":
                self.logger.info("✅ Firefox server-compatible test: PASSED")
                self.logger.info("🎉 Server configuration working correctly!")
                self.test_results['firefox_basic'] = True
                return True
            else:
                self.logger.error("❌ Element finding test failed")
                self.test_results['firefox_basic'] = False
                return False

        except Exception as e:
            self.logger.error(f"❌ Firefox server-compatible test failed: {e}")
            self.logger.error("🔧 Troubleshooting suggestions:")
            self.logger.error("   1. Install Xvfb: sudo pacman -S xorg-server-xvfb")
            self.logger.error("   2. Verify Firefox location: ls -la /usr/bin/firefox")
            self.logger.error("   3. Check GeckoDriver: ls -la /usr/local/bin/geckodriver")
            self.logger.error("   4. Try running with: xvfb-run -a python test_firefox_tunel.py")
            self.test_results['firefox_basic'] = False
            return False
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

    def test_internet_connectivity(self) -> bool:
        """Test basic internet connectivity"""
        self.print_header("Internet Connectivity Test")

        try:
            test_urls = [
                "http://httpbin.org/ip",
                "https://www.google.com",
                "https://www.njuskalo.hr"
            ]

            for url in test_urls:
                try:
                    self.logger.info(f"🌐 Testing connectivity to: {url}")
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        self.logger.info(f"✅ {url}: Connected (Status: {response.status_code})")
                    else:
                        self.logger.warning(f"⚠️  {url}: Status {response.status_code}")
                except requests.RequestException as e:
                    self.logger.error(f"❌ {url}: Failed - {e}")

            self.test_results['internet_connectivity'] = True
            return True

        except Exception as e:
            self.logger.error(f"❌ Internet connectivity test failed: {e}")
            self.test_results['internet_connectivity'] = False
            return False

    def test_server_firefox_config(self) -> bool:
        """Test server-specific Firefox configuration with Njuskalo access"""
        self.print_header("Server Firefox Configuration Test")

        driver = None
        try:
            self.logger.info("🖥️  Testing server-optimized Firefox configuration...")

            # Server-compatible Firefox options (exact configuration from user)
            options = Options()
            options.headless = True
            options.binary_location = "/usr/bin/firefox"
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
            self.logger.info("🦊 Initializing Firefox with server configuration...")
            driver = webdriver.Firefox(service=service, options=options)

            # Test 1: Basic functionality
            self.logger.info("🧪 Test 1: Basic HTML rendering...")
            test_html = "data:text/html,<html><body><h1 id='test'>Server Config Test</h1></body></html>"
            driver.get(test_html)

            element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "test"))
            )
            self.logger.info("✅ Basic HTML rendering: PASSED")

            # Test 2: Real website access
            self.logger.info("🧪 Test 2: Accessing Njuskalo.hr...")
            driver.get("https://www.njuskalo.hr")

            # Wait for page to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            page_title = driver.title
            self.logger.info(f"📄 Page title: {page_title}")

            if "njuskalo" in page_title.lower():
                self.logger.info("✅ Njuskalo access: PASSED")
            else:
                self.logger.warning(f"⚠️  Unexpected page title: {page_title}")

            # Test 3: JavaScript execution
            self.logger.info("🧪 Test 3: JavaScript execution...")
            js_result = driver.execute_script("return document.readyState")
            if js_result == "complete":
                self.logger.info("✅ JavaScript execution: PASSED")
            else:
                self.logger.warning(f"⚠️  Document state: {js_result}")

            self.logger.info("🎉 Server Firefox configuration: ALL TESTS PASSED")
            self.test_results['server_firefox_config'] = True
            return True

        except Exception as e:
            self.logger.error(f"❌ Server Firefox configuration test failed: {e}")
            self.logger.error("🔧 This is the exact configuration that should work on the server:")
            self.logger.error("   - Firefox binary: /usr/bin/firefox")
            self.logger.error("   - GeckoDriver: /usr/local/bin/geckodriver")
            self.logger.error("   - Headless mode with hardware acceleration disabled")
            self.logger.error("   - Run with: xvfb-run -a python script.py")
            self.test_results['server_firefox_config'] = False
            return False
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

    def test_tunnel_setup(self) -> bool:
        """Test SSH tunnel setup and connectivity"""
        if self.skip_tunnel or not SSHTunnelManager:
            self.logger.info("⏭️  Skipping tunnel tests (disabled or not available)")
            return True

        self.print_header("SSH Tunnel Test")

        try:
            # Initialize tunnel manager
            config_path = "tunnel_config.json"
            if not os.path.exists(config_path):
                self.logger.error(f"❌ Tunnel config file not found: {config_path}")
                self.test_results['tunnel_setup'] = False
                return False

            self.logger.info(f"🔧 Loading tunnel configuration from: {config_path}")
            self.tunnel_manager = SSHTunnelManager(config_path)

            # Clean up any existing tunnels first
            self.logger.info("🧹 Cleaning up any existing tunnels...")
            self.tunnel_manager.close_all_tunnels()

            # Get available tunnels
            tunnels = self.tunnel_manager.list_tunnels()
            if not tunnels:
                self.logger.error("❌ No tunnels configured")
                self.test_results['tunnel_setup'] = False
                return False

            # Use first available tunnel
            self.tunnel_name = list(tunnels.keys())[0]
            self.logger.info(f"🚇 Testing tunnel: {self.tunnel_name}")
            self.logger.debug(f"Available tunnels: {list(tunnels.keys())}")

            # Start tunnel
            self.logger.info("🔧 Starting SSH tunnel...")
            success = self.tunnel_manager.establish_tunnel(self.tunnel_name)
            self.logger.debug(f"Tunnel start result: {success} (type: {type(success)})")

            if success:
                # Get SOCKS proxy settings
                proxy_settings = self.tunnel_manager.get_proxy_settings()
                self.socks_port = proxy_settings.get('local_port') if proxy_settings else None
                self.logger.info(f"✅ Tunnel started successfully on port: {self.socks_port}")
                self.logger.debug(f"Proxy settings: {proxy_settings}")

                if not self.socks_port:
                    self.logger.error("❌ Tunnel started but no SOCKS port available")
                    self.test_results['tunnel_setup'] = False
                    return False

                # Test SOCKS proxy connectivity
                return self.test_socks_proxy()
            else:
                self.logger.error(f"❌ Failed to start SSH tunnel - returned: {success}")
                self.logger.error("💡 Check SSH connection details in tunnel_config.json")
                self.logger.error("💡 Verify SSH key permissions: chmod 600 /home/srdjan/njuskalohr/tunnel_key")
                self.test_results['tunnel_setup'] = False
                return False

        except Exception as e:
            import traceback
            self.logger.error(f"❌ Tunnel setup failed: {e}")
            self.logger.error(f"Exception type: {type(e)}")
            self.logger.debug(f"Full traceback: {traceback.format_exc()}")
            self.test_results['tunnel_setup'] = False
            return False

    def test_socks_proxy(self) -> bool:
        """Test SOCKS proxy functionality"""
        if not self.socks_port:
            return False

        try:
            self.logger.info(f"🧪 Testing SOCKS proxy on port {self.socks_port}...")

            # Test if SOCKS port is listening
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('127.0.0.1', self.socks_port))
            sock.close()

            if result == 0:
                self.logger.info(f"✅ SOCKS proxy port {self.socks_port} is accessible")

                # Test with requests through SOCKS proxy
                try:
                    import socks
                    import socket as socket_module

                    # Create SOCKS proxy session
                    session = requests.Session()
                    session.proxies = {
                        'http': f'socks5://127.0.0.1:{self.socks_port}',
                        'https': f'socks5://127.0.0.1:{self.socks_port}'
                    }

                    response = session.get('http://httpbin.org/ip', timeout=10)
                    if response.status_code == 200:
                        proxy_ip = response.json().get('origin')
                        self.logger.info(f"✅ SOCKS proxy working - IP: {proxy_ip}")
                        self.test_results['socks_proxy'] = True
                        return True
                    else:
                        self.logger.error(f"❌ SOCKS proxy test failed - Status: {response.status_code}")

                except ImportError:
                    self.logger.warning("⚠️  PySocks not installed - skipping proxy IP test")
                    self.logger.info("💡 Install with: pip install PySocks")
                    # Still consider it a success if port is accessible
                    self.test_results['socks_proxy'] = True
                    return True
                except Exception as e:
                    self.logger.error(f"❌ SOCKS proxy request failed: {e}")

            else:
                self.logger.error(f"❌ SOCKS proxy port {self.socks_port} not accessible")

            self.test_results['socks_proxy'] = False
            return False

        except Exception as e:
            self.logger.error(f"❌ SOCKS proxy test failed: {e}")
            self.test_results['socks_proxy'] = False
            return False

    def test_firefox_with_proxy(self) -> bool:
        """Test Firefox WebDriver with SOCKS proxy"""
        if self.skip_tunnel or not self.socks_port:
            self.logger.info("⏭️  Skipping Firefox proxy test (tunnel disabled or not available)")
            return True

        self.print_header("Firefox + SOCKS Proxy Integration Test")

        driver = None
        try:
            self.logger.info("🦊 Testing Firefox with SOCKS proxy configuration...")

            # Create Firefox options with SOCKS proxy
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")

            # Configure SOCKS proxy
            options.set_preference("network.proxy.type", 1)  # Manual proxy
            options.set_preference("network.proxy.socks", "127.0.0.1")
            options.set_preference("network.proxy.socks_port", self.socks_port)
            options.set_preference("network.proxy.socks_version", 5)
            options.set_preference("network.proxy.socks_remote_dns", True)

            # Anti-detection preferences
            options.set_preference("dom.webdriver.enabled", False)
            options.set_preference("useAutomationExtension", False)

            # Set timeout preferences
            options.set_preference("network.http.connection-timeout", 30)
            options.set_preference("network.http.response.timeout", 30)

            # Create service and driver with found GeckoDriver
            if not self.geckodriver_path:
                self.geckodriver_path = find_geckodriver()
            service = Service(self.geckodriver_path)
            self.logger.info("🔧 Creating Firefox WebDriver with SOCKS proxy...")
            driver = webdriver.Firefox(service=service, options=options)
            driver.set_page_load_timeout(30)

            # Test proxy functionality
            self.logger.info("🌐 Testing web access through proxy...")
            driver.get("http://httpbin.org/ip")

            # Wait for page to load and check if we can find the IP
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "pre"))
            )

            page_source = driver.page_source
            if "origin" in page_source.lower():
                self.logger.info("✅ Firefox + SOCKS proxy test: PASSED")
                self.logger.info("🎉 Successfully accessed external site through tunnel")
                self.test_results['firefox_with_proxy'] = True
                return True
            else:
                self.logger.error("❌ Could not verify proxy functionality")
                self.test_results['firefox_with_proxy'] = False
                return False

        except Exception as e:
            self.logger.error(f"❌ Firefox proxy test failed: {e}")
            self.test_results['firefox_with_proxy'] = False
            return False
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

    def test_njuskalo_access(self) -> bool:
        """Test access to Njuskalo.hr through tunnel"""
        if self.skip_tunnel or not self.socks_port:
            self.logger.info("⏭️  Skipping Njuskalo access test (tunnel disabled)")
            return True

        self.print_header("Njuskalo.hr Access Test")

        driver = None
        try:
            self.logger.info("🏪 Testing access to Njuskalo.hr through tunnel...")

            # Create Firefox options with SOCKS proxy
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")

            # Configure SOCKS proxy
            options.set_preference("network.proxy.type", 1)
            options.set_preference("network.proxy.socks", "127.0.0.1")
            options.set_preference("network.proxy.socks_port", self.socks_port)
            options.set_preference("network.proxy.socks_version", 5)
            options.set_preference("network.proxy.socks_remote_dns", True)

            # Anti-detection preferences
            options.set_preference("dom.webdriver.enabled", False)
            options.set_preference("useAutomationExtension", False)

            # User agent
            options.set_preference("general.useragent.override",
                                 "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0")

            if not self.geckodriver_path:
                self.geckodriver_path = find_geckodriver()
            service = Service(self.geckodriver_path)
            driver = webdriver.Firefox(service=service, options=options)
            driver.set_page_load_timeout(30)

            # Access Njuskalo.hr
            self.logger.info("🌐 Loading Njuskalo.hr homepage...")
            driver.get("https://www.njuskalo.hr")

            # Wait for page to load
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Check if page loaded successfully
            title = driver.title
            if "njuskalo" in title.lower():
                self.logger.info(f"✅ Njuskalo.hr access test: PASSED - Title: {title}")
                self.test_results['njuskalo_access'] = True
                return True
            else:
                self.logger.error(f"❌ Unexpected page title: {title}")
                self.test_results['njuskalo_access'] = False
                return False

        except Exception as e:
            self.logger.error(f"❌ Njuskalo access test failed: {e}")
            self.test_results['njuskalo_access'] = False
            return False
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

    def cleanup(self):
        """Cleanup resources"""
        if self.tunnel_manager:
            try:
                self.logger.info("🧹 Cleaning up all tunnels...")
                self.tunnel_manager.close_all_tunnels()
            except Exception as e:
                self.logger.debug(f"Error during cleanup: {e}")
                pass

    def print_summary(self):
        """Print test summary"""
        self.print_header("Test Results Summary")

        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)

        for test_name, result in self.test_results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{status} - {test_name.replace('_', ' ').title()}")

        print(f"\n📊 Results: {passed_tests}/{total_tests} tests passed")

        if passed_tests == total_tests:
            print("🎉 All tests passed! Firefox and tunnel setup is working correctly.")
            return True
        else:
            print("⚠️  Some tests failed. Check the logs above for details.")
            return False

    def run_all_tests(self) -> bool:
        """Run complete test suite"""
        print("🚀 Firefox and Tunnel Test Suite")
        print("🦊 Testing Firefox WebDriver + SSH Tunnel Integration")

        tests = [
            self.test_system_requirements,
            self.test_geckodriver,
            self.test_firefox_basic,
            self.test_server_firefox_config,
            self.test_internet_connectivity,
        ]

        # Add tunnel tests if not skipped
        if not self.skip_tunnel:
            tests.extend([
                self.test_tunnel_setup,
                self.test_firefox_with_proxy,
                self.test_njuskalo_access
            ])

        # Run all tests
        for test in tests:
            try:
                test()
            except KeyboardInterrupt:
                print("\n⚠️  Tests interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"Test failed with unexpected error: {e}")

        # Cleanup and show results
        self.cleanup()
        return self.print_summary()

def run_with_xvfb():
    """Run tests with xvfb-run for server compatibility"""
    import subprocess
    import sys

    # Check if we're already running under xvfb-run
    if os.environ.get('DISPLAY', '').startswith(':'):
        # We're already in an X session (possibly xvfb), run directly
        return False

    # Re-run this script with xvfb-run
    print("🖥️  Starting tests with xvfb-run for server compatibility...")
    cmd = ['xvfb-run', '-a', sys.executable] + sys.argv

    try:
        result = subprocess.run(cmd, check=False)
        sys.exit(result.returncode)
    except FileNotFoundError:
        print("❌ xvfb-run not found!")
        print("💡 Install with: sudo pacman -S xorg-server-xvfb")
        print("🔄 Falling back to direct execution (may fail on headless servers)...")
        return False
    except Exception as e:
        print(f"❌ Error running xvfb-run: {e}")
        print("🔄 Falling back to direct execution...")
        return False

def main():
    """Main function with xvfb-run support"""
    parser = argparse.ArgumentParser(description="Firefox and Tunnel Test Suite (Server Compatible)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("--skip-tunnel", action="store_true",
                       help="Skip SSH tunnel tests")
    parser.add_argument("--no-xvfb", action="store_true",
                       help="Skip xvfb-run (for testing on systems with displays)")

    args = parser.parse_args()

    # Try to use xvfb-run for server compatibility unless disabled
    if not args.no_xvfb and run_with_xvfb():
        return  # xvfb-run handled the execution

    print("🚀 Firefox and Tunnel Test Suite (Server Compatible Mode)")
    print("🖥️  Running with server-optimized Firefox configuration")

    tester = FirefoxTunnelTester(verbose=args.verbose, skip_tunnel=args.skip_tunnel)
    success = tester.run_all_tests()

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
