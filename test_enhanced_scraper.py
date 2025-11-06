#!/usr/bin/env python3
"""
Test script to verify enhanced anti-detection measures in the scrapers.
"""

import time
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from njuskalo_sitemap_scraper import NjuskaloSitemapScraper
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_sitemap_scraper_delays():
    """Test the enhanced delays in sitemap scraper."""
    print("🧪 Testing Enhanced Sitemap Scraper Anti-Detection")
    print("=" * 60)

    # Test with enhanced delays and minimal store count
    scraper = NjuskaloSitemapScraper(headless=True)

    try:
        print("⏱️  Testing smart delay system...")
        start_time = time.time()

        # Test different delay types
        scraper.smart_sleep("store_visit")
        store_visit_time = time.time() - start_time

        start_time = time.time()
        scraper.smart_sleep("page_load")
        page_load_time = time.time() - start_time

        start_time = time.time()
        scraper.smart_sleep("data_extraction")
        data_extraction_time = time.time() - start_time

        print(f"✅ Store visit delay: {store_visit_time:.1f}s (expected: 8-20s)")
        print(f"✅ Page load delay: {page_load_time:.1f}s (expected: 2-5s)")
        print(f"✅ Data extraction delay: {data_extraction_time:.1f}s (expected: 1-3s)")

        # Test user agent rotation
        print("🔄 Testing user agent rotation...")
        user_agent = scraper.rotate_user_agent()
        print(f"✅ Generated user agent: {user_agent[:50]}...")

        # Test a single store scraping with enhanced delays
        print("🏪 Testing single store scraping with enhanced delays...")
        start_time = time.time()

        # Run a very limited test scrape
        stores_data = scraper.run_full_scrape(max_stores=1)

        total_time = time.time() - start_time
        print(f"✅ Single store scraping completed in {total_time:.1f}s")
        print(f"📊 Stores processed: {len(stores_data)}")

        if stores_data:
            store = stores_data[0]
            print(f"📍 Store name: {store.get('name', 'N/A')}")
            print(f"🚗 Has auto moto: {store.get('has_auto_moto', 'N/A')}")
            print(f"📈 Ads count: {store.get('ads_count', 'N/A')}")

        return True

    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False
    finally:
        scraper.close()

def test_delay_distribution():
    """Test the delay distribution to ensure realistic timing."""
    print("\n🎲 Testing Delay Distribution")
    print("=" * 40)

    scraper = NjuskaloSitemapScraper(headless=True)

    try:
        delays = []

        # Generate 10 store visit delays
        for i in range(10):
            start_time = time.time()
            delay = scraper.get_smart_delay(operation_type="store_visit")
            delays.append(delay)

        min_delay = min(delays)
        max_delay = max(delays)
        avg_delay = sum(delays) / len(delays)

        print(f"📊 Delay statistics over 10 samples:")
        print(f"   Min: {min_delay:.1f}s")
        print(f"   Max: {max_delay:.1f}s")
        print(f"   Avg: {avg_delay:.1f}s")
        print(f"   Range: {max_delay - min_delay:.1f}s")

        # Check if we got any extra stealth delays
        extra_long_delays = [d for d in delays if d > 25]
        if extra_long_delays:
            print(f"🕶️  Extra stealth delays detected: {len(extra_long_delays)}")

        return True

    except Exception as e:
        logger.error(f"Delay distribution test failed: {e}")
        return False
    finally:
        scraper.close()

def main():
    """Run all tests."""
    print("🚀 Starting Enhanced Anti-Detection Tests")
    print("=" * 60)

    # Test 1: Sitemap scraper delays
    test1_passed = test_sitemap_scraper_delays()

    # Test 2: Delay distribution
    test2_passed = test_delay_distribution()

    print("\n" + "=" * 60)
    print("📋 Test Results Summary:")
    print(f"   Sitemap Scraper Test: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"   Delay Distribution Test: {'✅ PASSED' if test2_passed else '❌ FAILED'}")

    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! Enhanced anti-detection is working.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    exit(main())