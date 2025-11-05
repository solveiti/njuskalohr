#!/usr/bin/env python3
"""
Alternative version of the scraper that works with Chromium browser.
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
import shutil
import subprocess
import sys
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


def find_chrome_executable():
    """Find Chrome or Chromium executable on the system."""
    possible_paths = [
        '/usr/bin/google-chrome',
        '/usr/bin/google-chrome-stable',
        '/usr/bin/chromium-browser',
        '/usr/bin/chromium',
        '/snap/bin/chromium',
        '/usr/bin/chrome',
        'google-chrome',
        'chromium-browser',
        'chromium'
    ]

    for path in possible_paths:
        if shutil.which(path):
            logger.info(f"Found Chrome/Chromium at: {path}")
            return path

    return None


def install_chromium():
    """Install Chromium browser if not found."""
    try:
        print("🌐 Chrome/Chromium not found. Installing Chromium...")

        # Try to install Chromium using apt
        result = subprocess.run(
            ['sudo', 'apt', 'install', '-y', 'chromium-browser'],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("✅ Chromium installed successfully")
            return find_chrome_executable()
        else:
            print("❌ Failed to install Chromium automatically")
            return None

    except Exception as e:
        print(f"❌ Error installing Chromium: {e}")
        return None


class NjuskaloCarScraperChromium:
    """Web scraper for Njuskalo car listings using Chromium/Chrome."""

    def __init__(self, headless: bool = False):
        """Initialize the scraper with Chrome/Chromium WebDriver."""
        self.driver = None
        self.base_url = "https://www.njuskalo.hr"
        self.cars_url = "https://www.njuskalo.hr/auti"
        self.headless = headless
        self.chrome_path = None
        self.setup_driver()

    def setup_driver(self) -> None:
        """Set up Chrome/Chromium WebDriver."""
        # Find Chrome executable
        self.chrome_path = find_chrome_executable()

        if not self.chrome_path:
            # Try to install Chromium
            self.chrome_path = install_chromium()

        if not self.chrome_path:
            raise Exception(
                "❌ Chrome/Chromium not found and couldn't be installed automatically.\n"
                "Please install manually:\n"
                "  Ubuntu/Debian: sudo apt install chromium-browser\n"
                "  Fedora: sudo dnf install chromium\n"
                "  Arch: sudo pacman -S chromium"
            )

        chrome_options = Options()

        # Create unique temporary user data directory
        user_data_dir = tempfile.mkdtemp()  # Creates a unique temp directory
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")

        # Set the Chrome binary location
        chrome_options.binary_location = self.chrome_path

        # Add user agent to mimic real browser
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        # Disable automation flags
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Additional options for Linux compatibility
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")

        if self.headless:
            chrome_options.add_argument("--headless")

        chrome_options.add_argument("--window-size=1920,1080")

        try:
            # Try to use ChromeDriver from webdriver-manager first
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
            except Exception:
                # Fallback to system ChromeDriver
                chromedriver_path = shutil.which('chromedriver')
                if chromedriver_path:
                    service = Service(chromedriver_path)
                else:
                    # Try to install chromedriver
                    subprocess.run(['sudo', 'apt', 'install', '-y', 'chromium-chromedriver'], capture_output=True)
                    chromedriver_path = shutil.which('chromedriver')
                    if chromedriver_path:
                        service = Service(chromedriver_path)
                    else:
                        service = Service()  # Let selenium find it

            self.driver = webdriver.Chrome(service=service, options=chrome_options)

            # Execute script to remove webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            logger.info(f"Chrome/Chromium WebDriver initialized successfully using: {self.chrome_path}")

        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            raise

    def human_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0) -> None:
        """Add random delay to mimic human behavior."""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)

    def human_scroll(self) -> None:
        """Scroll the page in a human-like manner."""
        scroll_amount = random.randint(300, 800)
        self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        self.human_delay(0.5, 1.5)

        if random.random() > 0.7:
            back_scroll = random.randint(50, 200)
            self.driver.execute_script(f"window.scrollBy(0, -{back_scroll});")
            self.human_delay(0.3, 1.0)

    def move_mouse_randomly(self) -> None:
        """Move mouse cursor randomly."""
        try:
            actions = ActionChains(self.driver)
            window_size = self.driver.get_window_size()

            x = random.randint(100, window_size['width'] - 100)
            y = random.randint(100, window_size['height'] - 100)

            body = self.driver.find_element(By.TAG_NAME, "body")
            actions.move_to_element_with_offset(body, x, y).perform()

        except Exception as e:
            logger.debug(f"Mouse movement failed: {e}")

    def wait_for_page_load(self, timeout: int = 10) -> bool:
        """Wait for page to fully load."""
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
            cookie_selectors = [
                "[data-testid='cookie-accept-all']",
                ".cookie-accept",
                "#cookie-accept",
                "button[id*='cookie']",
                "button[class*='cookie']",
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
            logger.debug(f"No cookie banner found: {e}")

    def extract_car_data(self, car_element) -> Optional[Dict[str, str]]:
        """Extract car data from a single car listing element."""
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

            # Extract brand
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
        """Scrape car listings from njuskalo.hr/auti"""
        logger.info("Starting to scrape car listings...")
        cars_data = []

        try:
            logger.info(f"Navigating to {self.cars_url}")
            self.driver.get(self.cars_url)

            if not self.wait_for_page_load():
                logger.error("Page failed to load properly")
                return cars_data

            self.human_delay(2, 4)
            self.accept_cookies()
            self.move_mouse_randomly()
            self.human_scroll()

            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".EntityList-item, .advert-card, .listing-item"))
                )
            except TimeoutException:
                logger.error("No car listings found on the page")
                return cars_data

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

            for i, car_element in enumerate(car_elements):
                try:
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
        """Save car data to Excel file in datadump directory."""
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

            df.to_excel(filename, index=False, engine='openpyxl')
            logger.info(f"Data saved to {filename}")

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
        """Close the browser."""
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed")


def main():
    """Main function."""
    scraper = None

    try:
        print("🚗 Njuskalo Car Scraper (Chromium Version)")
        print("==========================================")
        print("Initializing scraper...")

        scraper = NjuskaloCarScraperChromium(headless=False)

        print("Scraping car listings...")
        cars_data = scraper.scrape_cars()

        if cars_data:
            print(f"\nFound {len(cars_data)} cars. Saving to Excel...")
            filename = f"njuskalo_cars_{int(time.time())}.xlsx"
            scraper.save_to_excel(cars_data, filename)

            print("\nFirst 3 results:")
            print("-" * 50)
            for i, car in enumerate(cars_data[:3]):
                print(f"{i+1}. {car.get('name', 'N/A')}")
                print(f"   Brand: {car.get('brand', 'N/A')}")
                print(f"   Link: {car.get('ad_link', 'N/A')}")
                print(f"   Image: {car.get('image_link', 'N/A')}")
                print()
        else:
            print("No cars found. Please check the website structure.")

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