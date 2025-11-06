#!/usr/bin/env python3
"""
Scraper Integration with SSH Tunneling

This module integrates the SSH tunnel manager with existing scrapers
to provide automatic IP rotation and anti-detection capabilities.
"""

import os
import sys
import time
import random
import logging
from typing import Optional, Dict, Any
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

try:
    from ssh_tunnel_manager import SSHTunnelManager
except ImportError:
    print("Error: ssh_tunnel_manager.py not found. Please ensure it's in the same directory.")
    sys.exit(1)

logger = logging.getLogger(__name__)

class TunnelIntegratedScraper:
    """Base class for scrapers with tunnel integration"""

    def __init__(self, tunnel_config_path: str = None, auto_rotate: bool = True):
        """
        Initialize scraper with tunnel integration

        Args:
            tunnel_config_path: Path to SSH tunnel configuration
            auto_rotate: Whether to automatically rotate tunnels
        """
        self.tunnel_manager = None
        self.current_tunnel = None
        self.auto_rotate = auto_rotate
        self.rotation_interval = 1800  # 30 minutes
        self.last_rotation = 0
        self.requests_count = 0
        self.max_requests_per_tunnel = 100

        # Initialize tunnel manager
        config_path = tunnel_config_path or "ssh_tunnels.json"
        if os.path.exists(config_path):
            self.tunnel_manager = SSHTunnelManager(config_path)
            logger.info("SSH tunnel manager initialized")
        else:
            logger.warning(f"Tunnel config not found: {config_path}")
            logger.warning("Running without tunnel integration")

    def get_proxy_settings(self) -> Optional[Dict[str, Any]]:
        """Get current proxy settings for requests/selenium"""
        if not self.tunnel_manager or not self.current_tunnel:
            return None

        tunnel_info = self.tunnel_manager.get_tunnel_info(self.current_tunnel)
        if not tunnel_info:
            return None

        return {
            'http': f'socks5://127.0.0.1:{tunnel_info["local_port"]}',
            'https': f'socks5://127.0.0.1:{tunnel_info["local_port"]}',
            'socks_proxy': f'127.0.0.1:{tunnel_info["local_port"]}',
            'proxy_type': 'socks5'
        }

    def setup_selenium_proxy(self, chrome_options):
        """Configure Chrome options with current proxy"""
        proxy_settings = self.get_proxy_settings()
        if proxy_settings:
            proxy_address = proxy_settings['socks_proxy']
            chrome_options.add_argument(f'--proxy-server=socks5://{proxy_address}')
            logger.info(f"Selenium configured with proxy: {proxy_address}")
        return chrome_options

    def setup_requests_proxy(self) -> Optional[Dict[str, str]]:
        """Get proxy settings for requests library"""
        proxy_settings = self.get_proxy_settings()
        if proxy_settings:
            return {
                'http': proxy_settings['http'],
                'https': proxy_settings['https']
            }
        return None

    def connect_tunnel(self, tunnel_name: str = None) -> bool:
        """Connect to a specific tunnel or auto-select"""
        if not self.tunnel_manager:
            logger.warning("No tunnel manager available")
            return False

        try:
            if tunnel_name:
                success = self.tunnel_manager.connect_tunnel(tunnel_name)
                if success:
                    self.current_tunnel = tunnel_name
            else:
                # Auto-select available tunnel
                tunnels = self.tunnel_manager.list_tunnels()
                available = [name for name, info in tunnels.items()
                           if info.get('status') == 'disconnected']

                if available:
                    selected = random.choice(available)
                    success = self.tunnel_manager.connect_tunnel(selected)
                    if success:
                        self.current_tunnel = selected
                else:
                    logger.warning("No available tunnels")
                    return False

            if success:
                logger.info(f"Connected to tunnel: {self.current_tunnel}")
                self.last_rotation = time.time()
                self.requests_count = 0
                return True
            else:
                logger.error(f"Failed to connect to tunnel: {tunnel_name or 'auto-selected'}")
                return False

        except Exception as e:
            logger.error(f"Error connecting to tunnel: {e}")
            return False

    def should_rotate_tunnel(self) -> bool:
        """Check if tunnel should be rotated"""
        if not self.auto_rotate or not self.tunnel_manager:
            return False

        # Time-based rotation
        time_since_rotation = time.time() - self.last_rotation
        if time_since_rotation > self.rotation_interval:
            logger.info("Time-based tunnel rotation triggered")
            return True

        # Request count-based rotation
        if self.requests_count > self.max_requests_per_tunnel:
            logger.info("Request count-based tunnel rotation triggered")
            return True

        # Health-based rotation
        if self.current_tunnel and not self.tunnel_manager.is_tunnel_healthy(self.current_tunnel):
            logger.info("Health-based tunnel rotation triggered")
            return True

        return False

    def rotate_tunnel(self) -> bool:
        """Rotate to a different tunnel"""
        if not self.tunnel_manager:
            return False

        try:
            # Disconnect current tunnel
            if self.current_tunnel:
                self.tunnel_manager.disconnect_tunnel(self.current_tunnel)

            # Connect to new tunnel
            return self.connect_tunnel()

        except Exception as e:
            logger.error(f"Error rotating tunnel: {e}")
            return False

    def pre_request_hook(self):
        """Call before making requests"""
        self.requests_count += 1

        # Check if tunnel rotation is needed
        if self.should_rotate_tunnel():
            logger.info("Rotating tunnel...")
            self.rotate_tunnel()

            # Add delay after rotation
            delay = random.uniform(5, 15)
            logger.info(f"Post-rotation delay: {delay:.1f}s")
            time.sleep(delay)

    def cleanup(self):
        """Cleanup tunnel connections"""
        if self.tunnel_manager and self.current_tunnel:
            self.tunnel_manager.disconnect_tunnel(self.current_tunnel)
            logger.info("Tunnel connections cleaned up")

