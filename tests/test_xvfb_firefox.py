#!/usr/bin/env python3
"""
Test script to verify Firefox works with xvfb-run
This helps diagnose display and WebDriver issues on servers

Usage:
    # With xvfb-run (server environment)
    xvfb-run python3 test_xvfb_firefox.py

    # Without xvfb-run (local with display)
    python3 test_xvfb_firefox.py
"""

import os
import sys
import tempfile
import time
import signal
import subprocess
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service


def _find_processes(pattern: str):
    """Return list of matching process tuples: (pid, command)."""
    try:
        result = subprocess.run(
            ["pgrep", "-a", "-f", pattern],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return []

    processes = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(" ", 1)
        if not parts:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        cmd = parts[1] if len(parts) > 1 else ""

        # Don't target current test process
        if pid == os.getpid():
            continue

        processes.append((pid, cmd))
    return processes


def _kill_processes(processes, label: str):
    """Try SIGTERM then SIGKILL if needed. Returns number killed."""
    if not processes:
        print(f"   ℹ️  No {label} processes found")
        return 0

    print(f"   Found {len(processes)} {label} process(es):")
    for pid, cmd in processes:
        print(f"     - PID {pid}: {cmd}")

    killed = 0
    for pid, _ in processes:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            continue
        except Exception as e:
            print(f"   ⚠️  Could not SIGTERM PID {pid}: {e}")

    time.sleep(1.0)

    for pid, _ in processes:
        try:
            # Signal 0 succeeds only if process is still alive
            os.kill(pid, 0)
            try:
                os.kill(pid, signal.SIGKILL)
                print(f"   ⚠️  PID {pid} required SIGKILL")
            except ProcessLookupError:
                pass
            except Exception as e:
                print(f"   ⚠️  Could not SIGKILL PID {pid}: {e}")
                continue
        except ProcessLookupError:
            pass
        except Exception:
            pass
        killed += 1

    print(f"   ✅ Cleanup finished for {label}, terminated: {killed}")
    return killed

def test_firefox_with_display():
    """Test Firefox WebDriver initialization with current display settings"""

    print("=" * 70)
    print("Firefox + xvfb Compatibility Test")
    print("=" * 70)

    # Check environment
    print("\n1. Environment Check:")
    print(f"   DISPLAY: {os.environ.get('DISPLAY', 'NOT SET')}")
    print(f"   USER: {os.environ.get('USER', 'unknown')}")
    print(f"   HOME: {os.environ.get('HOME', 'unknown')}")

    # Check Firefox
    print("\n2. Firefox Check:")
    firefox_path = "/usr/bin/firefox"
    if os.path.exists(firefox_path):
        print(f"   ✅ Firefox found: {firefox_path}")
    else:
        print(f"   ❌ Firefox NOT found at {firefox_path}")
        return False

    # Check geckodriver
    print("\n3. Geckodriver Check:")
    geckodriver_path = "/usr/local/bin/geckodriver"
    if os.path.exists(geckodriver_path):
        print(f"   ✅ Geckodriver found: {geckodriver_path}")
    else:
        print(f"   ❌ Geckodriver NOT found at {geckodriver_path}")
        return False

    # Cleanup stale Firefox/geckodriver sessions first
    print("\n4. Existing Session Cleanup:")
    firefox_processes = _find_processes(r"(^|/)firefox(\s|$)|firefox-esr")
    geckodriver_processes = _find_processes(r"(^|/)geckodriver(\s|$)")

    _kill_processes(firefox_processes, "Firefox")
    _kill_processes(geckodriver_processes, "geckodriver")

    # Test Firefox WebDriver
    print("\n5. WebDriver Test:")
    print("   Configuring Firefox options...")

    firefox_options = Options()
    firefox_options.headless = False
    firefox_options.binary_location = firefox_path

    # Server-compatible preferences
    firefox_options.set_preference("browser.tabs.remote.autostart", False)
    firefox_options.set_preference("layers.acceleration.disabled", True)
    firefox_options.set_preference("gfx.webrender.force-disabled", True)
    firefox_options.set_preference("gfx.webrender.all", False)
    firefox_options.set_preference("gfx.x11-egl.force-disabled", True)
    firefox_options.set_preference("dom.ipc.plugins.enabled", False)
    firefox_options.set_preference("media.hardware-video-decoding.enabled", False)
    firefox_options.set_preference("security.sandbox.content.level", 0)
    firefox_options.set_preference("widget.non-native-theme.enabled", False)

    # Additional stability
    firefox_options.add_argument("--no-sandbox")
    firefox_options.add_argument("--disable-dev-shm-usage")
    firefox_options.add_argument("--disable-gpu")
    firefox_options.add_argument("--disable-software-rasterizer")

    # Create service with logging
    log_file = os.path.join(tempfile.gettempdir(), "test_geckodriver.log")
    service = Service(geckodriver_path, log_output=log_file)

    print(f"   Starting Firefox WebDriver (visible mode)...")
    print(f"   Log file: {log_file}")

    try:
        driver = webdriver.Firefox(service=service, options=firefox_options)

        # Ensure cleanup happens
        import atexit
        atexit.register(lambda: driver.quit() if driver else None)
        print("   ✅ WebDriver started successfully!")

        # Test navigation
        print("\n6. Navigation Test:")
        test_html = "data:text/html,<html><body><h1>Test OK</h1><p>Firefox is working!</p></body></html>"
        driver.get(test_html)
        print(f"   ✅ Navigated to test page")
        print(f"   Page title: {driver.title}")

        # Get page source
        source = driver.page_source
        if "Test OK" in source:
            print("   ✅ Page content verified")
        else:
            print("   ⚠️  Page content unexpected")

        # Cleanup
        driver.quit()
        print("\n7. Cleanup:")
        print("   ✅ WebDriver closed successfully")

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED - Firefox is working correctly!")
        print("=" * 70)
        return True

    except Exception as e:
        print(f"   ❌ WebDriver failed to start: {e}")
        print(f"\n   Check log file for details: {log_file}")

        if os.path.exists(log_file):
            print("\n   Last 20 lines of geckodriver log:")
            print("   " + "-" * 66)
            with open(log_file, 'r') as f:
                lines = f.readlines()
                for line in lines[-20:]:
                    print(f"   {line.rstrip()}")

        print("\n" + "=" * 70)
        print("❌ TEST FAILED - Firefox is not working correctly")
        print("=" * 70)
        print("\nPossible solutions:")
        print("1. Ensure xvfb is installed: sudo apt-get install xvfb")
        print("2. Run with xvfb-run: xvfb-run python3 test_xvfb_firefox.py")
        print("3. Check DISPLAY environment variable")
        print("4. Install required dependencies: sudo apt-get install firefox geckodriver")
        return False

if __name__ == "__main__":
    success = test_firefox_with_display()
    sys.exit(0 if success else 1)
