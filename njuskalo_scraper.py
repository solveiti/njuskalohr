#!/usr/bin/env python3
"""
Njuskalo Car Scraper

This script scrapes car listings from njuskalo.hr using Selenium WebDriver
with Firefox browser, mimicking normal user behavior to avoid detection.
"""

import time
import random
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.firefox import GeckoDriverManager
import requests
from urllib.parse import urljoin
import logging
from typing import List, Dict, Optional
import tempfile


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AntiDetectionMixin:
    """Enhanced anti-detection methods for the regular scraper."""

    def smart_delay(self, min_seconds: float = 5.0, max_seconds: float = 12.0,
                   operation_type: str = "general") -> None:
        """Smart delay system with operation-specific timings."""
        delay_profiles = {
            "general": (5.0, 12.0),
            "page_load": (6.0, 15.0),
            "car_processing": (2.0, 6.0),
            "navigation": (8.0, 18.0),
            "error_recovery": (20.0, 40.0)
        }

        if operation_type in delay_profiles:
            min_delay, max_delay = delay_profiles[operation_type]
        else:
            min_delay, max_delay = min_seconds, max_seconds

        # Triangular distribution for more natural delays
        delay = random.triangular(min_delay, max_delay, (min_delay + max_delay) / 2)

        # 4% chance of extended delay for stealth
        if random.random() < 0.04:
            delay += random.uniform(15, 30)
            logger.info(f"Extended stealth delay: {delay:.1f}s")

        logger.debug(f"Smart delay: {delay:.1f}s for {operation_type}")
        time.sleep(delay)

    def enhanced_user_agent_rotation(self) -> str:
        """Return randomized Firefox user agent strings."""
        user_agents = [
            "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:119.0) Gecko/20100101 Firefox/119.0",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0"
        ]
        return random.choice(user_agents)

    def simulate_human_behavior(self) -> None:
        """Comprehensive human behavior simulation."""
        try:
            if hasattr(self, 'driver') and self.driver:
                # Random mouse movements
                from selenium.webdriver.common.action_chains import ActionChains
                actions = ActionChains(self.driver)
                window_size = self.driver.get_window_size()

                # Multiple movements with varying speeds
                for _ in range(random.randint(3, 7)):
                    x = random.randint(50, window_size['width'] - 50)
                    y = random.randint(50, window_size['height'] - 50)

                    try:
                        body = self.driver.find_element(By.TAG_NAME, "body")
                        actions.move_to_element_with_offset(body, x, y).perform()
                        time.sleep(random.uniform(0.1, 0.8))
                    except Exception:
                        break

                # Enhanced scrolling patterns
                self.advanced_scroll_simulation()

        except Exception as e:
            logger.debug(f"Human behavior simulation failed: {e}")

    def advanced_scroll_simulation(self) -> None:
        """Advanced scrolling patterns that mimic real user behavior."""
        try:
            if hasattr(self, 'driver') and self.driver:
                # Multi-phase scrolling
                for phase in range(random.randint(2, 4)):
                    scroll_distance = random.randint(300, 800)
                    self.driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
                    time.sleep(random.uniform(0.5, 2.0))

                # Occasional backwards scrolling
                if random.random() > 0.5:
                    back_distance = random.randint(100, 400)
                    self.driver.execute_script(f"window.scrollBy(0, -{back_distance});")
                    time.sleep(random.uniform(0.3, 1.5))

                # Random scroll to top
                if random.random() > 0.7:
                    self.driver.execute_script("window.scrollTo(0, 0);")
                    time.sleep(random.uniform(0.5, 2.0))

        except Exception as e:
            logger.debug(f"Advanced scroll failed: {e}")


