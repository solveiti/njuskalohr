#!/usr/bin/env python3
"""
Test the complete workflow with a limited number of stores.
"""

from njuskalo_sitemap_scraper import NjuskaloSitemapScraper
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_complete_workflow():
    """Test the complete scraping workflow with a few stores."""
    print("🧪 Testing Complete Workflow")
    print("=" * 40)

    scraper = None

    try:
        # Initialize scraper
        scraper = NjuskaloSitemapScraper(headless=True)

        print("🔍 Running complete workflow (limited to 3 stores for testing)...")

        # Run the full scrape with a limit
        stores_data = scraper.run_full_scrape(max_stores=3)

        if stores_data:
            print(f"\n✅ Successfully scraped {len(stores_data)} stores!")

            # Show results
            for i, store in enumerate(stores_data, 1):
                print(f"\n📊 Store {i}:")
                print(f"  Name: {store.get('name', 'N/A')}")
                print(f"  URL: {store.get('url', 'N/A')}")
                print(f"  Address: {store.get('address', 'N/A')}")
                print(f"  Ads Count: {store.get('ads_count', 'N/A')}")
                print(f"  Has Auto Moto: {store.get('has_auto_moto', 'N/A')}")
                print(f"  Error: {store.get('error', 'None')}")

            # Save to Excel
            if scraper.save_to_excel("test_workflow_results.xlsx"):
                print(f"\n📄 Results saved to test_workflow_results.xlsx")

            return True
        else:
            print("❌ No stores were scraped")
            return False

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

    finally:
        if scraper:
            scraper.close()


if __name__ == "__main__":
    success = test_complete_workflow()

    if success:
        print("\n🎉 Complete workflow test passed!")
        print("The scraper is ready for full use.")
    else:
        print("\n💥 Complete workflow test failed!")
        print("Check the logs for more details.")