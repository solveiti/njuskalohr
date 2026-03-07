#!/usr/bin/env python3
"""
Enhanced SSH Tunnel Integration for Njuskalo Scraper

This script uses the enhanced scraper with XML processing, auto moto detection,
and vehicle counting through SSH tunnels for better anonymity and stability.
"""

import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))

# Load VENV_PATH from .env file
env_file = os.path.join(script_dir, '.env')
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

venv_python = os.path.join(script_dir, venv_path, 'bin', 'python3')

# Check if we're already using the venv python or if we need to switch
current_python = sys.executable
is_venv_python = os.path.samefile(current_python, venv_python) if os.path.exists(venv_python) and os.path.exists(current_python) else False

if not is_venv_python and os.path.exists(venv_python):
    print(f"Restarting script in virtual environment: {venv_python}")
    print(f"Current Python: {current_python}")
    os.execv(venv_python, [venv_python] + sys.argv)
elif not os.path.exists(venv_python):
    print(f"Warning: Virtual environment not found at {venv_python}")

import time
import logging
from typing import Optional, Dict, List
from pathlib import Path

# Add current directory to Python path
sys.path.append(str(Path(__file__).parent))

# Sentry integration
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from dotenv import load_dotenv

load_dotenv()

# Initialize Sentry
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "1.0")),
        integrations=[LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)],
    )

# Import enhanced scraper
from enhanced_njuskalo_scraper import EnhancedNjuskaloScraper
from selenium.webdriver.firefox.options import Options
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
import tempfile
import random

# Import tunnel manager
try:
    from ssh_tunnel_manager import SSHTunnelManager
except ImportError:
    print("❌ Error: ssh_tunnel_manager.py not found in current directory")
    print("💡 Make sure ssh_tunnel_manager.py is in the same folder as this script")
    sys.exit(1)

logger = logging.getLogger(__name__)

