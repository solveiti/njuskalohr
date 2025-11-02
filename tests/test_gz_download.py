#!/usr/bin/env python3
"""
Test script specifically for downloading and decompressing the .gz sitemap file.
"""

from njuskalo_sitemap_scraper import NjuskaloSitemapScraper
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_gz_download():
    """Test downloading and decompressing the .gz sitemap file."""
    print("🧪 Testing .gz File Download and Decompression")
    print("=" * 50)

    scraper = None

    try:
        # Initialize scraper
        scraper = NjuskaloSitemapScraper(headless=True)  # Use headless for testing

        # Setup browser
        if not scraper.setup_browser():
            print("❌ Failed to setup browser")
            return False

        print("✅ Browser setup completed")

        # Test downloading the specific .gz file
        gz_url = "https://www.njuskalo.hr/sitemap-stores-01.xml.gz"
        print(f"\n🔍 Testing .gz file download: {gz_url}")

        xml_content = scraper.download_gz_file_with_browser(gz_url)

        if xml_content:
            print(f"✅ Successfully downloaded and decompressed .gz file!")
            print(f"   Content length: {len(xml_content)} characters")

            # Check if it contains XML
            if '<?xml' in xml_content:
                print("✅ Content contains XML declaration")
            elif '<urlset' in xml_content:
                print("✅ Content contains urlset element")

            # Try to extract store URLs
            store_urls = scraper.extract_store_urls(xml_content)

            if store_urls:
                print(f"✅ Found {len(store_urls)} store URLs!")

                # Show sample URLs
                print("\n📋 Sample store URLs:")
                for i, url in enumerate(store_urls[:10]):
                    print(f"  {i+1}. {url}")

                if len(store_urls) > 10:
                    print(f"  ... and {len(store_urls) - 10} more")

                # Save content to file for inspection
                with open("decompressed_sitemap.xml", "w", encoding="utf-8") as f:
                    f.write(xml_content)
                print("\n📄 Decompressed content saved to decompressed_sitemap.xml")

                return True
            else:
                print("❌ No store URLs found in decompressed content")

                # Save content for debugging
                with open("debug_decompressed.xml", "w", encoding="utf-8") as f:
                    f.write(xml_content[:5000])  # First 5000 chars
                print("📄 First 5000 characters saved to debug_decompressed.xml for inspection")

                return False
        else:
            print("❌ Failed to download and decompress .gz file")
            return False

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

    finally:
        if scraper:
            scraper.close()


if __name__ == "__main__":
    success = test_gz_download()

    if success:
        print("\n🎉 .gz file download test passed!")
        print("The scraper can now properly download and decompress sitemap files.")
    else:
        print("\n💥 .gz file download test failed!")
        print("Check the logs and debug files for more details.")