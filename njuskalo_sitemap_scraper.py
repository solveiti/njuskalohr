#!/usr/bin/env python3
"""
Njuskalo Sitemap Store Scraper

This script scrapes store information from njuskalo.hr by:
1. Downloading the sitemap index XML
2. Finding store-related sitemaps
3. Downloading and extracting gzipped XML files
4. Visiting store URLs (trgovina) to scrape store data
5. Checking if stores post in categoryId 2 ("Auto moto")
6. Extracting address and ad count information
"""

import time
import random
import pandas as pd
import requests
import gzip
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import logging
from typing import List, Dict, Optional
import re
from bs4 import BeautifulSoup
import os
from database import NjuskaloDatabase

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


class NjuskaloSitemapScraper:
    """Web scraper for Njuskalo stores using sitemap approach."""

    def __init__(self, headless: bool = False, use_database: bool = True):
        """
        Initialize the scraper with Chrome WebDriver.

        Args:
            headless: Whether to run Chrome in headless mode
            use_database: Whether to use database for storing results
        """
        self.driver = None
        self.base_url = "https://www.njuskalo.hr"
        self.sitemap_index_url = "https://www.njuskalo.hr/sitemap-index.xml"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.headless = headless
        self.use_database = use_database
        self.database = None
        self.stores_data = []

    def setup_browser(self):
        """Set up Chrome WebDriver with optimal settings."""
        try:
            chrome_options = Options()

            if self.headless:
                chrome_options.add_argument("--headless")

            # Anti-detection options
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--start-maximized")

            # User agent
            chrome_options.add_argument(
                "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)

            # Execute script to hide automation
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            logger.info("Browser setup completed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to setup browser: {e}")
            return False

    def download_sitemap_index(self) -> Optional[str]:
        """Download and parse the sitemap index XML using browser."""
        try:
            logger.info(f"Downloading sitemap index with browser from: {self.sitemap_index_url}")

            # Navigate to the sitemap index URL
            self.driver.get(self.sitemap_index_url)

            # Wait a moment for page to load
            time.sleep(random.uniform(1, 3))

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

            # Wait for page to load
            time.sleep(random.uniform(2, 4))

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
            time.sleep(random.uniform(1, 2))

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

    def scrape_store_info(self, store_url: str) -> Optional[Dict]:
        """Scrape information from a store page."""
        try:
            logger.info(f"Scraping store: {store_url}")

            self.driver.get(store_url)

            # Random delay to mimic human behavior
            time.sleep(random.uniform(2, 5))

            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            store_data = {
                'url': store_url,
                'name': None,
                'address': None,
                'ads_count': None,
                'has_auto_moto': False,
                'categories': [],
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

            logger.info(f"Successfully scraped store: {store_data['name'] or 'Unknown'} (Auto Moto: {store_data['has_auto_moto']}, Ads: {store_data['ads_count']})")
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
                'error': str(e)
            }

    def run_full_scrape(self, max_stores: int = None, initialize_db: bool = True) -> List[Dict]:
        """Run the complete scraping workflow."""
        try:
            logger.info("Starting Njuskalo sitemap scraping workflow")

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

            # Setup browser
            if not self.setup_browser():
                logger.error("Failed to setup browser")
                return []

            # Step 1: Download sitemap index using browser
            sitemap_index_content = self.download_sitemap_index()
            if not sitemap_index_content:
                logger.error("Failed to download sitemap index")
                return []

            # Step 2: Parse sitemap index to get individual sitemap URLs
            sitemap_urls = self.parse_sitemap_index(sitemap_index_content)
            if not sitemap_urls:
                logger.error("No sitemap URLs found")
                return []

            all_store_urls = set()  # Use set to avoid duplicates

            # Step 3: Focus on stores sitemap specifically
            stores_sitemap_found = False
            for sitemap_url in sitemap_urls:
                if 'stores' in sitemap_url.lower() or 'trgovina' in sitemap_url.lower():
                    logger.info(f"Processing stores sitemap: {sitemap_url}")
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
                        logger.info(f"Processing stores XML file: {stores_xml_url}")

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

                        # Delay between XML downloads
                        time.sleep(random.uniform(2, 4))

                    # Delay between sitemap processing
                    time.sleep(random.uniform(1, 3))

            # If no stores sitemap found, process all sitemaps as fallback
            if not stores_sitemap_found:
                logger.info("No specific stores sitemap found, processing all sitemaps")
                for sitemap_url in sitemap_urls:
                    logger.info(f"Processing sitemap: {sitemap_url}")

                    # Download and extract sitemap
                    sitemap_content = self.download_sitemap_with_browser(sitemap_url)
                    if not sitemap_content:
                        logger.warning(f"Skipping sitemap due to download failure: {sitemap_url}")
                        continue

                    # Extract store URLs from this sitemap
                    store_urls = self.extract_store_urls(sitemap_content)
                    all_store_urls.update(store_urls)

                    # Small delay between sitemap downloads
                    time.sleep(random.uniform(2, 4))

                    # Break early if we have enough URLs for testing
                    if max_stores and len(all_store_urls) >= max_stores * 2:  # Get extra to account for filtering
                        break

            logger.info(f"Found total of {len(all_store_urls)} unique store URLs")

            # Convert to list and limit if needed
            store_urls_list = list(all_store_urls)
            if max_stores:
                store_urls_list = store_urls_list[:max_stores]
                logger.info(f"Limited to first {len(store_urls_list)} stores for testing")

            # Step 4: Scrape each store
            for i, store_url in enumerate(store_urls_list, 1):
                logger.info(f"Processing store {i}/{len(store_urls_list)}: {store_url}")

                try:
                    store_data = self.scrape_store_info(store_url)
                    if store_data:
                        self.stores_data.append(store_data)

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

                # Random delay between store visits
                time.sleep(random.uniform(3, 7))

            logger.info(f"Completed scraping {len(self.stores_data)} stores")

            # Print database statistics if enabled
            if self.use_database and self.database:
                try:
                    stats = self.database.get_database_stats()
                    logger.info(f"Database stats - Total: {stats['total_stores']}, Valid: {stats['valid_stores']}, Invalid: {stats['invalid_stores']}")
                except Exception as e:
                    logger.warning(f"Failed to get database stats: {e}")

            return self.stores_data

        except Exception as e:
            logger.error(f"Error in full scrape workflow: {e}")
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

            # Prepare data for DataFrame
            df_data = []
            for store in self.stores_data:
                row = {
                    'Store Name': store.get('name', ''),
                    'URL': store.get('url', ''),
                    'Address': store.get('address', ''),
                    'Ads Count': store.get('ads_count', ''),
                    'Has Auto Moto': store.get('has_auto_moto', False),
                    'Categories Count': len(store.get('categories', [])),
                    'Error': store.get('error', '')
                }
                df_data.append(row)

            df = pd.DataFrame(df_data)
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
    # Example usage
    scraper = NjuskaloSitemapScraper(headless=False)

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