#!/usr/bin/env python3
"""
SSH Tunnel Integration for Njuskalo Scraper

This script modifies the existing scraper to use SSH tunnels through SOCKS proxy.
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
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
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

    def setup_browser(self) -> None:
        """
        Enhanced browser setup with SSH tunnel proxy support.
        This overrides the parent method to add SOCKS proxy configuration.
        """
        try:
            chrome_options = Options()

            # Create unique temporary user data directory
            user_data_dir = tempfile.mkdtemp()
            chrome_options.add_argument(f"--user-data-dir={user_data_dir}")

            # Enhanced anti-detection arguments
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")

            # Additional stealth options
            chrome_options.add_argument("--no-first-run")
            chrome_options.add_argument("--no-service-autorun")
            chrome_options.add_argument("--password-store=basic")
            chrome_options.add_argument("--use-mock-keychain")
            chrome_options.add_argument("--disable-component-extensions-with-background-pages")
            chrome_options.add_argument("--disable-default-apps")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            chrome_options.add_argument("--disable-features=TranslateUI")
            chrome_options.add_argument("--disable-ipc-flooding-protection")

            # 🔥 ADD SOCKS PROXY CONFIGURATION HERE 🔥
            if self.use_tunnels and hasattr(self, 'socks_proxy_port') and self.socks_proxy_port:
                proxy_url = f"socks5://127.0.0.1:{self.socks_proxy_port}"
                chrome_options.add_argument(f"--proxy-server={proxy_url}")
                logger.info(f"🌐 Browser configured to use SOCKS proxy: {proxy_url}")
            elif self.use_tunnels:
                logger.warning("⚠️ Tunnels enabled but no SOCKS proxy port available - using direct connection")

            # Set user agent
            user_agents = [
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
            ]
            chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")

            # Randomize window size slightly
            width = random.randint(1366, 1920)
            height = random.randint(768, 1080)
            chrome_options.add_argument(f"--window-size={width},{height}")

            # Standard options
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-web-security")

            if self.headless:
                chrome_options.add_argument("--headless")

            # Setup Chrome service
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)

            # Advanced anti-detection scripts
            stealth_scripts = [
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
                "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})",
                "Object.defineProperty(navigator, 'languages', {get: () => ['hr-HR', 'hr', 'en-US', 'en']})",
                "window.chrome = {runtime: {}}",
                "Object.defineProperty(navigator, 'permissions', {get: () => ({query: x => Promise.resolve({state: 'granted'})})})",
                "Object.defineProperty(navigator, 'connection', {get: () => ({effectiveType: '4g', downlink: 10, rtt: 50})})"
            ]

            for script in stealth_scripts:
                self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                    'source': script
                })

            # Set timeouts
            self.driver.implicitly_wait(10)
            self.driver.set_page_load_timeout(60)

            logger.info("✅ Browser setup completed with tunnel integration")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to setup browser: {e}")
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