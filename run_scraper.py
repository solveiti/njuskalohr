#!/usr/bin/env python3
"""
Simple launcher script for Njuskalo sitemap store scraper.
"""

import sys
import os
from njuskalo_sitemap_scraper import NjuskaloSitemapScraper
import time


def run_scraper(headless=False, output_file=None, max_stores=None):
    """
    Run the sitemap-based store scraper with specified options.

    Args:
        headless: Whether to run in headless mode
        output_file: Custom output filename
        max_stores: Maximum number of stores to scrape (for testing)
    """
    scraper = None

    try:
        print("🏪 Njuskalo Store Scraper (Sitemap-based)")
        print("=" * 50)

        # Create scraper
        print("🔧 Initializing browser...")
        scraper = NjuskaloSitemapScraper(headless=headless)

        print("�️  Starting sitemap-based scraping workflow:")
        print("   1. Downloading sitemap index XML")
        print("   2. Finding store-related sitemaps")
        print("   3. Extracting store URLs from XML files")
        print("   4. Visiting each store (trgovina) page")
        print("   5. Checking for Auto Moto category (categoryId=2)")
        print("   6. Extracting address and ad counts")
        print()
        print("⏳ This may take several minutes depending on the number of stores...")

        # Run the full scraping workflow
        stores_data = scraper.run_full_scrape(max_stores=max_stores)

        if stores_data:
            # Generate filename if not provided
            if not output_file:
                timestamp = int(time.time())
                output_file = f"njuskalo_stores_{timestamp}.xlsx"

            print(f"💾 Saving {len(stores_data)} stores to {output_file}...")
            success = scraper.save_to_excel(output_file)

            if success:
                print("✅ Scraping completed successfully!")
                print(f"📊 Results saved to: {output_file}")

                # Show summary statistics
                if len(stores_data) > 0:
                    print("\n📋 Scraping Summary:")
                    print("-" * 40)

                    total_stores = len(stores_data)
                    auto_moto_stores = [s for s in stores_data if s.get('has_auto_moto')]
                    stores_with_ads = [s for s in stores_data if s.get('ads_count') is not None]
                    stores_with_address = [s for s in stores_data if s.get('address')]

                    print(f"📊 Total stores processed: {total_stores}")
                    print(f"🚗 Stores with Auto Moto category: {len(auto_moto_stores)}")
                    print(f"📍 Stores with address info: {len(stores_with_address)}")
                    print(f"📈 Stores with ad counts: {len(stores_with_ads)}")

                    if stores_with_ads:
                        total_ads = sum(s['ads_count'] for s in stores_with_ads if s['ads_count'])
                        avg_ads = total_ads / len(stores_with_ads) if stores_with_ads else 0
                        print(f"📢 Total ads across all stores: {total_ads}")
                        print(f"📊 Average ads per store: {avg_ads:.1f}")

                    print("\n🔍 Sample Auto Moto stores:")
                    for i, store in enumerate(auto_moto_stores[:5]):  # Show first 5
                        name = store.get('name', 'Unknown')[:40]
                        ads = store.get('ads_count', 'N/A')
                        print(f"   {i+1}. {name}... ({ads} ads)")

                    if len(auto_moto_stores) > 5:
                        print(f"   ... and {len(auto_moto_stores) - 5} more")

            else:
                print("❌ Failed to save results")
        else:
            print("❌ No stores found. This could mean:")
            print("   • No store URLs found in sitemaps")
            print("   • Website structure has changed")
            print("   • Network connectivity issues")
            print("💡 Check sitemap_scraper.log for detailed information")

    except KeyboardInterrupt:
        print("\n⛔ Scraping interrupted by user")

    except Exception as e:
        print(f"❌ Error occurred: {e}")
        print("💡 Check sitemap_scraper.log for detailed error information")

    finally:
        if scraper:
            print("🔒 Closing browser...")
            scraper.close()


def main():
    """Main function with command line options."""

    print("Select scraping mode:")
    print("1. Normal mode (with browser window)")
    print("2. Headless mode (no browser window - faster)")
    print("3. Test mode (headless, limited stores)")
    print("4. Exit")

    try:
        choice = input("\nEnter your choice (1-4): ").strip()

        if choice == "1":
            run_scraper(headless=False)
        elif choice == "2":
            run_scraper(headless=True)
        elif choice == "3":
            print("🧪 Running in test mode (first 10 stores only)")
            run_scraper(headless=True, max_stores=10)
        elif choice == "4":
            print("👋 Goodbye!")
            sys.exit(0)
        else:
            print("❌ Invalid choice. Please run the script again.")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()