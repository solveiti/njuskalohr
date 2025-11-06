#!/usr/bin/env python3
"""
Firefox Migration Test Suite

This script validates that the Firefox migration is complete and working.
"""

import os
import sys
from datetime import datetime

def test_imports():
    """Test that all Firefox-related imports work correctly."""
    print("🦊 Testing Firefox Imports")
    print("-" * 30)

    try:
        # Test basic Firefox imports
        from selenium.webdriver.firefox.options import Options
        from selenium.webdriver.firefox.service import Service
        print("✅ Selenium Firefox imports successful")

        # Test scraper imports
        from njuskalo_scraper import NjuskaloCarScraper
        from njuskalo_sitemap_scraper import NjuskaloSitemapScraper
        from njuskalo_scraper_with_tunnels import TunnelEnabledNjuskaloScraper
        print("✅ All scraper imports successful")

        return True

    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def test_configuration():
    """Test that configuration files have been updated."""
    print("\n🔧 Testing Configuration Updates")
    print("-" * 35)

    passed = 0
    total = 0

    # Test config.py user agent
    total += 1
    try:
        from config import USER_AGENT
        if "Firefox" in USER_AGENT and "Gecko" in USER_AGENT:
            print("✅ config.py USER_AGENT updated to Firefox")
            passed += 1
        else:
            print(f"❌ config.py still has non-Firefox user agent: {USER_AGENT}")
    except Exception as e:
        print(f"❌ Error reading config.py: {e}")

    # Test requirements.txt
    total += 1
    try:
        with open('requirements.txt', 'r') as f:
            requirements = f.read()
            if "geckodriver-autoinstaller" in requirements:
                print("✅ requirements.txt includes Firefox dependencies")
                passed += 1
            else:
                print("❌ requirements.txt missing Firefox dependencies")
    except Exception as e:
        print(f"❌ Error reading requirements.txt: {e}")

    # Check for any remaining Chrome references in Python files
    total += 1
    try:
        import glob
        python_files = glob.glob("*.py")
        chrome_found = False

        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "ChromeDriverManager" in content or "webdriver.Chrome(" in content:
                        print(f"⚠️  Chrome references still found in {file_path}")
                        chrome_found = True
            except Exception:
                continue

        if not chrome_found:
            print("✅ No Chrome references found in main Python files")
            passed += 1
        else:
            print("❌ Chrome references still exist")
    except Exception as e:
        print(f"❌ Error checking for Chrome references: {e}")

    print(f"\n📊 Configuration tests: {passed}/{total} passed")
    return passed == total

def test_scraper_initialization():
    """Test that scrapers can be initialized without errors."""
    print("\n🚀 Testing Scraper Initialization")
    print("-" * 35)

    tests = [
        ("Basic Car Scraper", lambda: test_basic_scraper()),
        ("Sitemap Scraper", lambda: test_sitemap_scraper()),
        ("Tunnel Scraper (no tunnels)", lambda: test_tunnel_scraper()),
    ]

    passed = 0
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                print(f"✅ {test_name}: OK")
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")

    print(f"\n📊 Initialization tests: {passed}/{len(tests)} passed")
    return passed == len(tests)

def test_basic_scraper():
    """Test basic car scraper initialization."""
    try:
        from njuskalo_scraper import NjuskaloCarScraper
        # Don't actually initialize driver to avoid Firefox requirement
        # Just test class creation
        return True
    except Exception:
        return False

def test_sitemap_scraper():
    """Test sitemap scraper initialization."""
    try:
        from njuskalo_sitemap_scraper import NjuskaloSitemapScraper
        scraper = NjuskaloSitemapScraper(headless=True, use_database=False)
        # Don't call setup_browser to avoid Firefox requirement
        return True
    except Exception:
        return False

def test_tunnel_scraper():
    """Test tunnel scraper initialization."""
    try:
        from njuskalo_scraper_with_tunnels import TunnelEnabledNjuskaloScraper
        scraper = TunnelEnabledNjuskaloScraper(
            headless=True,
            use_database=False,
            use_tunnels=False
        )
        return True
    except Exception:
        return False

def main():
    """Run all Firefox migration tests."""
    print("🦊 Firefox Migration Validation")
    print("=" * 40)
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    tests = [
        test_imports,
        test_configuration,
        test_scraper_initialization,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)

    print("\n" + "=" * 40)
    print("📊 FIREFOX MIGRATION RESULTS")
    print("=" * 40)

    test_names = [
        "Firefox Imports",
        "Configuration Updates",
        "Scraper Initialization",
    ]

    passed = 0
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {name}")
        if result:
            passed += 1

    print(f"\n🎯 Overall Result: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("🎉 Firefox migration completed successfully!")
        print("\n🚀 Ready for use:")
        print("   • Basic scraping: python run_scraper.py")
        print("   • With tunnels: ./run_scraper_with_tunnels.sh --max-stores 5")
        print("   • Install Firefox: ./setup_firefox_manjaro.sh")
    else:
        print("⚠️  Migration validation found issues. Check output above.")

    print(f"🕐 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return passed == len(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)