class EnhancedNjuskaloScraper(TunnelIntegratedScraper):
    """Enhanced Njuskalo scraper with tunnel integration"""

    def __init__(self, tunnel_config_path: str = None):
        super().__init__(tunnel_config_path)

        # Import existing scraper components
        try:
            from njuskalo_sitemap_scraper import NjuskaloSitemapScraper
            self.base_scraper = NjuskaloSitemapScraper
        except ImportError:
            logger.error("Could not import NjuskaloSitemapScraper")
            self.base_scraper = None

    def setup_enhanced_chrome_options(self):
        """Setup Chrome with anti-detection and proxy"""
        from selenium.webdriver.chrome.options import Options

        chrome_options = Options()

        # Anti-detection measures
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-images')
        chrome_options.add_argument('--disable-javascript')

        # Random user agent
        user_agents = [
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0'
        ]
        chrome_options.add_argument(f'--user-agent={random.choice(user_agents)}')

        # Setup proxy if available
        chrome_options = self.setup_selenium_proxy(chrome_options)

        return chrome_options

    def scrape_with_rotation(self, urls: list, delay_range: tuple = (10, 25)):
        """Scrape URLs with automatic tunnel rotation"""
        if not self.current_tunnel:
            logger.info("Connecting to initial tunnel...")
            if not self.connect_tunnel():
                logger.warning("No tunnel available, scraping without proxy")

        results = []

        for i, url in enumerate(urls):
            try:
                # Pre-request checks and rotation
                self.pre_request_hook()

                logger.info(f"Scraping {i+1}/{len(urls)}: {url}")

                # Add intelligent delay
                if i > 0:
                    delay = random.uniform(*delay_range)
                    logger.info(f"Delay before request: {delay:.1f}s")
                    time.sleep(delay)

                # Perform scraping (this would be implemented with actual scraping logic)
                result = self.scrape_single_url(url)
                results.append(result)

                logger.info(f"✅ Successfully scraped: {url}")

            except Exception as e:
                logger.error(f"❌ Error scraping {url}: {e}")

                # On error, try rotating tunnel
                if self.tunnel_manager:
                    logger.info("Attempting tunnel rotation after error...")
                    self.rotate_tunnel()
                    time.sleep(random.uniform(30, 60))  # Longer delay after error

        return results

    def scrape_single_url(self, url: str):
        """Scrape a single URL (placeholder - implement actual scraping logic)"""
        # This would contain the actual scraping implementation
        # For now, return a placeholder
        return {
            'url': url,
            'timestamp': time.time(),
            'tunnel': self.current_tunnel,
            'proxy': self.get_proxy_settings()
        }

def create_enhanced_scraper_script():
    """Create an enhanced scraper script with tunnel integration"""

    script_content = '''#!/usr/bin/env python3
"""
Enhanced Njuskalo Scraper with SSH Tunnel Integration

Usage:
    python3 enhanced_scraper.py --config ssh_tunnels.json --urls urls.txt
    python3 enhanced_scraper.py --auto-rotate --delay 15-30
"""

import argparse
import logging
from scraper_tunnel_integration import EnhancedNjuskaloScraper

def main():
    parser = argparse.ArgumentParser(description="Enhanced Njuskalo Scraper with Tunnels")
    parser.add_argument('--config', default='ssh_tunnels.json', help='Tunnel configuration file')
    parser.add_argument('--urls', help='File containing URLs to scrape')
    parser.add_argument('--url', help='Single URL to scrape')
    parser.add_argument('--auto-rotate', action='store_true', help='Enable auto tunnel rotation')
    parser.add_argument('--delay', default='10-25', help='Delay range between requests (e.g., 10-25)')
    parser.add_argument('--max-requests', type=int, default=100, help='Max requests per tunnel')
    parser.add_argument('--rotation-interval', type=int, default=1800, help='Tunnel rotation interval (seconds)')
    parser.add_argument('--output', default='scrape_results.json', help='Output file')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')

    # Parse delay range
    delay_parts = args.delay.split('-')
    delay_range = (float(delay_parts[0]), float(delay_parts[1]) if len(delay_parts) > 1 else float(delay_parts[0]))

    # Initialize scraper
    scraper = EnhancedNjuskaloScraper(args.config)
    scraper.auto_rotate = args.auto_rotate
    scraper.max_requests_per_tunnel = args.max_requests
    scraper.rotation_interval = args.rotation_interval

    try:
        # Prepare URLs
        urls = []
        if args.urls:
            with open(args.urls, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
        elif args.url:
            urls = [args.url]
        else:
            print("Error: Please provide either --urls or --url")
            return

        # Start scraping
        print(f"Starting enhanced scraping of {len(urls)} URLs...")
        results = scraper.scrape_with_rotation(urls, delay_range)

        # Save results
        import json
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"Scraping completed. Results saved to: {args.output}")

    except KeyboardInterrupt:
        print("\\nScraping interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        scraper.cleanup()

if __name__ == '__main__':
    main()
'''

    return script_content

def main():
    """Create the enhanced scraper script"""
    script_content = create_enhanced_scraper_script()

    script_path = Path(__file__).parent / "enhanced_scraper.py"
    with open(script_path, 'w') as f:
        f.write(script_content)

    os.chmod(script_path, 0o755)

    print(f"Enhanced scraper script created: {script_path}")
    print("Usage examples:")
    print("  python3 enhanced_scraper.py --urls urls.txt --auto-rotate")
    print("  python3 enhanced_scraper.py --url 'https://example.com' --delay 20-40")

if __name__ == '__main__':
    main()