class NjuskaloCarScraper(AntiDetectionMixin):
    """Web scraper for Njuskalo car listings with human-like behavior simulation."""

    def __init__(self, headless: bool = True):
        """
        Initialize the scraper with Firefox WebDriver.

        Args:
            headless: Whether to run Firefox in headless mode
        """
        self.driver = None
        self.base_url = "https://www.njuskalo.hr"
        self.cars_url = "https://www.njuskalo.hr/auti?page=4"
        self.headless = headless
        self.setup_driver()

    def setup_driver(self) -> None:
        """Set up Firefox WebDriver with enhanced anti-detection options."""
        firefox_options = Options()

        # Create unique temporary profile directory
        profile_dir = tempfile.mkdtemp()

        # Enhanced anti-detection preferences
        firefox_options.set_preference("dom.webdriver.enabled", False)
        firefox_options.set_preference("useAutomationExtension", False)
        firefox_options.set_preference("general.platform.override", "Linux x86_64")
        firefox_options.set_preference("general.appversion.override", "5.0 (X11)")

        # Set user agent
        firefox_options.set_preference("general.useragent.override", self.enhanced_user_agent_rotation())

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

        if self.headless:
            firefox_options.add_argument("--headless")

        # Randomized window size for better stealth
        width = random.randint(1366, 1920)
        height = random.randint(768, 1080)
        firefox_options.add_argument(f"--width={width}")
        firefox_options.add_argument(f"--height={height}")

        try:
            # Use webdriver-manager to automatically download and manage GeckoDriver
            service = Service(GeckoDriverManager().install())
            self.driver = webdriver.Firefox(service=service, options=firefox_options)

            # Set window size programmatically as well
            self.driver.set_window_size(width, height)

            # Firefox-specific anti-detection scripts
            stealth_scripts = [
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
                "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})",
                "Object.defineProperty(navigator, 'languages', {get: () => ['hr-HR', 'hr', 'en-US', 'en']})",
                "Object.defineProperty(navigator, 'permissions', {get: () => ({query: () => Promise.resolve({state: 'granted'})})})",
                "Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 4})",
            ]

            for script in stealth_scripts:
                try:
                    self.driver.execute_script(script)
                except Exception as e:
                    logger.debug(f"Stealth script failed: {e}")

            # Set realistic timeouts
            self.driver.implicitly_wait(10)
            self.driver.set_page_load_timeout(30)

            logger.info("Firefox WebDriver initialized successfully with enhanced anti-detection")

        except Exception as e:
            logger.error(f"Failed to initialize Firefox WebDriver: {e}")
            raise

    def human_delay(self, min_seconds: float = 3.0, max_seconds: float = 8.0) -> None:
        """
        Enhanced random delay using smart delay system.

        Args:
            min_seconds: Minimum delay time
            max_seconds: Maximum delay time
        """
        # Use the smart delay from AntiDetectionMixin
        self.smart_delay(min_seconds, max_seconds, "general")

    def human_scroll(self) -> None:
        """Enhanced human-like scrolling using advanced simulation."""
        # Use the advanced scroll simulation from AntiDetectionMixin
        self.advanced_scroll_simulation()

    def move_mouse_randomly(self) -> None:
        """Enhanced mouse movement using comprehensive behavior simulation."""
        # Use the comprehensive human behavior simulation
        self.simulate_human_behavior()

    def wait_for_page_load(self, timeout: int = 10) -> bool:
        """
        Wait for page to fully load.

        Args:
            timeout: Maximum time to wait

        Returns:
            True if page loaded successfully, False otherwise
        """
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            return True
        except TimeoutException:
            logger.warning("Page load timeout")
            return False

    def accept_cookies(self) -> None:
        """Accept cookies if cookie banner is present."""
        try:
            # Common selectors for cookie banners
            cookie_selectors = [
                "[data-testid='cookie-accept-all']",
                ".cookie-accept",
                "#cookie-accept",
                "button[id*='cookie']",
                "button[class*='cookie']",
                "button:contains('Prihvati')",
                "button:contains('Accept')",
                ".gdpr-accept"
            ]

            for selector in cookie_selectors:
                try:
                    cookie_button = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    cookie_button.click()
                    logger.info("Cookie banner accepted")
                    self.human_delay(1, 2)
                    return
                except TimeoutException:
                    continue

        except Exception as e:
            logger.debug(f"No cookie banner found or error accepting cookies: {e}")

    def extract_car_data(self, car_element) -> Optional[Dict[str, str]]:
        """
        Extract car data from a single car listing element.

        Args:
            car_element: Selenium WebElement representing a car listing

        Returns:
            Dictionary with car data or None if extraction fails
        """
        try:
            car_data = {}

            # Extract car name/title
            try:
                title_element = car_element.find_element(By.CSS_SELECTOR, ".EntityList-item-title a, h3 a, .advert-title a")
                car_data['name'] = title_element.text.strip()
                car_data['ad_link'] = urljoin(self.base_url, title_element.get_attribute('href'))
            except NoSuchElementException:
                logger.warning("Could not find car title")
                return None

            # Extract brand - try multiple selectors
            try:
                brand_selectors = [
                    ".EntityList-item-subtitle",
                    ".advert-subtitle",
                    ".brand-model",
                    "[data-testid='entity-brand']"
                ]

                brand_text = ""
                for selector in brand_selectors:
                    try:
                        brand_element = car_element.find_element(By.CSS_SELECTOR, selector)
                        brand_text = brand_element.text.strip()
                        break
                    except NoSuchElementException:
                        continue

                # If we couldn't find brand in subtitle, extract from title
                if not brand_text and car_data.get('name'):
                    # Extract just the first word as brand
                    first_word = car_data['name'].split()[0] if car_data['name'] else ""
                    # Clean up common patterns
                    brand_text = first_word.replace('*', '').replace('!', '').strip()

                car_data['brand'] = brand_text

            except Exception as e:
                logger.debug(f"Could not extract brand: {e}")
                car_data['brand'] = ""

            # Extract image URL
            try:
                img_selectors = [
                    ".EntityList-item-image img",
                    ".advert-image img",
                    ".listing-image img",
                    "img[data-testid='entity-image']",
                    ".EntityList-item img",
                    "img"  # Fallback to any img in the element
                ]

                image_url = ""
                for selector in img_selectors:
                    try:
                        img_elements = car_element.find_elements(By.CSS_SELECTOR, selector)
                        for img_element in img_elements:
                            # Try different attributes for image URL
                            image_url = (img_element.get_attribute('src') or
                                       img_element.get_attribute('data-src') or
                                       img_element.get_attribute('data-lazy-src') or
                                       img_element.get_attribute('data-original'))
                            if image_url and not image_url.startswith('data:') and 'loading' not in image_url:
                                break
                        if image_url:
                            break
                    except NoSuchElementException:
                        continue

                car_data['image_link'] = image_url if image_url else ""

            except Exception as e:
                logger.debug(f"Could not extract image: {e}")
                car_data['image_link'] = ""

            return car_data

        except Exception as e:
            logger.error(f"Error extracting car data: {e}")
            return None

    def scrape_cars(self) -> List[Dict[str, str]]:
        """
        Scrape car listings with enhanced anti-detection measures.

        Returns:
            List of dictionaries containing car data
        """
        logger.info("Starting to scrape car listings with enhanced stealth...")
        cars_data = []

        try:
            # Navigate to cars page
            logger.info(f"Navigating to {self.cars_url}")
            self.driver.get(self.cars_url)

            # Wait for page to load
            if not self.wait_for_page_load():
                logger.error("Page failed to load properly")
                return cars_data

            # Enhanced delay after page load
            self.smart_delay(5.0, 12.0, "page_load")

            # Accept cookies if present
            self.accept_cookies()

            # Enhanced human behavior simulation
            self.simulate_human_behavior()

            # Scroll to make sure all content is loaded
            self.human_scroll()

            # Additional delay before element detection
            self.smart_delay(3.0, 7.0, "car_processing")

            # Wait for listings to be present
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".EntityList-item, .advert-card, .listing-item"))
                )
            except TimeoutException:
                logger.error("No car listings found on the page")
                return cars_data

            # Find all car listing elements - try multiple selectors
            car_selectors = [
                ".EntityList-item",
                ".advert-card",
                ".listing-item",
                ".classified-list-item",
                "[data-testid='entity-item']"
            ]

            car_elements = []
            for selector in car_selectors:
                car_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if car_elements:
                    logger.info(f"Found {len(car_elements)} car elements using selector: {selector}")
                    break

            if not car_elements:
                logger.error("No car elements found with any selector")
                return cars_data

            # Extract data from each car element with enhanced delays
            for i, car_element in enumerate(car_elements):
                try:
                    # Enhanced delays between car processing
                    if i > 0:
                        if i % 4 == 0:  # Every 4th car, longer delay
                            self.smart_delay(3.0, 7.0, "car_processing")
                            self.simulate_human_behavior()
                        elif i % 2 == 0:  # Every 2nd car, medium delay
                            self.smart_delay(1.5, 4.0, "car_processing")
                        else:  # Regular short delay
                            time.sleep(random.uniform(0.8, 2.0))

                    car_data = self.extract_car_data(car_element)
                    if car_data:
                        cars_data.append(car_data)
                        logger.info(f"Extracted data for car {i+1}: {car_data.get('name', 'Unknown')}")

                except Exception as e:
                    logger.error(f"Error processing car element {i+1}: {e}")
                    # Add error recovery delay
                    self.smart_delay(5.0, 10.0, "error_recovery")
                    continue

            logger.info(f"Successfully scraped {len(cars_data)} cars with enhanced stealth")

        except Exception as e:
            logger.error(f"Error during scraping: {e}")

        return cars_data

    def save_to_excel(self, cars_data: List[Dict[str, str]], filename: str = "njuskalo_cars.xlsx") -> bool:
        """
        Save car data to Excel file in datadump directory.

        Args:
            cars_data: List of car data dictionaries
            filename: Output filename

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            if not cars_data:
                logger.warning("No data to save")
                return False

            # Create datadump directory if it doesn't exist
            import os
            datadump_dir = "datadump"
            os.makedirs(datadump_dir, exist_ok=True)

            # Ensure filename goes to datadump directory
            if not filename.startswith(datadump_dir):
                filename = os.path.join(datadump_dir, filename)

            # Create DataFrame with specific header format
            df_data = []
            for i, car in enumerate(cars_data, start=1):
                row = {
                    'id': i,  # Sequential ID
                    'vat': '',  # VAT - set as empty since no data available on scraped page
                    'name': car.get('name', ''),  # Car name/title
                    'subname': car.get('brand', ''),  # Car brand as subname
                    'address': car.get('location', ''),  # Car location
                    'total': 1,  # Each car counts as 1
                    'new': 1 if car.get('condition', '').lower() == 'new' else 0,  # New car flag
                    'used': 1 if car.get('condition', '').lower() == 'used' else 0,  # Used car flag
                    'test': 0  # Test field - set to 0 for now
                }
                df_data.append(row)

            df = pd.DataFrame(df_data)

            # Ensure columns are in the correct order
            column_order = ['id', 'vat', 'name', 'subname', 'address', 'total', 'new', 'used', 'test']
            df = df.reindex(columns=column_order)

            # Fill NaN values with empty strings for VAT column
            df['vat'] = df['vat'].fillna('')

            # Save to Excel
            df.to_excel(filename, index=False, engine='openpyxl')
            logger.info(f"Data saved to {filename}")

            # Print summary
            print(f"\nScraping Summary:")
            print(f"Total cars scraped: {len(cars_data)}")
            print(f"Data saved to: {filename}")
            print(f"Columns: {', '.join(column_order)}")

            # Show data breakdown
            new_count = sum(1 for car in cars_data if car.get('condition', '').lower() == 'new')
            used_count = sum(1 for car in cars_data if car.get('condition', '').lower() == 'used')
            print(f"New cars: {new_count}")
            print(f"Used cars: {used_count}")

            return True

        except Exception as e:
            logger.error(f"Error saving to Excel: {e}")
            return False

    def close(self) -> None:
        """Close the browser and clean up resources."""
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed")


def main():
    """Main function to run the scraper."""
    scraper = None

    try:
        print("Njuskalo Car Scraper")
        print("===================")
        print("Initializing scraper...")

        # Create scraper instance (headless by default, use headless=False for visible browser during testing)
        scraper = NjuskaloCarScraper(headless=True)

        print("Scraping car listings...")

        # Scrape cars from first page
        cars_data = scraper.scrape_cars()

        if cars_data:
            print(f"\nFound {len(cars_data)} cars. Saving to Excel...")

            # Save to Excel file
            filename = f"njuskalo_cars_{int(time.time())}.xlsx"
            scraper.save_to_excel(cars_data, filename)

            # Display first few results
            print("\nFirst 3 results:")
            print("-" * 50)
            for i, car in enumerate(cars_data[:3]):
                print(f"{i+1}. {car.get('name', 'N/A')}")
                print(f"   Brand: {car.get('brand', 'N/A')}")
                print(f"   Link: {car.get('ad_link', 'N/A')}")
                print(f"   Image: {car.get('image_link', 'N/A')}")
                print()
        else:
            print("No cars found. Please check the website structure or try again later.")

    except KeyboardInterrupt:
        print("\nScraping interrupted by user")

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"An error occurred: {e}")

    finally:
        if scraper:
            scraper.close()


if __name__ == "__main__":
    main()