class TunnelEnabledEnhancedScraper(EnhancedNjuskaloScraper):
    """Enhanced scraper with SSH tunnel support and vehicle counting"""

    DIRECT_CONNECTION = "__DIRECT__"

    def __init__(self, headless=False, use_database=True, tunnel_config_path=None, use_tunnels=True, preferred_tunnel=None):
        """
        Initialize enhanced scraper with SSH tunnel support

        Args:
            headless: Run browser in headless mode
            use_database: Save data to database
            tunnel_config_path: Path to tunnel configuration file
            use_tunnels: Enable/disable tunnel usage
            preferred_tunnel: Specific tunnel name to use (e.g., 'server2')
        """
        super().__init__(headless, use_database)
        self.use_tunnels = use_tunnels
        self.tunnel_config_path = tunnel_config_path or "tunnel_config.json"
        self.tunnel_manager = None
        self.current_tunnel = None
        self.socks_proxy_port = None
        self.preferred_tunnel = preferred_tunnel
        self.current_connection_mode = self.DIRECT_CONNECTION
        self.mix_direct_ip = use_tunnels and not bool(preferred_tunnel)
        self.stores_on_current_tunnel = 0
        self._next_rotation_after = random.randint(2, 5)

        if self.use_tunnels:
            self._setup_tunnel_manager()

    def _setup_tunnel_manager(self):
        """Initialize the SSH tunnel manager"""
        try:
            if not os.path.exists(self.tunnel_config_path):
                logger.error(f"❌ Tunnel config file not found: {self.tunnel_config_path}")
                self.use_tunnels = False
                return

            self.tunnel_manager = SSHTunnelManager(self.tunnel_config_path)
            logger.info("✅ Tunnel manager initialized with config: " + self.tunnel_config_path)
        except Exception as e:
            logger.error(f"❌ Failed to initialize tunnel manager: {e}")
            self.use_tunnels = False

    def _check_and_kill_port(self, port: int) -> bool:
        """Check if port is in use and kill the process using it"""
        import subprocess
        try:
            # Check if port is in use
            result = subprocess.run(
                ['lsof', '-ti', f':{port}'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                logger.warning(f"⚠️ Port {port} is already in use by PID(s): {', '.join(pids)}")

                # Kill the processes
                for pid in pids:
                    try:
                        subprocess.run(['kill', '-9', pid], timeout=5)
                        logger.info(f"✅ Killed process {pid} using port {port}")
                    except Exception as e:
                        logger.warning(f"Failed to kill process {pid}: {e}")

                # Wait a moment for port to be released
                time.sleep(1)
                return True
            return False
        except FileNotFoundError:
            # lsof not available, try netstat
            try:
                result = subprocess.run(
                    ['netstat', '-tlnp', '|', 'grep', f':{port}'],
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.stdout:
                    logger.warning(f"⚠️ Port {port} appears to be in use")
                    return False
            except:
                pass
            return False
        except Exception as e:
            logger.debug(f"Error checking port {port}: {e}")
            return False

    def _start_tunnel(self, tunnel_name: Optional[str] = None, exclude_current: bool = False) -> bool:
        """Start SSH tunnel and return success status"""
        if not self.use_tunnels or not self.tunnel_manager:
            return True

        try:
            # Get available tunnels
            tunnels = self.tunnel_manager.list_tunnels()
            if not tunnels:
                logger.error("❌ No tunnels configured")
                return False

            # Resolve target tunnel
            if tunnel_name:
                if tunnel_name not in tunnels:
                    logger.error(f"❌ Requested tunnel '{tunnel_name}' not found in config")
                    logger.info(f"Available tunnels: {', '.join(tunnels.keys())}")
                    return False
            elif self.preferred_tunnel:
                if self.preferred_tunnel in tunnels:
                    tunnel_name = self.preferred_tunnel
                    logger.info(f"🚇 Using preferred tunnel: {tunnel_name}")
                else:
                    logger.error(f"❌ Preferred tunnel '{self.preferred_tunnel}' not found in config")
                    logger.info(f"Available tunnels: {', '.join(tunnels.keys())}")
                    return False
            else:
                candidates = list(tunnels.keys())
                if exclude_current and self.current_tunnel and len(candidates) > 1:
                    candidates = [name for name in candidates if name != self.current_tunnel]
                tunnel_name = random.choice(candidates)
                logger.info(f"🚇 Starting SSH tunnel (random): {tunnel_name}")

            # Check if tunnel port is already in use and clean it up
            tunnel_config = tunnels[tunnel_name]
            local_port = tunnel_config['config']['local_port']
            if self._check_and_kill_port(local_port):
                logger.info(f"🧹 Cleaned up port {local_port}")

            # Start the tunnel
            success = self.tunnel_manager.establish_tunnel(tunnel_name)
            if success:
                proxy_settings = self.tunnel_manager.get_proxy_settings()
                self.socks_proxy_port = proxy_settings.get('local_port') if proxy_settings else None
                self.current_tunnel = tunnel_name
                self.current_connection_mode = tunnel_name
                logger.info(f"✅ SSH tunnel active: {tunnel_name} (SOCKS proxy on port {self.socks_proxy_port})")

                # Wait a moment for tunnel to stabilize (reduced)
                time.sleep(1.5)

                # Test tunnel connectivity
                if self._test_tunnel_connectivity():
                    logger.info("🎉 SSH tunnel is active - traffic will be routed through remote server")
                    return True
                else:
                    logger.error("❌ Tunnel connectivity test failed")
                    return False
            else:
                logger.error(f"❌ Failed to start tunnel: {tunnel_name}")
                return False

        except Exception as e:
            logger.error(f"❌ Error starting tunnel: {e}")
            return False

    def _test_tunnel_connectivity(self) -> bool:
        """Test if the tunnel is working properly"""
        if not self.socks_proxy_port:
            return False

        try:
            import socket
            # Test if SOCKS port is accessible
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('127.0.0.1', self.socks_proxy_port))
            sock.close()
            return result == 0
        except:
            return False

    def _stop_tunnel(self):
        """Stop the current SSH tunnel"""
        if self.tunnel_manager and self.current_tunnel:
            try:
                logger.info(f"🛑 Stopping SSH tunnel: {self.current_tunnel}")
                self.tunnel_manager.close_tunnel(self.current_tunnel)
            except Exception as e:
                logger.warning(f"⚠️ Error stopping tunnel: {e}")
            finally:
                self.current_tunnel = None
                self.socks_proxy_port = None

    def _switch_to_direct_connection(self):
        """Switch scraping traffic back to the server's original IP (no SOCKS proxy)."""
        if self.current_tunnel:
            self._stop_tunnel()
        self.current_tunnel = None
        self.socks_proxy_port = None
        self.current_connection_mode = self.DIRECT_CONNECTION
        logger.info("🌐 Using direct connection (original server IP)")

    def _configured_tunnel_names(self) -> List[str]:
        """Return configured tunnel names."""
        if not self.tunnel_manager:
            return []
        return list(self.tunnel_manager.list_tunnels().keys())

    def _ensure_browser_with_current_tunnel(self) -> bool:
        """Ensure browser exists and uses currently selected tunnel/proxy."""
        if self.driver:
            return True
        return self.setup_browser()

    def _rotate_tunnel_before_store(self) -> bool:
        """Rotate between direct server IP and SOCKS tunnels between stores."""
        if not self.use_tunnels or not self.tunnel_manager:
            return self._ensure_browser_with_current_tunnel()

        tunnel_names = self._configured_tunnel_names()
        if not tunnel_names:
            logger.error("❌ No tunnels configured")
            return False

        if self.preferred_tunnel:
            target_mode = self.preferred_tunnel
        else:
            candidates = list(tunnel_names)
            if self.mix_direct_ip:
                candidates.append(self.DIRECT_CONNECTION)

            current_mode = self.current_connection_mode
            target_mode = current_mode

            if not current_mode:
                target_mode = random.choice(candidates)
            elif len(candidates) > 1 and self.stores_on_current_tunnel >= self._next_rotation_after:
                target_mode = random.choice([mode for mode in candidates if mode != current_mode])

        mode_changed = target_mode != self.current_connection_mode

        if mode_changed:
            active_phase = getattr(self, '_scrape_phase', None) or 'unknown-phase'
            logger.info(
                f"🔄 Rotating connection from "
                f"{self.current_connection_mode or self.DIRECT_CONNECTION} to {target_mode} "
                f"after {self.stores_on_current_tunnel} store(s) during {active_phase}"
            )

            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
                self.driver = None

            if target_mode == self.DIRECT_CONNECTION:
                self._switch_to_direct_connection()
            else:
                if self.current_tunnel and self.current_tunnel != target_mode:
                    self._stop_tunnel()

                if not self._start_tunnel(tunnel_name=target_mode):
                    logger.error(f"❌ Failed to switch to tunnel {target_mode}")
                    return False

            self.stores_on_current_tunnel = 0
            self._next_rotation_after = random.randint(2, 5)

        return self._ensure_browser_with_current_tunnel()

    def scrape_store_with_vehicle_counting(self, store_url: str) -> Optional[Dict]:
        """Scrape one store and rotate tunnel randomly between stores when enabled."""
        active_phase = getattr(self, '_scrape_phase', None) or 'unspecified-phase'
        logger.info(f"🧭 Tunnel scrape phase: {active_phase}")
        if self.use_tunnels:
            if not self._rotate_tunnel_before_store():
                return {
                    'url': store_url,
                    'error': 'Failed to initialize/rotate SSH tunnel',
                    'has_auto_moto': False,
                    'scraped': False,
                    'new_vehicle_count': 0,
                    'used_vehicle_count': 0,
                    'test_vehicle_count': 0,
                    'total_vehicle_count': 0
                }
        elif not self.driver and not self.setup_browser():
            return {
                'url': store_url,
                'error': 'Failed to initialize browser',
                'has_auto_moto': False,
                'scraped': False,
                'new_vehicle_count': 0,
                'used_vehicle_count': 0,
                'test_vehicle_count': 0,
                'total_vehicle_count': 0
            }

        result = super().scrape_store_with_vehicle_counting(store_url)

        if self.use_tunnels and result and not result.get('error'):
            self.stores_on_current_tunnel += 1

        return result

    def test_firefox_local(self):
        """Test if Firefox works locally without tunnels using server-compatible config"""
        try:
            logger.info("🧪 Testing Firefox installation locally with server config...")

            # Use server-compatible options
            test_options = Options()
            test_options.headless = True

            # ALWAYS use system Firefox, not webdriver's bundled version
            firefox_binary = "/usr/bin/firefox"
            if not os.path.exists(firefox_binary):
                raise FileNotFoundError(f"System Firefox not found at {firefox_binary}. Install with: sudo apt-get install firefox")
            test_options.binary_location = firefox_binary

            test_options.set_preference("browser.tabs.remote.autostart", False)
            test_options.set_preference("layers.acceleration.disabled", True)
            test_options.set_preference("gfx.webrender.force-disabled", True)
            test_options.set_preference("dom.ipc.plugins.enabled", False)
            test_options.set_preference("media.hardware-video-decoding.enabled", False)
            test_options.set_preference("media.hardware-video-decoding.force-enabled", False)
            test_options.set_preference("browser.startup.homepage", "about:blank")
            test_options.set_preference("security.sandbox.content.level", 0)
            test_options.set_preference("network.proxy.type", 0)

            # Use system geckodriver
            test_service = Service("/usr/local/bin/geckodriver")
            test_driver = webdriver.Firefox(service=test_service, options=test_options)
            test_driver.get("data:text/html,<html><body><h1>Firefox Server Test OK</h1></body></html>")
            test_driver.quit()
            logger.info("✅ Firefox server-compatible test: PASSED")
            return True
        except Exception as e:
            logger.error(f"❌ Firefox server-compatible test: FAILED - {e}")
            return False

    def _find_geckodriver(self):
        """Find GeckoDriver from multiple locations"""
        import glob
        import shutil

        possible_paths = [
            "/usr/local/bin/geckodriver",
            "/usr/bin/geckodriver",
        ]

        # Check exact paths first
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

        # Try to find in PATH
        path_geckodriver = shutil.which("geckodriver")
        if path_geckodriver:
            return path_geckodriver

        return None

    def setup_browser(self) -> bool:
        """
        Enhanced browser setup with SSH tunnel proxy support using Firefox.
        """
        try:
            # First test if Firefox works locally to isolate server-side issues
            if not self.test_firefox_local():
                logger.error("🚨 Firefox installation issue detected - aborting browser setup")
                return False

            firefox_options = Options()

            # Server-compatible configuration (exact setup that works)
            firefox_options.headless = False

            # ALWAYS use system Firefox, not webdriver's bundled version
            firefox_binary = "/usr/bin/firefox"
            if not os.path.exists(firefox_binary):
                raise FileNotFoundError(f"System Firefox not found at {firefox_binary}. Install with: sudo apt-get install firefox")
            firefox_options.binary_location = firefox_binary
            logger.info(f"🦊 Using system Firefox: {firefox_binary}")

            # Server-specific preferences for stability
            firefox_options.set_preference("browser.tabs.remote.autostart", False)
            firefox_options.set_preference("layers.acceleration.disabled", True)
            firefox_options.set_preference("gfx.webrender.force-disabled", True)
            firefox_options.set_preference("gfx.webrender.all", False)
            firefox_options.set_preference("gfx.x11-egl.force-disabled", True)
            firefox_options.set_preference("dom.ipc.plugins.enabled", False)
            firefox_options.set_preference("media.hardware-video-decoding.enabled", False)
            firefox_options.set_preference("media.hardware-video-decoding.force-enabled", False)
            firefox_options.set_preference("browser.startup.homepage", "about:blank")
            firefox_options.set_preference("security.sandbox.content.level", 0)

            # Enhanced anti-detection preferences
            firefox_options.set_preference("dom.webdriver.enabled", False)
            firefox_options.set_preference("useAutomationExtension", False)
            firefox_options.set_preference("general.platform.override", "Linux x86_64")
            firefox_options.set_preference("general.appversion.override", "5.0 (X11)")

            # Set user agent — use the shared pool from AntiDetectionMixin
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

            # 🔥 SOCKS PROXY CONFIGURATION 🔥
            if self.use_tunnels and self.current_tunnel and self.socks_proxy_port:
                # Configure SOCKS proxy in Firefox
                firefox_options.set_preference("network.proxy.type", 1)  # Manual proxy configuration
                firefox_options.set_preference("network.proxy.socks", "127.0.0.1")
                firefox_options.set_preference("network.proxy.socks_port", self.socks_proxy_port)
                firefox_options.set_preference("network.proxy.socks_version", 5)
                firefox_options.set_preference("network.proxy.socks_remote_dns", True)
                logger.info(f"🌐 Firefox configured to use SOCKS proxy: 127.0.0.1:{self.socks_proxy_port}")
            else:
                # Ensure direct connection when no active tunnel is selected
                firefox_options.set_preference("network.proxy.type", 0)
                if self.use_tunnels:
                    logger.info("🌐 Firefox configured for direct connection (original server IP)")

            # Server compatibility - ensure headless mode is properly set
            if self.headless:
                firefox_options.headless = True

            # Additional Firefox arguments
            firefox_options.add_argument("--no-sandbox")
            firefox_options.add_argument("--disable-dev-shm-usage")

            # Set window size
            width = random.randint(1366, 1920)
            height = random.randint(768, 1080)
            firefox_options.add_argument(f"--width={width}")
            firefox_options.add_argument(f"--height={height}")

            # Setup Firefox service with timeout configurations
            geckodriver_path = self._find_geckodriver()
            if not geckodriver_path:
                logger.error("❌ GeckoDriver not found")
                return False

            service = Service(geckodriver_path)

            # Add timeout configurations for server-side issues
            firefox_options.set_preference("network.http.connection-timeout", 30)
            firefox_options.set_preference("network.http.response.timeout", 30)
            firefox_options.set_preference("dom.max_script_run_time", 30)
            firefox_options.set_preference("dom.max_chrome_script_run_time", 30)

            # Configure WebDriver with retry logic for connection issues
            logger.info("🔧 Starting Firefox WebDriver (checking for server-side issues)...")
            max_retries = 3
            retry_delay = 2

            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        logger.info(f"🔄 Retry attempt {attempt + 1}/{max_retries}")
                        # Clean up any stale geckodriver processes
                        import subprocess
                        try:
                            subprocess.run(['pkill', '-9', 'geckodriver'], timeout=2)
                            time.sleep(1)
                        except:
                            pass

                    self.driver = webdriver.Firefox(service=service, options=firefox_options)
                    logger.info("✅ Firefox WebDriver started successfully")
                    break

                except Exception as e:
                    error_msg = str(e).lower()

                    if attempt < max_retries - 1:
                        if 'connection refused' in error_msg or 'newconnectionerror' in error_msg:
                            logger.warning(f"⚠️ Connection refused on attempt {attempt + 1}, retrying in {retry_delay}s...")
                            time.sleep(retry_delay)
                            continue
                        elif 'timeout' in error_msg:
                            logger.warning(f"⚠️ Timeout on attempt {attempt + 1}, retrying in {retry_delay}s...")
                            time.sleep(retry_delay)
                            continue

                    # Final attempt failed
                    logger.error(f"❌ Failed to start Firefox WebDriver after {max_retries} attempts: {e}")
                    logger.error(f"Geckodriver path: {geckodriver_path}")
                    logger.error(f"Firefox binary: {firefox_binary}")
                    logger.error(f"Headless mode: {self.headless}")
                    logger.error("Display issue: ensure DISPLAY=:3 is set (check DISPLAY_NUM in .env)")

                    # Try to clean up any zombie processes
                    try:
                        import subprocess
                        subprocess.run(['pkill', '-9', 'firefox'], timeout=2)
                        subprocess.run(['pkill', '-9', 'geckodriver'], timeout=2)
                    except:
                        pass

                    raise

            # Set shorter page load timeout to catch server issues
            self.driver.set_page_load_timeout(30)  # 30 seconds for page loads
            self.driver.implicitly_wait(10)  # 10 seconds for element waits

            # Set window size programmatically as well
            self.driver.set_window_size(width, height)

            # Apply full stealth suite via shared mixin method
            self._inject_stealth_scripts()

            logger.info("✅ Firefox browser setup completed with tunnel integration")
            return True

        except Exception as e:
            error_msg = str(e).lower()
            logger.error(f"❌ Failed to setup Firefox browser: {e}")

            # Analyze error to distinguish between local vs server-side issues
            if "httpconnectionpool" in error_msg and "read timed out" in error_msg:
                if "localhost" in error_msg:
                    logger.error("🌐 SERVER-SIDE ISSUE DETECTED: Connection timeout to localhost")
                    logger.error("   This suggests a proxy/tunnel configuration problem, not Firefox")
                    logger.error("🔧 SOLUTIONS:")
                    logger.error("   1. Check if SSH tunnel is running: ps aux | grep ssh")
                    logger.error("   2. Verify SOCKS proxy port: netstat -tulpn | grep :1080")
                    logger.error("   3. Test tunnel connection: curl --socks5 127.0.0.1:1080 http://httpbin.org/ip")
                    logger.error("   4. Restart tunnel: ./setup_tunnels.sh")
                else:
                    logger.error("🌐 NETWORK ISSUE DETECTED: External server connection problem")
                    logger.error("🔧 SOLUTIONS:")
                    logger.error("   1. Check internet connection")
                    logger.error("   2. Try different proxy server")
                    logger.error("   3. Run without tunnels: --no-tunnels")
            elif "geckodriver" in error_msg or "firefox" in error_msg:
                logger.error("🦊 LOCAL FIREFOX ISSUE DETECTED")
                logger.error("🔧 SOLUTIONS:")
                logger.error("   1. Install Firefox: sudo apt install firefox")
                logger.error("   2. Reinstall GeckoDriver (see README installation section)")
            elif "permission" in error_msg or "display" in error_msg:
                logger.error("🖥️ DISPLAY/PERMISSION ISSUE DETECTED")
                logger.error("🔧 SOLUTIONS:")
                logger.error("   1. Verify the VNC display is running: DISPLAY=:3 xdpyinfo | head -5")
                logger.error("   2. Check DISPLAY_NUM in .env matches the running screen number")
            else:
                logger.error("🔍 UNKNOWN ISSUE - Full error details above")
                logger.error("🔧 GENERAL SOLUTIONS:")
                logger.error("   1. Try without tunnels: python script.py --no-tunnels")
                logger.error("   2. Check system requirements")

            if hasattr(self, 'driver') and self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
            return False

    def run_enhanced_scrape_with_tunnels(self, max_stores: int = None) -> Dict:
        """
        Run enhanced scraping with SSH tunnel support.

        Args:
            max_stores: Maximum number of stores to scrape

        Returns:
            Dict containing scraping results
        """
        try:
            logger.info("🚀 Enhanced Njuskalo Scraper with SSH Tunnel Support")
            logger.info("=" * 60)

            # Step 1: Validate tunnel setup and announce connection strategy
            if self.use_tunnels:
                tunnel_names = self._configured_tunnel_names()
                if not tunnel_names:
                    logger.error("❌ No usable tunnel definitions found, continuing without tunnel support")
                    self.use_tunnels = False
                elif self.preferred_tunnel:
                    logger.info(f"🔒 Preferred tunnel mode enabled: {self.preferred_tunnel}")
                else:
                    logger.info(
                        "🔀 Mixed connection mode enabled: direct server IP + SOCKS tunnels "
                        f"({', '.join(tunnel_names)})"
                    )
                    self.current_connection_mode = self.DIRECT_CONNECTION

            # Step 2: Run enhanced scraping workflow
            logger.info("🧭 Two-phase scrape enabled: (1) classify new XML stores, (2) scrape all auto stores in random order")
            logger.info("🔧 Setting up browser with tunnel configuration...")
            results = self.run_enhanced_scrape(max_stores)

            return results

        except KeyboardInterrupt:
            logger.info("\n⚠️ Scraping interrupted by user")
            return {'error': 'interrupted', 'stores_scraped': 0}
        except Exception as e:
            logger.error(f"❌ Error in tunnel-enabled scraping: {e}")
            return {'error': str(e), 'stores_scraped': 0}
        finally:
            # Cleanup browser
            if hasattr(self, 'driver') and self.driver:
                try:
                    self.driver.quit()
                    logger.info("Browser closed successfully")
                except Exception as e:
                    logger.warning(f"Error closing browser: {e}")

            # Cleanup tunnel
            if self.use_tunnels:
                self._stop_tunnel()


def main():
    """Main function for command line usage"""
    import argparse

    parser = argparse.ArgumentParser(description="Enhanced Njuskalo Scraper with SSH Tunnel Support")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--max-stores", type=int, help="Maximum number of stores to scrape")
    parser.add_argument("--tunnel-config", default="tunnel_config.json", help="Path to tunnel config file")
    parser.add_argument("--tunnel", help="Specific tunnel name to use")
    parser.add_argument("--no-tunnels", action="store_true", help="Disable tunnel usage")
    parser.add_argument("--no-database", action="store_true", help="Disable database usage")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    try:
        # Create enhanced scraper with tunnel support
        scraper = TunnelEnabledEnhancedScraper(
            headless=args.headless,
            use_database=not args.no_database,
            tunnel_config_path=args.tunnel_config,
            use_tunnels=not args.no_tunnels,
            preferred_tunnel=args.tunnel
        )

        # Run enhanced scraping
        results = scraper.run_enhanced_scrape_with_tunnels(max_stores=args.max_stores)

        # Print results
        print("\n" + "="*60)
        print("🏁 ENHANCED SCRAPING WITH TUNNELS - RESULTS")
        print("="*60)
        print(f"XML Available: {'✅' if results.get('xml_available') else '❌'}")
        print(f"New URLs Found: {results.get('new_urls_found', 0)}")
        print(f"Stores Scraped: {results.get('stores_scraped', 0)}")
        print(f"Auto Moto Stores: {results.get('auto_moto_stores', 0)}")
        print(f"New Vehicles: {results.get('new_vehicles', 0)}")
        print(f"Used Vehicles: {results.get('used_vehicles', 0)}")
        print(f"Total Vehicles: {results.get('total_vehicles', 0)}")
        print(f"Errors: {len(results.get('errors', []))}")
        if results.get('errors'):
            print("\nErrors encountered:")
            for error in results['errors'][:5]:  # Show first 5 errors
                print(f"  - {error}")
        print("="*60)

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        # Ensure scraper cleanup happens
        try:
            if 'scraper' in locals() and hasattr(scraper, 'driver') and scraper.driver:
                scraper.driver.quit()
                logger.info("Browser cleanup completed")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")


if __name__ == "__main__":
    main()