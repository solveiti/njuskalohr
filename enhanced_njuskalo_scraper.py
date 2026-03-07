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
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
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

    def _normalize_auto_moto_url(self, href: str) -> str:
        """Normalize Auto Moto URL so it explicitly contains categoryId=2."""
        parsed = urlparse(href)
        query_pairs = [
            (k, v)
            for (k, v) in parse_qsl(parsed.query, keep_blank_values=True)
            if k.lower() not in ('categoryid', 'category_id')
        ]
        query_pairs.append(('categoryId', '2'))
        new_query = urlencode(query_pairs)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))

    def _parse_count_from_text(self, text: str) -> Optional[int]:
        """Parse integer ad count from text like 'Auto moto 1.234'."""
        if not text:
            return None

        match = re.search(r'(\d[\d\.\s]*)', text)
        if not match:
            return None

        digits_only = re.sub(r'\D', '', match.group(1))
        if not digits_only:
            return None

        try:
            return int(digits_only)
        except ValueError:
            return None

    def _extract_auto_moto_category_info(self, store_url: str) -> Optional[Dict[str, Optional[int]]]:
        """
        Extract Auto Moto link info from store page.

        Returns:
            {
                'url': '<auto moto url normalized to categoryId=2>',
                'total_ads': <count from link text or None>
            }
        """
        try:
            if not self.driver:
                return None

            link_selectors = [
                'a[href*="categoryId=2"]',
                'a[href*="category_id=2"]',
                'a[href*="categoryid=2"]',
                'a'
            ]

            seen_hrefs = set()
            for selector in link_selectors:
                try:
                    links = self.driver.find_elements(By.CSS_SELECTOR, selector)
                except Exception:
                    links = []

                for link in links:
                    try:
                        href = (link.get_attribute('href') or '').strip()
                        if not href or href in seen_hrefs:
                            continue
                        seen_hrefs.add(href)

                        link_text = (link.text or '').strip().lower()
                        text_content = (link.get_attribute('textContent') or '').strip().lower()
                        if 'auto moto' not in link_text and 'auto moto' not in text_content:
                            continue

                        href_lower = href.lower()
                        if 'categoryid=2' not in href_lower and 'category_id=2' not in href_lower:
                            continue

                        normalized_url = self._normalize_auto_moto_url(href)
                        total_ads = self._parse_count_from_text(link.get_attribute('textContent') or link.text or '')

                        logger.info(
                            f"✅ Auto Moto link detected: {normalized_url} "
                            f"(total near link: {total_ads if total_ads is not None else 'unknown'})"
                        )
                        return {'url': normalized_url, 'total_ads': total_ads}
                    except Exception:
                        continue

            return None
        except Exception as e:
            logger.debug(f"Auto Moto link extraction failed for {store_url}: {e}")
            return None

    def _extract_auto_moto_category_url(self, store_url: str) -> Optional[str]:
        """Backward-compatible helper that returns only Auto Moto URL."""
        info = self._extract_auto_moto_category_info(store_url)
        return info.get('url') if info else None

    def _build_paginated_url(self, base_url: str, page: int) -> str:
        """Build paginated URL by setting/replacing the `page` query parameter."""
        parsed = urlparse(base_url)
        query_pairs = [(k, v) for (k, v) in parse_qsl(parsed.query, keep_blank_values=True) if k.lower() != 'page']
        query_pairs.append(('page', str(page)))
        new_query = urlencode(query_pairs)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))

    def _count_vehicle_types_on_current_page(self) -> Dict[str, int]:
        """
        Count new/used/test ads on current page using listing flags.
        One listing contributes to at most one type bucket.
        """
        page_counts = {
            'new_vehicle_count': 0,
            'used_vehicle_count': 0,
            'test_vehicle_count': 0,
            'total_vehicle_count': 0,
            'unclassified_count': 0
        }

        listing_selectors = [
            '.entity-item',
            '.ad-item',
            '.listing-item',
            '[data-testid="ad-item"]',
            '.classified-item'
        ]

        listings = []
        for selector in listing_selectors:
            try:
                listings = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if listings:
                    break
            except Exception:
                continue

        # Fallback: try global flag scan if listing wrappers are not found.
        if not listings:
            try:
                flag_elements = self.driver.find_elements(By.CSS_SELECTOR, 'li.entity-flag span.flag')
                for flag in flag_elements:
                    flag_text = (flag.text or '').strip().lower()
                    if 'testno vozilo' in flag_text:
                        page_counts['test_vehicle_count'] += 1
                    elif 'novo vozilo' in flag_text:
                        page_counts['new_vehicle_count'] += 1
                    elif 'rabljeno vozilo' in flag_text or 'polovno vozilo' in flag_text:
                        page_counts['used_vehicle_count'] += 1
            except Exception:
                pass

            page_counts['total_vehicle_count'] = (
                page_counts['new_vehicle_count']
                + page_counts['used_vehicle_count']
                + page_counts['test_vehicle_count']
            )
            return page_counts

        for listing in listings:
            try:
                listing_text = (listing.text or '').lower()
                listing_html = (listing.get_attribute('innerHTML') or '').lower()
                flag_texts = []
                classified = False

                try:
                    flags = listing.find_elements(By.CSS_SELECTOR, 'li.entity-flag span.flag, .entity-flag span.flag, .entity-flag, .flag')
                    flag_texts = [(flag.text or '').lower() for flag in flags if (flag.text or '').strip()]
                except Exception:
                    flag_texts = []

                searchable = ' '.join(flag_texts) if flag_texts else listing_text

                if 'testno vozilo' in searchable:
                    page_counts['test_vehicle_count'] += 1
                    classified = True
                elif 'novo vozilo' in searchable:
                    page_counts['new_vehicle_count'] += 1
                    classified = True
                elif 'rabljeno vozilo' in searchable or 'polovno vozilo' in searchable:
                    page_counts['used_vehicle_count'] += 1
                    classified = True

                if not classified:
                    html_searchable = f"{listing_text} {listing_html}"
                    if 'testno vozilo' in html_searchable:
                        page_counts['test_vehicle_count'] += 1
                        classified = True
                    elif 'novo vozilo' in html_searchable:
                        page_counts['new_vehicle_count'] += 1
                        classified = True
                    elif 'rabljeno vozilo' in html_searchable or 'polovno vozilo' in html_searchable:
                        page_counts['used_vehicle_count'] += 1
                        classified = True

                if not classified:
                    page_counts['unclassified_count'] += 1
            except Exception:
                continue

        page_counts['total_vehicle_count'] = len(listings)
        return page_counts

    def _has_next_page(self, current_page: int) -> bool:
        """Detect if pagination indicates a next page exists."""
        next_selectors = [
            '.Pagination .next:not(.disabled)',
            '.Pagination .page-next:not(.disabled)',
            '.pagination .next:not(.disabled)',
            '.pagination .page-next:not(.disabled)',
            'a[aria-label="Next"]:not([disabled])',
            '.pager .next:not(.disabled)',
            '[data-testid="next-page"]:not([disabled])'
        ]

        for selector in next_selectors:
            try:
                next_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in next_elements:
                    classes = (element.get_attribute('class') or '').lower()
                    if element.is_enabled() and 'disabled' not in classes:
                        return True
            except Exception:
                continue

        # Numeric pagination fallback: if there is a link/button for current_page + 1
        try:
            next_page_num = str(current_page + 1)
            candidates = self.driver.find_elements(By.CSS_SELECTOR, '.Pagination a, .Pagination button, .pagination a, .pagination button, .pager a, .pager button')
            for candidate in candidates:
                text = (candidate.text or '').strip()
                if text == next_page_num:
                    return True
        except Exception:
            pass

        return False

    def _get_last_pagination_page(self) -> int:
        """Get last page number from Pagination controls."""
        try:
            elements = self.driver.find_elements(
                By.CSS_SELECTOR,
                '.Pagination a, .Pagination button, .pagination a, .pagination button, .pager a, .pager button'
            )
            pages = []
            for element in elements:
                text = (element.text or '').strip()
                if text.isdigit():
                    pages.append(int(text))
            return max(pages) if pages else 1
        except Exception:
            return 1

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

            if not self.driver:
                logger.warning("⚠️ Browser driver missing before auto moto check, reinitializing...")
                if not self.setup_browser():
                    raise RuntimeError("Browser initialization failed before auto moto check")

            # Visit the store page without category filter first
            if not self.navigate_to(store_url):
                raise RuntimeError(f"Navigation failed for {store_url}")
            self.smart_sleep("page_load")

            # Wait for page to load (reduced timeout)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Strict requirement: must have explicit Auto Moto link with categoryId=2
            auto_moto_info = self._extract_auto_moto_category_info(store_url)
            if auto_moto_info and auto_moto_info.get('url'):
                return True

            logger.info("❌ No valid Auto Moto link (categoryId=2) found on store page")
            return False

        except Exception as e:
            logger.error(f"❌ Error checking auto moto category: {e}")
            raise

    def count_vehicle_types(self, store_url: str) -> Dict[str, int]:
        """
        Count new, used, and test vehicles on a store page.

        Args:
            store_url: The store URL to analyze

        Returns:
            Dict with new_count, used_count, test_count, and total_count
        """
        empty_counts = {
            'new_vehicle_count': 0,
            'used_vehicle_count': 0,
            'test_vehicle_count': 0,
            'total_vehicle_count': 0
        }

        try:
            # Resolve Auto Moto category URL from the store page first.
            # This enforces that counting only happens for explicit Auto Moto category links.
            if not self.navigate_to(store_url):
                raise RuntimeError(f"Navigation failed for store URL: {store_url}")

            self.smart_sleep("page_load")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            auto_moto_info = self._extract_auto_moto_category_info(store_url)
            if not auto_moto_info:
                logger.info(f"⏭️ Skipping vehicle count - no Auto Moto category link found: {store_url}")
                return empty_counts

            auto_moto_url = auto_moto_info['url']
            expected_total_ads = auto_moto_info.get('total_ads')

            logger.info(f"🚗 Counting vehicles via Auto Moto pagination: {auto_moto_url}")

            max_recount_attempts = 3
            last_counts = dict(empty_counts)

            for attempt in range(1, max_recount_attempts + 1):
                vehicle_counts = {
                    'new_vehicle_count': 0,
                    'used_vehicle_count': 0,
                    'test_vehicle_count': 0,
                    'total_vehicle_count': 0
                }

                # Restart counting for this store from page 1 on each attempt
                first_page_url = self._build_paginated_url(auto_moto_url, 1)
                if not self.navigate_to(first_page_url):
                    logger.warning("⚠️ Failed to navigate to first Auto Moto page")
                    return empty_counts

                self.smart_sleep("pagination")
                WebDriverWait(self.driver, 8).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )

                max_pages = self._get_last_pagination_page()
                max_pages = max(1, min(max_pages, 150))
                logger.info(f"📚 Pagination detected: {max_pages} page(s) [attempt {attempt}/{max_recount_attempts}]")

                for page in range(1, max_pages + 1):
                    if page > 1:
                        paginated_url = self._build_paginated_url(auto_moto_url, page)
                        logger.debug(f"📄 Counting page {page}: {paginated_url}")

                        if not self.navigate_to(paginated_url):
                            logger.warning(f"⚠️ Failed to navigate to page {page}, stopping pagination")
                            break

                        self.smart_sleep("pagination")

                        try:
                            WebDriverWait(self.driver, 8).until(
                                EC.presence_of_element_located((By.TAG_NAME, "body"))
                            )
                        except TimeoutException:
                            logger.warning(f"⚠️ Timed out loading page {page}, stopping pagination")
                            break

                    page_counts = self._count_vehicle_types_on_current_page()
                    unclassified = page_counts.get('unclassified_count', 0)
                    if unclassified > 0:
                        page_counts['used_vehicle_count'] += unclassified

                    vehicle_counts['new_vehicle_count'] += page_counts['new_vehicle_count']
                    vehicle_counts['used_vehicle_count'] += page_counts['used_vehicle_count']
                    vehicle_counts['test_vehicle_count'] += page_counts['test_vehicle_count']

                    logger.info(
                        f"📄 Page {page}: new={page_counts['new_vehicle_count']}, "
                        f"used={page_counts['used_vehicle_count']}, "
                        f"test={page_counts['test_vehicle_count']}, "
                        f"ads={page_counts['total_vehicle_count']}"
                        + (f", fallback_used+={unclassified}" if unclassified > 0 else "")
                    )

                    if page_counts['total_vehicle_count'] == 0:
                        logger.info(f"⏹️ Stopping at page {page}: no ads found")
                        break

                categorized_total = (
                    vehicle_counts['new_vehicle_count']
                    + vehicle_counts['used_vehicle_count']
                    + vehicle_counts['test_vehicle_count']
                )

                if expected_total_ads is None:
                    vehicle_counts['total_vehicle_count'] = categorized_total
                    logger.info(
                        f"🚗 Vehicle counts - New: {vehicle_counts['new_vehicle_count']}, "
                        f"Used: {vehicle_counts['used_vehicle_count']}, "
                        f"Test: {vehicle_counts['test_vehicle_count']}, "
                        f"Total: {vehicle_counts['total_vehicle_count']}"
                    )
                    return vehicle_counts

                if categorized_total == expected_total_ads:
                    vehicle_counts['total_vehicle_count'] = expected_total_ads
                    logger.info(
                        f"✅ Vehicle totals matched on attempt {attempt}/{max_recount_attempts}: "
                        f"{categorized_total}/{expected_total_ads}"
                    )
                    logger.info(
                        f"🚗 Vehicle counts - New: {vehicle_counts['new_vehicle_count']}, "
                        f"Used: {vehicle_counts['used_vehicle_count']}, "
                        f"Test: {vehicle_counts['test_vehicle_count']}, "
                        f"Total: {vehicle_counts['total_vehicle_count']}"
                    )
                    return vehicle_counts

                last_counts = dict(vehicle_counts)
                logger.warning(
                    f"⚠️ Mismatch on attempt {attempt}/{max_recount_attempts}: "
                    f"categorized={categorized_total}, expected={expected_total_ads}. "
                    "Restarting store ad count from page 1."
                )
                self.smart_sleep("store_visit")

            # Final fallback after retries: keep expected total aligned for downstream DB stats
            categorized_total = (
                last_counts['new_vehicle_count']
                + last_counts['used_vehicle_count']
                + last_counts['test_vehicle_count']
            )
            delta = expected_total_ads - categorized_total
            if delta > 0:
                last_counts['used_vehicle_count'] += delta
            elif delta < 0:
                to_remove = abs(delta)
                for key in ('used_vehicle_count', 'new_vehicle_count', 'test_vehicle_count'):
                    if to_remove <= 0:
                        break
                    removable = min(last_counts[key], to_remove)
                    last_counts[key] -= removable
                    to_remove -= removable

            last_counts['total_vehicle_count'] = expected_total_ads
            logger.warning(
                f"⚠️ Store recount failed after {max_recount_attempts} attempts; "
                "applied final reconciliation to expected Auto Moto total."
            )
            return last_counts

        except Exception as e:
            logger.error(f"❌ Error counting vehicle types: {e}")
            return empty_counts

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
                'scraped': False,
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

            # Step 1: Always compare XML vs DB and capture only newly added store URLs
            new_urls, xml_success = self.download_and_process_xml_sitemap()
            results['xml_available'] = xml_success
            results['new_urls_found'] = len(new_urls)

            if not xml_success:
                logger.warning("⚠️ XML sitemap unavailable - cannot determine newly added stores")
                return results

            # Ensure browser is initialized before any store navigation.
            if not self.driver:
                logger.info("🌐 Initializing browser for store scraping...")
                if not self.setup_browser():
                    error_msg = "Failed to initialize browser before store scraping"
                    logger.error(f"❌ {error_msg}")
                    results['errors'].append(error_msg)
                    return results

            def process_store_batch(store_urls: List[str], phase_name: str, update_summary: bool) -> None:
                """Process a batch of stores, optionally updating final summary counters."""
                self._scrape_phase = phase_name
                for i, store_url in enumerate(store_urls, 1):
                    try:
                        logger.info(f"🔄 [{phase_name}] Scraping store {i}/{len(store_urls)}: {store_url}")

                        if not self.driver:
                            logger.warning("⚠️ Browser driver missing before store scrape, reinitializing...")
                            if not self.setup_browser():
                                error_msg = f"Browser unavailable for store scrape: {store_url}"
                                logger.error(f"❌ {error_msg}")
                                results['errors'].append(error_msg)
                                continue

                        store_data = self.scrape_store_with_vehicle_counting(store_url)

                        if not store_data:
                            logger.warning(f"⚠️ No data retrieved for store: {store_url}")
                            continue

                        if store_data.get('error'):
                            logger.error(f"❌ Store scrape failed for {store_url}: {store_data['error']}")
                            results['errors'].append(f"Store {store_url}: {store_data['error']}")
                            continue

                        snap_new = store_data.get('new_vehicle_count', 0)
                        snap_used = store_data.get('used_vehicle_count', 0)
                        snap_test = store_data.get('test_vehicle_count', 0)
                        is_automoto = store_data.get('has_auto_moto', False)

                        if self.database:
                            success = self.database.save_store_data(
                                url=store_url,
                                store_data=store_data,
                                is_valid=True
                            )

                            if success:
                                self.database.save_store_snapshot(
                                    url=store_url,
                                    active_new=snap_new,
                                    active_used=snap_used,
                                    active_test=snap_test,
                                )

                                if update_summary:
                                    results['stores_scraped'] += 1
                                    if is_automoto:
                                        results['auto_moto_stores'] += 1
                                        results['new_vehicles'] += snap_new
                                        results['used_vehicles'] += snap_used
                                        results['test_vehicles'] += snap_test
                                        results['total_vehicles'] += snap_new + snap_used + snap_test

                        self.smart_sleep("store_visit")

                    except Exception as e:
                        logger.error(f"❌ Error scraping store {store_url}: {e}")
                        results['errors'].append(f"Store {store_url}: {e}")
                        if self.database:
                            self.database.mark_url_invalid(store_url)
                self._scrape_phase = None

            # Step 2: Scrape newly added stores first to classify which of them are auto stores.
            new_urls_to_classify = list(new_urls)
            random.shuffle(new_urls_to_classify)
            if new_urls_to_classify:
                logger.info(
                    f"📋 Phase 1 - classify new stores: {len(new_urls_to_classify)} URL(s) "
                    "(randomized order)"
                )
                process_store_batch(new_urls_to_classify, "new-store-classification", update_summary=False)
            else:
                logger.info("ℹ️ No newly added stores found in XML compared to DB")

            # Step 3: Scrape all auto stores in randomized order to reduce detection risk.
            auto_store_urls = self.database.get_auto_moto_urls() if self.database else []
            random.shuffle(auto_store_urls)

            if max_stores and len(auto_store_urls) > max_stores:
                auto_store_urls = auto_store_urls[:max_stores]
                logger.info(f"📊 Limited auto-store scraping to {len(auto_store_urls)} stores for testing")

            if not auto_store_urls:
                logger.warning("⚠️ No auto moto store URLs found after new-store classification")
                return results

            logger.info(
                f"📋 Phase 2 - scrape all auto stores: {len(auto_store_urls)} URL(s) "
                "(randomized order)"
            )
            process_store_batch(auto_store_urls, "auto-store-full-scrape", update_summary=True)

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