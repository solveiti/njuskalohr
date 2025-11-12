#!/usr/bin/env python3
"""
Test script for Njuskalo Stealth Publish

This script tests the stealth publish functionality with various configurations.
"""

import sys
import time
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from njuskalo_stealth_publish import NjuskaloStealthPublish


def test_stealth_publish():
    """Test the stealth publish functionality"""

    print("🧪 Testing Njuskalo Stealth Publish")
    print("=" * 50)

    # Test 1: Visible mode for development
    print("\n1️⃣ Testing in visible mode (for debugging)...")

    stealth_publish = NjuskaloStealthPublish(
        headless=False,  # Visible mode for testing
        use_tunnel=False,  # No tunnel for initial test
        username="srdjanmsd",
        password="rvp2mqu@xye1JRC0fjt",
        persistent=False  # Disable persistence for clean testing
    )

    try:
        # Test browser setup
        print("🔧 Testing browser setup...")
        if stealth_publish.setup_stealth_browser():
            print("✅ Browser setup successful")

            # Test navigation
            print("🌐 Testing navigation to login page...")
            if stealth_publish.navigate_to_login():
                print("✅ Navigation successful")

                # Take screenshot of login page
                stealth_publish.take_screenshot("test_login_page")

                print("\n🎯 Login page loaded successfully!")
                print("You can now inspect the browser and page content.")
                print("Press Enter to continue with automated login or Ctrl+C to stop...")

                try:
                    input()

                    # Test login
                    print("🔐 Testing automated login...")
                    if stealth_publish.perform_login():
                        print("✅ Login process completed")

                        # Verify login
                        if stealth_publish.verify_login_success():
                            print("🎉 Login verification successful!")
                        else:
                            print("⚠️ Login verification inconclusive")

                        stealth_publish.take_screenshot("test_login_result")
                    else:
                        print("❌ Login process failed")

                except KeyboardInterrupt:
                    print("\n👋 Test interrupted by user")

            else:
                print("❌ Navigation failed")
        else:
            print("❌ Browser setup failed")

    except Exception as e:
        print(f"❌ Test error: {e}")
    finally:
        # Cleanup
        if hasattr(stealth_publish, 'driver') and stealth_publish.driver:
            print("🧹 Cleaning up browser...")
            try:
                stealth_publish.driver.quit()
            except:
                pass

    print("\n✅ Test completed!")


def test_headless_publish():
    """Test headless publish"""

    print("\n2️⃣ Testing in headless mode...")

    stealth_publish = NjuskaloStealthPublish(
        headless=True,
        use_tunnel=False,
        username="srdjanmsd",
        password="rvp2mqu@xye1JRC0fjt",
        persistent=False  # Clean test environment
    )

    success = stealth_publish.run_stealth_publish()

    if success:
        print("✅ Headless publish test successful!")
    else:
        print("❌ Headless publish test failed!")

    return success
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test Njuskalo Stealth Publish")
    parser.add_argument("--mode", choices=["visible", "headless", "both"],
                       default="visible", help="Test mode")

    args = parser.parse_args()

    if args.mode in ["visible", "both"]:
        test_stealth_publish()

    if args.mode in ["headless", "both"]:
        test_headless_publish()

    print("\n🏁 All tests completed!")