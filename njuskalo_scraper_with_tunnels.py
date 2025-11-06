#!/usr/bin/env python3
"""
SSH Tunnel Integration for Njuskalo Scraper

This script modifies the existing scraper to use SSH tunnels through SOCKS proxy.
Now using Firefox for better stability and anti-detection.
"""

import sys
import os
import time
import logging
from typing import Optional
from pathlib import Path

# Add current directory to Python path
sys.path.append(str(Path(__file__).parent))

# Import your existing scraper
from njuskalo_sitemap_scraper import NjuskaloSitemapScraper, AntiDetectionMixin
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

class TunnelEnabledNjuskaloScraper(NjuskaloSitemapScraper):
    """Enhanced version of NjuskaloSitemapScraper with SSH tunnel support"""

    def __init__(self, headless=True, use_database=True, tunnel_config_path=None, use_tunnels=True):
        """
        Initialize scraper with SSH tunnel support

        Args:
            headless: Run browser in headless mode
            use_database: Save data to database
            tunnel_config_path: Path to tunnel configuration file
            use_tunnels: Enable/disable tunnel usage
        """
        self.use_tunnels = use_tunnels
        self.tunnel_manager = None
        self.current_tunnel = None
        self.socks_proxy_port = None

        # Initialize tunnel manager if tunnels are enabled
        if self.use_tunnels:
            config_path = tunnel_config_path or "tunnel_config.json"
            if os.path.exists(config_path):
                try:
                    self.tunnel_manager = SSHTunnelManager(config_path)
                    logger.info(f"✅ Tunnel manager initialized with config: {config_path}")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize tunnel manager: {e}")
                    logger.info("🔄 Continuing without tunnels...")
                    self.use_tunnels = False
            else:
                logger.warning(f"⚠️ Tunnel config not found: {config_path}")
                logger.info("🔄 Continuing without tunnels...")
                self.use_tunnels = False

        # Initialize parent class
        super().__init__(headless=headless, use_database=use_database)

    def start_tunnel(self, tunnel_name: str = None) -> bool:
        """Start SSH tunnel and get SOCKS proxy port"""
        if not self.use_tunnels or not self.tunnel_manager:
            return False

        try:
            # Get available tunnels
            available_tunnels = list(self.tunnel_manager.tunnels.keys())
            if not available_tunnels:
                logger.error("❌ No tunnels configured")
                return False

            # Use specified tunnel or first available
            tunnel_name = tunnel_name or available_tunnels[0]

            if tunnel_name not in available_tunnels:
                logger.error(f"❌ Tunnel '{tunnel_name}' not found. Available: {available_tunnels}")
                return False

            # Start the tunnel
            logger.info(f"🚇 Starting SSH tunnel: {tunnel_name}")
            if self.tunnel_manager.establish_tunnel(tunnel_name):
                self.current_tunnel = tunnel_name

                # Get the local SOCKS proxy port
                tunnel_config = self.tunnel_manager.tunnels[tunnel_name]
                self.socks_proxy_port = tunnel_config.local_port

                logger.info(f"✅ SSH tunnel active: {tunnel_name} (SOCKS proxy on port {self.socks_proxy_port})")

                # Wait a moment for tunnel to establish
                time.sleep(3)
                return True
            else:
                logger.error(f"❌ Failed to start tunnel: {tunnel_name}")
                return False

        except Exception as e:
            logger.error(f"❌ Error starting tunnel: {e}")
            return False

    def stop_tunnel(self):
        """Stop current SSH tunnel"""
        if self.current_tunnel and self.tunnel_manager:
            logger.info(f"🛑 Stopping SSH tunnel: {self.current_tunnel}")
            self.tunnel_manager.close_tunnel(self.current_tunnel)
            self.current_tunnel = None
            self.socks_proxy_port = None

    def test_firefox_local(self):
        """Test if Firefox works locally without tunnels"""
        try:
            logger.info("🧪 Testing Firefox installation locally...")
            test_options = Options()
            test_options.add_argument("--headless")
            test_service = Service("/usr/local/bin/geckodriver")
            test_driver = webdriver.Firefox(service=test_service, options=test_options)
            test_driver.get("data:text/html,<html><body><h1>Firefox Test OK</h1></body></html>")
            test_driver.quit()
            logger.info("✅ Firefox installation test: PASSED")
            return True
        except Exception as e:
            logger.error(f"❌ Firefox installation test: FAILED - {e}")
            return False

    def setup_browser(self) -> None:
        """
        Enhanced browser setup with SSH tunnel proxy support using Firefox.
        This overrides the parent method to add SOCKS proxy configuration.
        """
        try:
            # First test if Firefox works locally to isolate server-side issues
            if not self.test_firefox_local():
                logger.error("🚨 Firefox installation issue detected - aborting browser setup")
                return False

            firefox_options = Options()

            # Create unique temporary profile directory
            profile_dir = tempfile.mkdtemp()

            # Enhanced anti-detection preferences
            firefox_options.set_preference("dom.webdriver.enabled", False)
            firefox_options.set_preference("useAutomationExtension", False)
            firefox_options.set_preference("general.platform.override", "Linux x86_64")
            firefox_options.set_preference("general.appversion.override", "5.0 (X11)")

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

            # 🔥 ADD SOCKS PROXY CONFIGURATION HERE 🔥
            if self.use_tunnels and hasattr(self, 'socks_proxy_port') and self.socks_proxy_port:
                # Configure SOCKS proxy in Firefox
                firefox_options.set_preference("network.proxy.type", 1)  # Manual proxy configuration
                firefox_options.set_preference("network.proxy.socks", "127.0.0.1")
                firefox_options.set_preference("network.proxy.socks_port", self.socks_proxy_port)
                firefox_options.set_preference("network.proxy.socks_version", 5)
                firefox_options.set_preference("network.proxy.socks_remote_dns", True)
                logger.info(f"🌐 Firefox configured to use SOCKS proxy: 127.0.0.1:{self.socks_proxy_port}")
            elif self.use_tunnels:
                logger.warning("⚠️ Tunnels enabled but no SOCKS proxy port available - using direct connection")

            # Set user agent
            user_agents = [
                "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
                "Mozilla/5.0 (X11; Linux x86_64; rv:119.0) Gecko/20100101 Firefox/119.0",
                "Mozilla/5.0 (X11; Linux x86_64; rv:118.0) Gecko/20100101 Firefox/118.0"
            ]
            firefox_options.set_preference("general.useragent.override", random.choice(user_agents))

            # Window size and display preferences
            if self.headless:
                firefox_options.add_argument("--headless")

            # Additional Firefox arguments
            firefox_options.add_argument("--no-sandbox")
            firefox_options.add_argument("--disable-dev-shm-usage")

            # Set window size
            width = random.randint(1366, 1920)
            height = random.randint(768, 1080)
            firefox_options.add_argument(f"--width={width}")
            firefox_options.add_argument(f"--height={height}")

            # Setup Firefox service with timeout configurations
            service = Service("/usr/local/bin/geckodriver")

            # Add timeout configurations for server-side issues
            firefox_options.set_preference("network.http.connection-timeout", 30)
            firefox_options.set_preference("network.http.response.timeout", 30)
            firefox_options.set_preference("dom.max_script_run_time", 30)
            firefox_options.set_preference("dom.max_chrome_script_run_time", 30)

            # Configure WebDriver with shorter timeout to detect server issues faster
            logger.info("🔧 Starting Firefox WebDriver (checking for server-side issues)...")
            self.driver = webdriver.Firefox(service=service, options=firefox_options)

            # Set shorter page load timeout to catch server issues
            self.driver.set_page_load_timeout(30)  # 30 seconds instead of default 300
            self.driver.implicitly_wait(10)  # 10 seconds for element waits

            # Set window size programmatically as well
            self.driver.set_window_size(width, height)

            # Firefox-specific anti-detection JavaScript
            stealth_scripts = [
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
                "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})",
                "Object.defineProperty(navigator, 'languages', {get: () => ['hr-HR', 'hr', 'en-US', 'en']})",
                "Object.defineProperty(navigator, 'permissions', {get: () => ({query: x => Promise.resolve({state: 'granted'})})})",
                "Object.defineProperty(navigator, 'connection', {get: () => ({effectiveType: '4g', downlink: 10, rtt: 50})})"
            ]

            for script in stealth_scripts:
                try:
                    self.driver.execute_script(f"(function(){{ {script} }})()")
                except Exception as e:
                    logger.debug(f"Script execution warning: {e}")

            # Set timeouts
            self.driver.implicitly_wait(10)
            self.driver.set_page_load_timeout(60)

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

    def run_full_scrape(self, max_stores=None, tunnel_name=None):
        """
        Enhanced scraping with tunnel support

        Args:
            max_stores: Maximum number of stores to scrape
            tunnel_name: Specific tunnel to use (optional)
        """
        tunnel_started = False

        try:
            # Start tunnel if enabled
            if self.use_tunnels:
                tunnel_started = self.start_tunnel(tunnel_name)
                if tunnel_started:
                    logger.info("🎉 SSH tunnel is active - traffic will be routed through remote server")
                else:
                    logger.warning("⚠️ Failed to start tunnel - continuing with direct connection")

            # Setup browser AFTER tunnel is established
            logger.info("🔧 Setting up browser with tunnel configuration...")
            if not self.setup_browser():
                raise Exception("Browser setup failed")

            # Run the normal scraping process (but skip browser setup in parent)
            logger.info("🏪 Starting enhanced scraping with tunnel support...")

            # Call parent's scraping logic directly without browser setup
            from njuskalo_sitemap_scraper import NjuskaloSitemapScraper
            return NjuskaloSitemapScraper.run_full_scrape(self, max_stores=max_stores)

        except Exception as e:
            logger.error(f"❌ Scraping failed: {e}")
            raise
        finally:
            # Always clean up
            if hasattr(self, 'driver') and self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            if tunnel_started:
                self.stop_tunnel()

    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            if hasattr(self, 'current_tunnel') and self.current_tunnel:
                self.stop_tunnel()
        except:
            pass


