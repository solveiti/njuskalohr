#!/usr/bin/env python3
"""
Njuskalo Sitemap Store Scraper

This script scrapes store information from njuskalo.hr by:
1. Downloading the sitemap index XML
2. Finding store-related sitemaps
3. Downloading and extracting gzipped XML files
4. Visiting store URLs (trgovina) with categoryId=2 filter to show only car ads
5. Checking if stores post in categoryId 2 ("Auto moto")
6. Extracting address and ad count information for car-related ads only
"""

import os
import sys

# Ensure we're running in the virtual environment
if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    # Try to load VENV_PATH from .env file
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    venv_path = '.venv'  # Default value

    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if line.strip() and not line.strip().startswith('#'):
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        if key.strip() == 'VENV_PATH':
                            venv_path = value.strip()
                            break

    venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), venv_path, 'bin', 'python3')
    if os.path.exists(venv_python):
        print(f"Restarting script in virtual environment: {venv_python}")
        os.execv(venv_python, [venv_python] + sys.argv)
    else:
        print(f"Warning: Virtual environment not found at {venv_python}")

import time
import random
import pandas as pd
import requests
import gzip
import xml.etree.ElementTree as ET
import os
from urllib.parse import urljoin, urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import logging
from typing import List, Dict, Optional
import re
from bs4 import BeautifulSoup
import os
from database import NjuskaloDatabase
import tempfile
import tempfile


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/sitemap_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AntiDetectionMixin:
    """Mixin class providing advanced anti-detection methods."""

    def get_smart_delay(self, min_seconds: float = 5.0, max_seconds: float = 15.0,
                       operation_type: str = "store_visit") -> float:
        """
        Generate intelligent random delays based on operation type.

        Args:
            min_seconds: Minimum delay
            max_seconds: Maximum delay
            operation_type: Type of operation for context-specific delays

        Returns:
            Delay in seconds
        """
        base_delays = {
            "store_visit": (8.0, 20.0),      # Between store visits - longest delay
            "page_load": (2.0, 5.0),         # After page loads
            "pagination": (3.0, 8.0),        # Between page navigations
            "data_extraction": (1.0, 3.0),   # During data extraction
            "sitemap_download": (4.0, 10.0), # Between sitemap downloads
            "error_recovery": (15.0, 30.0)   # After errors - extra long
        }

        if operation_type in base_delays:
            min_delay, max_delay = base_delays[operation_type]
        else:
            min_delay, max_delay = min_seconds, max_seconds

        # Add some randomness with weighted distribution (favor middle range)
        delay = random.triangular(min_delay, max_delay, (min_delay + max_delay) / 2)

        # Occasionally add extra long delays (5% chance)
        if random.random() < 0.05:
            delay += random.uniform(10, 25)
            logger.info(f"Added extra stealth delay: {delay:.1f}s")

        return delay

    def smart_sleep(self, operation_type: str = "store_visit",
                   min_seconds: float = None, max_seconds: float = None) -> None:
        """Sleep with intelligent delays based on operation type."""
        delay = self.get_smart_delay(
            min_seconds or 5.0,
            max_seconds or 15.0,
            operation_type
        )
        logger.debug(f"Sleeping {delay:.1f}s for {operation_type}")
        time.sleep(delay)

    def add_human_behavior(self) -> None:
        """Add realistic human-like behavior patterns."""
        try:
            # Random mouse movements
            if hasattr(self, 'driver') and self.driver:
                from selenium.webdriver.common.action_chains import ActionChains
                actions = ActionChains(self.driver)

                # Get window size for realistic movements
                window_size = self.driver.get_window_size()

                # Multiple small mouse movements (reduced iterations)
                for _ in range(random.randint(1, 3)):
                    x = random.randint(100, window_size['width'] - 100)
                    y = random.randint(100, window_size['height'] - 100)

                    try:
                        body = self.driver.find_element(By.TAG_NAME, "body")
                        actions.move_to_element_with_offset(body, x, y).perform()
                        time.sleep(random.uniform(0.05, 0.2))
                    except Exception:
                        break

                # Random scrolling patterns
                self.human_scroll_pattern()

        except Exception as e:
            logger.debug(f"Human behavior simulation failed: {e}")

    def human_scroll_pattern(self) -> None:
        """Simulate realistic human scrolling patterns."""
        try:
            if hasattr(self, 'driver') and self.driver:
                # Scroll down in chunks (reduced iterations and wait times)
                for _ in range(random.randint(1, 2)):
                    scroll_amount = random.randint(200, 600)
                    self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                    time.sleep(random.uniform(0.1, 0.4))

                # Sometimes scroll back up
                if random.random() > 0.6:
                    back_scroll = random.randint(100, 300)
                    self.driver.execute_script(f"window.scrollBy(0, -{back_scroll});")
                    time.sleep(random.uniform(0.1, 0.3))

                # Final scroll to top occasionally
                if random.random() > 0.8:
                    self.driver.execute_script("window.scrollTo(0, 0);")
                    time.sleep(random.uniform(0.2, 0.6))

        except Exception as e:
            logger.debug(f"Scroll pattern failed: {e}")

    def rotate_user_agent(self) -> str:
        """Get a random realistic Firefox user agent."""
        user_agents = [
            "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:119.0) Gecko/20100101 Firefox/119.0",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:119.0) Gecko/20100101 Firefox/119.0"
        ]
        return random.choice(user_agents)

    def add_request_headers(self) -> dict:
        """Generate realistic request headers."""
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'hr-HR,hr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
        return headers

    def accept_cookies(self) -> None:
        """Accept cookies if cookie banner is present."""
        try:
            cookie_selectors = [
                "[data-testid='cookie-accept-all']",
                ".cookie-accept",
                "#cookie-accept",
                "button[id*='cookie']",
                "button[class*='cookie']",
                ".gdpr-accept",
                "[data-cy='accept-all']",
                ".accept-all-cookies",
                ".cookie-consent-accept"
            ]

            for selector in cookie_selectors:
                try:
                    cookie_button = WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    cookie_button.click()
                    logger.info("Cookie banner accepted")
                    self.smart_sleep("data_extraction", min_seconds=0.5, max_seconds=2.0)
                    return
                except TimeoutException:
                    continue

        except Exception as e:
            logger.debug(f"No cookie banner found or error accepting: {e}")


