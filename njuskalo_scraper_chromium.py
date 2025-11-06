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


class AntiDetectionMixin:
    """Advanced anti-detection methods for web scraping."""

    def enhanced_human_delay(self, min_seconds: float = 3.0, max_seconds: float = 8.0,
                            operation_type: str = "general") -> None:
        """Enhanced delay system with operation-specific timings."""
        delay_configs = {
            "general": (3.0, 8.0),
            "page_load": (4.0, 10.0),
            "data_extraction": (2.0, 5.0),
            "navigation": (5.0, 12.0),
            "error_recovery": (15.0, 30.0)
        }

        if operation_type in delay_configs:
            min_delay, max_delay = delay_configs[operation_type]
        else:
            min_delay, max_delay = min_seconds, max_seconds

        # Use triangular distribution for more realistic delays
        delay = random.triangular(min_delay, max_delay, (min_delay + max_delay) / 2)

        # 3% chance of extra long delay
        if random.random() < 0.03:
            delay += random.uniform(10, 20)
            logger.info(f"Added stealth delay: {delay:.1f}s")

        logger.debug(f"Sleeping {delay:.1f}s for {operation_type}")
        time.sleep(delay)

    def advanced_mouse_movement(self) -> None:
        """Advanced mouse movement patterns."""
        try:
            if hasattr(self, 'driver') and self.driver:
                actions = ActionChains(self.driver)
                window_size = self.driver.get_window_size()

                # Multiple random movements
                for _ in range(random.randint(3, 6)):
                    x = random.randint(50, window_size['width'] - 50)
                    y = random.randint(50, window_size['height'] - 50)

                    try:
                        body = self.driver.find_element(By.TAG_NAME, "body")
                        actions.move_to_element_with_offset(body, x, y).perform()
                        time.sleep(random.uniform(0.1, 0.7))
                    except Exception:
                        break

        except Exception as e:
            logger.debug(f"Mouse movement failed: {e}")

    def rotate_user_agents(self) -> str:
        """Get random user agent string."""
        agents = [
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        ]
        return random.choice(agents)


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


class NjuskaloCarScraperChromium(AntiDetectionMixin):
    """Web scraper for Njuskalo car listings using Chromium/Chrome."""

    def __init__(self, headless: bool = True):
        """Initialize the scraper with Chrome/Chromium WebDriver."""
        self.driver = None
        self.base_url = "https://www.njuskalo.hr"
        self.cars_url = "https://www.njuskalo.hr/auti"
        self.headless = headless
        self.chrome_path = None
        self.setup_driver()

    def setup_driver(self) -> None:
        """Set up Chrome/Chromium WebDriver with enhanced anti-detection."""
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

        # Enhanced anti-detection user agent rotation
        chrome_options.add_argument(f"--user-agent={self.rotate_user_agents()}")

        # Enhanced automation hiding
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Advanced stealth options
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
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
        chrome_options.add_argument("--disable-features=TranslateUI,VizDisplayCompositor")
        chrome_options.add_argument("--disable-ipc-flooding-protection")

        # System compatibility options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-web-security")

        # Randomize window size
        width = random.randint(1366, 1920)
        height = random.randint(768, 1080)
        chrome_options.add_argument(f"--window-size={width},{height}")

        if self.headless:
            chrome_options.add_argument("--headless")

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

            # Advanced anti-detection scripts
            stealth_scripts = [
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
                "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})",
                "Object.defineProperty(navigator, 'languages', {get: () => ['hr-HR', 'hr', 'en-US', 'en']})",
                "window.chrome = {runtime: {}}",
                "Object.defineProperty(navigator, 'permissions', {get: () => ({query: () => Promise.resolve({state: 'granted'})})})",
            ]

            for script in stealth_scripts:
                try:
                    self.driver.execute_script(script)
                except Exception as e:
                    logger.debug(f"Stealth script failed: {e}")

            # Set realistic timeouts
            self.driver.implicitly_wait(10)
            self.driver.set_page_load_timeout(30)

            logger.info(f"Chrome/Chromium WebDriver initialized successfully with enhanced anti-detection using: {self.chrome_path}")

        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            raise

    def human_delay(self, min_seconds: float = 3.0, max_seconds: float = 8.0) -> None:
        """Enhanced random delay to mimic realistic human behavior."""
        # Use the enhanced delay from AntiDetectionMixin
        self.enhanced_human_delay(min_seconds, max_seconds)

    def human_scroll(self) -> None:
        """Enhanced human-like scrolling with varied patterns."""
        # Multiple scroll actions
        for _ in range(random.randint(2, 4)):
            scroll_amount = random.randint(200, 600)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            time.sleep(random.uniform(0.5, 1.5))

        # Random scroll back
        if random.random() > 0.6:
            back_scroll = random.randint(100, 400)
            self.driver.execute_script(f"window.scrollBy(0, -{back_scroll});")
            time.sleep(random.uniform(0.3, 1.2))

        # Occasional scroll to top
        if random.random() > 0.8:
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(random.uniform(0.5, 1.5))

    def move_mouse_randomly(self) -> None:
        """Enhanced mouse movement with multiple patterns."""
        # Use the advanced mouse movement from AntiDetectionMixin
        self.advanced_mouse_movement()

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
        """Scrape car listings from njuskalo.hr/auti with enhanced anti-detection."""
        logger.info("Starting to scrape car listings...")
        cars_data = []

        try:
            logger.info(f"Navigating to {self.cars_url}")
            self.driver.get(self.cars_url)

            if not self.wait_for_page_load():
                logger.error("Page failed to load properly")
                return cars_data

            # Enhanced delays and behavior simulation
            self.enhanced_human_delay(4.0, 8.0, "page_load")
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
                    # Enhanced delays between car processing
                    if i > 0:
                        if i % 5 == 0:  # Every 5th car, longer delay
                            self.enhanced_human_delay(2.0, 5.0, "data_extraction")
                            self.move_mouse_randomly()
                        elif i % 3 == 0:  # Every 3rd car, medium delay
                            self.enhanced_human_delay(1.0, 3.0, "data_extraction")
                        else:  # Regular short delay
                            time.sleep(random.uniform(0.5, 1.5))

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

        scraper = NjuskaloCarScraperChromium(headless=True)  # Headless browser by default

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