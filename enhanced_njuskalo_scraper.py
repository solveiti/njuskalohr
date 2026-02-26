#!/usr/bin/env python3
"""
Enhanced Njuskalo Sitemap Scraper with XML Processing and Vehicle Counting

This enhanced scraper implements:
1. XML sitemap download and comparison with database
2. New URL detection and storage
3. Auto moto category detection and flagging
4. Vehicle type counting (Novo vozilo vs Rabljeno vozilo)
5. Fallback scraping from database when XML unavailable
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
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from njuskalo_sitemap_scraper import NjuskaloSitemapScraper
from database import NjuskaloDatabase

logger = logging.getLogger(__name__)

class EnhancedNjuskaloScraper(NjuskaloSitemapScraper):
    """Enhanced scraper with XML processing and vehicle counting capabilities."""

    def __init__(self, headless: bool = False, use_database: bool = True):
        """Initialize enhanced scraper."""
        super().__init__(headless, use_database)
        self.xml_available = True  # Track if XML is accessible

    def _should_fetch_from_xml(self) -> bool:
        """
        Check if we should fetch from XML or use existing database URLs.
        Returns True if database is empty or older than 2 weeks.

        Returns:
            bool: True if should fetch from XML, False if should use database
        """
        if not self.database:
            logger.warning("⚠️ No database connection - defaulting to XML fetch")
            return True

        try:
            latest_update = self.database.get_latest_update_timestamp()

            if latest_update is None:
                logger.info("📋 Database is empty - will fetch from XML")
                return True

            # Calculate age of latest update
            age = datetime.now() - latest_update
            two_weeks = timedelta(weeks=2)

            if age > two_weeks:
                logger.info(f"📅 Database is {age.days} days old (last update: {latest_update}) - will fetch from XML")
                return True
            else:
                logger.info(f"✅ Database is fresh ({age.days} days old, last update: {latest_update}) - using existing URLs")
                return False

        except Exception as e:
            logger.error(f"❌ Error checking database age: {e} - defaulting to XML fetch")
            return True

    def download_and_process_xml_sitemap(self) -> Tuple[List[str], bool]:
        """
        Download XML sitemap, compare with database, and find new URLs.
        Checks for local XML file first before attempting download.

        Returns:
            Tuple of (new_urls, xml_success)
        """
        logger.info("🔄 Starting XML sitemap processing...")

        try:
            # Check for local sitemap index first
            local_sitemap_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sitemap-index.xml')
            if os.path.exists(local_sitemap_path):
                logger.info(f"📁 Found local sitemap file: {local_sitemap_path}")
                try:
                    with open(local_sitemap_path, 'r', encoding='utf-8') as f:
                        sitemap_index_content = f.read()
                    logger.info("✅ Successfully loaded local sitemap index")
                except Exception as e:
                    logger.error(f"❌ Failed to read local sitemap file: {e}")
                    sitemap_index_content = None
            else:
                # No local file - download from web
                logger.info("🌐 No local sitemap found, downloading from web...")

                # Setup browser for XML download
                if not self.setup_browser():
                    logger.error("❌ Failed to setup browser for XML processing")
                    return [], False

                # Download sitemap index
                sitemap_index_content = self.download_sitemap_index()

            if not sitemap_index_content:
                logger.error("❌ Failed to get sitemap index")
                self.xml_available = False
                return [], False

            # Ensure browser is set up for downloading referenced sitemaps (even if using local index)
            if not self.driver:
                if not self.setup_browser():
                    logger.error("❌ Failed to setup browser for processing sitemaps")
                    return [], False

            # Get all store URLs from sitemaps
            all_store_urls = self._get_all_store_urls_from_sitemaps()
            if not all_store_urls:
                logger.error("❌ No store URLs found in XML sitemaps")
                self.xml_available = False
                return [], False

            logger.info(f"✅ Found {len(all_store_urls)} total URLs in XML sitemaps")

            # Compare with existing database URLs
            existing_urls = set()
            if self.use_database and self.database:
                existing_urls = self.database.get_existing_urls()
                logger.info(f"📊 Found {len(existing_urls)} existing URLs in database")

            # Find new URLs
            new_urls = [url for url in all_store_urls if url not in existing_urls]
            logger.info(f"🆕 Found {len(new_urls)} new URLs to process")

            # Add new URLs to database
            if new_urls and self.use_database and self.database:
                self._add_new_urls_to_database(new_urls)

            self.xml_available = True
            return new_urls, True

        except Exception as e:
            logger.error(f"❌ XML sitemap processing failed: {e}")
            self.xml_available = False
            return [], False

    def _add_new_urls_to_database(self, new_urls: List[str]) -> int:
        """Add new URLs to database with placeholder data."""
        added_count = 0

        for url in new_urls:
            placeholder_data = {
                'url': url,
                'name': None,
                'address': None,
                'ads_count': None,
                'has_auto_moto': False,  # Default to False, will be determined during scraping
                'categories': [],
                'new_vehicle_count': 0,
                'used_vehicle_count': 0,
                'test_vehicle_count': 0,
                'total_vehicle_count': 0,
                'scraped': False
            }

            success = self.database.save_store_data(
                url=url,
                store_data=placeholder_data,
                is_valid=True
            )

            if success:
                added_count += 1
            else:
                logger.warning(f"⚠️ Failed to add URL to database: {url}")

        logger.info(f"✅ Successfully added {added_count}/{len(new_urls)} new URLs to database")
        return added_count

    def check_auto_moto_category(self, store_url: str) -> bool:
        """
        Check if a store has Auto moto category on the page.

        Args:
            store_url: The store URL to check

        Returns:
            bool: True if store has auto moto category
        """
        try:
            logger.info(f"🔍 Checking auto moto category for: {store_url}")

            # Visit the store page without category filter first
            self.navigate_to(store_url)
            self.smart_sleep("page_load")

            # Wait for page to load (reduced timeout)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Look for auto moto indicators
            auto_moto_indicators = [
                # Category links
                'a[href*="categoryId=2"]',
                'a[href*="category=auto"]',
                'a[href*="category=moto"]',
                'a[href*="automobili"]',
                'a[href*="motocikli"]',

                # Text content indicators
                '.category-list',
                '.categories',
                '.store-categories',
                '.navigation',
                '.category-nav'
            ]

            # Check for auto moto links or text
            for selector in auto_moto_indicators:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text.lower() if hasattr(element, 'text') else ''
                        href = element.get_attribute('href') if hasattr(element, 'get_attribute') else ''

                        if any(keyword in text for keyword in ['auto', 'moto', 'vozil', 'automobil']):
                            logger.info(f"✅ Auto moto category found via text: {text[:50]}")
                            return True
                        if any(keyword in href for keyword in ['categoryId=2', 'auto', 'moto']):
                            logger.info(f"✅ Auto moto category found via link: {href}")
                            return True
                except:
                    continue

            # Check page source for category indicators
            try:
                page_source = self.driver.page_source.lower()
                if 'categoryid=2' in page_source or 'category=auto' in page_source:
                    logger.info("✅ Auto moto category found in page source")
                    return True
            except:
                pass

            # Try visiting with auto moto filter to see if it works
            try:
                filtered_url = self.add_car_category_filter(store_url)
                self.navigate_to(filtered_url)
                self.smart_sleep("page_load", 3, 8)

                # Check if we get results or error page
                page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()

                # Look for indicators that auto moto category exists
                if any(keyword in page_text for keyword in ['vozilo', 'automobil', 'moto', 'auto']):
                    # Check if there are actual listings
                    listing_indicators = [
                        '.entity-list',
                        '.ads-list',
                        '.listings',
                        '.search-results',
                        '.entity-item'
                    ]

                    for selector in listing_indicators:
                        try:
                            listings = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            if listings:
                                logger.info("✅ Auto moto category confirmed - found listings")
                                return True
                        except:
                            continue

            except Exception as e:
                logger.debug(f"Error checking filtered URL: {e}")

            logger.info("❌ No auto moto category found")
            return False

        except Exception as e:
            logger.error(f"❌ Error checking auto moto category: {e}")
            return False

    def count_vehicle_types(self, store_url: str) -> Dict[str, int]:
        """
        Count new, used, and test vehicles on a store page.

        Args:
            store_url: The store URL to analyze

        Returns:
            Dict with new_count, used_count, test_count, and total_count
        """
        vehicle_counts = {
            'new_vehicle_count': 0,
            'used_vehicle_count': 0,
            'test_vehicle_count': 0,
            'total_vehicle_count': 0
        }

        try:
            # Visit store with auto moto filter
            filtered_url = self.add_car_category_filter(store_url)
            logger.info(f"🚗 Counting vehicles for: {filtered_url}")

            self.navigate_to(filtered_url)
            self.smart_sleep("page_load")

            # Wait for page to load (reduced timeout)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Get page content for analysis
            page_source = self.driver.page_source
            page_text = self.driver.find_element(By.TAG_NAME, "body").text

            # Count "Novo vozilo" (New vehicle)
            new_vehicle_patterns = [
                r'novo\s+vozilo',
                r'new\s+vehicle',
                r'novo\s*vozilo',
                r'\bnovo\b.*\bvozilo\b'
            ]

            new_count = 0
            for pattern in new_vehicle_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                new_count += len(matches)

            # Also check in HTML source for more accurate counting
            new_html_patterns = [
                r'novo[\s\-_]*vozilo',
                r'new[\s\-_]*vehicle',
                r'condition["\']?[\s]*:[\s]*["\']?new',
                r'stanje["\']?[\s]*:[\s]*["\']?novo'
            ]

            for pattern in new_html_patterns:
                matches = re.findall(pattern, page_source, re.IGNORECASE)
                new_count += len(matches)

            # Count "Rabljeno vozilo" (Used vehicle)
            used_vehicle_patterns = [
                r'rabljeno\s+vozilo',
                r'used\s+vehicle',
                r'rabljeno\s*vozilo',
                r'\brabljeno\b.*\bvozilo\b',
                r'polovn[oia]\s*vozilo'
            ]

            used_count = 0
            for pattern in used_vehicle_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                used_count += len(matches)

            # Also check in HTML source
            used_html_patterns = [
                r'rabljeno[\s\-_]*vozilo',
                r'used[\s\-_]*vehicle',
                r'condition["\']?[\s]*:[\s]*["\']?used',
                r'stanje["\']?[\s]*:[\s]*["\']?rabljeno',
                r'polovn[oia][\s\-_]*vozilo'
            ]

            for pattern in used_html_patterns:
                matches = re.findall(pattern, page_source, re.IGNORECASE)
                used_count += len(matches)

            # Count "Testno vozilo" (Test/demo vehicle)
            test_vehicle_patterns = [
                r'testno\s+vozilo',
                r'testno\s*vozilo',
                r'\btestno\b.*\bvozilo\b'
            ]

            test_count = 0
            for pattern in test_vehicle_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                test_count += len(matches)

            test_html_patterns = [
                r'testno[\s\-_]*vozilo',
                r'condition["\']?[\s]*:[\s]*["\']?test',
                r'stanje["\']?[\s]*:[\s]*["\']?testno'
            ]

            for pattern in test_html_patterns:
                matches = re.findall(pattern, page_source, re.IGNORECASE)
                test_count += len(matches)

            # Try to extract from listing elements directly
            try:
                # Look for individual vehicle listings
                listing_selectors = [
                    '.entity-item',
                    '.ad-item',
                    '.listing-item',
                    '.search-result',
                    '.vehicle-item'
                ]

                for selector in listing_selectors:
                    listings = self.driver.find_elements(By.CSS_SELECTOR, selector)

                    listing_new_count = 0
                    listing_used_count = 0
                    listing_test_count = 0

                    for listing in listings:
                        try:
                            listing_text = listing.text.lower()
                            listing_html = listing.get_attribute('innerHTML').lower()

                            # Check for new vehicle indicators
                            if any(keyword in listing_text for keyword in ['novo vozilo', 'new vehicle']):
                                listing_new_count += 1
                            elif any(keyword in listing_html for keyword in ['novo', 'new']):
                                listing_new_count += 1

                            # Check for used vehicle indicators
                            if any(keyword in listing_text for keyword in ['rabljeno vozilo', 'used vehicle', 'polovno']):
                                listing_used_count += 1
                            elif any(keyword in listing_html for keyword in ['rabljeno', 'used', 'polovno']):
                                listing_used_count += 1

                            # Check for test vehicle indicators
                            if 'testno vozilo' in listing_text:
                                listing_test_count += 1
                            elif 'testno' in listing_html:
                                listing_test_count += 1

                        except:
                            continue

                    # Use listing counts if they seem more accurate
                    if listing_new_count > 0 or listing_used_count > 0 or listing_test_count > 0:
                        new_count = max(new_count, listing_new_count)
                        used_count = max(used_count, listing_used_count)
                        test_count = max(test_count, listing_test_count)
                        break

            except Exception as e:
                logger.debug(f"Error counting from listings: {e}")

            # Clean up counts (cap at reasonable number)
            vehicle_counts['new_vehicle_count'] = min(new_count, 100)
            vehicle_counts['used_vehicle_count'] = min(used_count, 100)
            vehicle_counts['test_vehicle_count'] = min(test_count, 100)
            vehicle_counts['total_vehicle_count'] = (
                vehicle_counts['new_vehicle_count']
                + vehicle_counts['used_vehicle_count']
                + vehicle_counts['test_vehicle_count']
            )

            logger.info(
                f"🚗 Vehicle counts - New: {vehicle_counts['new_vehicle_count']}, "
                f"Used: {vehicle_counts['used_vehicle_count']}, "
                f"Test: {vehicle_counts['test_vehicle_count']}, "
                f"Total: {vehicle_counts['total_vehicle_count']}"
            )

            return vehicle_counts

        except Exception as e:
            logger.error(f"❌ Error counting vehicle types: {e}")
            return vehicle_counts

    def scrape_store_with_vehicle_counting(self, store_url: str) -> Optional[Dict]:
        """
        Enhanced store scraping with auto moto detection and vehicle counting.

        Args:
            store_url: The store URL to scrape

        Returns:
            Dict containing store data with vehicle counts
        """
        try:
            logger.info(f"🏪 Scraping store with vehicle counting: {store_url}")

            # First check if store has auto moto category
            has_auto_moto = self.check_auto_moto_category(store_url)

            # Start with basic store data
            store_data = {
                'url': store_url,
                'name': None,
                'address': None,
                'ads_count': None,
                'has_auto_moto': has_auto_moto,
                'categories': [],
                'new_vehicle_count': 0,
                'used_vehicle_count': 0,
                'test_vehicle_count': 0,
                'total_vehicle_count': 0,
                'scraped': True,
                'error': None
            }

            # If no auto moto category, return early
            if not has_auto_moto:
                logger.info(f"⏭️ Skipping detailed scraping - no auto moto category: {store_url}")
                return store_data

            # Scrape basic store info (name, address, etc.)
            basic_store_data = self.scrape_store_info(store_url)
            if basic_store_data:
                store_data.update({
                    'name': basic_store_data.get('name'),
                    'address': basic_store_data.get('address'),
                    'ads_count': basic_store_data.get('ads_count'),
                    'categories': basic_store_data.get('categories', [])
                })

            # Count vehicle types for auto moto stores
            vehicle_counts = self.count_vehicle_types(store_url)
            store_data.update(vehicle_counts)

            logger.info(f"✅ Successfully scraped store: {store_data['name'] or 'Unknown'} - Auto moto: {has_auto_moto}, Vehicles: {store_data['total_vehicle_count']}")

            return store_data

        except Exception as e:
            logger.error(f"❌ Error scraping store {store_url}: {e}")
            return {
                'url': store_url,
                'error': str(e),
                'has_auto_moto': False,
                'scraped': True,
                'new_vehicle_count': 0,
                'used_vehicle_count': 0,
                'test_vehicle_count': 0,
                'total_vehicle_count': 0
            }

    def run_enhanced_scrape(self, max_stores: int = None) -> Dict[str, any]:
        """
        Run the enhanced scraping workflow.

        Args:
            max_stores: Maximum number of stores to scrape

        Returns:
            Dict containing scraping results and statistics
        """
        results = {
            'xml_available': False,
            'new_urls_found': 0,
            'stores_scraped': 0,
            'auto_moto_stores': 0,
            'new_vehicles': 0,
            'used_vehicles': 0,
            'test_vehicles': 0,
            'total_vehicles': 0,
            'errors': []
        }

        try:
            logger.info("🚀 Starting enhanced Njuskalo scraping workflow")

            # Initialize database
            if self.use_database:
                try:
                    self.database = NjuskaloDatabase()
                    self.database.connect()
                    self.database.create_tables()
                    # Ensure all columns and tables exist
                    self.database.migrate_add_is_automoto_column()
                    self.database.migrate_add_store_snapshots_table()
                    logger.info("✅ Database initialized successfully")
                except Exception as e:
                    logger.error(f"❌ Database initialization failed: {e}")
                    results['errors'].append(f"Database error: {e}")
                    return results

            # Step 1: Check if we should fetch from XML or use database
            should_fetch_xml = self._should_fetch_from_xml()

            new_urls = []
            xml_success = False

            if should_fetch_xml:
                # Database is empty or old - fetch from XML
                new_urls, xml_success = self.download_and_process_xml_sitemap()
                results['xml_available'] = xml_success
                results['new_urls_found'] = len(new_urls)

                if not xml_success:
                    logger.warning("⚠️ XML sitemap unavailable - falling back to database URLs")
            else:
                # Database is fresh - skip XML processing
                logger.info("⏭️ Skipping XML processing - using fresh database URLs")
                results['xml_available'] = False  # Didn't fetch XML
                results['new_urls_found'] = 0  # No new URLs from XML

            # Step 2: Determine which URLs to scrape
            urls_to_scrape = []

            if xml_success and new_urls:
                # XML available - scrape new URLs
                urls_to_scrape = new_urls
                logger.info(f"📋 Will scrape {len(new_urls)} new URLs from XML")
            else:
                # XML unavailable or no new URLs or database is fresh - scrape from database
                if self.database:
                    # Get URLs marked as auto moto for re-scraping
                    auto_moto_urls = self.database.get_auto_moto_urls()
                    if auto_moto_urls:
                        urls_to_scrape = auto_moto_urls
                        logger.info(f"📋 Will scrape {len(auto_moto_urls)} auto moto URLs from database")
                    else:
                        # Bootstrap case: DB has URLs but none classified as auto moto yet.
                        # Scrape valid non-auto rows to discover auto moto stores.
                        non_auto_rows = self.database.get_non_auto_moto_stores()
                        urls_to_scrape = [row['url'] for row in non_auto_rows]
                        logger.warning(
                            "⚠️ No auto moto URLs in database yet - bootstrapping from "
                            f"{len(urls_to_scrape)} valid non-auto URLs"
                        )

            if not urls_to_scrape:
                logger.warning("⚠️ No URLs to scrape found")
                return results

            # Limit URLs if specified
            if max_stores and len(urls_to_scrape) > max_stores:
                urls_to_scrape = urls_to_scrape[:max_stores]
                logger.info(f"📊 Limited to {len(urls_to_scrape)} stores for testing")

            # Step 3: Scrape stores
            for i, store_url in enumerate(urls_to_scrape, 1):
                try:
                    logger.info(f"🔄 Scraping store {i}/{len(urls_to_scrape)}: {store_url}")

                    # Scrape store with vehicle counting
                    store_data = self.scrape_store_with_vehicle_counting(store_url)

                    if store_data:
                        # Capture counts before save_store_data pops them from the dict
                        snap_new  = store_data.get('new_vehicle_count', 0)
                        snap_used = store_data.get('used_vehicle_count', 0)
                        snap_test = store_data.get('test_vehicle_count', 0)
                        is_automoto = store_data.get('has_auto_moto', False)

                        # Save to database
                        if self.database:
                            success = self.database.save_store_data(
                                url=store_url,
                                store_data=store_data,
                                is_valid=True
                            )

                            if success:
                                results['stores_scraped'] += 1

                                if is_automoto:
                                    results['auto_moto_stores'] += 1
                                    results['new_vehicles'] += snap_new
                                    results['used_vehicles'] += snap_used
                                    results['test_vehicles'] += snap_test
                                    results['total_vehicles'] += snap_new + snap_used + snap_test

                                # Record snapshot for active/sold tracking
                                self.database.save_store_snapshot(
                                    url=store_url,
                                    active_new=snap_new,
                                    active_used=snap_used,
                                    active_test=snap_test,
                                )

                        # Add delay between stores
                        self.smart_sleep("store_visit")

                    else:
                        logger.warning(f"⚠️ No data retrieved for store: {store_url}")

                except Exception as e:
                    logger.error(f"❌ Error scraping store {store_url}: {e}")
                    results['errors'].append(f"Store {store_url}: {e}")

                    # Mark as invalid in database
                    if self.database:
                        self.database.mark_url_invalid(store_url)

            # Step 4: Final statistics
            logger.info("📊 Scraping completed - Final statistics:")
            logger.info(f"   🌐 XML Available: {results['xml_available']}")
            logger.info(f"   🆕 New URLs Found: {results['new_urls_found']}")
            logger.info(f"   🏪 Stores Scraped: {results['stores_scraped']}")
            logger.info(f"   🚗 Auto Moto Stores: {results['auto_moto_stores']}")
            logger.info(f"   🆕 New Vehicles: {results['new_vehicles']}")
            logger.info(f"   🔄 Used Vehicles: {results['used_vehicles']}")
            logger.info(f"   🧪 Test Vehicles: {results['test_vehicles']}")
            logger.info(f"   📈 Total Vehicles: {results['total_vehicles']}")
            logger.info(f"   ❌ Errors: {len(results['errors'])}")

            return results

        except Exception as e:
            logger.error(f"❌ Enhanced scraping workflow failed: {e}")
            results['errors'].append(f"Workflow error: {e}")
            return results

        finally:
            # Cleanup
            if self.driver:
                self.driver.quit()
            if self.database:
                self.database.disconnect()


# Add helper method to database class for getting auto moto URLs
def get_auto_moto_urls(self) -> List[str]:
    """Get URLs of stores marked as having auto moto category."""
    try:
        rows = self.connection.execute(
            """
            SELECT url FROM scraped_stores
            WHERE is_automoto = 1 AND is_valid = 1
            ORDER BY updated_at DESC
            """
        ).fetchall()
        return [row['url'] for row in rows]
    except Exception as e:
        self.logger.error(f"Error getting auto moto URLs: {e}")
        return []

# Monkey patch the method to NjuskaloDatabase class
NjuskaloDatabase.get_auto_moto_urls = get_auto_moto_urls


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Enhanced Njuskalo Scraper")
    parser.add_argument("--max-stores", type=int, help="Maximum number of stores to scrape")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Create and run enhanced scraper
    scraper = EnhancedNjuskaloScraper(headless=args.headless or False)
    results = scraper.run_enhanced_scrape(max_stores=args.max_stores)

    print("\\n" + "="*60)
    print("🏁 ENHANCED SCRAPING RESULTS")
    print("="*60)
    print(f"XML Available: {'✅' if results['xml_available'] else '❌'}")
    print(f"New URLs Found: {results['new_urls_found']}")
    print(f"Stores Scraped: {results['stores_scraped']}")
    print(f"Auto Moto Stores: {results['auto_moto_stores']}")
    print(f"New Vehicles: {results['new_vehicles']}")
    print(f"Used Vehicles: {results['used_vehicles']}")
    print(f"Test Vehicles: {results['test_vehicles']}")
    print(f"Total Vehicles: {results['total_vehicles']}")
    print(f"Errors: {len(results['errors'])}")
    print("="*60)