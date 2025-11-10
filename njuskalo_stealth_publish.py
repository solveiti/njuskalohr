#!/usr/bin/env python3
"""
Stealth Publish Script for Njuskalo.hr

This script uses advanced stealth techniques from the enhanced tunnel scraper
to log into njuskalo.hr with maximum anonymity and detection avoidance for publishing ads.

Features:
- Advanced Firefox stealth configuration
- Anti-detection techniques
- SSH tunnel support (optional)
- Real Firefox browser for development
- Comprehensive error handling
- Detailed logging

Usage:
    # Development mode with visible Firefox
    python njuskalo_stealth_publish.py --visible

    # Headless mode
    python njuskalo_stealth_publish.py

    # With SSH tunnel (if configured)
    python njuskalo_stealth_publish.py --tunnel

    # Custom credentials
    python njuskalo_stealth_publish.py --username "your_user" --password "your_pass"
"""

import os
import sys
import time
import random
import logging
import argparse
import tempfile
from pathlib import Path
from typing import Optional, Dict, List
from urllib.parse import urljoin

# Selenium imports
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    WebDriverException, ElementClickInterceptedException
)

# Environment setup
from dotenv import load_dotenv
load_dotenv()


class NjuskaloStealthPublish:
    """Advanced stealth publish for Njuskalo.hr using enhanced anti-detection techniques"""

    def __init__(self, headless: bool = True, use_tunnel: bool = False,
                 username: str = None, password: str = None, persistent: bool = True):
        """
        Initialize stealth publish system

        Args:
            headless: Run browser in headless mode
            use_tunnel: Enable SSH tunnel support
            username: Njuskalo username
            password: Njuskalo password
            persistent: Use persistent browser profile to avoid new device detection
        """
        self.headless = headless
        self.use_tunnel = use_tunnel
        self.persistent = persistent
        self.driver = None
        self.logger = self._setup_logging()

        # Login credentials
        self.username = username or "MilkicHalo"
        self.password = password or "rvp2mqu@xye1JRC0fjt"

        # Njuskalo URLs
        self.base_url = os.getenv("NJUSKALO_BASE_URL", "https://www.njuskalo.hr")
        self.login_url = urljoin(self.base_url, "/prijava")

        # Persistent profile management
        self.profile_dir = None
        self.device_fingerprint = None
        if self.persistent:
            self._setup_persistent_profile()

        # Tunnel configuration
        self.socks_proxy_port = None
        self.tunnel_manager = None

        if self.use_tunnel:
            self._setup_tunnel()

    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive logging"""
        logger = logging.getLogger("NjuskaloStealthPublish")
        logger.setLevel(logging.INFO)

        # Create logs directory if needed
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)

        # File handler
        file_handler = logging.FileHandler(logs_dir / "njuskalo_stealth_publish.log")
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)

        # Add handlers if not already added
        if not logger.handlers:
            logger.addHandler(console_handler)
            logger.addHandler(file_handler)

        return logger

    def _setup_persistent_profile(self):
        """Setup persistent Firefox profile to avoid new device detection"""
        try:
            # Create persistent profile directory
            profiles_base = Path("browser_profiles")
            profiles_base.mkdir(exist_ok=True)

            # Use username-based profile directory
            safe_username = "".join(c for c in self.username if c.isalnum() or c in "-_")
            self.profile_dir = profiles_base / f"njuskalo_profile_{safe_username}"
            self.profile_dir.mkdir(exist_ok=True)

            self.logger.info(f"📁 Using persistent profile: {self.profile_dir}")

            # Generate consistent device fingerprint
            import hashlib
            fingerprint_seed = f"{self.username}_{self.base_url}_njuskalo_stealth"
            self.device_fingerprint = hashlib.md5(fingerprint_seed.encode()).hexdigest()

            # Create device fingerprint file for consistency
            fingerprint_file = self.profile_dir / "device_fingerprint.txt"
            if not fingerprint_file.exists():
                with open(fingerprint_file, 'w') as f:
                    f.write(self.device_fingerprint)
                self.logger.info(f"🔑 Generated device fingerprint: {self.device_fingerprint[:8]}...")
            else:
                with open(fingerprint_file, 'r') as f:
                    self.device_fingerprint = f.read().strip()
                self.logger.info(f"🔑 Loaded existing device fingerprint: {self.device_fingerprint[:8]}...")

        except Exception as e:
            self.logger.error(f"❌ Error setting up persistent profile: {e}")
            self.persistent = False

    def _setup_tunnel(self):
        """Setup SSH tunnel if available"""
        try:
            # Import tunnel manager if available
            sys.path.append(str(Path(__file__).parent))
            from ssh_tunnel_manager import SSHTunnelManager

            tunnel_config_path = "tunnel_config.json"
            if os.path.exists(tunnel_config_path):
                self.tunnel_manager = SSHTunnelManager(tunnel_config_path)
                self.logger.info("✅ SSH tunnel manager initialized")
            else:
                self.logger.warning("⚠️ Tunnel config not found, continuing without tunnel")
                self.use_tunnel = False
        except ImportError:
            self.logger.warning("⚠️ SSH tunnel manager not available, continuing without tunnel")
            self.use_tunnel = False

    def _start_tunnel(self) -> bool:
        """Start SSH tunnel and configure proxy"""
        if not self.use_tunnel or not self.tunnel_manager:
            return True

        try:
            tunnels = self.tunnel_manager.list_tunnels()
            if not tunnels:
                self.logger.error("❌ No tunnels configured")
                return False

            # Use first available tunnel
            tunnel_name = list(tunnels.keys())[0]
            self.logger.info(f"🚇 Starting SSH tunnel: {tunnel_name}")

            success = self.tunnel_manager.establish_tunnel(tunnel_name)
            if success:
                proxy_settings = self.tunnel_manager.get_proxy_settings()
                self.socks_proxy_port = proxy_settings.get('local_port') if proxy_settings else None
                self.logger.info(f"✅ SSH tunnel active on port {self.socks_proxy_port}")
                time.sleep(3)  # Let tunnel stabilize
                return True
            else:
                self.logger.error(f"❌ Failed to start tunnel: {tunnel_name}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Error starting tunnel: {e}")
            return False

    def _find_geckodriver(self) -> Optional[str]:
        """Find GeckoDriver in system"""
        import shutil
        import glob

        # Check common locations
        possible_paths = [
            "/usr/local/bin/geckodriver",
            "/usr/bin/geckodriver",
        ]

        for path in possible_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                return path

        # Check webdriver-manager cache
        wdm_pattern = "/home/*/.*wdm/drivers/geckodriver/linux64/*/geckodriver"
        matches = glob.glob(wdm_pattern)
        if matches:
            for match in matches:
                if os.access(match, os.X_OK):
                    return match

        # Try PATH
        path_geckodriver = shutil.which("geckodriver")
        if path_geckodriver:
            return path_geckodriver

        return None

    def _get_random_user_agent(self) -> str:
        """Generate random but realistic user agent"""
        user_agents = [
            "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:119.0) Gecko/20100101 Firefox/119.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:118.0) Gecko/20100101 Firefox/118.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:117.0) Gecko/20100101 Firefox/117.0",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"
        ]
        return random.choice(user_agents)

    def _get_random_screen_size(self) -> tuple:
        """Generate random but realistic screen dimensions"""
        if self.persistent and hasattr(self, 'device_fingerprint'):
            # Use consistent screen size based on device fingerprint
            import hashlib
            seed = int(hashlib.md5(self.device_fingerprint.encode()).hexdigest()[:8], 16)
            random.seed(seed)

        common_resolutions = [
            (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
            (1600, 900), (1280, 720), (1024, 768), (1680, 1050)
        ]
        return random.choice(common_resolutions)

    def _get_consistent_fingerprint(self) -> Dict[str, str]:
        """Generate consistent device fingerprint for persistent sessions"""
        if not self.persistent or not hasattr(self, 'device_fingerprint'):
            return {
                'user_agent': self._get_random_user_agent(),
                'platform': "Linux x86_64"
            }

        # Generate consistent values based on device fingerprint
        import hashlib
        seed = int(hashlib.md5(self.device_fingerprint.encode()).hexdigest()[:8], 16)
        random.seed(seed)

        user_agents = [
            "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:119.0) Gecko/20100101 Firefox/119.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:118.0) Gecko/20100101 Firefox/118.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:117.0) Gecko/20100101 Firefox/117.0",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"
        ]

        platforms = [
            "Linux x86_64",
            "Linux i686"
        ]

        fingerprint = {
            'user_agent': random.choice(user_agents),
            'platform': random.choice(platforms)
        }

        # Reset random state
        random.seed()

        return fingerprint

    def save_session_data(self):
        """Save session cookies and local storage for persistence"""
        if not self.persistent or not self.driver or not self.profile_dir:
            return

        try:
            # Save cookies
            cookies_file = self.profile_dir / "session_cookies.json"
            cookies = self.driver.get_cookies()

            import json
            with open(cookies_file, 'w') as f:
                json.dump(cookies, f, indent=2)

            self.logger.info(f"💾 Saved {len(cookies)} cookies to profile")

            # Save local storage (if accessible)
            try:
                local_storage = self.driver.execute_script("return window.localStorage;")
                if local_storage:
                    storage_file = self.profile_dir / "local_storage.json"
                    with open(storage_file, 'w') as f:
                        json.dump(local_storage, f, indent=2)
                    self.logger.info("💾 Saved local storage data")
            except Exception as e:
                self.logger.debug(f"Could not save local storage: {e}")

        except Exception as e:
            self.logger.warning(f"⚠️ Error saving session data: {e}")

    def restore_session_data(self):
        """Restore session cookies and local storage for device continuity"""
        if not self.persistent or not self.driver or not self.profile_dir:
            return

        try:
            # First navigate to domain to set cookies
            self.driver.get(self.base_url)
            time.sleep(2)

            # Restore cookies
            cookies_file = self.profile_dir / "session_cookies.json"
            if cookies_file.exists():
                import json
                with open(cookies_file, 'r') as f:
                    cookies = json.load(f)

                for cookie in cookies:
                    try:
                        # Remove domain if it starts with dot (selenium requirement)
                        if 'domain' in cookie and cookie['domain'].startswith('.'):
                            cookie['domain'] = cookie['domain'][1:]
                        self.driver.add_cookie(cookie)
                    except Exception as e:
                        self.logger.debug(f"Could not restore cookie {cookie.get('name', 'unknown')}: {e}")

                self.logger.info(f"🔄 Restored {len(cookies)} cookies")

            # Restore local storage
            storage_file = self.profile_dir / "local_storage.json"
            if storage_file.exists():
                try:
                    import json
                    with open(storage_file, 'r') as f:
                        local_storage = json.load(f)

                    for key, value in local_storage.items():
                        self.driver.execute_script(f"window.localStorage.setItem('{key}', '{value}');")

                    self.logger.info("🔄 Restored local storage data")
                except Exception as e:
                    self.logger.debug(f"Could not restore local storage: {e}")

        except Exception as e:
            self.logger.warning(f"⚠️ Error restoring session data: {e}")

    def setup_stealth_browser(self) -> bool:
        """
        Setup Firefox with advanced stealth configuration
        Uses all techniques from enhanced tunnel scraper
        """
        try:
            self.logger.info("🕵️ Setting up stealth Firefox browser...")

            # Find geckodriver
            geckodriver_path = self._find_geckodriver()
            if not geckodriver_path:
                self.logger.error("❌ GeckoDriver not found")
                return False

            # Create Firefox options with stealth configuration
            firefox_options = Options()

            # Headless configuration
            firefox_options.headless = self.headless

            # Set binary location (prefer system Firefox)
            if os.path.exists("/usr/bin/firefox"):
                firefox_options.binary_location = "/usr/bin/firefox"

            # === ADVANCED STEALTH PREFERENCES ===

            # Disable webdriver detection
            firefox_options.set_preference("dom.webdriver.enabled", False)
            firefox_options.set_preference("useAutomationExtension", False)
            firefox_options.set_preference("marionette.enabled", False)

            # Platform and User-Agent (will be overridden if using persistent profile)
            firefox_options.set_preference("general.platform.override", "Linux x86_64")
            firefox_options.set_preference("general.appversion.override", "5.0 (X11)")

            # Default user agent (may be overridden by persistent fingerprint)
            if not (self.persistent and self.profile_dir):
                user_agent = self._get_random_user_agent()
                firefox_options.set_preference("general.useragent.override", user_agent)
                self.logger.info(f"🎭 Using Random User-Agent: {user_agent}")
            else:
                self.logger.info("🎭 User-Agent will be set by persistent fingerprint")

            # Language preferences (Croatian + English for Njuskalo)
            firefox_options.set_preference("intl.accept_languages", "hr-HR,hr,en-US,en")
            firefox_options.set_preference("javascript.use_us_english_locale", False)

            # Timezone (Croatia)
            firefox_options.set_preference("privacy.reduceTimerPrecision", False)

            # Disable automation indicators
            firefox_options.set_preference("fission.autostart", False)
            firefox_options.set_preference("browser.tabs.remote.autostart", False)

            # Hardware acceleration (disable for stealth)
            firefox_options.set_preference("layers.acceleration.disabled", True)
            firefox_options.set_preference("gfx.webrender.force-disabled", True)
            firefox_options.set_preference("media.hardware-video-decoding.enabled", False)

            # Disable tracking protection (some sites detect it)
            firefox_options.set_preference("privacy.trackingprotection.enabled", False)
            firefox_options.set_preference("privacy.trackingprotection.pbmode.enabled", False)

            # WebGL and Canvas fingerprinting
            firefox_options.set_preference("webgl.disabled", True)
            firefox_options.set_preference("privacy.resistFingerprinting", False)  # Can cause detection

            # Plugin configuration
            firefox_options.set_preference("dom.ipc.plugins.enabled", False)
            firefox_options.set_preference("media.peerconnection.enabled", False)
            firefox_options.set_preference("media.navigator.enabled", False)

            # Network preferences
            firefox_options.set_preference("network.http.connection-timeout", 30)
            firefox_options.set_preference("network.http.response.timeout", 30)
            firefox_options.set_preference("dom.max_script_run_time", 30)

            # === DEVICE PERSISTENCE CONFIGURATION ===
            if self.persistent and self.profile_dir:
                # Use persistent profile directory
                from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
                profile = FirefoxProfile(str(self.profile_dir))
                firefox_options.profile = profile

                # Enable persistent storage for device recognition
                firefox_options.set_preference("browser.cache.disk.enable", True)
                firefox_options.set_preference("browser.cache.memory.enable", True)
                firefox_options.set_preference("dom.storage.enabled", True)
                firefox_options.set_preference("privacy.clearOnShutdown.cookies", False)
                firefox_options.set_preference("privacy.clearOnShutdown.sessions", False)
                firefox_options.set_preference("privacy.clearOnShutdown.offlineApps", False)
                firefox_options.set_preference("network.cookie.lifetimePolicy", 0)  # Accept all cookies

                # Consistent device fingerprint based on username
                consistent_fingerprint = self._get_consistent_fingerprint()
                firefox_options.set_preference("general.useragent.override", consistent_fingerprint['user_agent'])
                firefox_options.set_preference("general.platform.override", consistent_fingerprint['platform'])

                self.logger.info("🔒 Configured persistent device profile")
            else:
                # Standard stealth mode (no persistence)
                firefox_options.set_preference("browser.cache.disk.enable", False)
                firefox_options.set_preference("browser.cache.memory.enable", False)
                firefox_options.set_preference("browser.cache.offline.enable", False)
                firefox_options.set_preference("network.http.use-cache", False)

            # Security sandbox
            firefox_options.set_preference("security.sandbox.content.level", 0)

            # === PROXY CONFIGURATION ===
            if self.use_tunnel and self.socks_proxy_port:
                # SOCKS proxy through SSH tunnel
                firefox_options.set_preference("network.proxy.type", 1)
                firefox_options.set_preference("network.proxy.socks", "127.0.0.1")
                firefox_options.set_preference("network.proxy.socks_port", self.socks_proxy_port)
                firefox_options.set_preference("network.proxy.socks_version", 5)
                firefox_options.set_preference("network.proxy.socks_remote_dns", True)
                self.logger.info(f"🌐 SOCKS proxy configured: 127.0.0.1:{self.socks_proxy_port}")
            else:
                firefox_options.set_preference("network.proxy.type", 0)  # Direct connection

            # === FIREFOX ARGUMENTS ===
            firefox_options.add_argument("--no-sandbox")
            firefox_options.add_argument("--disable-dev-shm-usage")

            # Random window size
            width, height = self._get_random_screen_size()
            firefox_options.add_argument(f"--width={width}")
            firefox_options.add_argument(f"--height={height}")

            # Create service
            service = Service(geckodriver_path)

            # Initialize WebDriver
            self.logger.info("🔧 Starting Firefox WebDriver...")
            self.driver = webdriver.Firefox(service=service, options=firefox_options)

            # Set timeouts
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)

            # Set window size programmatically
            self.driver.set_window_size(width, height)

            # === JAVASCRIPT STEALTH INJECTION ===
            stealth_scripts = [
                # Remove webdriver property
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",

                # Fake plugins
                "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})",

                # Fake languages
                "Object.defineProperty(navigator, 'languages', {get: () => ['hr-HR', 'hr', 'en-US', 'en']})",

                # Fake permissions
                "const originalQuery = window.navigator.permissions.query;"
                "window.navigator.permissions.query = (parameters) => ("
                "  parameters.name === 'notifications' ?"
                "  Promise.resolve({ state: Notification.permission }) :"
                "  originalQuery(parameters)"
                ");",

                # Hide automation
                "delete window.chrome;",
                "window.chrome = { runtime: {} };",
            ]

            # Apply stealth scripts
            for script in stealth_scripts:
                try:
                    self.driver.execute_script(script)
                except Exception as e:
                    self.logger.debug(f"Stealth script warning: {e}")

            self.logger.info("✅ Stealth browser setup completed")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to setup browser: {e}")
            if hasattr(self, 'driver') and self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
            return False

    def _human_like_typing(self, element, text: str, min_delay: float = 0.05, max_delay: float = 0.15):
        """Type text with human-like delays and patterns"""
        for char in text:
            element.send_keys(char)
            # Random delay between keystrokes
            delay = random.uniform(min_delay, max_delay)
            time.sleep(delay)

            # Occasional longer pause (like thinking)
            if random.random() < 0.1:  # 10% chance
                time.sleep(random.uniform(0.2, 0.5))

    def _human_like_mouse_movement(self, element):
        """Move mouse to element with human-like behavior"""
        try:
            actions = ActionChains(self.driver)

            # Get element location
            location = element.location
            size = element.size

            # Calculate random point within element
            x_offset = random.randint(5, size['width'] - 5)
            y_offset = random.randint(5, size['height'] - 5)

            # Move to element with slight randomness
            actions.move_to_element_with_offset(element, x_offset, y_offset)
            actions.perform()

            # Small random delay
            time.sleep(random.uniform(0.1, 0.3))

        except Exception as e:
            self.logger.debug(f"Mouse movement warning: {e}")

    def handle_advertisement_popup(self) -> bool:
        """Handle advertisement notice popup with Didomi consent button and other popups"""
        try:
            self.logger.info("🔍 Checking for consent/advertisement popups...")

            # Wait a bit for popup to appear
            time.sleep(random.uniform(1, 2))

            # Common selectors for popup accept buttons (prioritized order)
            accept_button_selectors = [
                "#didomi-notice-agree-button",  # Didomi consent management button
                "button:contains('Prihvati i zatvori')",
                "button[text*='Prihvati i zatvori']",
                "input[value*='Prihvati i zatvori']",
                "a:contains('Prihvati i zatvori')",
                ".accept-button",
                ".cookie-accept",
                ".gdpr-accept",
                "[data-accept]",
                "button[class*='accept']",
                "button[id*='accept']",
                ".popup button:contains('Prihvati')",
                ".modal button:contains('Prihvati')",
                ".overlay button:contains('Prihvati')"
            ]

            # Additional Didomi consent management selectors
            didomi_selectors = [
                "#didomi-notice-agree-button",
                "[data-didomi-id='agree']",
                ".didomi-notice-component-button[aria-labelledby*='agree']",
                ".didomi-button-agree",
                ".didomi-continue-without-agreeing"
            ]

            # Also look for generic close/accept buttons in popups
            generic_popup_selectors = [
                ".popup .close-button",
                ".modal .close-button",
                ".overlay .close-button",
                ".popup button[type='button']",
                ".modal button[type='button']",
                ".cookie-banner button",
                ".gdpr-banner button"
            ]

            # Try to find and click the accept button (check Didomi first, then others)
            button_found = False
            all_selectors = didomi_selectors + accept_button_selectors + generic_popup_selectors

            for selector in all_selectors:
                try:
                    # Wait a short time for the button to appear
                    button = WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )

                    if button.is_displayed():
                        self.logger.info(f"✅ Found popup accept button: {selector}")

                        # Human-like interaction with popup
                        time.sleep(random.uniform(0.5, 1.0))

                        # Scroll button into view
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                        time.sleep(random.uniform(0.2, 0.5))

                        # Move mouse to button
                        self._human_like_mouse_movement(button)

                        # Click the button
                        try:
                            button.click()
                            button_type = "Didomi consent" if "didomi" in selector.lower() else "popup accept"
                            self.logger.info(f"🎯 Clicked {button_type} button")
                        except ElementClickInterceptedException:
                            # Use JavaScript click if regular click fails
                            self.driver.execute_script("arguments[0].click();", button)
                            button_type = "Didomi consent" if "didomi" in selector.lower() else "popup accept"
                            self.logger.info(f"🎯 JavaScript clicked {button_type} button")

                        # Wait for popup to disappear
                        time.sleep(random.uniform(1, 2))
                        button_found = True
                        break

                except (TimeoutException, NoSuchElementException):
                    continue
                except Exception as e:
                    self.logger.debug(f"Error with selector {selector}: {e}")
                    continue

            if not button_found:
                self.logger.info("ℹ️ No consent/advertisement popup found or already handled")
            else:
                self.logger.info("✅ Consent/advertisement popup handled successfully")

            return True

        except Exception as e:
            self.logger.warning(f"⚠️ Error handling advertisement popup: {e}")
            return True  # Continue anyway, popup handling is not critical

    def navigate_to_login(self) -> bool:
        """Navigate to Njuskalo login page with stealth"""
        try:
            self.logger.info(f"🌐 Navigating to login page: {self.login_url}")

            # Navigate to login page
            self.driver.get(self.login_url)

            # Wait for page load with human-like delay
            time.sleep(random.uniform(2, 4))

            # Restore session data if using persistent profile
            if self.persistent:
                self.restore_session_data()

            # Handle advertisement popup if present
            self.handle_advertisement_popup()

            # Check if we're on login page
            if "prijava" in self.driver.current_url.lower():
                self.logger.info("✅ Successfully reached login page")
                return True
            else:
                self.logger.warning(f"⚠️ Unexpected URL: {self.driver.current_url}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Failed to navigate to login: {e}")
            return False

    def perform_login(self) -> bool:
        """Perform login with advanced stealth techniques"""
        try:
            self.logger.info("🔐 Starting stealth publish process...")

            # Wait for login form to load
            try:
                # Common selectors for Njuskalo login form (Croatian field names)
                username_selectors = [
                    "input[placeholder*='Korisničko ime']",
                    "input[name*='korisnicko']",
                    "input[name*='username']",
                    "input[name='email']",
                    "input[type='email']",
                    "#username",
                    "#email",
                    ".username",
                    ".email",
                    "input[id*='korisnicko']",
                    "input[class*='korisnicko']"
                ]

                password_selectors = [
                    "input[placeholder*='Lozinka']",
                    "input[name*='lozinka']",
                    "input[name='password']",
                    "input[type='password']",
                    "#password",
                    ".password",
                    "input[id*='lozinka']",
                    "input[class*='lozinka']"
                ]

                # Find username field
                username_field = None
                for selector in username_selectors:
                    try:
                        username_field = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        self.logger.info(f"✅ Found username field: {selector}")
                        break
                    except TimeoutException:
                        continue

                if not username_field:
                    self.logger.error("❌ Username field not found")
                    return False

                # Find password field
                password_field = None
                for selector in password_selectors:
                    try:
                        password_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                        self.logger.info(f"✅ Found password field: {selector}")
                        break
                    except NoSuchElementException:
                        continue

                if not password_field:
                    self.logger.error("❌ Password field not found")
                    return False

                # Human-like interaction
                self.logger.info("👤 Performing human-like login interaction...")

                # Scroll username field into view
                self.driver.execute_script("arguments[0].scrollIntoView(true);", username_field)
                time.sleep(random.uniform(0.5, 1.0))

                # Move mouse to username field
                self._human_like_mouse_movement(username_field)

                # Click username field
                username_field.click()
                time.sleep(random.uniform(0.2, 0.5))

                # Clear and type username
                username_field.clear()
                time.sleep(random.uniform(0.1, 0.3))
                self._human_like_typing(username_field, self.username)

                self.logger.info(f"✅ Username entered: {self.username}")

                # Random delay before password
                time.sleep(random.uniform(0.5, 1.5))

                # Move to password field
                self._human_like_mouse_movement(password_field)
                password_field.click()
                time.sleep(random.uniform(0.2, 0.5))

                # Clear and type password
                password_field.clear()
                time.sleep(random.uniform(0.1, 0.3))
                self._human_like_typing(password_field, self.password, 0.03, 0.1)  # Faster for password

                self.logger.info("✅ Password entered")

                # Find and click login button
                login_button_selectors = [
                    "button[type='submit']",
                    "input[type='submit']",
                    "button.login",
                    ".login-button",
                    "#login-button",
                    "button:contains('Prijavi se')",
                    "button:contains('Prijaviť')",
                    "button:contains('Login')",
                    "button:contains('Ulogiraj')",
                    "input[value*='Prijavi']",
                    "button[value*='Prijavi']"
                ]

                login_button = None
                for selector in login_button_selectors:
                    try:
                        login_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                        break
                    except NoSuchElementException:
                        continue

                if not login_button:
                    # Try submitting form directly
                    self.logger.info("🔄 Login button not found, submitting form...")
                    password_field.send_keys(Keys.RETURN)
                else:
                    # Click login button with human behavior
                    self.logger.info("🖱️ Clicking login button...")
                    time.sleep(random.uniform(0.5, 1.0))
                    self._human_like_mouse_movement(login_button)

                    try:
                        login_button.click()
                    except ElementClickInterceptedException:
                        # Use JavaScript click if regular click fails
                        self.driver.execute_script("arguments[0].click();", login_button)

                # Wait for login to complete
                self.logger.info("⏳ Waiting for login to complete...")
                time.sleep(random.uniform(3, 6))

                # Handle any popups that might appear after login
                self.handle_advertisement_popup()

                # Check if login was successful
                current_url = self.driver.current_url
                if "prijava" not in current_url.lower() or "dashboard" in current_url.lower() or "moj-njuskalo" in current_url.lower():
                    self.logger.info("🎉 Login appears successful!")
                    self.logger.info(f"Current URL: {current_url}")
                    return True
                else:
                    # Check for error messages
                    try:
                        error_selectors = [
                            ".error", ".alert-error", ".login-error",
                            ".message-error", "[class*='error']"
                        ]
                        for selector in error_selectors:
                            try:
                                error_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                                if error_element.is_displayed():
                                    error_text = error_element.text
                                    self.logger.error(f"❌ Login error: {error_text}")
                                    return False
                            except NoSuchElementException:
                                continue
                    except Exception:
                        pass

                    self.logger.warning("⚠️ Login status unclear, checking page content...")
                    return True  # Continue anyway

            except TimeoutException:
                self.logger.error("❌ Login form not found or timed out")
                return False

        except Exception as e:
            self.logger.error(f"❌ Login failed: {e}")
            return False

    def verify_login_success(self) -> bool:
        """Verify that login was successful"""
        try:
            self.logger.info("🔍 Verifying login success...")

            # Check URL
            current_url = self.driver.current_url
            self.logger.info(f"Current URL: {current_url}")

            # Look for logged-in indicators
            logged_in_indicators = [
                "a[href*='logout']",
                "a[href*='odjavi']",
                ".user-menu",
                ".profile-menu",
                "[class*='user']",
                "[class*='profile']"
            ]

            for indicator in logged_in_indicators:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, indicator)
                    if element.is_displayed():
                        self.logger.info(f"✅ Found logged-in indicator: {indicator}")
                        if self.persistent:
                            self.save_session_data()
                        return True
                except NoSuchElementException:
                    continue

            # Check page title
            title = self.driver.title
            self.logger.info(f"Page title: {title}")

            # If we're not on login page, assume success
            if "prijava" not in current_url.lower():
                self.logger.info("✅ No longer on login page - assuming success")
                if self.persistent:
                    self.save_session_data()
                return True

            self.logger.warning("⚠️ Could not verify login success definitively")
            return False

        except Exception as e:
            self.logger.error(f"❌ Error verifying login: {e}")
            return False

    def take_screenshot(self, name: str = "login_result"):
        """Take screenshot for debugging"""
        try:
            screenshots_dir = Path("screenshots")
            screenshots_dir.mkdir(exist_ok=True)

            timestamp = int(time.time())
            filename = screenshots_dir / f"{name}_{timestamp}.png"

            self.driver.save_screenshot(str(filename))
            self.logger.info(f"📸 Screenshot saved: {filename}")

        except Exception as e:
            self.logger.error(f"❌ Failed to take screenshot: {e}")

    def run_stealth_publish(self) -> bool:
        """Main method to run complete stealth publish process"""
        try:
            self.logger.info("🚀 Starting Njuskalo Stealth Publish")
            self.logger.info("=" * 50)

            # Step 1: Setup tunnel if enabled
            if self.use_tunnel:
                if not self._start_tunnel():
                    self.logger.error("❌ Tunnel setup failed, continuing without tunnel")
                    self.use_tunnel = False

            # Step 2: Setup stealth browser
            if not self.setup_stealth_browser():
                return False

            # Step 3: Navigate to login page
            if not self.navigate_to_login():
                return False

            # Step 4: Perform login
            if not self.perform_login():
                return False

            # Step 5: Verify login success
            success = self.verify_login_success()

            # Step 6: Take screenshot
            self.take_screenshot("login_success" if success else "login_failed")

            if success:
                self.logger.info("🎉 Stealth publish completed successfully!")
                self.logger.info(f"You are now logged in to Njuskalo as: {self.username}")

                # Keep browser open for development
                if not self.headless:
                    self.logger.info("🖥️ Browser will stay open for development...")
                    self.logger.info("Press Ctrl+C to close browser and exit")
                    try:
                        while True:
                            time.sleep(1)
                    except KeyboardInterrupt:
                        self.logger.info("👋 Closing browser...")

                return True
            else:
                self.logger.error("❌ Login verification failed")
                return False

        except Exception as e:
            self.logger.error(f"❌ Stealth publish failed: {e}")
            return False
        finally:
            # Cleanup
            if hasattr(self, 'driver') and self.driver and self.headless:
                try:
                    self.driver.quit()
                except:
                    pass


def main():
    """Main function with argument parsing"""
    parser = argparse.ArgumentParser(description="Njuskalo.hr Stealth Publish")
    parser.add_argument("--visible", action="store_true",
                       help="Run in visible mode (not headless)")
    parser.add_argument("--tunnel", action="store_true",
                       help="Use SSH tunnel for anonymity")
    parser.add_argument("--username", type=str, default="MilkicHalo",
                       help="Njuskalo username")
    parser.add_argument("--password", type=str, default="rvp2mqu@xye1JRC0fjt",
                       help="Njuskalo password")
    parser.add_argument("--no-persistent", action="store_true",
                       help="Disable persistent profile (always appear as new device)")

    args = parser.parse_args()

    # Create stealth publish instance
    stealth_publish = NjuskaloStealthPublish(
        headless=not args.visible,
        use_tunnel=args.tunnel,
        username=args.username,
        password=args.password,
        persistent=not args.no_persistent  # Persistent by default
    )

    # Run publish process
    success = stealth_publish.run_stealth_publish()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()