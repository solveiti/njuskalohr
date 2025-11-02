#!/usr/bin/env python3
"""
Test script to verify the scraper works with a known store URL.
"""

from njuskalo_sitemap_scraper import NjuskaloSitemapScraper
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_single_store():
    """Test scraping a single known store."""
    print("🧪 Testing Single Store Scraping")
    print("=" * 40)

    scraper = None

    try:
        # Initialize scraper
        scraper = NjuskaloSitemapScraper(headless=True)  # Use headless for testing

        # Setup browser
        if not scraper.setup_browser():
            print("❌ Failed to setup browser")
            return False

        # Test with the known store URL
        test_url = "https://www.njuskalo.hr/trgovina/zunicautomobili"
        print(f"🔍 Testing store: {test_url}")

        # Scrape the store
        store_data = scraper.scrape_store_info(test_url)

        if store_data:
            print("✅ Successfully scraped store data:")
            print(f"   Name: {store_data.get('name', 'N/A')}")
            print(f"   Address: {store_data.get('address', 'N/A')}")
            print(f"   Ads Count: {store_data.get('ads_count', 'N/A')}")
            print(f"   Has Auto Moto: {store_data.get('has_auto_moto', 'N/A')}")
            print(f"   Categories Found: {len(store_data.get('categories', []))}")
            print(f"   Error: {store_data.get('error', 'None')}")

            # Save to Excel for inspection
            scraper.stores_data = [store_data]
            if scraper.save_to_excel("test_single_store.xlsx"):
                print("📄 Results saved to test_single_store.xlsx")

            return True
        else:
            print("❌ Failed to scrape store data")
            return False

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

    finally:
        if scraper:
            scraper.close()


if __name__ == "__main__":
    success = test_single_store()

    if success:
        print("\n🎉 Single store test passed!")
    else:
        print("\n💥 Single store test failed!")
        print("Check the logs for more details.")