class NjuskaloSitemapScraper(AntiDetectionMixin):
    """Web scraper for Njuskalo stores using sitemap approach."""

    def __init__(self, headless: bool = True, use_database: bool = True):
        """
        Initialize the scraper with Firefox WebDriver.

        Args:
            headless: Whether to run Firefox in headless mode
            use_database: Whether to use database for storing results
        """
        self.driver = None
        self.base_url = os.getenv("NJUSKALO_BASE_URL", "https://www.njuskalo.hr")
        self.sitemap_index_url = os.getenv("NJUSKALO_SITEMAP_INDEX_URL", "https://www.njuskalo.hr/sitemap-index.xml")
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0'
        })
        self.headless = headless
        self.use_database = use_database
        self.database = None
        self.stores_data = []

    def setup_browser(self) -> bool:
        """Set up Firefox WebDriver with server-compatible configuration."""
        try:
            firefox_options = Options()

            # Server-compatible configuration (exact setup that works)
            firefox_options.headless = True

            # ALWAYS use system Firefox, not webdriver's bundled version
            firefox_binary = "/usr/bin/firefox"
            if not os.path.exists(firefox_binary):
                raise FileNotFoundError(f"System Firefox not found at {firefox_binary}. Install with: sudo apt-get install firefox")
            firefox_options.binary_location = firefox_binary
            self.logger.info(f"🦊 Using system Firefox: {firefox_binary}")

            # Server-specific preferences for stability
            firefox_options.set_preference("browser.tabs.remote.autostart", False)
            firefox_options.set_preference("layers.acceleration.disabled", True)
            firefox_options.set_preference("gfx.webrender.force-disabled", True)
            firefox_options.set_preference("dom.ipc.plugins.enabled", False)
            firefox_options.set_preference("media.hardware-video-decoding.enabled", False)
            firefox_options.set_preference("media.hardware-video-decoding.force-enabled", False)
            firefox_options.set_preference("browser.startup.homepage", "about:blank")
            firefox_options.set_preference("security.sandbox.content.level", 0)
            firefox_options.set_preference("network.proxy.type", 0)

            # Enhanced anti-detection preferences
            firefox_options.set_preference("dom.webdriver.enabled", False)
            firefox_options.set_preference("useAutomationExtension", False)
            firefox_options.set_preference("general.platform.override", "Linux x86_64")
            firefox_options.set_preference("general.appversion.override", "5.0 (X11)")

            # Set user agent
            firefox_options.set_preference("general.useragent.override", self.rotate_user_agent())

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

            # Server compatibility - override headless setting to ensure it's properly set
            if self.headless:
                firefox_options.headless = True

            # Set window size for consistency
            width = random.randint(1366, 1920)
            height = random.randint(768, 1080)

            # Setup Firefox service with explicit geckodriver path
            service = Service("/usr/local/bin/geckodriver")
            self.driver = webdriver.Firefox(service=service, options=firefox_options)

            # Set window size programmatically as well
            self.driver.set_window_size(width, height)

            # Firefox-specific anti-detection JavaScript
            stealth_scripts = [
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
                "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})",
                "Object.defineProperty(navigator, 'languages', {get: () => ['hr-HR', 'hr', 'en-US', 'en']})",
                "Object.defineProperty(navigator, 'permissions', {get: () => ({query: () => Promise.resolve({state: 'granted'})})})",
            ]

            for script in stealth_scripts:
                try:
                    self.driver.execute_script(script)
                except Exception as e:
                    logger.debug(f"Stealth script failed: {e}")

            # Set realistic timeouts
            self.driver.implicitly_wait(5)
            self.driver.set_page_load_timeout(20)

            logger.info("Firefox browser setup completed successfully with enhanced anti-detection")
            return True

        except Exception as e:
            logger.error(f"Failed to setup Firefox browser: {e}")
            return False

    def download_sitemap_index(self) -> Optional[str]:
        """Download and parse the sitemap index XML using browser."""
        try:
            logger.info(f"Downloading sitemap index with browser from: {self.sitemap_index_url}")

            # Navigate to the sitemap index URL
            self.driver.get(self.sitemap_index_url)

            # Enhanced delay and human behavior
            self.smart_sleep("sitemap_download")
            self.add_human_behavior()

            # Get the page source
            xml_content = self.driver.page_source

            # Clean up the content - remove HTML wrapper if present
            if '<html' in xml_content.lower():
                # Find the XML content within the HTML
                if '<?xml' in xml_content:
                    start_pos = xml_content.find('<?xml')
                    xml_content = xml_content[start_pos:]

                    # Find the end of XML content
                    if '</sitemapindex>' in xml_content:
                        end_pos = xml_content.find('</sitemapindex>') + len('</sitemapindex>')
                        xml_content = xml_content[:end_pos]

            logger.info("Successfully downloaded sitemap index with browser")
            return xml_content

        except Exception as e:
            logger.error(f"Failed to download sitemap index with browser: {e}")
            # Add error recovery delay
            self.smart_sleep("error_recovery")
            return None

    def parse_sitemap_index(self, xml_content: str) -> List[str]:
        """Parse sitemap index and extract URLs of individual sitemaps."""
        sitemap_urls = []

        try:
            root = ET.fromstring(xml_content)

            # Handle namespace
            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

            # Prioritize store-specific sitemaps
            store_sitemaps = []
            seller_sitemaps = []
            other_sitemaps = []

            for sitemap in root.findall('.//ns:sitemap', namespace):
                loc_element = sitemap.find('ns:loc', namespace)
                if loc_element is not None:
                    sitemap_url = loc_element.text.strip()

                    if 'stores' in sitemap_url.lower() or 'trgovina' in sitemap_url:
                        store_sitemaps.append(sitemap_url)
                        logger.info(f"Found store sitemap: {sitemap_url}")
                    elif 'seller' in sitemap_url.lower():
                        seller_sitemaps.append(sitemap_url)
                        logger.info(f"Found seller sitemap: {sitemap_url}")
                    else:
                        other_sitemaps.append(sitemap_url)

            # Combine with priority: stores first, then sellers, then others
            sitemap_urls = store_sitemaps + seller_sitemaps + other_sitemaps

            logger.info(f"Found {len(sitemap_urls)} sitemap URLs (stores: {len(store_sitemaps)}, sellers: {len(seller_sitemaps)}, others: {len(other_sitemaps)})")
            return sitemap_urls

        except Exception as e:
            logger.error(f"Failed to parse sitemap index: {e}")
            return []

    def download_sitemap_with_browser(self, sitemap_url: str) -> Optional[str]:
        """Download sitemap using browser for non-gzipped files."""
        try:
            logger.info(f"Downloading sitemap with browser: {sitemap_url}")

            # Navigate to the sitemap URL
            self.driver.get(sitemap_url)

            # Enhanced delay and behavior simulation
            self.smart_sleep("sitemap_download")
            self.add_human_behavior()

            # Get the page source
            xml_content = self.driver.page_source

            # Clean up the content - remove HTML wrapper if present
            if '<html' in xml_content.lower() and '<?xml' in xml_content:
                # Extract XML from within HTML
                start_pos = xml_content.find('<?xml')
                xml_content = xml_content[start_pos:]

                # Find the end of XML content
                if '</urlset>' in xml_content:
                    end_pos = xml_content.find('</urlset>') + len('</urlset>')
                    xml_content = xml_content[:end_pos]
                elif '</sitemapindex>' in xml_content:
                    end_pos = xml_content.find('</sitemapindex>') + len('</sitemapindex>')
                    xml_content = xml_content[:end_pos]

            # Validate we have XML content
            if not ('<?xml' in xml_content or '<urlset' in xml_content or '<sitemapindex' in xml_content):
                logger.warning("No valid XML content found in response")
                return None

            logger.info(f"Successfully downloaded sitemap ({len(xml_content)} characters)")
            return xml_content

        except Exception as e:
            logger.error(f"Failed to download sitemap {sitemap_url} with browser: {e}")
            return None

    def download_gz_file_with_browser(self, gz_url: str) -> Optional[str]:
        """Download and decompress a .gz file using browser session."""
        try:
            logger.info(f"Downloading .gz file: {gz_url}")

            # First, navigate to establish browser session and cookies
            self.driver.get(self.base_url)
            time.sleep(random.uniform(0.5, 1.0))

            # Get cookies from browser session
            cookies = {}
            for cookie in self.driver.get_cookies():
                cookies[cookie['name']] = cookie['value']

            # Use requests session with browser cookies and headers
            headers = {
                'User-Agent': self.driver.execute_script("return navigator.userAgent;"),
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9,hr;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Upgrade-Insecure-Requests': '1',
            }

            # Download the .gz file
            response = self.session.get(gz_url, headers=headers, cookies=cookies, timeout=30)
            response.raise_for_status()

            logger.info(f"Downloaded .gz file ({len(response.content)} bytes)")

            # Decompress the content
            try:
                xml_content = gzip.decompress(response.content).decode('utf-8')
                logger.info(f"Successfully decompressed .gz file ({len(xml_content)} characters)")
                return xml_content
            except Exception as decompress_error:
                logger.error(f"Failed to decompress .gz file: {decompress_error}")
                # Try to use content as-is in case it's not actually compressed
                try:
                    xml_content = response.content.decode('utf-8')
                    if '<?xml' in xml_content or '<urlset' in xml_content:
                        logger.info("Content was not compressed, using as-is")
                        return xml_content
                except Exception:
                    pass
                return None

        except Exception as e:
            logger.error(f"Failed to download .gz file {gz_url}: {e}")
            return None

    def extract_store_urls(self, xml_content: str) -> List[str]:
        """Extract store URLs (trgovina) from sitemap XML."""
        store_urls = []

        try:
            root = ET.fromstring(xml_content)

            # Handle namespace
            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

            for url in root.findall('.//ns:url', namespace):
                loc_element = url.find('ns:loc', namespace)
                if loc_element is not None:
                    url_text = loc_element.text.strip()
                    # Check if URL contains 'trgovina' (store in Croatian)
                    if '/trgovina/' in url_text:
                        store_urls.append(url_text)

            logger.info(f"Found {len(store_urls)} store URLs in this sitemap")
            return store_urls

        except ET.ParseError as e:
            logger.warning(f"XML parsing failed: {e}")
            # Try regex fallback
            try:
                import re
                url_pattern = r'<loc>(https://[^<]*?/trgovina/[^<]+)</loc>'
                matches = re.findall(url_pattern, xml_content)
                store_urls = matches
                logger.info(f"Regex fallback found {len(store_urls)} store URLs")
                return store_urls
            except Exception as regex_e:
                logger.error(f"Regex fallback also failed: {regex_e}")
                return []

        except Exception as e:
            logger.error(f"Failed to extract store URLs: {e}")
            return []

    def add_car_category_filter(self, url: str) -> str:
        """
        Add categoryId=2 parameter to URL to filter for cars only.

        This ensures that when visiting store pages, only car-related ads
        are displayed, which improves the accuracy of vehicle counting
        and eliminates irrelevant listings.

        Args:
            url: The original store URL

        Returns:
            URL with categoryId=2 parameter added
        """
        try:
            if '?' in url:
                # URL already has parameters, add categoryId as additional parameter
                filtered_url = f"{url}&categoryId=2"
            else:
                # URL has no parameters, add categoryId as first parameter
                filtered_url = f"{url}?categoryId=2"

            logger.debug(f"Added car filter to URL: {url} -> {filtered_url}")
            return filtered_url
        except Exception as e:
            logger.warning(f"Failed to add car filter to URL {url}: {e}")
            return url

    def detect_vehicle_flags(self) -> Dict[str, int]:
        """
        Detect vehicle flags on the current page using enhanced selectors.

        Returns:
            Dictionary with 'new_count' and 'used_count' keys
        """
        new_count = 0
        used_count = 0

        try:
            # Primary method: Look for specific vehicle flags in li.entity-flag span.flag elements
            flag_elements = self.driver.find_elements(By.CSS_SELECTOR, "li.entity-flag span.flag")
            if flag_elements:
                logger.debug(f"Found {len(flag_elements)} entity-flag elements")
                for flag_element in flag_elements:
                    try:
                        flag_text = flag_element.text.lower()
                        if 'novo vozilo' in flag_text:
                            new_count += 1
                            logger.debug(f"Found 'Novo vozilo' flag: {flag_text}")
                        elif 'rabljeno vozilo' in flag_text:
                            used_count += 1
                            logger.debug(f"Found 'Rabljeno vozilo' flag: {flag_text}")
                    except Exception as e:
                        logger.debug(f"Error reading flag text: {e}")
                        continue

                # Return early if we found flags using the primary method
                if new_count > 0 or used_count > 0:
                    return {'new_count': new_count, 'used_count': used_count}

            # Secondary method: Look for flags in broader entity-flag containers
            flag_containers = self.driver.find_elements(By.CSS_SELECTOR, "li.entity-flag")
            if flag_containers:
                logger.debug(f"Found {len(flag_containers)} entity-flag containers")
                for container in flag_containers:
                    try:
                        container_text = container.text.lower()
                        if 'novo vozilo' in container_text:
                            new_count += 1
                        elif 'rabljeno vozilo' in container_text:
                            used_count += 1
                    except Exception as e:
                        logger.debug(f"Error reading container text: {e}")
                        continue

                # Return if we found any flags
                if new_count > 0 or used_count > 0:
                    return {'new_count': new_count, 'used_count': used_count}

            # Fallback method: Search in various ad elements
            ad_selectors = [
                '.entity-item',
                '.ad-item',
                '.listing-item',
                '[data-testid="ad-item"]',
                '.classified-item'
            ]

            for selector in ad_selectors:
                try:
                    ad_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if ad_elements:
                        for ad_element in ad_elements:
                            try:
                                ad_text = ad_element.text.lower()
                                if 'novo vozilo' in ad_text:
                                    new_count += 1
                                elif 'rabljeno vozilo' in ad_text:
                                    used_count += 1
                            except Exception:
                                continue
                        break  # Exit after first successful selector
                except Exception:
                    continue

        except Exception as e:
            logger.warning(f"Error in vehicle flag detection: {e}")

        return {'new_count': new_count, 'used_count': used_count}

    def count_vehicle_ads(self, store_url: str) -> Dict[str, int]:
        """
        Count 'Novo vozilo' and 'Rabljeno vozilo' ads by paginating through all store ads.
        Uses enhanced detection to find vehicle flags in li.entity-flag span.flag elements.
        """
        new_count = 0
        used_count = 0
        page = 1
        max_pages = 20  # Safety limit to prevent infinite loops

        # Add car category filter to base URL
        filtered_store_url = self.add_car_category_filter(store_url)

        try:
            while page <= max_pages:
                # Construct paginated URL with car filter
                if '?' in filtered_store_url:
                    paginated_url = f"{filtered_store_url}&page={page}"
                else:
                    paginated_url = f"{filtered_store_url}?page={page}"

                logger.info(f"Checking page {page} of store ads: {paginated_url}")

                self.driver.get(paginated_url)

                # Enhanced delays for pagination
                self.smart_sleep("pagination")
                self.add_human_behavior()

                # Wait for page to load
                try:
                    WebDriverWait(self.driver, 7).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                except TimeoutException:
                    logger.warning(f"Page {page} failed to load")
                    break

                # Use enhanced vehicle flag detection
                page_counts = self.detect_vehicle_flags()
                page_new_count = page_counts['new_count']
                page_used_count = page_counts['used_count']

                # Check if we found any vehicles on this page
                ads_found = page_new_count > 0 or page_used_count > 0

                # If no ads found with standard selectors, try searching page text
                if not ads_found:
                    try:
                        page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                        page_new_count = page_text.count('novo vozilo')
                        page_used_count = page_text.count('rabljeno vozilo')

                        # If we found vehicle mentions, consider this a valid page
                        if page_new_count > 0 or page_used_count > 0:
                            ads_found = True
                    except Exception:
                        pass

                new_count += page_new_count
                used_count += page_used_count

                logger.info(f"Page {page}: Found {page_new_count} new vehicles, {page_used_count} used vehicles")

                # Check if there's a next page
                next_page_exists = False
                next_selectors = [
                    '.pagination .next',
                    '.pagination .page-next',
                    'a[aria-label="Next"]',
                    '.pager .next',
                    '[data-testid="next-page"]'
                ]

                for selector in next_selectors:
                    try:
                        next_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if next_element.is_enabled() and not next_element.get_attribute('disabled'):
                            next_page_exists = True
                            break
                    except NoSuchElementException:
                        continue

                # Also check if we found no ads on this page (might indicate end)
                if not ads_found or not next_page_exists:
                    logger.info(f"No more pages found after page {page}")
                    break

                page += 1

        except Exception as e:
            logger.error(f"Error counting vehicle ads: {e}")

        result = {'new_count': new_count, 'used_count': used_count}
        logger.info(f"Total vehicle counts - New: {new_count}, Used: {used_count}")
        return result

    def scrape_store_info(self, store_url: str) -> Optional[Dict]:
        """Scrape information from a store page."""
        try:
            # Add car category filter to URL
            filtered_url = self.add_car_category_filter(store_url)
            logger.info(f"Scraping store: {store_url} (filtered: {filtered_url})")

            self.driver.get(filtered_url)

            # Enhanced delay and human behavior simulation
            self.smart_sleep("page_load")
            self.add_human_behavior()

            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Additional delay before data extraction
            self.smart_sleep("data_extraction")

            store_data = {
                'url': store_url,
                'name': None,
                'address': None,
                'ads_count': None,
                'has_auto_moto': False,
                'categories': [],
                'new_ads_count': 0,
                'used_ads_count': 0,
                'error': None
            }

            # Extract store name
            try:
                name_selectors = [
                    'h1',
                    '.store-name',
                    '.shop-name',
                    '.entity-name',
                    '[data-testid="store-name"]',
                    '.profile-header h1',
                    '.seller-info h1',
                    '.store-title'
                ]

                for selector in name_selectors:
                    try:
                        name_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        store_data['name'] = name_element.text.strip()
                        if store_data['name']:
                            break
                    except NoSuchElementException:
                        continue

            except Exception as e:
                logger.warning(f"Could not extract store name: {e}")

            # Extract address - try multiple approaches
            try:
                address_selectors = [
                    '.store-address',
                    '.shop-address',
                    '.address',
                    '[data-testid="store-address"]',
                    '.contact-info .address',
                    '.store-info .address',
                    '.profile-info .address',
                    '.seller-contact',
                    '.contact-details'
                ]

                for selector in address_selectors:
                    try:
                        address_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        address_text = address_element.text.strip()
                        if address_text and len(address_text) > 5:  # Basic validation
                            store_data['address'] = address_text
                            break
                    except NoSuchElementException:
                        continue

                # If no address found via CSS selectors, try text search
                if not store_data['address']:
                    try:
                        page_text = self.driver.find_element(By.TAG_NAME, "body").text
                        # Look for Croatian city patterns or postal codes
                        address_patterns = [
                            r'\d{5}\s+[A-ZČĆŽŠĐ][a-zčćžšđ]+',  # Postal code + city
                            r'[A-ZČĆŽŠĐ][a-zčćžšđ]+\s+\d+[a-z]?',  # Street + number
                        ]

                        for pattern in address_patterns:
                            matches = re.findall(pattern, page_text)
                            if matches:
                                store_data['address'] = matches[0]
                                break
                    except Exception:
                        pass

            except Exception as e:
                logger.warning(f"Could not extract address: {e}")

            # Extract ads count from entities-count class and similar
            try:
                count_selectors = [
                    '.entities-count',
                    '.ads-count',
                    '.listings-count',
                    '[data-testid="entities-count"]',
                    '.entity-count',
                    '.total-ads'
                ]

                for selector in count_selectors:
                    try:
                        count_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        ads_text = count_element.text.strip()
                        # Extract number from text like "123 oglasa", "45 ads", or just "67"
                        ads_match = re.search(r'(\d+)', ads_text)
                        if ads_match:
                            store_data['ads_count'] = int(ads_match.group(1))
                            break
                    except NoSuchElementException:
                        continue

                # If no specific count element found, look in page text
                if store_data['ads_count'] is None:
                    try:
                        page_text = self.driver.find_element(By.TAG_NAME, "body").text
                        # Look for Croatian patterns like "X oglasa" or "X objava"
                        count_patterns = [
                            r'(\d+)\s+oglas[ai]',  # "123 oglasa" or "1 oglas"
                            r'(\d+)\s+objav[ae]',  # "123 objave" or "1 objava"
                        ]

                        for pattern in count_patterns:
                            matches = re.findall(pattern, page_text, re.IGNORECASE)
                            if matches:
                                store_data['ads_count'] = int(matches[0])
                                break
                    except Exception:
                        pass

            except Exception as e:
                logger.warning(f"Could not extract ads count: {e}")

            # Check for Auto moto category (categoryId 2)
            try:
                # Look for category links or elements that might indicate Auto moto
                category_selectors = [
                    'a[href*="categoryId=2"]',
                    'a[href*="/auti"]',
                    'a[href*="/auto"]',
                    'a[href*="/moto"]',
                    '.category-link',
                    '[data-category-id="2"]',
                    '.category-item'
                ]

                categories_found = []

                # Check page source for category indicators
                page_source = self.driver.page_source.lower()
                if 'categoryid=2' in page_source or 'categoryid%3d2' in page_source:
                    store_data['has_auto_moto'] = True

                for selector in category_selectors:
                    try:
                        category_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in category_elements:
                            try:
                                category_text = element.text.strip()
                                category_href = element.get_attribute('href') or ''

                                categories_found.append({
                                    'text': category_text,
                                    'href': category_href
                                })

                                # Check if this is Auto moto category
                                if ('categoryId=2' in category_href or
                                    'categoryid=2' in category_href.lower() or
                                    'auti' in category_href.lower() or
                                    'auto' in category_text.lower() or
                                    'moto' in category_text.lower() or
                                    'vozila' in category_text.lower()):
                                    store_data['has_auto_moto'] = True
                            except Exception:
                                continue

                    except Exception:
                        continue

                store_data['categories'] = categories_found

                # Additional check: look for auto-related keywords in page text
                if not store_data['has_auto_moto']:
                    page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                    auto_keywords = ['automobil', 'vozilo', 'auto', 'motocikl', 'motor']
                    if any(keyword in page_text for keyword in auto_keywords):
                        # Additional validation - these keywords should appear multiple times
                        keyword_count = sum(page_text.count(keyword) for keyword in auto_keywords)
                        if keyword_count >= 3:  # Threshold to avoid false positives
                            store_data['has_auto_moto'] = True

            except Exception as e:
                logger.warning(f"Could not check for Auto moto category: {e}")

            # Count new and used vehicle ads if this store has auto moto category
            if store_data['has_auto_moto']:
                try:
                    logger.info("Counting vehicle ads (new vs used)...")
                    vehicle_counts = self.count_vehicle_ads(store_url)
                    store_data['new_ads_count'] = vehicle_counts['new_count']
                    store_data['used_ads_count'] = vehicle_counts['used_count']
                except Exception as e:
                    logger.warning(f"Could not count vehicle ads: {e}")
                    store_data['new_ads_count'] = 0
                    store_data['used_ads_count'] = 0

            logger.info(f"Successfully scraped store: {store_data['name'] or 'Unknown'} (Auto Moto: {store_data['has_auto_moto']}, Ads: {store_data['ads_count']}, New: {store_data['new_ads_count']}, Used: {store_data['used_ads_count']})")
            return store_data

        except Exception as e:
            logger.error(f"Failed to scrape store {store_url}: {e}")
            return {
                'url': store_url,
                'name': None,
                'address': None,
                'ads_count': None,
                'has_auto_moto': False,
                'categories': [],
                'new_ads_count': 0,
                'used_ads_count': 0,
                'error': str(e)
            }

    def discover_and_add_new_urls(self) -> List[str]:
        """
        Discover new store URLs from sitemaps and add them to the database.

        Returns:
            List of new URLs that were added to the database
        """
        logger.info("Starting URL discovery process...")

        # Get all store URLs from sitemaps
        all_store_urls = self._get_all_store_urls_from_sitemaps()

        if not all_store_urls:
            logger.warning("No store URLs found in sitemaps")
            return []

        logger.info(f"Found {len(all_store_urls)} total store URLs in sitemaps")

        # Get existing URLs from database
        existing_urls = set()
        if self.use_database and self.database:
            existing_urls = self.database.get_existing_urls()
            logger.info(f"Found {len(existing_urls)} existing URLs in database")

        # Find new URLs
        new_urls = [url for url in all_store_urls if url not in existing_urls]
        logger.info(f"Found {len(new_urls)} new URLs to add")

        # Add new URLs to database with minimal placeholder data
        if new_urls and self.use_database and self.database:
            added_count = 0
            for url in new_urls:
                placeholder_data = {
                    'url': url,
                    'name': None,
                    'address': None,
                    'ads_count': None,
                    'has_auto_moto': None,  # Will be determined during scraping
                    'categories': [],
                    'new_ads_count': 0,
                    'used_ads_count': 0,
                    'scraped': False  # Flag to indicate not yet scraped
                }

                success = self.database.save_store_data(
                    url=url,
                    store_data=placeholder_data,
                    is_valid=True
                )

                if success:
                    added_count += 1
                else:
                    logger.warning(f"Failed to add URL to database: {url}")

            logger.info(f"Successfully added {added_count} new URLs to database")

        return new_urls

    def _get_all_store_urls_from_sitemaps(self) -> List[str]:
        """
        Get all store URLs from sitemaps without scraping individual stores.

        Returns:
            List of all store URLs found in sitemaps
        """
        try:
            # Setup browser
            if not self.setup_browser():
                logger.error("Failed to setup browser for URL discovery")
                return []

            # Step 1: Download sitemap index
            sitemap_index_content = self.download_sitemap_index()
            if not sitemap_index_content:
                logger.error("Failed to download sitemap index for URL discovery")
                return []

            # Step 2: Parse sitemap index to get individual sitemap URLs
            sitemap_urls = self.parse_sitemap_index(sitemap_index_content)
            if not sitemap_urls:
                logger.error("No sitemap URLs found for URL discovery")
                return []

            all_store_urls = set()  # Use set to avoid duplicates

            # Step 3: Focus on stores sitemap specifically
            stores_sitemap_found = False
            for sitemap_url in sitemap_urls:
                if 'stores' in sitemap_url.lower() or 'trgovina' in sitemap_url.lower():
                    logger.info(f"Processing stores sitemap for URL discovery: {sitemap_url}")
                    stores_sitemap_found = True

                    # Download the stores sitemap index (non-gzipped)
                    stores_sitemap_content = self.download_sitemap_with_browser(sitemap_url)
                    if not stores_sitemap_content:
                        logger.warning(f"Failed to download stores sitemap: {sitemap_url}")
                        continue

                    # Parse to get the actual stores XML.gz file URLs
                    stores_xml_urls = self.parse_sitemap_index(stores_sitemap_content)

                    # Process each stores XML file (usually .xml.gz files)
                    for stores_xml_url in stores_xml_urls:
                        logger.info(f"Processing stores XML file for URLs: {stores_xml_url}")

                        # Check if it's a .gz file and use appropriate download method
                        if stores_xml_url.endswith('.gz'):
                            stores_xml_content = self.download_gz_file_with_browser(stores_xml_url)
                        else:
                            stores_xml_content = self.download_sitemap_with_browser(stores_xml_url)

                        if not stores_xml_content:
                            logger.warning(f"Failed to download stores XML: {stores_xml_url}")
                            continue

                        # Extract store URLs from this XML
                        store_urls = self.extract_store_urls(stores_xml_content)
                        all_store_urls.update(store_urls)

                        # Delay between XML downloads (reduced)
                        time.sleep(random.uniform(0.3, 0.7))

                    # Delay between sitemap processing (reduced)
                    time.sleep(random.uniform(0.3, 0.7))

            # If no stores sitemap found, process all sitemaps as fallback
            if not stores_sitemap_found:
                logger.info("No specific stores sitemap found, processing all sitemaps for URL discovery")
                for sitemap_url in sitemap_urls:
                    logger.info(f"Processing sitemap for URL discovery: {sitemap_url}")

                    # Download and extract sitemap
                    sitemap_content = self.download_sitemap_with_browser(sitemap_url)
                    if not sitemap_content:
                        logger.warning(f"Skipping sitemap due to download failure: {sitemap_url}")
                        continue

                    # Extract store URLs from this sitemap
                    store_urls = self.extract_store_urls(sitemap_content)
                    all_store_urls.update(store_urls)

                    # Small delay between sitemap downloads (reduced)
                    time.sleep(random.uniform(0.3, 0.7))

            return list(all_store_urls)

        except Exception as e:
            logger.error(f"Error during URL discovery: {e}")
            return []

    def run_full_scrape(self, max_stores: int = None, initialize_db: bool = True) -> List[Dict]:
        """Run the optimized scraping workflow that focuses on auto moto stores."""
        try:
            logger.info("Starting optimized Njuskalo sitemap scraping workflow")

            # Initialize database if enabled
            if self.use_database and initialize_db:
                try:
                    self.database = NjuskaloDatabase()
                    self.database.connect()
                    self.database.create_tables()
                    logger.info("Database initialized successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize database: {e}")
                    self.use_database = False  # Fall back to non-database mode

            # Step 1: Discover and add new URLs to database
            new_urls = self.discover_and_add_new_urls()
            logger.info(f"URL discovery completed. Found {len(new_urls)} new URLs")

            # Step 2: Determine which stores to scrape
            stores_to_scrape = []

            if self.use_database and self.database:
                # Get existing auto moto stores (already identified as having car ads)
                auto_moto_stores = self.database.get_auto_moto_stores()
                logger.info(f"Found {len(auto_moto_stores)} existing auto moto stores")

                # Add URLs of auto moto stores that need re-scraping
                for store in auto_moto_stores:
                    stores_to_scrape.append(store['url'])

                # Add new URLs that haven't been scraped yet
                # We need to scrape these to determine if they have car ads
                new_store_urls = [url for url in new_urls]
                stores_to_scrape.extend(new_store_urls)

                logger.info(f"Total stores to scrape: {len(stores_to_scrape)} (Auto moto: {len(auto_moto_stores)}, New: {len(new_store_urls)})")
            else:
                # Fallback: if no database, just scrape new URLs
                stores_to_scrape = new_urls
                logger.info(f"No database available, will scrape {len(stores_to_scrape)} new URLs")

            # Limit stores if max_stores is specified
            if max_stores and len(stores_to_scrape) > max_stores:
                stores_to_scrape = stores_to_scrape[:max_stores]
                logger.info(f"Limited to first {len(stores_to_scrape)} stores for testing")

            # Step 3: Setup browser for scraping
            if not self.setup_browser():
                logger.error("Failed to setup browser")
                return []

            # Step 4: Scrape selected stores
            auto_moto_count = 0
            non_auto_moto_count = 0

            for i, store_url in enumerate(stores_to_scrape, 1):
                logger.info(f"Processing store {i}/{len(stores_to_scrape)}: {store_url}")

                try:
                    store_data = self.scrape_store_info(store_url)
                    if store_data:
                        self.stores_data.append(store_data)

                        # Track auto moto vs non-auto moto
                        if store_data.get('has_auto_moto'):
                            auto_moto_count += 1
                        else:
                            non_auto_moto_count += 1

                        # Save to database if enabled
                        if self.use_database and self.database:
                            is_valid = store_data.get('error') is None
                            success = self.database.save_store_data(
                                url=store_url,
                                store_data=store_data,
                                is_valid=is_valid
                            )
                            if success:
                                logger.debug(f"Saved store data to database: {store_url}")
                            else:
                                logger.warning(f"Failed to save store data to database: {store_url}")
                    else:
                        # Mark URL as invalid in database
                        if self.use_database and self.database:
                            self.database.mark_url_invalid(store_url)
                            logger.debug(f"Marked URL as invalid in database: {store_url}")

                except Exception as e:
                    logger.error(f"Error processing store {store_url}: {e}")
                    # Mark as invalid in database
                    if self.use_database and self.database:
                        self.database.mark_url_invalid(store_url)

                # Enhanced random delay between store visits with progress-based scaling
                progress_factor = i / len(stores_to_scrape)

                # Increase delays as we progress to avoid pattern detection
                if progress_factor > 0.7:  # After 70% completion, use longer delays
                    self.smart_sleep("store_visit", min_seconds=12.0, max_seconds=25.0)
                else:
                    self.smart_sleep("store_visit")

                # Occasionally add extra long breaks (every 10-15 stores)
                if i % random.randint(10, 15) == 0:
                    extra_delay = random.uniform(30, 60)
                    logger.info(f"Taking extended break: {extra_delay:.1f}s after {i} stores")
                    time.sleep(extra_delay)

            logger.info(f"Completed scraping {len(self.stores_data)} stores")
            logger.info(f"Auto moto stores: {auto_moto_count}, Non-auto moto stores: {non_auto_moto_count}")

            # Print database statistics if enabled
            if self.use_database and self.database:
                try:
                    stats = self.database.get_database_stats()
                    logger.info(f"Database stats - Total: {stats['total_stores']}, Valid: {stats['valid_stores']}, Invalid: {stats['invalid_stores']}")
                except Exception as e:
                    logger.warning(f"Failed to get database stats: {e}")

            return self.stores_data

        except Exception as e:
            logger.error(f"Error in optimized scrape workflow: {e}")
            return self.stores_data
        finally:
            # Clean up database connection
            if self.use_database and self.database:
                try:
                    self.database.disconnect()
                    logger.info("Database connection closed")
                except Exception as e:
                    logger.warning(f"Error closing database connection: {e}")

    def run_auto_moto_only_scrape(self, max_stores: int = None) -> List[Dict]:
        """
        Run scraping workflow that only processes stores known to have auto moto category.
        This is the most efficient mode for getting car-related data.
        """
        try:
            logger.info("Starting auto moto only scraping workflow")

            # Initialize database
            if self.use_database:
                try:
                    self.database = NjuskaloDatabase()
                    self.database.connect()
                    self.database.create_tables()
                    logger.info("Database initialized successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize database: {e}")
                    return []
            else:
                logger.error("Database is required for auto moto only scraping")
                return []

            # Get auto moto stores from database
            auto_moto_stores = self.database.get_auto_moto_stores()

            if not auto_moto_stores:
                logger.warning("No auto moto stores found in database. Run full scrape first to identify auto moto stores.")
                return []

            logger.info(f"Found {len(auto_moto_stores)} auto moto stores to scrape")

            # Limit stores if specified
            stores_to_scrape = [store['url'] for store in auto_moto_stores]
            if max_stores and len(stores_to_scrape) > max_stores:
                stores_to_scrape = stores_to_scrape[:max_stores]
                logger.info(f"Limited to first {len(stores_to_scrape)} auto moto stores")

            # Setup browser
            if not self.setup_browser():
                logger.error("Failed to setup browser")
                return []

            # Scrape only auto moto stores
            for i, store_url in enumerate(stores_to_scrape, 1):
                logger.info(f"Processing auto moto store {i}/{len(stores_to_scrape)}: {store_url}")

                try:
                    store_data = self.scrape_store_info(store_url)
                    if store_data:
                        self.stores_data.append(store_data)

                        # Update database with latest data
                        if self.database:
                            is_valid = store_data.get('error') is None
                            success = self.database.save_store_data(
                                url=store_url,
                                store_data=store_data,
                                is_valid=is_valid
                            )
                            if success:
                                logger.debug(f"Updated store data in database: {store_url}")
                            else:
                                logger.warning(f"Failed to update store data in database: {store_url}")

                except Exception as e:
                    logger.error(f"Error processing auto moto store {store_url}: {e}")
                    if self.database:
                        self.database.mark_url_invalid(store_url)

                # Enhanced random delay between store visits for auto moto stores
                progress_factor = i / len(stores_to_scrape)

                # Scale delays based on progress and store count
                if progress_factor > 0.8:  # After 80% completion for focused scraping
                    self.smart_sleep("store_visit", min_seconds=15.0, max_seconds=30.0)
                else:
                    self.smart_sleep("store_visit", min_seconds=10.0, max_seconds=20.0)

                # Extended breaks for auto moto scraping (every 8-12 stores)
                if i % random.randint(8, 12) == 0:
                    extra_delay = random.uniform(45, 90)
                    logger.info(f"Taking extended auto moto break: {extra_delay:.1f}s after {i} stores")
                    time.sleep(extra_delay)

            logger.info(f"Completed scraping {len(self.stores_data)} auto moto stores")

            return self.stores_data

        except Exception as e:
            logger.error(f"Error in auto moto only scrape workflow: {e}")
            return self.stores_data
        finally:
            # Clean up database connection
            if self.use_database and self.database:
                try:
                    self.database.disconnect()
                    logger.info("Database connection closed")
                except Exception as e:
                    logger.warning(f"Error closing database connection: {e}")

    def save_to_excel(self, filename: str = None) -> bool:
        """Save scraped data to Excel file in datadump directory."""
        try:
            if not self.stores_data:
                logger.warning("No data to save")
                return False

            # Create datadump directory if it doesn't exist
            import os
            datadump_dir = "datadump"
            os.makedirs(datadump_dir, exist_ok=True)

            if not filename:
                timestamp = int(time.time())
                filename = f"njuskalo_stores_{timestamp}.xlsx"

            # Ensure filename goes to datadump directory
            if not filename.startswith(datadump_dir):
                filename = os.path.join(datadump_dir, filename)

            # Prepare data for DataFrame with specific header format
            df_data = []
            for i, store in enumerate(self.stores_data, start=1):
                row = {
                    'id': i,  # Sequential ID
                    'vat': '',  # VAT - set as empty since no data available on scraped page
                    'name': store.get('name', ''),  # Store name
                    'subname': store.get('subname', ''),  # Store subname/category
                    'address': store.get('address', ''),  # Store address
                    'total': store.get('ads_count', 0),  # Total number of ads (old ads_count)
                    'new': store.get('new_ads_count', 0),  # New vehicle ads count
                    'used': store.get('used_ads_count', 0),  # Used vehicle ads count
                    'test': 0  # Test field - set to 0 for now
                }
                df_data.append(row)

            df = pd.DataFrame(df_data)

            # Ensure columns are in the correct order
            column_order = ['id', 'vat', 'name', 'subname', 'address', 'total', 'new', 'used', 'test']
            df = df.reindex(columns=column_order)

            # Fill NaN values with empty strings for VAT column
            df['vat'] = df['vat'].fillna('')

            df.to_excel(filename, index=False)

            logger.info(f"Data saved to {filename}")
            return True

        except Exception as e:
            logger.error(f"Failed to save data to Excel: {e}")
            return False

    def close(self):
        """Clean up resources."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser closed successfully")
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")

        if hasattr(self, 'session'):
            self.session.close()


if __name__ == "__main__":
    # Example usage - headless by default, use headless=False for manual testing/debugging
    scraper = NjuskaloSitemapScraper(headless=True)

    try:
        # For testing, limit to 5 stores
        stores_data = scraper.run_full_scrape(max_stores=5)

        if stores_data:
            scraper.save_to_excel()

            # Print summary
            print(f"\n📊 Scraping Summary:")
            print(f"Total stores processed: {len(stores_data)}")

            auto_moto_stores = [s for s in stores_data if s.get('has_auto_moto')]
            print(f"Stores with Auto Moto category: {len(auto_moto_stores)}")

            stores_with_ads = [s for s in stores_data if s.get('ads_count')]
            if stores_with_ads:
                total_ads = sum(s['ads_count'] for s in stores_with_ads)
                print(f"Total ads across all stores: {total_ads}")

        else:
            print("No stores found. Check the logs for details.")

    finally:
        scraper.close()