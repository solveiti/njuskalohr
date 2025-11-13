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
from typing import Optional, Dict, List, Union
from urllib.parse import urljoin

# Selenium imports
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webelement import WebElement
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
                 username: str = None, password: str = None, persistent: bool = True,
                 user_uuid: str = None, test_mode: bool = False, submit_ad: bool = False):
        """
        Initialize stealth publish system

        Args:
            headless: Run browser in headless mode
            use_tunnel: Enable SSH tunnel support
            username: Njuskalo username
            password: Njuskalo password
            persistent: Use persistent browser profile to avoid new device detection
            user_uuid: UUID for persistent Firefox session (avoids confirmation codes)
            test_mode: Enable test mode for 2FA (manual code input vs database retrieval)
            submit_ad: Enable ad submission process after successful login
        """
        self.headless = headless
        self.use_tunnel = use_tunnel
        self.persistent = persistent
        self.user_uuid = user_uuid
        self.test_mode = test_mode
        self.submit_ad = submit_ad
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

        # Firefox session management (UUID-based)
        self.firefox_session_dir = None
        self.session_fingerprint = None

        # Setup Firefox session management
        if self.user_uuid:
            self._setup_firefox_session()
        elif self.persistent:
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

    def _setup_firefox_session(self):
        """Setup UUID-based Firefox session to avoid confirmation codes"""
        try:
            import uuid
            import time

            # Validate UUID format
            if self.user_uuid:
                try:
                    uuid.UUID(self.user_uuid)
                except ValueError:
                    self.logger.error(f"❌ Invalid UUID format: {self.user_uuid}")
                    self.user_uuid = None
                    return

            # Create Firefox sessions directory
            sessions_base = Path("firefoxsessions")
            sessions_base.mkdir(exist_ok=True)

            # Use UUID as session directory name
            if self.user_uuid:
                session_id = self.user_uuid
            else:
                # Generate new UUID if not provided
                session_id = str(uuid.uuid4())
                self.user_uuid = session_id
                self.logger.info(f"🆔 Generated new session UUID: {session_id}")

            self.firefox_session_dir = sessions_base / session_id
            self.firefox_session_dir.mkdir(exist_ok=True)

            self.logger.info(f"🔥 Using Firefox session: {session_id}")
            self.logger.info(f"📁 Session directory: {self.firefox_session_dir}")

            # Generate consistent device fingerprint based on UUID
            import hashlib
            fingerprint_seed = f"{self.user_uuid}_{self.base_url}_firefox_session"
            self.device_fingerprint = hashlib.md5(fingerprint_seed.encode()).hexdigest()

            # Create session fingerprint for browser preferences
            self.session_fingerprint = self._get_consistent_fingerprint()

            # Save session metadata
            session_info = {
                "uuid": self.user_uuid,
                "username": self.username,
                "created": time.time(),
                "last_used": time.time(),
                "fingerprint": self.device_fingerprint
            }

            import json
            session_file = self.firefox_session_dir / "session_info.json"
            with open(session_file, 'w') as f:
                json.dump(session_info, f, indent=2)

            self.logger.info(f"💾 Session metadata saved")

        except Exception as e:
            self.logger.error(f"❌ Error setting up Firefox session: {e}")
            self.user_uuid = None
            self.firefox_session_dir = None

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

    def _check_if_already_logged_in(self) -> bool:
        """Check if user is already logged in by looking for logged-in indicators"""
        try:
            self.logger.info("🔍 Checking if already logged in...")

            # Look for logged-in indicators using CSS selectors
            css_selectors = [
                "a[href*='logout']",
                "a[href*='odjavi']",
                "a[href*='moj-njuskalo']",
                ".user-menu",
                ".profile-menu",
                "[class*='user-info']",
                "[class*='profile']"
            ]

            for selector in css_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            self.logger.info(f"✅ Found logged-in indicator: {selector} - '{element.text}'")
                            return True
                except Exception:
                    continue

            # Look for text-based indicators using XPath
            xpath_selectors = [
                "//a[contains(text(), 'Odjavi se')]",
                "//button[contains(text(), 'Odjavi se')]",
                "//a[contains(text(), 'Moj Njuškalo')]",
                "//a[contains(@href, 'logout')]",
                "//a[contains(@href, 'odjavi')]"
            ]

            for xpath in xpath_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    for element in elements:
                        if element.is_displayed():
                            self.logger.info(f"✅ Found logged-in indicator: {xpath} - '{element.text}'")
                            return True
                except Exception:
                    continue

            # Check page source for logged-in text (more comprehensive)
            page_source = self.driver.page_source.lower()
            logged_in_texts = [
                "moj njuškalo",
                "odjavi se",
                "objavi oglas",
                "moja objava",
                "moj profil",
                "postavke računa"
            ]

            for text in logged_in_texts:
                if text in page_source:
                    self.logger.info(f"✅ Found logged-in text in page: '{text}'")
                    return True

            # Check page title
            title = self.driver.title.lower()
            if "moj njuškalo" in title:
                self.logger.info(f"✅ Found logged-in page title: {title}")
                return True

            self.logger.info("ℹ️ No logged-in indicators found")
            return False

        except Exception as e:
            self.logger.warning(f"⚠️ Error checking login status: {e}")
            return False

    def navigate_to_login(self) -> bool:
        """Navigate to Njuskalo login page with stealth"""
        try:
            self.logger.info(f"🌐 Navigating to login page: {self.login_url}")

            # Navigate to login page
            self.driver.get(self.login_url)

            # Wait for page load with human-like delay
            time.sleep(random.uniform(2, 4))

            self.logger.info(f"📍 Current URL after navigation: {self.driver.current_url}")

            # Restore session data if using persistent profile
            if self.persistent:
                self.restore_session_data()

            # Handle advertisement popup if present
            self.handle_advertisement_popup()

            # Check if we're on login page or already logged in (redirected to homepage)
            current_url = self.driver.current_url.lower()
            if "prijava" in current_url:
                self.logger.info("✅ Successfully reached login page")
                return True
            elif current_url.startswith(self.base_url.lower()):
                self.logger.info("✅ Redirected to Njuskalo domain - checking login status...")
                # Check if we're actually logged in
                if self._check_if_already_logged_in():
                    self.logger.info("🎉 Already logged in! Skipping login process")
                    return True
                else:
                    self.logger.info("🔄 Not logged in, trying alternative login approaches")

                    # Try different login URL patterns
                    login_urls = [
                        f"{self.base_url}/prijava",
                        f"{self.base_url}/login",
                        f"{self.base_url}/korisnici/prijava"
                    ]

                    for url in login_urls:
                        self.logger.info(f"🔄 Trying login URL: {url}")
                        self.driver.get(url)
                        time.sleep(random.uniform(1, 2))

                        if "prijava" in self.driver.current_url.lower() or "login" in self.driver.current_url.lower():
                            self.logger.info(f"✅ Successfully reached login page: {self.driver.current_url}")
                            return True

                    # If still not on login page, check if we can find login link on current page
                    self.logger.info("🔍 Looking for login link on current page...")
                    login_link_selectors = [
                        "a[href*='prijava']",
                        "a[href*='login']",
                        "//a[contains(text(), 'Prijavi se')]",
                        "//a[contains(text(), 'Login')]"
                    ]

                    for selector in login_link_selectors:
                        try:
                            if selector.startswith("//"):
                                element = self.driver.find_element(By.XPATH, selector)
                            else:
                                element = self.driver.find_element(By.CSS_SELECTOR, selector)

                            if element.is_displayed():
                                self.logger.info(f"🔗 Found login link: {selector}")
                                element.click()
                                time.sleep(random.uniform(1, 2))
                                if "prijava" in self.driver.current_url.lower():
                                    return True
                        except:
                            continue

                    self.logger.warning(f"⚠️ Unable to reach login page from: {self.driver.current_url}")
                    return False
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

            # Check if already logged in first
            if self._check_if_already_logged_in():
                self.logger.info("🎉 Already logged in! Skipping login form")
                return True

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

                # Wait for initial response
                self.logger.info("⏳ Waiting for login response...")
                time.sleep(random.uniform(3, 6))

                # Handle any popups that might appear after login
                self.handle_advertisement_popup()

                # Check if 2FA is required
                if self._check_2fa_required():
                    self.logger.info("🔐 Two-factor authentication required")
                    if not self._handle_2fa():
                        self.logger.error("❌ 2FA failed")
                        return False

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

    def _check_2fa_required(self) -> bool:
        """Check if two-factor authentication is required"""
        try:
            # Look for 2FA step button
            tfa_button_selector = ".form-action.form-action--submit.button-standard.button-standard--alpha.button-standard--full.TwoFactorAuthentication-stepNextAction"

            try:
                tfa_button = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, tfa_button_selector))
                )
                if tfa_button.is_displayed():
                    self.logger.info("🔐 Two-factor authentication step detected")
                    return True
            except TimeoutException:
                # Also check for alternative 2FA indicators
                tfa_indicators = [
                    "[class*='TwoFactor']",
                    "[class*='verification']",
                    "input[placeholder*='kod']",
                    "input[placeholder*='code']"
                ]

                for indicator in tfa_indicators:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, indicator)
                        if element.is_displayed():
                            self.logger.info(f"🔐 2FA indicator found: {indicator}")
                            return True
                    except NoSuchElementException:
                        continue

            return False

        except Exception as e:
            self.logger.error(f"❌ Error checking 2FA requirement: {e}")
            return False

    def _handle_2fa(self) -> bool:
        """Handle two-factor authentication process"""
        try:
            self.logger.info("🔐 Handling two-factor authentication...")

            # Step 1: Click the "Next Step" button to trigger 2FA
            tfa_step_button_selector = ".form-action.form-action--submit.button-standard.button-standard--alpha.button-standard--full.TwoFactorAuthentication-stepNextAction"

            try:
                tfa_step_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, tfa_step_button_selector))
                )

                self.logger.info("📱 Clicking 2FA step button to request code...")
                self._human_like_mouse_movement(tfa_step_button)
                time.sleep(random.uniform(1, 2))
                tfa_step_button.click()

            except TimeoutException:
                self.logger.error("❌ 2FA step button not found")
                return False

            # Wait for the code input form to appear
            time.sleep(random.uniform(2, 4))

            # Step 2: Handle code input (different for test vs production)
            if self._is_test_environment():
                return self._handle_2fa_test_mode()
            else:
                return self._handle_2fa_production_mode()

        except Exception as e:
            self.logger.error(f"❌ 2FA handling failed: {e}")
            return False

    def _is_test_environment(self) -> bool:
        """Check if we're in test environment (based on test_mode parameter or username)"""
        if hasattr(self, 'test_mode') and self.test_mode:
            return True

        # Fallback: check username
        test_usernames = ["test", "srdjanmsd", "testuser"]
        return self.username.lower() in test_usernames

    def _handle_2fa_test_mode(self) -> bool:
        """Handle 2FA in test mode - wait for user input"""
        try:
            self.logger.info("🧪 Test mode: Waiting for manual code input...")

            # Look for code input field
            code_input_selectors = [
                "input[placeholder*='kod']",
                "input[placeholder*='code']",
                "input[name*='verification']",
                "input[name*='kod']",
                "[class*='TwoFactor'] input[type='text']",
                "[class*='TwoFactor'] input[type='number']"
            ]

            code_input = None
            for selector in code_input_selectors:
                try:
                    code_input = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    self.logger.info(f"✅ Found code input field: {selector}")
                    break
                except TimeoutException:
                    continue

            if not code_input:
                self.logger.error("❌ Code input field not found")
                return False

            # In test mode, wait for user to manually enter the code
            print("\n" + "="*60)
            print("🔐 TWO-FACTOR AUTHENTICATION REQUIRED")
            print("="*60)
            print("Please check your phone/email for the verification code.")
            print("Enter the code in the browser window and press Enter here when done.")
            print("="*60)

            try:
                input("Press Enter when you have entered the code in the browser...")
            except KeyboardInterrupt:
                self.logger.info("👋 2FA interrupted by user")
                return False

            # Look for and click submit button
            return self._click_2fa_submit_button()

        except Exception as e:
            self.logger.error(f"❌ 2FA test mode failed: {e}")
            return False

    def _handle_2fa_production_mode(self) -> bool:
        """Handle 2FA in production mode - get code from database"""
        try:
            self.logger.info("🏭 Production mode: Waiting for database code...")

            # Check if UUID is available for database lookup
            if not self.user_uuid:
                self.logger.error("❌ No UUID provided for database lookup in production mode")
                self.logger.info("💡 Falling back to test mode for manual code entry")
                return self._handle_2fa_test_mode()

            # Wait 15 minutes for the code to appear in database
            max_wait_time = 15 * 60  # 15 minutes in seconds
            check_interval = 30  # Check every 30 seconds

            self.logger.info("⏰ Waiting up to 15 minutes for verification code in database...")

            start_time = time.time()
            code = None

            while (time.time() - start_time) < max_wait_time:
                code = self._get_2fa_code_from_database()
                if code:
                    break

                remaining_time = max_wait_time - (time.time() - start_time)
                self.logger.info(f"⏳ No code yet, checking again in {check_interval}s (remaining: {int(remaining_time/60)}m {int(remaining_time%60)}s)")
                time.sleep(check_interval)

            if not code:
                self.logger.error("❌ Timeout waiting for 2FA code in database")
                return False

            # Enter the code
            return self._enter_2fa_code(code)

        except Exception as e:
            self.logger.error(f"❌ 2FA production mode failed: {e}")
            return False

    def _get_2fa_code_from_database(self) -> str:
        """Get 2FA code from database users table by UUID"""
        try:
            import pymysql
            import json
            import os

            self.logger.info(f"🔍 Retrieving 2FA code for UUID: {self.user_uuid}")

            # Database connection configuration (using existing DATABASE_* variables)
            db_config = {
                'host': os.getenv('DATABASE_HOST', 'localhost'),
                'port': int(os.getenv('DATABASE_PORT', 3306)),
                'user': os.getenv('DATABASE_USER', 'root'),
                'password': os.getenv('DATABASE_PASSWORD', ''),
                'database': os.getenv('DATABASE_NAME', 'njuskalohr'),
                'charset': 'utf8mb4'
            }

            self.logger.debug(f"🔗 Connecting to database: {db_config['host']}")

            connection = pymysql.connect(**db_config)

            try:
                with connection.cursor() as cursor:
                    # Get user by UUID from users table (UUID is stored as binary(16))
                    # First try to convert UUID string to binary format for lookup
                    import uuid as uuid_lib

                    try:
                        # Convert UUID string to binary format
                        uuid_obj = uuid_lib.UUID(self.user_uuid)
                        uuid_binary = uuid_obj.bytes
                    except ValueError:
                        self.logger.error(f"❌ Invalid UUID format: {self.user_uuid}")
                        return None

                    # Try multiple possible columns that might contain JSON data
                    json_columns = ['njuskalo', 'profile', 'avtonet']
                    user_data = None
                    used_column = None

                    for column in json_columns:
                        sql = f"SELECT {column} FROM users WHERE uuid = %s AND {column} IS NOT NULL LIMIT 1"
                        cursor.execute(sql, (uuid_binary,))
                        result = cursor.fetchone()

                        if result and result[0]:
                            user_data = result[0]
                            used_column = column
                            self.logger.debug(f"📄 Found data in column '{column}': {user_data}")
                            break

                    if not user_data:
                        # Also try with UUID as string (in case it's stored differently)
                        for column in json_columns:
                            sql = f"SELECT {column} FROM users WHERE HEX(uuid) = %s AND {column} IS NOT NULL LIMIT 1"
                            cursor.execute(sql, (self.user_uuid.replace('-', '').upper(),))
                            result = cursor.fetchone()

                            if result and result[0]:
                                user_data = result[0]
                                used_column = column
                                self.logger.debug(f"📄 Found data in column '{column}' (string lookup): {user_data}")
                                break

                    if not user_data:
                        self.logger.warning(f"⚠️ No user found with UUID: {self.user_uuid}")
                        return None

                    self.logger.info(f"📄 Retrieved data from '{used_column}' column")

                    # Parse JSON data
                    try:
                        if isinstance(user_data, str):
                            user_info = json.loads(user_data)
                        else:
                            user_info = user_data

                        # Extract code from JSON structure
                        verification_code = None

                        if isinstance(user_info, list) and len(user_info) > 0:
                            # If it's an array, get the first item
                            user_obj = user_info[0]
                            verification_code = user_obj.get('code')
                        elif isinstance(user_info, dict):
                            # If it's already a dict, use it directly
                            verification_code = user_info.get('code')
                        else:
                            self.logger.error(f"❌ Unexpected user data format: {type(user_info)}")
                            return None

                        # Get the verification code
                        if verification_code:
                            self.logger.info(f"✅ Found 2FA code: {verification_code}")
                            return str(verification_code)
                        else:
                            self.logger.info("ℹ️ No verification code found in user data")
                            return None

                    except json.JSONDecodeError as e:
                        self.logger.error(f"❌ Failed to parse JSON data from '{used_column}': {e}")
                        self.logger.debug(f"Raw data: {user_data}")
                        return None

            finally:
                connection.close()
                self.logger.debug("🔗 Database connection closed")

        except pymysql.Error as e:
            self.logger.error(f"❌ MySQL error: {e}")
            return None
        except ImportError:
            self.logger.error("❌ PyMySQL not installed. Install with: pip install pymysql")
            return None
        except Exception as e:
            self.logger.error(f"❌ Error getting code from database: {e}")
            return None

    def _enter_2fa_code(self, code: str) -> bool:
        """Enter the 2FA code and submit"""
        try:
            self.logger.info(f"🔑 Entering 2FA code: {code}")

            # Find code input field
            code_input_selectors = [
                "input[placeholder*='kod']",
                "input[placeholder*='code']",
                "input[name*='verification']",
                "input[name*='kod']",
                "[class*='TwoFactor'] input[type='text']",
                "[class*='TwoFactor'] input[type='number']"
            ]

            code_input = None
            for selector in code_input_selectors:
                try:
                    code_input = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    break
                except TimeoutException:
                    continue

            if not code_input:
                self.logger.error("❌ Code input field not found")
                return False

            # Clear and enter code with human-like behavior
            code_input.clear()
            time.sleep(random.uniform(0.5, 1))

            for digit in code:
                code_input.send_keys(digit)
                time.sleep(random.uniform(0.1, 0.3))

            time.sleep(random.uniform(1, 2))

            # Click submit button
            return self._click_2fa_submit_button()

        except Exception as e:
            self.logger.error(f"❌ Error entering 2FA code: {e}")
            return False

    def _click_2fa_submit_button(self) -> bool:
        """Click the 2FA submit button"""
        try:
            submit_button_selector = ".form-action.form-action--submit.button-standard.button-standard--alpha.button-standard--full.TwoFactorAuthentication-submitAction"

            submit_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, submit_button_selector))
            )

            self.logger.info("✅ Clicking 2FA submit button...")
            self._human_like_mouse_movement(submit_button)
            time.sleep(random.uniform(1, 2))
            submit_button.click()

            # Wait for submission to complete
            time.sleep(random.uniform(3, 6))

            self.logger.info("🎉 2FA submission completed!")
            return True

        except TimeoutException:
            self.logger.error("❌ 2FA submit button not found")
            return False
        except Exception as e:
            self.logger.error(f"❌ Error clicking 2FA submit button: {e}")
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

    def submit_ad(self) -> bool:
        """Submit a new ad through the category selection process"""
        try:
            self.logger.info("📝 Starting ad submission process...")

            # Step 1: Click on "Predaj oglas" button
            self.logger.info("🔍 Looking for 'Predaj oglas' button...")

            try:
                # Wait for the "Predaj oglas" button to be present and clickable
                predaj_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "span.Header-submitClassifiedInner"))
                )

                # Human-like mouse movement before clicking
                self._human_like_mouse_movement(predaj_button)
                time.sleep(random.uniform(0.5, 1.2))

                predaj_button.click()
                self.logger.info("✅ Clicked 'Predaj oglas' button")

                # Wait for page transition
                time.sleep(random.uniform(2, 4))

            except Exception as e:
                self.logger.error(f"❌ Failed to click 'Predaj oglas' button: {e}")
                return False

            # Step 2: Select "Auto Moto" category
            self.logger.info("🔍 Looking for 'Auto Moto' category...")

            try:
                # Wait for the Auto Moto category to be clickable
                auto_moto_label = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "label[for='submitCategorySelectorLevelCategory2']"))
                )

                # Human-like mouse movement before clicking
                self._human_like_mouse_movement(auto_moto_label)
                time.sleep(random.uniform(0.5, 1.2))

                auto_moto_label.click()
                self.logger.info("✅ Selected 'Auto Moto' category")

                # Wait for subcategories to load
                time.sleep(random.uniform(1.5, 2.5))

            except Exception as e:
                self.logger.error(f"❌ Failed to select 'Auto Moto' category: {e}")
                return False

            # Step 3: Select "Osobni automobili" subcategory
            self.logger.info("🔍 Looking for 'Osobni automobili' subcategory...")

            try:
                # Wait for the Osobni automobili subcategory to be clickable
                osobni_label = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "label[for='submitCategorySelectorLevelCategory13688']"))
                )

                # Human-like mouse movement before clicking
                self._human_like_mouse_movement(osobni_label)
                time.sleep(random.uniform(0.5, 1.2))

                osobni_label.click()
                self.logger.info("✅ Selected 'Osobni automobili' subcategory")

                # Wait for the form to update and sub-subcategories to load
                time.sleep(random.uniform(1.5, 2.5))

            except Exception as e:
                self.logger.error(f"❌ Failed to select 'Osobni automobili' subcategory: {e}")
                return False

            # Step 3.5: Select "Rabljeni automobili" (Used cars) sub-subcategory
            self.logger.info("🔍 Looking for 'Rabljeni automobili' sub-subcategory...")

            try:
                # Wait for the Rabljeni automobili sub-subcategory to be clickable
                rabljeni_label = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "label[for='submitCategorySelectorLevelCategory7']"))
                )

                # Human-like mouse movement before clicking
                self._human_like_mouse_movement(rabljeni_label)
                time.sleep(random.uniform(0.5, 1.2))

                rabljeni_label.click()
                self.logger.info("✅ Selected 'Rabljeni automobili' sub-subcategory")

                # Wait for the form to update
                time.sleep(random.uniform(1.5, 2.5))

            except Exception as e:
                self.logger.error(f"❌ Failed to select 'Rabljeni automobili' sub-subcategory: {e}")
                return False

            # Step 4: Click "Nastavi" button
            self.logger.info("🔍 Looking for 'Nastavi' button...")

            try:
                # Wait for the Nastavi button to be clickable
                nastavi_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.SubmitCategorySelector-submit"))
                )

                # Human-like mouse movement before clicking
                self._human_like_mouse_movement(nastavi_button)
                time.sleep(random.uniform(0.5, 1.2))

                nastavi_button.click()
                self.logger.info("✅ Clicked 'Nastavi' button")

                # Wait for the next page to load
                time.sleep(random.uniform(2, 4))

                # Step 5: Click "Odaberi" button for advertising package
                if not self._click_advertising_package_button():
                    return False

                # Step 6: Fill the ad form with data from database
                if not self._fill_ad_form():
                    return False

                # Take screenshot after successful completion
                self.take_screenshot("ad_submission_complete")

                return True

            except Exception as e:
                self.logger.error(f"❌ Failed to click 'Nastavi' button: {e}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Ad submission process failed: {e}")
            # Take screenshot on error for debugging
            self.take_screenshot("ad_submission_error")
            return False

    def _get_ad_data_from_database(self) -> dict:
        """Get ad data from database with status validation"""
        try:
            import pymysql
            import json
            import os

            # Check if we have UUID for database lookup
            if not self.user_uuid:
                if self._is_test_environment():
                    # In test mode, prompt for UUID
                    print("\n" + "="*60)
                    print("🔍 AD DATA RETRIEVAL - TEST MODE")
                    print("="*60)
                    print("Enter the UUID of the ad you want to publish:")
                    print("="*60)

                    try:
                        uuid_input = input("UUID: ").strip()
                        if not uuid_input:
                            self.logger.error("❌ No UUID provided")
                            return None
                        self.user_uuid = uuid_input
                    except KeyboardInterrupt:
                        self.logger.info("👋 Ad data retrieval interrupted by user")
                        return None
                else:
                    self.logger.error("❌ No UUID provided for database lookup in production mode")
                    return None

            self.logger.info(f"🔍 Retrieving ad data for UUID: {self.user_uuid}")

            # Database connection configuration (using existing DATABASE_* variables)
            db_config = {
                'host': os.getenv('DATABASE_HOST', 'localhost'),
                'port': int(os.getenv('DATABASE_PORT', 3306)),
                'user': os.getenv('DATABASE_USER', 'root'),
                'password': os.getenv('DATABASE_PASSWORD', ''),
                'database': os.getenv('DATABASE_NAME', 'njuskalohr'),
                'charset': 'utf8mb4'
            }

            self.logger.debug(f"🔗 Connecting to database: {db_config['host']}")

            connection = pymysql.connect(**db_config)

            try:
                with connection.cursor() as cursor:
                    # Get ad by UUID from adItem table
                    import uuid as uuid_lib

                    try:
                        # Convert UUID string to binary format
                        uuid_obj = uuid_lib.UUID(self.user_uuid)
                        uuid_binary = uuid_obj.bytes
                    except ValueError:
                        self.logger.error(f"❌ Invalid UUID format: {self.user_uuid}")
                        return None

                    # Query adItem table for ad data with status validation
                    sql = """
                        SELECT uuid, content, status, publishNjuskalo
                        FROM adItem
                        WHERE uuid = %s
                        LIMIT 1
                    """
                    cursor.execute(sql, (uuid_binary,))
                    result = cursor.fetchone()

                    if not result:
                        # Also try with UUID as string (in case it's stored differently)
                        sql = """
                            SELECT uuid, content, status, publishNjuskalo
                            FROM adItem
                            WHERE HEX(uuid) = %s
                            LIMIT 1
                        """
                        cursor.execute(sql, (self.user_uuid.replace('-', '').upper(),))
                        result = cursor.fetchone()

                    if not result:
                        self.logger.error(f"❌ No ad found with UUID: {self.user_uuid}")
                        return None

                    uuid_col, content_col, status_col, publish_njuskalo_col = result

                    # Status validation - check if ad is published and publishNjuskalo is true
                    if status_col != "PUBLISHED":
                        self.logger.error(f"❌ Ad status is '{status_col}', expected 'PUBLISHED'")
                        self.logger.error("❌ Cannot proceed with ad submission - ad must have status='PUBLISHED'")
                        return None

                    if not publish_njuskalo_col:
                        self.logger.error(f"❌ publishNjuskalo is '{publish_njuskalo_col}', expected True")
                        self.logger.error("❌ Cannot proceed with ad submission - publishNjuskalo must be True")
                        return None

                    self.logger.info(f"✅ Ad status validation passed - status='PUBLISHED', publishNjuskalo=True")

                    # Parse JSON content
                    try:
                        if isinstance(content_col, str):
                            ad_content = json.loads(content_col)
                        else:
                            ad_content = content_col

                        if not ad_content:
                            self.logger.error("❌ Ad content is empty")
                            return None

                        self.logger.info(f"✅ Retrieved ad content: {len(str(ad_content))} characters")
                        self.logger.debug(f"Ad content preview: {str(ad_content)[:200]}...")

                        return {
                            'uuid': self.user_uuid,
                            'content': ad_content,
                            'status': status_col,
                            'publishNjuskalo': publish_njuskalo_col
                        }

                    except json.JSONDecodeError as e:
                        self.logger.error(f"❌ Failed to parse JSON content: {e}")
                        return None

            finally:
                connection.close()
                self.logger.debug("🔗 Database connection closed")

        except pymysql.Error as e:
            self.logger.error(f"❌ MySQL error: {e}")
            return None
        except ImportError:
            self.logger.error("❌ PyMySQL not installed. Install with: pip install pymysql")
            return None
        except Exception as e:
            self.logger.error(f"❌ Error getting ad data from database: {e}")
            return None

    def _click_advertising_package_button(self) -> bool:
        """Click the 'Odaberi' advertising package button"""
        try:
            self.logger.info("🔍 Looking for 'Odaberi' advertising package button...")

            # Wait for the advertising package selection page to load
            time.sleep(random.uniform(2, 3))

            # Look for the specific submit button for advertising package
            odaberi_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[type="submit"][id="submit-button-01"]'))
            )

            # Human-like mouse movement before clicking
            self._human_like_mouse_movement(odaberi_button)
            time.sleep(random.uniform(0.5, 1.2))

            odaberi_button.click()
            self.logger.info("✅ Clicked 'Odaberi' advertising package button")

            # Wait for the form page to load
            time.sleep(random.uniform(2, 4))

            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to click 'Odaberi' button: {e}")
            self.take_screenshot("odaberi_button_error")
            return False

    def _fill_ad_form(self) -> bool:
        """Fill the ad form with data from database"""
        try:
            self.logger.info("📝 Starting ad form filling process...")

            # Step 1: Get ad data from database with status validation
            ad_data = self._get_ad_data_from_database()
            if not ad_data:
                self.logger.error("❌ Failed to retrieve valid ad data - cannot proceed with form filling")
                return False

            # Extract content for form filling
            ad_content = ad_data['content']
            self.logger.info(f"✅ Ad data validated - proceeding with form filling for UUID: {ad_data['uuid']}")

            # Wait for form to be fully loaded
            time.sleep(random.uniform(2, 3))

            # Take screenshot of the loaded form for debugging
            self.take_screenshot("ad_form_loaded")

            # Step 2: Fill basic ad information
            if not self._fill_basic_ad_info(ad_content):
                self.logger.error("❌ Failed to fill basic ad information")
                return False

            # Step 3: Fill vehicle details
            if not self._fill_vehicle_details(ad_content):
                self.logger.error("❌ Failed to fill vehicle details")
                return False

            # Step 4: Fill contact information
            if not self._fill_contact_info(ad_content):
                self.logger.error("❌ Failed to fill contact information")
                return False

            # Step 5: Fill additional options (features)
            if not self._fill_vehicle_features(ad_content):
                self.logger.warning("⚠️ Some vehicle features may not have been filled")
                # Don't fail the entire process for feature filling issues

            # Step 6: Upload images (if available)
            if not self._upload_images(ad_content):
                self.logger.warning("⚠️ Image upload failed or no images available")
                # Don't fail the entire process for image upload issues

            # Step 7: Final validation and submission preparation
            if not self._prepare_form_submission(ad_content):
                self.logger.error("❌ Form preparation for submission failed")
                return False

            # Take screenshot after successful form completion
            self.take_screenshot("ad_form_completed")

            self.logger.info("🎉 Ad form filling completed successfully!")
            return True

        except Exception as e:
            self.logger.error(f"❌ Ad form filling failed: {e}")
            self.take_screenshot("ad_form_error")
            return False

    def _fill_basic_ad_info(self, ad_content: dict) -> bool:
        """Fill basic ad information (price, description, etc.)"""
        try:
            self.logger.info("💰 Filling basic ad information...")

            # Fill price
            if 'price' in ad_content and ad_content['price']:
                price_field = self._find_form_field([
                    'input[name*="price"]',
                    'input[id*="price"]',
                    'input[placeholder*="cijena"]',
                    'input[placeholder*="Cijena"]',
                    'input[type="number"]'
                ])

                if price_field:
                    self._human_like_typing(price_field, str(ad_content['price']))
                    self.logger.info(f"✅ Price filled: {ad_content['price']}")
                else:
                    self.logger.warning("⚠️ Price field not found")

            # Fill description
            if 'description' in ad_content and ad_content['description']:
                desc_field = self._find_form_field([
                    'textarea[name*="description"]',
                    'textarea[id*="description"]',
                    'textarea[name*="opis"]',
                    'textarea[placeholder*="opis"]'
                ])

                if desc_field:
                    # Clean description text
                    description = ad_content['description'].strip()
                    self._human_like_typing(desc_field, description, 0.02, 0.08)  # Faster typing for long text
                    self.logger.info(f"✅ Description filled: {len(description)} characters")
                else:
                    self.logger.warning("⚠️ Description field not found")

            return True

        except Exception as e:
            self.logger.error(f"❌ Error filling basic ad info: {e}")
            return False

    def _fill_vehicle_details(self, ad_content: dict) -> bool:
        """Fill vehicle-specific details (make, model, year, etc.)"""
        try:
            self.logger.info("🚗 Filling vehicle details...")

            # Vehicle manufacturer/make
            if 'vehicleManufacturerName' in ad_content:
                make_field = self._find_form_field([
                    'select[name*="make"]',
                    'select[name*="manufacturer"]',
                    'input[name*="make"]',
                    'input[name*="manufacturer"]'
                ])

                if make_field:
                    if make_field.tag_name == 'select':
                        self._select_dropdown_option(make_field, ad_content['vehicleManufacturerName'])
                    else:
                        self._human_like_typing(make_field, ad_content['vehicleManufacturerName'])
                    self.logger.info(f"✅ Vehicle make filled: {ad_content['vehicleManufacturerName']}")

            # Vehicle model
            if 'vehicleBaseModelName' in ad_content:
                model_field = self._find_form_field([
                    'select[name*="model"]',
                    'input[name*="model"]'
                ])

                if model_field:
                    if model_field.tag_name == 'select':
                        # Wait for model dropdown to load after make selection
                        time.sleep(random.uniform(1, 2))
                        self._select_dropdown_option(model_field, ad_content['vehicleBaseModelName'])
                    else:
                        self._human_like_typing(model_field, ad_content['vehicleBaseModelName'])
                    self.logger.info(f"✅ Vehicle model filled: {ad_content['vehicleBaseModelName']}")

            # Year of manufacture
            if 'vehicleTrimYear' in ad_content:
                year_field = self._find_form_field([
                    'select[name*="year"]',
                    'select[name*="godina"]',
                    'input[name*="year"]',
                    'input[name*="godina"]'
                ])

                if year_field:
                    if year_field.tag_name == 'select':
                        self._select_dropdown_option(year_field, str(ad_content['vehicleTrimYear']))
                    else:
                        self._human_like_typing(year_field, str(ad_content['vehicleTrimYear']))
                    self.logger.info(f"✅ Vehicle year filled: {ad_content['vehicleTrimYear']}")

            # Engine displacement
            if 'vehicleEngineDisplacement' in ad_content:
                displacement_field = self._find_form_field([
                    'input[name*="displacement"]',
                    'input[name*="engine"]',
                    'input[name*="ccm"]'
                ])

                if displacement_field:
                    self._human_like_typing(displacement_field, str(ad_content['vehicleEngineDisplacement']))
                    self.logger.info(f"✅ Engine displacement filled: {ad_content['vehicleEngineDisplacement']}")

            # Engine power
            if 'vehicleEnginePower' in ad_content:
                power_field = self._find_form_field([
                    'input[name*="power"]',
                    'input[name*="kw"]',
                    'input[name*="snaga"]'
                ])

                if power_field:
                    self._human_like_typing(power_field, str(ad_content['vehicleEnginePower']))
                    self.logger.info(f"✅ Engine power filled: {ad_content['vehicleEnginePower']} kW")

            # Mileage/Odometer
            if 'vehicleCurrentOdometer' in ad_content:
                mileage_field = self._find_form_field([
                    'input[name*="mileage"]',
                    'input[name*="odometer"]',
                    'input[name*="km"]',
                    'input[name*="kilometraza"]'
                ])

                if mileage_field:
                    self._human_like_typing(mileage_field, str(ad_content['vehicleCurrentOdometer']))
                    self.logger.info(f"✅ Mileage filled: {ad_content['vehicleCurrentOdometer']} km")

            # Fuel type
            if 'vehicleFuelType' in ad_content:
                fuel_field = self._find_form_field([
                    'select[name*="fuel"]',
                    'select[name*="gorivo"]'
                ])

                if fuel_field:
                    fuel_mapping = {
                        'DIESEL': ['Diesel', 'DIESEL', 'diesel'],
                        'PETROL': ['Benzin', 'PETROL', 'petrol', 'Gasoline'],
                        'HYBRID': ['Hibrid', 'HYBRID', 'hybrid'],
                        'ELECTRIC': ['Električni', 'ELECTRIC', 'electric']
                    }
                    fuel_options = fuel_mapping.get(ad_content['vehicleFuelType'], [ad_content['vehicleFuelType']])
                    self._select_dropdown_option(fuel_field, fuel_options)
                    self.logger.info(f"✅ Fuel type filled: {ad_content['vehicleFuelType']}")

            # Transmission type
            if 'vehicleTransmissionType' in ad_content:
                transmission_field = self._find_form_field([
                    'select[name*="transmission"]',
                    'select[name*="mjenjac"]'
                ])

                if transmission_field:
                    transmission_mapping = {
                        'Automatic': ['Automatski', 'Automatic', 'automatski'],
                        'Manual': ['Ručni', 'Manual', 'ručni', 'Manualni']
                    }
                    trans_options = transmission_mapping.get(ad_content['vehicleTransmissionType'], [ad_content['vehicleTransmissionType']])
                    self._select_dropdown_option(transmission_field, trans_options)
                    self.logger.info(f"✅ Transmission filled: {ad_content['vehicleTransmissionType']}")

            # VIN number
            if 'vin' in ad_content and ad_content['vin']:
                vin_field = self._find_form_field([
                    'input[name*="vin"]',
                    'input[name*="VIN"]',
                    'input[placeholder*="vin"]'
                ])

                if vin_field:
                    self._human_like_typing(vin_field, ad_content['vin'])
                    self.logger.info(f"✅ VIN filled: {ad_content['vin']}")

            return True

        except Exception as e:
            self.logger.error(f"❌ Error filling vehicle details: {e}")
            return False

    def _fill_contact_info(self, ad_content: dict) -> bool:
        """Fill contact information"""
        try:
            self.logger.info("📞 Filling contact information...")

            if 'contact' not in ad_content:
                self.logger.warning("⚠️ No contact information found in ad data")
                return True

            contact = ad_content['contact']

            # Contact name
            if 'name' in contact and contact['name']:
                name_field = self._find_form_field([
                    'input[name*="contact_name"]',
                    'input[name*="name"]',
                    'input[name*="ime"]',
                    'input[placeholder*="ime"]'
                ])

                if name_field:
                    self._human_like_typing(name_field, contact['name'])
                    self.logger.info(f"✅ Contact name filled: {contact['name']}")

            # Phone number
            if 'phone' in contact and contact['phone']:
                # Get first non-empty phone number
                phone_number = None
                if isinstance(contact['phone'], list):
                    for phone in contact['phone']:
                        if phone and phone.strip():
                            phone_number = phone.strip()
                            break
                else:
                    phone_number = contact['phone']

                if phone_number:
                    phone_field = self._find_form_field([
                        'input[name*="phone"]',
                        'input[name*="telefon"]',
                        'input[type="tel"]'
                    ])

                    if phone_field:
                        self._human_like_typing(phone_field, phone_number)
                        self.logger.info(f"✅ Phone number filled: {phone_number}")

            # Email address
            if 'email' in contact and contact['email']:
                # Get first non-empty email
                email_address = None
                if isinstance(contact['email'], list):
                    for email in contact['email']:
                        if email and email.strip():
                            email_address = email.strip()
                            break
                else:
                    email_address = contact['email']

                if email_address:
                    email_field = self._find_form_field([
                        'input[name*="email"]',
                        'input[type="email"]'
                    ])

                    if email_field:
                        self._human_like_typing(email_field, email_address)
                        self.logger.info(f"✅ Email filled: {email_address}")

            # Location
            if 'location' in contact and contact['location']:
                location_field = self._find_form_field([
                    'input[name*="location"]',
                    'input[name*="lokacija"]',
                    'input[name*="mjesto"]',
                    'select[name*="location"]'
                ])

                if location_field:
                    if location_field.tag_name == 'select':
                        self._select_dropdown_option(location_field, contact['location'])
                    else:
                        self._human_like_typing(location_field, contact['location'])
                    self.logger.info(f"✅ Location filled: {contact['location']}")

            return True

        except Exception as e:
            self.logger.error(f"❌ Error filling contact info: {e}")
            return False

    def _fill_vehicle_features(self, ad_content: dict) -> bool:
        """Fill vehicle features/equipment checkboxes"""
        try:
            self.logger.info("🔧 Filling vehicle features...")

            if 'features' not in ad_content or not ad_content['features']:
                self.logger.info("ℹ️ No features found in ad data")
                return True

            features_filled = 0
            features_total = len(ad_content['features'])

            for feature in ad_content['features']:
                if self._select_feature_checkbox(feature):
                    features_filled += 1

                # Small delay between feature selections
                time.sleep(random.uniform(0.1, 0.3))

            self.logger.info(f"✅ Features filled: {features_filled}/{features_total}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Error filling vehicle features: {e}")
            return False

    def _upload_images(self, ad_content: dict) -> bool:
        """Upload vehicle images (placeholder - implement based on available images)"""
        try:
            self.logger.info("📷 Processing image upload...")

            # Look for image upload field
            upload_field = self._find_form_field([
                'input[type="file"]',
                'input[name*="image"]',
                'input[name*="photo"]',
                'input[name*="slika"]'
            ])

            if upload_field:
                self.logger.info("📷 Image upload field found, but no images provided in ad data")
                # TODO: Implement actual image upload logic when images are available in ad_content
            else:
                self.logger.info("📷 No image upload field found")

            return True

        except Exception as e:
            self.logger.warning(f"⚠️ Image upload warning: {e}")
            return False

    def _prepare_form_submission(self, ad_content: dict) -> bool:
        """Prepare form for submission (final validation, terms acceptance, etc.)"""
        try:
            self.logger.info("📋 Preparing form for submission...")

            # Look for terms and conditions checkbox
            terms_checkbox = self._find_form_field([
                'input[type="checkbox"][name*="terms"]',
                'input[type="checkbox"][name*="uvjeti"]',
                'input[type="checkbox"][name*="agree"]',
                'input[type="checkbox"][id*="terms"]'
            ])

            if terms_checkbox and not terms_checkbox.is_selected():
                self._human_like_mouse_movement(terms_checkbox)
                terms_checkbox.click()
                self.logger.info("✅ Terms and conditions accepted")

            # Look for privacy policy checkbox
            privacy_checkbox = self._find_form_field([
                'input[type="checkbox"][name*="privacy"]',
                'input[type="checkbox"][name*="privatnost"]',
                'input[type="checkbox"][id*="privacy"]'
            ])

            if privacy_checkbox and not privacy_checkbox.is_selected():
                self._human_like_mouse_movement(privacy_checkbox)
                privacy_checkbox.click()
                self.logger.info("✅ Privacy policy accepted")

            # Final form validation
            self.logger.info("✅ Form ready for submission")
            return True

        except Exception as e:
            self.logger.error(f"❌ Error preparing form submission: {e}")
            return False

    def _find_form_field(self, selectors: list) -> WebElement:
        """Find form field using multiple selector strategies"""
        try:
            for selector in selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element.is_displayed() and element.is_enabled():
                        return element
                except NoSuchElementException:
                    continue
            return None
        except Exception as e:
            self.logger.debug(f"Field search error: {e}")
            return None

    def _select_dropdown_option(self, select_element: WebElement, options: Union[List[str], str]) -> bool:
        """Select option from dropdown by matching text"""
        try:
            if isinstance(options, str):
                options = [options]

            select = Select(select_element)

            for option_text in options:
                # Try exact match first
                try:
                    select.select_by_visible_text(option_text)
                    return True
                except NoSuchElementException:
                    pass

                # Try partial match
                for option in select.options:
                    if option_text.lower() in option.text.lower():
                        select.select_by_visible_text(option.text)
                        return True

            self.logger.debug(f"No matching option found for: {options}")
            return False

        except Exception as e:
            self.logger.debug(f"Dropdown selection error: {e}")
            return False

    def _select_feature_checkbox(self, feature_name: str) -> bool:
        """Find and select a feature checkbox by name"""
        try:
            # Search strategies for finding feature checkboxes
            search_strategies = [
                # By label text (most common)
                f"//label[contains(text(), '{feature_name}')]//input[@type='checkbox']",
                f"//label[contains(text(), '{feature_name}')]/input[@type='checkbox']",

                # By checkbox value or name attribute
                f"//input[@type='checkbox'][@value='{feature_name}']",
                f"//input[@type='checkbox'][contains(@name, '{feature_name.lower()}')]",

                # By ID matching feature name
                f"//input[@type='checkbox'][contains(@id, '{feature_name.lower()}')]",

                # Adjacent label approach
                f"//input[@type='checkbox'][following-sibling::label[contains(text(), '{feature_name}')]]",
                f"//input[@type='checkbox'][preceding-sibling::label[contains(text(), '{feature_name}')]]"
            ]

            for strategy in search_strategies:
                try:
                    checkbox = self.driver.find_element(By.XPATH, strategy)
                    if checkbox.is_displayed() and not checkbox.is_selected():
                        self._human_like_mouse_movement(checkbox)
                        checkbox.click()
                        self.logger.debug(f"✅ Feature selected: {feature_name}")
                        return True
                except NoSuchElementException:
                    continue

            self.logger.debug(f"⚠️ Feature checkbox not found: {feature_name}")
            return False

        except Exception as e:
            self.logger.debug(f"Feature selection error for '{feature_name}': {e}")
            return False

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
                self.logger.info("🎉 Login completed successfully!")
                self.logger.info(f"You are now logged in to Njuskalo as: {self.username}")

                # Step 7: Submit ad if enabled
                if self.submit_ad:
                    self.logger.info("📝 Proceeding with ad submission...")
                    ad_success = self.submit_ad()
                    if ad_success:
                        self.logger.info("🎉 Ad submission process completed successfully!")
                    else:
                        self.logger.error("❌ Ad submission failed")
                        return False

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
    parser.add_argument("--uuid", type=str,
                       help="UUID for persistent Firefox session (avoids confirmation codes)")
    parser.add_argument("--test-mode", action="store_true",
                       help="Enable test mode for 2FA (manual code input)")
    parser.add_argument("--submit-ad", action="store_true",
                       help="Enable ad submission after successful login")

    args = parser.parse_args()

    # Create stealth publish instance
    stealth_publish = NjuskaloStealthPublish(
        headless=not args.visible,
        use_tunnel=args.tunnel,
        username=args.username,
        password=args.password,
        persistent=not args.no_persistent,  # Persistent by default
        user_uuid=args.uuid,  # Pass UUID if provided
        test_mode=args.test_mode,  # Enable test mode if requested
        submit_ad=args.submit_ad  # Enable ad submission if requested
    )

    # Run publish process
    success = stealth_publish.run_stealth_publish()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()