def main():
    """
    Main function to run the tunnel-enabled scraper
    """
    import argparse

    parser = argparse.ArgumentParser(description="Njuskalo Scraper with SSH Tunnel Support")
    parser.add_argument('--headless', action='store_true', default=True, help='Run in headless mode')
    parser.add_argument('--max-stores', type=int, help='Maximum stores to scrape (for testing)')
    parser.add_argument('--tunnel-config', default='tunnel_config.json', help='Tunnel configuration file')
    parser.add_argument('--tunnel', help='Specific tunnel name to use')
    parser.add_argument('--no-tunnels', action='store_true', help='Disable tunnel usage')
    parser.add_argument('--no-database', action='store_true', help='Disable database storage')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    try:
        print("🚀 Njuskalo Scraper with SSH Tunnel Support")
        print("=" * 60)

        # Initialize scraper
        scraper = TunnelEnabledNjuskaloScraper(
            headless=args.headless,
            use_database=not args.no_database,
            tunnel_config_path=args.tunnel_config,
            use_tunnels=not args.no_tunnels
        )

        # Run scraping
        stores_data = scraper.run_full_scrape(
            max_stores=args.max_stores,
            tunnel_name=args.tunnel
        )

        if stores_data:
            print(f"\n✅ Scraping completed successfully!")
            print(f"📊 Total stores processed: {len(stores_data)}")
        else:
            print("⚠️ No data was collected")

    except KeyboardInterrupt:
        print("\n⚠️ Scraping interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.exception("Detailed error information:")
        sys.exit(1)


if __name__ == "__main__":
    main()