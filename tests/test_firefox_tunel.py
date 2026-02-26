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
    python tests/test_firefox_tunel.py
    python tests/test_firefox_tunel.py --verbose
    python tests/test_firefox_tunel.py --skip-tunnel
"""

import sys
import os
import time
from pathlib import Path

# Load .env before anything else so DISPLAY_NUM is available
_project_root = Path(__file__).parent.parent
sys.path.insert(0, str(_project_root))

try:
    from dotenv import load_dotenv
    load_dotenv(_project_root / ".env")
except ImportError:
    pass  # dotenv optional — rely on shell env

# Set DISPLAY from DISPLAY_NUM if DISPLAY is not already in the environment
# (mirrors what run.sh does)
if not os.environ.get("DISPLAY"):
    display_num = os.environ.get("DISPLAY_NUM", ":3")
    os.environ["DISPLAY"] = display_num
    print(f"ℹ️  DISPLAY not set — using DISPLAY_NUM={display_num} from .env")

import logging
import argparse
import subprocess
import requests
import socket
from typing import Optional, Dict, Any

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

    for path in possible_paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            return path

    # Check webdriver-manager cache
    wdm_pattern = os.path.expanduser("~/.wdm/drivers/geckodriver/linux64/*/geckodriver")
    matches = glob.glob(wdm_pattern)
    for match in matches:
        if os.access(match, os.X_OK):
            return match

    return shutil.which("geckodriver")


def setup_logging(verbose: bool = False):
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
        print(f"\n{'='*60}")
        print(f"🧪 {title}")
        print(f"{'='*60}")

    def test_system_requirements(self) -> bool:
        """Test basic system requirements"""
        self.print_header("System Requirements Check")

        try:
            python_version = sys.version
            self.logger.info(f"🐍 Python version: {python_version}")

            # Firefox
            try:
                result = subprocess.run(['firefox', '--version'],
                                        capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    self.logger.info(f"🦊 Firefox version: {result.stdout.strip()}")
                    self.test_results['firefox_installed'] = True
                else:
                    self.logger.error("❌ Firefox not found in system PATH")
                    self.logger.error("💡 Install with: sudo apt install firefox")
                    self.test_results['firefox_installed'] = False
                    return False
            except FileNotFoundError:
                self.logger.error("❌ Firefox not installed or not in PATH")
                self.logger.error("💡 Install with: sudo apt install firefox")
                self.test_results['firefox_installed'] = False
                return False
            except subprocess.TimeoutExpired:
                self.logger.error("❌ Firefox version check timed out")
                self.test_results['firefox_installed'] = False
                return False

            # Display
            display = os.environ.get('DISPLAY')
            if display:
                self.logger.info(f"🖥️  DISPLAY: {display}")
                # Verify the display is actually reachable
                try:
                    check = subprocess.run(
                        ['xdpyinfo'], capture_output=True, text=True, timeout=5,
                        env={**os.environ, 'DISPLAY': display}
                    )
                    if check.returncode == 0:
                        self.logger.info(f"✅ X display {display} is reachable")
                    else:
                        self.logger.warning(
                            f"⚠️  X display {display} is set but xdpyinfo failed — "
                            "check that the VNC/Xvfb session is running"
                        )
                        self.logger.warning(
                            f"💡 Verify with: DISPLAY={display} xdpyinfo | head -5"
                        )
                except FileNotFoundError:
                    self.logger.info(f"🖥️  xdpyinfo not available; assuming DISPLAY={display} is valid")
            else:
                self.logger.error("❌ DISPLAY is not set")
                self.logger.error(
                    "💡 Set DISPLAY_NUM in .env (default :3) — the VNC screen "
                    "must already be running on the server"
                )
                self.logger.error(
                    f"💡 Verify: DISPLAY=:3 xdpyinfo | head -5"
                )
                self.test_results['system_requirements'] = False
                return False

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

            driver_path = find_geckodriver()
            if not driver_path:
                self.logger.error("❌ GeckoDriver not found")
                self.logger.error("💡 Install the latest release:")
                self.logger.error(
                    "   GECKO_VER=$(curl -s https://api.github.com/repos/mozilla/geckodriver/releases/latest"
                    " | grep '\"tag_name\"' | cut -d'\"' -f4)"
                )
                self.logger.error(
                    "   curl -L \"https://github.com/mozilla/geckodriver/releases/download/"
                    "${GECKO_VER}/geckodriver-${GECKO_VER}-linux64.tar.gz\""
                    " | sudo tar -xz -C /usr/local/bin"
                )
                self.logger.error("   sudo chmod +x /usr/local/bin/geckodriver")
                self.test_results['geckodriver'] = False
                return False

            self.logger.info(f"✅ GeckoDriver found at: {driver_path}")
            self.geckodriver_path = driver_path

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

    def _build_firefox_options(self, socks_port: Optional[int] = None,
                                user_agent: Optional[str] = None) -> Options:
        """Build reusable Firefox options for server (VNC display) mode"""
        options = Options()
        # Non-headless: rely on the VNC display set in DISPLAY
        options.set_preference("browser.tabs.remote.autostart", False)
        options.set_preference("layers.acceleration.disabled", True)
        options.set_preference("gfx.webrender.force-disabled", True)
        options.set_preference("dom.ipc.plugins.enabled", False)
        options.set_preference("media.hardware-video-decoding.enabled", False)
        options.set_preference("media.hardware-video-decoding.force-enabled", False)
        options.set_preference("browser.startup.homepage", "about:blank")
        options.set_preference("security.sandbox.content.level", 0)
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)

        if socks_port:
            options.set_preference("network.proxy.type", 1)
            options.set_preference("network.proxy.socks", "127.0.0.1")
            options.set_preference("network.proxy.socks_port", socks_port)
            options.set_preference("network.proxy.socks_version", 5)
            options.set_preference("network.proxy.socks_remote_dns", True)
        else:
            options.set_preference("network.proxy.type", 0)

        if user_agent:
            options.set_preference("general.useragent.override", user_agent)

        return options

    def test_firefox_basic(self) -> bool:
        """Test basic Firefox WebDriver functionality"""
        self.print_header("Firefox Basic Test")

        driver = None
        try:
            self.logger.info("🦊 Starting Firefox WebDriver (using DISPLAY=%s)...",
                             os.environ.get('DISPLAY', 'not set'))

            if not self.geckodriver_path:
                self.geckodriver_path = find_geckodriver()
            service = Service(self.geckodriver_path)
            options = self._build_firefox_options()

            driver = webdriver.Firefox(service=service, options=options)

            self.logger.info("🌐 Testing basic navigation...")
            test_html = (
                "data:text/html,<html><body>"
                "<h1 id='test'>Firefox WebDriver Test</h1>"
                f"<p>Timestamp: {time.time()}</p>"
                "</body></html>"
            )
            driver.get(test_html)

            element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "test"))
            )

            if element and element.text == "Firefox WebDriver Test":
                self.logger.info("✅ Firefox basic test: PASSED")
                self.test_results['firefox_basic'] = True
                return True
            else:
                self.logger.error("❌ Element finding test failed")
                self.test_results['firefox_basic'] = False
                return False

        except Exception as e:
            self.logger.error(f"❌ Firefox basic test failed: {e}")
            self.logger.error("🔧 Troubleshooting:")
            self.logger.error(
                f"   1. Verify VNC/X display is running: "
                f"DISPLAY={os.environ.get('DISPLAY', ':3')} xdpyinfo | head -5"
            )
            self.logger.error(
                "   2. Check DISPLAY_NUM in .env matches the running VNC screen"
            )
            self.logger.error("   3. Verify Firefox: ls -la /usr/bin/firefox")
            self.logger.error("   4. Verify GeckoDriver: ls -la /usr/local/bin/geckodriver")
            self.test_results['firefox_basic'] = False
            return False
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

    def test_internet_connectivity(self) -> bool:
        """Test basic internet connectivity"""
        self.print_header("Internet Connectivity Test")

        try:
            test_urls = [
                os.getenv("TEST_IP_CHECK_URL", "http://httpbin.org/ip"),
                os.getenv("TEST_GOOGLE_URL", "https://www.google.com"),
                os.getenv("NJUSKALO_BASE_URL", "https://www.njuskalo.hr"),
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
        """Test server Firefox configuration with live Njuskalo access"""
        self.print_header("Server Firefox Configuration Test")

        driver = None
        try:
            self.logger.info("🖥️  Testing server-optimized Firefox configuration...")

            if not self.geckodriver_path:
                self.geckodriver_path = find_geckodriver()
            service = Service(self.geckodriver_path)
            options = self._build_firefox_options()

            self.logger.info("🦊 Initializing Firefox...")
            driver = webdriver.Firefox(service=service, options=options)

            # Test 1: Basic HTML
            self.logger.info("🧪 Test 1: Basic HTML rendering...")
            driver.get("data:text/html,<html><body><h1 id='test'>Server Config Test</h1></body></html>")
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "test"))
            )
            self.logger.info("✅ Basic HTML rendering: PASSED")

            # Test 2: Njuskalo.hr
            self.logger.info("🧪 Test 2: Accessing Njuskalo.hr...")
            driver.get(os.getenv("NJUSKALO_BASE_URL", "https://www.njuskalo.hr"))
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            page_title = driver.title
            self.logger.info(f"📄 Page title: {page_title}")
            if "njuskalo" in page_title.lower():
                self.logger.info("✅ Njuskalo access: PASSED")
            else:
                self.logger.warning(f"⚠️  Unexpected page title: {page_title}")

            # Test 3: JavaScript
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
            self.logger.error("🔧 Expected configuration:")
            self.logger.error("   - Firefox binary: /usr/bin/firefox")
            self.logger.error("   - GeckoDriver: /usr/local/bin/geckodriver")
            self.logger.error(
                f"   - DISPLAY: {os.environ.get('DISPLAY', 'not set')} "
                "(from DISPLAY_NUM in .env)"
            )
            self.logger.error(
                "   - Verify VNC screen is running: "
                f"DISPLAY={os.environ.get('DISPLAY', ':3')} xdpyinfo | head -5"
            )
            self.test_results['server_firefox_config'] = False
            return False
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

    def test_tunnel_setup(self) -> bool:
        """Test SSH tunnel setup and connectivity"""
        if self.skip_tunnel or not SSHTunnelManager:
            self.logger.info("⏭️  Skipping tunnel tests (disabled or not available)")
            return True

        self.print_header("SSH Tunnel Test")

        try:
            config_path = _project_root / "tunnel_config.json"
            if not config_path.exists():
                self.logger.error(f"❌ Tunnel config file not found: {config_path}")
                self.test_results['tunnel_setup'] = False
                return False

            self.logger.info(f"🔧 Loading tunnel configuration from: {config_path}")
            self.tunnel_manager = SSHTunnelManager(str(config_path))

            self.logger.info("🧹 Cleaning up any existing tunnels...")
            self.tunnel_manager.close_all_tunnels()

            tunnels = self.tunnel_manager.list_tunnels()
            if not tunnels:
                self.logger.error("❌ No tunnels configured")
                self.test_results['tunnel_setup'] = False
                return False

            self.tunnel_name = list(tunnels.keys())[0]
            self.logger.info(f"🚇 Testing tunnel: {self.tunnel_name}")

            self.logger.info("🔧 Starting SSH tunnel...")
            success = self.tunnel_manager.establish_tunnel(self.tunnel_name)

            if success:
                proxy_settings = self.tunnel_manager.get_proxy_settings()
                self.socks_port = proxy_settings.get('local_port') if proxy_settings else None
                self.logger.info(f"✅ Tunnel started on port: {self.socks_port}")

                if not self.socks_port:
                    self.logger.error("❌ Tunnel started but no SOCKS port available")
                    self.test_results['tunnel_setup'] = False
                    return False

                return self.test_socks_proxy()
            else:
                self.logger.error(f"❌ Failed to start SSH tunnel")
                self.logger.error("💡 Check SSH connection details in tunnel_config.json")
                self.logger.error("💡 Verify SSH key permissions: chmod 600 tunnel_key")
                self.test_results['tunnel_setup'] = False
                return False

        except Exception as e:
            import traceback
            self.logger.error(f"❌ Tunnel setup failed: {e}")
            self.logger.debug(f"Full traceback: {traceback.format_exc()}")
            self.test_results['tunnel_setup'] = False
            return False

    def test_socks_proxy(self) -> bool:
        """Test SOCKS proxy functionality"""
        if not self.socks_port:
            return False

        try:
            self.logger.info(f"🧪 Testing SOCKS proxy on port {self.socks_port}...")

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('127.0.0.1', self.socks_port))
            sock.close()

            if result == 0:
                self.logger.info(f"✅ SOCKS proxy port {self.socks_port} is accessible")

                try:
                    session = requests.Session()
                    session.proxies = {
                        'http': f'socks5://127.0.0.1:{self.socks_port}',
                        'https': f'socks5://127.0.0.1:{self.socks_port}',
                    }
                    response = session.get(
                        os.getenv("TEST_IP_CHECK_URL", "http://httpbin.org/ip"), timeout=10
                    )
                    if response.status_code == 200:
                        proxy_ip = response.json().get('origin')
                        self.logger.info(f"✅ SOCKS proxy working — IP: {proxy_ip}")
                        self.test_results['socks_proxy'] = True
                        return True
                    else:
                        self.logger.error(f"❌ SOCKS proxy test failed — Status: {response.status_code}")

                except ImportError:
                    self.logger.warning("⚠️  PySocks not installed — skipping proxy IP test")
                    self.logger.info("💡 Install with: pip install PySocks")
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
            self.logger.info("🦊 Testing Firefox with SOCKS proxy...")

            if not self.geckodriver_path:
                self.geckodriver_path = find_geckodriver()
            service = Service(self.geckodriver_path)
            options = self._build_firefox_options(socks_port=self.socks_port)

            driver = webdriver.Firefox(service=service, options=options)
            driver.set_page_load_timeout(30)

            self.logger.info("🌐 Testing web access through proxy...")
            driver.get(os.getenv("TEST_IP_CHECK_URL", "http://httpbin.org/ip"))

            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "pre"))
            )

            if "origin" in driver.page_source.lower():
                self.logger.info("✅ Firefox + SOCKS proxy test: PASSED")
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
                except Exception:
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

            if not self.geckodriver_path:
                self.geckodriver_path = find_geckodriver()
            service = Service(self.geckodriver_path)
            options = self._build_firefox_options(
                socks_port=self.socks_port,
                user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
            )

            driver = webdriver.Firefox(service=service, options=options)
            driver.set_page_load_timeout(30)

            self.logger.info("🌐 Loading Njuskalo.hr homepage...")
            driver.get(os.getenv("NJUSKALO_BASE_URL", "https://www.njuskalo.hr"))

            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            title = driver.title
            if "njuskalo" in title.lower():
                self.logger.info(f"✅ Njuskalo.hr access test: PASSED — Title: {title}")
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
                except Exception:
                    pass

    def cleanup(self):
        if self.tunnel_manager:
            try:
                self.logger.info("🧹 Cleaning up all tunnels...")
                self.tunnel_manager.close_all_tunnels()
            except Exception as e:
                self.logger.debug(f"Error during cleanup: {e}")

    def print_summary(self):
        self.print_header("Test Results Summary")

        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results.values() if r)

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
        print("🚀 Firefox and Tunnel Test Suite")
        print(f"🖥️  DISPLAY: {os.environ.get('DISPLAY', 'not set')}")

        tests = [
            self.test_system_requirements,
            self.test_geckodriver,
            self.test_firefox_basic,
            self.test_server_firefox_config,
            self.test_internet_connectivity,
        ]

        if not self.skip_tunnel:
            tests.extend([
                self.test_tunnel_setup,
                self.test_firefox_with_proxy,
                self.test_njuskalo_access,
            ])

        for test in tests:
            try:
                test()
            except KeyboardInterrupt:
                print("\n⚠️  Tests interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"Test failed with unexpected error: {e}")

        self.cleanup()
        return self.print_summary()


def main():
    parser = argparse.ArgumentParser(
        description="Firefox and Tunnel Test Suite — VNC display mode"
    )
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose logging")
    parser.add_argument("--skip-tunnel", action="store_true",
                        help="Skip SSH tunnel tests")

    args = parser.parse_args()

    print(f"🚀 Firefox and Tunnel Test Suite")
    print(f"🖥️  Using DISPLAY: {os.environ.get('DISPLAY', 'not set')}")

    tester = FirefoxTunnelTester(verbose=args.verbose, skip_tunnel=args.skip_tunnel)
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
