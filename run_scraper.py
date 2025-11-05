#!/usr/bin/env python3
"""
Simple launcher script for Njuskalo sitemap store scraper.
"""

import sys
import os
from njuskalo_sitemap_scraper import NjuskaloSitemapScraper
import time


def run_scraper(headless=False, output_file=None, max_stores=None, use_database=True):
    """
    Run the sitemap-based store scraper with specified options.

    Args:
        headless: Whether to run in headless mode
        output_file: Custom output filename
        max_stores: Maximum number of stores to scrape (for testing)
        use_database: Whether to save data to PostgreSQL database
    """
    scraper = None

    try:
        print("🏪 Njuskalo Store Scraper (Sitemap-based)")
        print("=" * 50)

        # Create scraper
        print("🔧 Initializing browser...")
        scraper = NjuskaloSitemapScraper(headless=headless, use_database=use_database)

        print("📊 Starting sitemap-based scraping workflow:")
        print("   1. Downloading sitemap index XML")
        print("   2. Finding store-related sitemaps")
        print("   3. Extracting store URLs from XML files")
        print("   4. Visiting each store (trgovina) page")
        print("   5. Checking for Auto Moto category (categoryId=2)")
        print("   6. Extracting address and ad counts")
        if use_database:
            print("   7. Saving data to PostgreSQL database")
        print()
        print("⏳ This may take several minutes depending on the number of stores...")

        # Run the full scraping workflow
        stores_data = scraper.run_full_scrape(max_stores=max_stores)

        if stores_data:
            # Create datadump directory
            import os
            datadump_dir = "datadump"
            os.makedirs(datadump_dir, exist_ok=True)

            # Generate filename if not provided
            if not output_file:
                timestamp = int(time.time())
                output_file = f"njuskalo_stores_{timestamp}.xlsx"

            print(f"💾 Saving {len(stores_data)} stores to {output_file}...")
            success = scraper.save_to_excel(output_file)

            if success:
                print("✅ Scraping completed successfully!")
                print(f"📊 Results saved to: datadump/{output_file}")
                if use_database:
                    print("🗃️  Data also saved to MySQL database")

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

                    if auto_moto_stores:
                        print(f"\n🚗 Auto Moto Stores:")
                        for store in auto_moto_stores[:5]:  # Show first 5
                            store_name = store.get('name', 'Unknown')
                            ads_count = store.get('ads_count', 'N/A')
                            print(f"   • {store_name} ({ads_count} ads)")
                        if len(auto_moto_stores) > 5:
                            print(f"   ... and {len(auto_moto_stores) - 5} more")

            else:
                print("❌ Failed to save results to Excel file")
                return False

        else:
            print("❌ No data was scraped")
            return False

        return True

    except KeyboardInterrupt:
        print("\n\n⏹️  Scraping interrupted by user")
        return False

    except Exception as e:
        print(f"❌ An error occurred: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Clean up browser
        if scraper and scraper.driver:
            try:
                scraper.driver.quit()
                print("🔧 Browser closed")
            except Exception:
                pass


def main():
    """Main function with command line argument parsing."""
    import argparse

    parser = argparse.ArgumentParser(description='Njuskalo Store Scraper')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--output', help='Output Excel filename')
    parser.add_argument('--max-stores', type=int, help='Maximum number of stores to scrape (for testing)')
    parser.add_argument('--no-database', action='store_true', help='Disable database storage')

    args = parser.parse_args()

    use_database = not args.no_database

    print("Starting Njuskalo scraper...")
    success = run_scraper(
        headless=args.headless,
        output_file=args.output,
        max_stores=args.max_stores,
        use_database=use_database
    )

    if success:
        print("\n🎉 Scraping completed successfully!")
        if use_database:
            print("💡 Use 'python db_manager.py stats' to view database statistics")
            print("💡 Use 'python db_manager.py list-valid' to view stored data")
    else:
        print("\n💥 Scraping failed or was interrupted")
        sys.exit(1)


if __name__ == "__main__":
    main()