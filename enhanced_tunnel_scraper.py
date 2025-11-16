#!/usr/bin/env python3
"""
Enhanced SSH Tunnel Integration for Njuskalo Scraper

This script uses the enhanced scraper with XML processing, auto moto detection,
and vehicle counting through SSH tunnels for better anonymity and stability.
"""

import sys
import os
import time
import logging
from typing import Optional, Dict
from pathlib import Path

# Add current directory to Python path
sys.path.append(str(Path(__file__).parent))

# Sentry integration
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from dotenv import load_dotenv

load_dotenv()

# Initialize Sentry
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "1.0")),
        integrations=[LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)],
    )

# Import enhanced scraper
from enhanced_njuskalo_scraper import EnhancedNjuskaloScraper
from selenium.webdriver.firefox.options import Options
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
import tempfile
import random

# Import tunnel manager
try:
    from ssh_tunnel_manager import SSHTunnelManager
except ImportError:
    print("❌ Error: ssh_tunnel_manager.py not found in current directory")
    print("💡 Make sure ssh_tunnel_manager.py is in the same folder as this script")
    sys.exit(1)

logger = logging.getLogger(__name__)

class TunnelEnabledEnhancedScraper(EnhancedNjuskaloScraper):
    """Enhanced scraper with SSH tunnel support and vehicle counting"""

    def __init__(self, headless=True, use_database=True, tunnel_config_path=None, use_tunnels=True):
        """
        Initialize enhanced scraper with SSH tunnel support

        Args:
            headless: Run browser in headless mode
            use_database: Save data to database
            tunnel_config_path: Path to tunnel configuration file
            use_tunnels: Enable/disable tunnel usage
        """
        super().__init__(headless, use_database)
        self.use_tunnels = use_tunnels
        self.tunnel_config_path = tunnel_config_path or "tunnel_config.json"
        self.tunnel_manager = None
        self.current_tunnel = None
        self.socks_proxy_port = None

        if self.use_tunnels:
            self._setup_tunnel_manager()

    def _setup_tunnel_manager(self):
        """Initialize the SSH tunnel manager"""
        try:
            if not os.path.exists(self.tunnel_config_path):
                logger.error(f"❌ Tunnel config file not found: {self.tunnel_config_path}")
                self.use_tunnels = False
                return

            self.tunnel_manager = SSHTunnelManager(self.tunnel_config_path)
            logger.info("✅ Tunnel manager initialized with config: " + self.tunnel_config_path)
        except Exception as e:
            logger.error(f"❌ Failed to initialize tunnel manager: {e}")
            self.use_tunnels = False

    def _start_tunnel(self) -> bool:
        """Start SSH tunnel and return success status"""
        if not self.use_tunnels or not self.tunnel_manager:
            return True

        try:
            # Get available tunnels
            tunnels = self.tunnel_manager.list_tunnels()
            if not tunnels:
                logger.error("❌ No tunnels configured")
                return False

            # Use first available tunnel
            tunnel_name = list(tunnels.keys())[0]
            logger.info(f"🚇 Starting SSH tunnel: {tunnel_name}")

            # Start the tunnel
            success = self.tunnel_manager.establish_tunnel(tunnel_name)
            if success:
                proxy_settings = self.tunnel_manager.get_proxy_settings()
                self.socks_proxy_port = proxy_settings.get('local_port') if proxy_settings else None
                self.current_tunnel = tunnel_name
                logger.info(f"✅ SSH tunnel active: {tunnel_name} (SOCKS proxy on port {self.socks_proxy_port})")

                # Wait a moment for tunnel to stabilize (reduced)
                time.sleep(1.5)

                # Test tunnel connectivity
                if self._test_tunnel_connectivity():
                    logger.info("🎉 SSH tunnel is active - traffic will be routed through remote server")
                    return True
                else:
                    logger.error("❌ Tunnel connectivity test failed")
                    return False
            else:
                logger.error(f"❌ Failed to start tunnel: {tunnel_name}")
                return False

        except Exception as e:
            logger.error(f"❌ Error starting tunnel: {e}")
            return False

    def _test_tunnel_connectivity(self) -> bool:
        """Test if the tunnel is working properly"""
        if not self.socks_proxy_port:
            return False

        try:
            import socket
            # Test if SOCKS port is accessible
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('127.0.0.1', self.socks_proxy_port))
            sock.close()
            return result == 0
        except:
            return False

    def _stop_tunnel(self):
        """Stop the current SSH tunnel"""
        if self.tunnel_manager and self.current_tunnel:
            try:
                logger.info(f"🛑 Stopping SSH tunnel: {self.current_tunnel}")
                self.tunnel_manager.close_tunnel(self.current_tunnel)
            except Exception as e:
                logger.warning(f"⚠️ Error stopping tunnel: {e}")
            finally:
                self.current_tunnel = None
                self.socks_proxy_port = None

    def test_firefox_local(self):
        """Test if Firefox works locally without tunnels using server-compatible config"""
        try:
            logger.info("🧪 Testing Firefox installation locally with server config...")

            # Use server-compatible options
            test_options = Options()
            test_options.headless = True
            test_options.binary_location = "/usr/bin/firefox"
            test_options.set_preference("browser.tabs.remote.autostart", False)
            test_options.set_preference("layers.acceleration.disabled", True)
            test_options.set_preference("gfx.webrender.force-disabled", True)
            test_options.set_preference("dom.ipc.plugins.enabled", False)
            test_options.set_preference("media.hardware-video-decoding.enabled", False)
            test_options.set_preference("media.hardware-video-decoding.force-enabled", False)
            test_options.set_preference("browser.startup.homepage", "about:blank")
            test_options.set_preference("security.sandbox.content.level", 0)
            test_options.set_preference("network.proxy.type", 0)

            # Use system geckodriver
            test_service = Service("/usr/local/bin/geckodriver")
            test_driver = webdriver.Firefox(service=test_service, options=test_options)
            test_driver.get("data:text/html,<html><body><h1>Firefox Server Test OK</h1></body></html>")
            test_driver.quit()
            logger.info("✅ Firefox server-compatible test: PASSED")
            return True
        except Exception as e:
            logger.error(f"❌ Firefox server-compatible test: FAILED - {e}")
            return False

    def _find_geckodriver(self):
        """Find GeckoDriver from multiple locations"""
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
        wdm_pattern = "/home/*/.*wdm/drivers/geckodriver/linux64/*/geckodriver"
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

    def setup_browser(self) -> bool:
        """
        Enhanced browser setup with SSH tunnel proxy support using Firefox.
        """
        try:
            # First test if Firefox works locally to isolate server-side issues
            if not self.test_firefox_local():
                logger.error("🚨 Firefox installation issue detected - aborting browser setup")
                return False

            firefox_options = Options()

            # Server-compatible configuration (exact setup that works)
            firefox_options.headless = True
            firefox_options.binary_location = "/usr/bin/firefox"  # Set the Firefox binary explicitly

            # Server-specific preferences for stability
            firefox_options.set_preference("browser.tabs.remote.autostart", False)
            firefox_options.set_preference("layers.acceleration.disabled", True)
            firefox_options.set_preference("gfx.webrender.force-disabled", True)
            firefox_options.set_preference("dom.ipc.plugins.enabled", False)
            firefox_options.set_preference("media.hardware-video-decoding.enabled", False)
            firefox_options.set_preference("media.hardware-video-decoding.force-enabled", False)
            firefox_options.set_preference("browser.startup.homepage", "about:blank")
            firefox_options.set_preference("security.sandbox.content.level", 0)

            # Enhanced anti-detection preferences
            firefox_options.set_preference("dom.webdriver.enabled", False)
            firefox_options.set_preference("useAutomationExtension", False)
            firefox_options.set_preference("general.platform.override", "Linux x86_64")
            firefox_options.set_preference("general.appversion.override", "5.0 (X11)")

            # Set user agent
            user_agents = [
                "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
                "Mozilla/5.0 (X11; Linux x86_64; rv:119.0) Gecko/20100101 Firefox/119.0",
                "Mozilla/5.0 (X11; Linux x86_64; rv:118.0) Gecko/20100101 Firefox/118.0"
            ]
            firefox_options.set_preference("general.useragent.override", random.choice(user_agents))

            # Privacy and security preferences
            firefox_options.set_preference("privacy.trackingprotection.enabled", False)
            firefox_options.set_preference("dom.ipc.plugins.enabled.libflashplayer.so", False)
            firefox_options.set_preference("media.peerconnection.enabled", False)
            firefox_options.set_preference("media.navigator.enabled", False)
            firefox_options.set_preference("webgl.disabled", True)
            firefox_options.set_preference("javascript.enabled", True)

            # Disable automation indicators
            firefox_options.set_preference("marionette.enabled", False)
            firefox_options.set_preference("fission.autostart", False)

            # Performance preferences
            firefox_options.set_preference("browser.cache.disk.enable", False)
            firefox_options.set_preference("browser.cache.memory.enable", False)
            firefox_options.set_preference("browser.cache.offline.enable", False)
            firefox_options.set_preference("network.http.use-cache", False)

            # 🔥 SOCKS PROXY CONFIGURATION 🔥
            if self.use_tunnels and hasattr(self, 'socks_proxy_port') and self.socks_proxy_port:
                # Configure SOCKS proxy in Firefox
                firefox_options.set_preference("network.proxy.type", 1)  # Manual proxy configuration
                firefox_options.set_preference("network.proxy.socks", "127.0.0.1")
                firefox_options.set_preference("network.proxy.socks_port", self.socks_proxy_port)
                firefox_options.set_preference("network.proxy.socks_version", 5)
                firefox_options.set_preference("network.proxy.socks_remote_dns", True)
                logger.info(f"🌐 Firefox configured to use SOCKS proxy: 127.0.0.1:{self.socks_proxy_port}")
            elif not self.use_tunnels:
                # Ensure no proxy when tunnels disabled (server-compatible setting)
                firefox_options.set_preference("network.proxy.type", 0)
            else:
                logger.warning("⚠️ Tunnels enabled but no SOCKS proxy port available - using direct connection")
                firefox_options.set_preference("network.proxy.type", 0)

            # Server compatibility - ensure headless mode is properly set
            if self.headless:
                firefox_options.headless = True

            # Additional Firefox arguments
            firefox_options.add_argument("--no-sandbox")
            firefox_options.add_argument("--disable-dev-shm-usage")

            # Set window size
            width = random.randint(1366, 1920)
            height = random.randint(768, 1080)
            firefox_options.add_argument(f"--width={width}")
            firefox_options.add_argument(f"--height={height}")

            # Setup Firefox service with timeout configurations
            geckodriver_path = self._find_geckodriver()
            if not geckodriver_path:
                logger.error("❌ GeckoDriver not found")
                return False

            service = Service(geckodriver_path)

            # Add timeout configurations for server-side issues
            firefox_options.set_preference("network.http.connection-timeout", 30)
            firefox_options.set_preference("network.http.response.timeout", 30)
            firefox_options.set_preference("dom.max_script_run_time", 30)
            firefox_options.set_preference("dom.max_chrome_script_run_time", 30)

            # Configure WebDriver with shorter timeout to detect server issues faster
            logger.info("🔧 Starting Firefox WebDriver (checking for server-side issues)...")
            self.driver = webdriver.Firefox(service=service, options=firefox_options)

            # Set shorter page load timeout to catch server issues
            self.driver.set_page_load_timeout(20)  # 20 seconds for faster timeout
            self.driver.implicitly_wait(10)  # 10 seconds for element waits

            # Set window size programmatically as well
            self.driver.set_window_size(width, height)

            # Firefox-specific anti-detection JavaScript
            stealth_scripts = [
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
                "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})",
                "Object.defineProperty(navigator, 'languages', {get: () => ['hr-HR', 'hr', 'en-US', 'en']})",
            ]

            for script in stealth_scripts:
                try:
                    self.driver.execute_script(script)
                except Exception as e:
                    logger.debug(f"Could not execute stealth script: {e}")

            logger.info("✅ Firefox browser setup completed with tunnel integration")
            return True

        except Exception as e:
            error_msg = str(e).lower()
            logger.error(f"❌ Failed to setup Firefox browser: {e}")

            # Analyze error to distinguish between local vs server-side issues
            if "httpconnectionpool" in error_msg and "read timed out" in error_msg:
                if "localhost" in error_msg:
                    logger.error("🌐 SERVER-SIDE ISSUE DETECTED: Connection timeout to localhost")
                    logger.error("   This suggests a proxy/tunnel configuration problem, not Firefox")
                    logger.error("🔧 SOLUTIONS:")
                    logger.error("   1. Check if SSH tunnel is running: ps aux | grep ssh")
                    logger.error("   2. Verify SOCKS proxy port: netstat -tulpn | grep :1080")
                    logger.error("   3. Test tunnel connection: curl --socks5 127.0.0.1:1080 http://httpbin.org/ip")
                    logger.error("   4. Restart tunnel: ./setup_tunnels.sh")
                else:
                    logger.error("🌐 NETWORK ISSUE DETECTED: External server connection problem")
                    logger.error("🔧 SOLUTIONS:")
                    logger.error("   1. Check internet connection")
                    logger.error("   2. Try different proxy server")
                    logger.error("   3. Run without tunnels: --no-tunnels")
            elif "geckodriver" in error_msg or "firefox" in error_msg:
                logger.error("🦊 LOCAL FIREFOX ISSUE DETECTED")
                logger.error("🔧 SOLUTIONS:")
                logger.error("   1. Install Firefox: sudo pacman -S firefox")
                logger.error("   2. Update GeckoDriver: pip install --upgrade geckodriver-autoinstaller")
            elif "permission" in error_msg or "display" in error_msg:
                logger.error("🖥️ DISPLAY/PERMISSION ISSUE DETECTED")
                logger.error("🔧 SOLUTIONS:")
                logger.error("   1. Install Xvfb: sudo pacman -S xorg-server-xvfb")
                logger.error("   2. Run with Xvfb: xvfb-run python script.py")
            else:
                logger.error("🔍 UNKNOWN ISSUE - Full error details above")
                logger.error("🔧 GENERAL SOLUTIONS:")
                logger.error("   1. Try without tunnels: python script.py --no-tunnels")
                logger.error("   2. Check system requirements")

            if hasattr(self, 'driver') and self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
            return False

    def run_enhanced_scrape_with_tunnels(self, max_stores: int = None) -> Dict:
        """
        Run enhanced scraping with SSH tunnel support.

        Args:
            max_stores: Maximum number of stores to scrape

        Returns:
            Dict containing scraping results
        """
        try:
            logger.info("🚀 Enhanced Njuskalo Scraper with SSH Tunnel Support")
            logger.info("=" * 60)

            # Step 1: Setup tunnel if enabled
            if self.use_tunnels:
                if not self._start_tunnel():
                    logger.error("❌ Failed to setup tunnel, continuing without tunnel...")
                    self.use_tunnels = False

            # Step 2: Run enhanced scraping workflow
            logger.info("🔧 Setting up browser with tunnel configuration...")
            results = self.run_enhanced_scrape(max_stores)

            return results

        except KeyboardInterrupt:
            logger.info("\n⚠️ Scraping interrupted by user")
            return {'error': 'interrupted', 'stores_scraped': 0}
        except Exception as e:
            logger.error(f"❌ Error in tunnel-enabled scraping: {e}")
            return {'error': str(e), 'stores_scraped': 0}
        finally:
            # Cleanup tunnel
            if self.use_tunnels:
                self._stop_tunnel()


