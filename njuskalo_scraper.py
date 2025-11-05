#!/usr/bin/env python3
"""
Njuskalo Car Scraper

This script scrapes car listings from njuskalo.hr using Selenium WebDriver
with Chrome browser, mimicking normal user behavior to avoid detection.
"""

import time
import random
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
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


class NjuskaloCarScraper:
    """Web scraper for Njuskalo car listings with human-like behavior simulation."""

    def __init__(self, headless: bool = True):
        """
        Initialize the scraper with Chrome WebDriver.

        Args:
            headless: Whether to run Chrome in headless mode
        """
        self.driver = None
        self.base_url = "https://www.njuskalo.hr"
        self.cars_url = "https://www.njuskalo.hr/auti?page=4"
        self.headless = headless
        self.setup_driver()

    def setup_driver(self) -> None:
        """Set up Chrome WebDriver with options to mimic human behavior."""
        chrome_options = Options()
        # Create unique temporary user data directory
        user_data_dir = tempfile.mkdtemp()  # Creates a unique temp directory
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")

        # Add user agent to mimic real browser
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        # Disable automation flags that websites use to detect bots
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Additional options to appear more human-like
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")

        if self.headless:
            chrome_options.add_argument("--headless")

        # Window size to mimic typical desktop resolution
        chrome_options.add_argument("--window-size=1920,1080")

        try:
            # Use webdriver-manager to automatically download and manage ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)

            # Execute script to remove webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            logger.info("Chrome WebDriver initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Chrome WebDriver: {e}")
            raise

    def human_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0) -> None:
        """
        Add random delay to mimic human behavior.

        Args:
            min_seconds: Minimum delay time
            max_seconds: Maximum delay time
        """
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)

    def human_scroll(self) -> None:
        """Scroll the page in a human-like manner."""
        # Random scroll amount
        scroll_amount = random.randint(300, 800)

        # Scroll down
        self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        self.human_delay(0.5, 1.5)

        # Sometimes scroll back up a bit
        if random.random() > 0.7:
            back_scroll = random.randint(50, 200)
            self.driver.execute_script(f"window.scrollBy(0, -{back_scroll});")
            self.human_delay(0.3, 1.0)

    def move_mouse_randomly(self) -> None:
        """Move mouse cursor randomly to mimic human behavior."""
        try:
            actions = ActionChains(self.driver)
            # Get window size
            window_size = self.driver.get_window_size()

            # Random coordinates within window
            x = random.randint(100, window_size['width'] - 100)
            y = random.randint(100, window_size['height'] - 100)

            # Move to random element on page
            body = self.driver.find_element(By.TAG_NAME, "body")
            actions.move_to_element_with_offset(body, x, y).perform()

        except Exception as e:
            logger.debug(f"Mouse movement failed: {e}")

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
        Scrape car listings from the first page of njuskalo.hr/auti

        Returns:
            List of dictionaries containing car data
        """
        logger.info("Starting to scrape car listings...")
        cars_data = []

        try:
            # Navigate to cars page
            logger.info(f"Navigating to {self.cars_url}")
            self.driver.get(self.cars_url)

            # Wait for page to load
            if not self.wait_for_page_load():
                logger.error("Page failed to load properly")
                return cars_data

            # Human-like delay after page load
            self.human_delay(2, 4)

            # Accept cookies if present
            self.accept_cookies()

            # Random mouse movement
            self.move_mouse_randomly()

            # Scroll to make sure all content is loaded
            self.human_scroll()

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

            # Extract data from each car element
            for i, car_element in enumerate(car_elements):
                try:
                    # Add human-like behavior between extractions
                    if i > 0 and i % 5 == 0:
                        self.human_delay(1, 2)
                        self.move_mouse_randomly()

                    car_data = self.extract_car_data(car_element)
                    if car_data:
                        cars_data.append(car_data)
                        logger.info(f"Extracted data for car {i+1}: {car_data.get('name', 'Unknown')}")

                except Exception as e:
                    logger.error(f"Error processing car element {i+1}: {e}")
                    continue

            logger.info(f"Successfully scraped {len(cars_data)} cars")

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

        # Create scraper instance (set headless=False for visible browser during testing)
        scraper = NjuskaloCarScraper(headless=False)

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