def main():
    """Main function for command line usage"""
    import argparse

    parser = argparse.ArgumentParser(description="Enhanced Njuskalo Scraper with SSH Tunnel Support")
    parser.add_argument("--headless", action="store_true", default=True, help="Run browser in headless mode")
    parser.add_argument("--max-stores", type=int, help="Maximum number of stores to scrape")
    parser.add_argument("--tunnel-config", default="tunnel_config.json", help="Path to tunnel config file")
    parser.add_argument("--tunnel", help="Specific tunnel name to use")
    parser.add_argument("--no-tunnels", action="store_true", help="Disable tunnel usage")
    parser.add_argument("--no-database", action="store_true", help="Disable database usage")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    try:
        # Create enhanced scraper with tunnel support
        scraper = TunnelEnabledEnhancedScraper(
            headless=args.headless,
            use_database=not args.no_database,
            tunnel_config_path=args.tunnel_config,
            use_tunnels=not args.no_tunnels
        )

        # Run enhanced scraping
        results = scraper.run_enhanced_scrape_with_tunnels(max_stores=args.max_stores)

        # Print results
        print("\n" + "="*60)
        print("🏁 ENHANCED SCRAPING WITH TUNNELS - RESULTS")
        print("="*60)
        print(f"XML Available: {'✅' if results.get('xml_available') else '❌'}")
        print(f"New URLs Found: {results.get('new_urls_found', 0)}")
        print(f"Stores Scraped: {results.get('stores_scraped', 0)}")
        print(f"Auto Moto Stores: {results.get('auto_moto_stores', 0)}")
        print(f"New Vehicles: {results.get('new_vehicles', 0)}")
        print(f"Used Vehicles: {results.get('used_vehicles', 0)}")
        print(f"Total Vehicles: {results.get('total_vehicles', 0)}")
        print(f"Errors: {len(results.get('errors', []))}")
        if results.get('errors'):
            print("\nErrors encountered:")
            for error in results['errors'][:5]:  # Show first 5 errors
                print(f"  - {error}")
        print("="*60)

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()