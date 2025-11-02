#!/usr/bin/env python3
"""
Test script to verify browser-based sitemap downloading works with the stores sitemap.
"""

from njuskalo_sitemap_scraper import NjuskaloSitemapScraper
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_browser_sitemap_download():
    """Test downloading sitemaps using browser to bypass protections."""
    print("🧪 Testing Browser-Based Sitemap Download")
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

        # Test 1: Download sitemap index
        print("\n🔍 Test 1: Downloading sitemap index...")
        sitemap_index_content = scraper.download_sitemap_index()

        if sitemap_index_content and len(sitemap_index_content) > 100:
            print(f"✅ Sitemap index downloaded ({len(sitemap_index_content)} characters)")

            # Parse the index
            sitemap_urls = scraper.parse_sitemap_index(sitemap_index_content)
            print(f"✅ Found {len(sitemap_urls)} sitemap URLs")

            # Find stores sitemap
            stores_sitemap_url = None
            for url in sitemap_urls:
                if 'stores' in url.lower():
                    stores_sitemap_url = url
                    break

            if stores_sitemap_url:
                print(f"✅ Found stores sitemap: {stores_sitemap_url}")

                # Test 2: Download stores sitemap
                print("\n🔍 Test 2: Downloading stores sitemap...")
                stores_sitemap_content = scraper.download_sitemap_with_browser(stores_sitemap_url)

                if stores_sitemap_content and len(stores_sitemap_content) > 100:
                    print(f"✅ Stores sitemap downloaded ({len(stores_sitemap_content)} characters)")

                    # Parse stores sitemap to get XML.gz URL
                    stores_xml_urls = scraper.parse_sitemap_index(stores_sitemap_content)
                    print(f"✅ Found {len(stores_xml_urls)} stores XML URLs")

                    if stores_xml_urls:
                        xml_gz_url = stores_xml_urls[0]  # Should be the .xml.gz file
                        print(f"✅ Found stores XML.gz file: {xml_gz_url}")

                        # Test 3: Download and extract the XML.gz file
                        print("\n🔍 Test 3: Downloading stores XML.gz file...")
                        stores_xml_content = scraper.download_sitemap_with_browser(xml_gz_url)

                        if stores_xml_content and len(stores_xml_content) > 100:
                            print(f"✅ Stores XML content downloaded ({len(stores_xml_content)} characters)")

                            # Test 4: Extract store URLs
                            print("\n🔍 Test 4: Extracting store URLs...")
                            store_urls = scraper.extract_store_urls(stores_xml_content)

                            if store_urls:
                                print(f"✅ Found {len(store_urls)} store URLs!")

                                # Show sample URLs
                                print("\n📋 Sample store URLs:")
                                for i, url in enumerate(store_urls[:10]):
                                    print(f"  {i+1}. {url}")

                                if len(store_urls) > 10:
                                    print(f"  ... and {len(store_urls) - 10} more")

                                return True
                            else:
                                print("❌ No store URLs found in XML content")
                                return False
                        else:
                            print("❌ Failed to download stores XML content")
                            return False
                    else:
                        print("❌ No XML URLs found in stores sitemap")
                        return False
                else:
                    print("❌ Failed to download stores sitemap")
                    return False
            else:
                print("❌ No stores sitemap found")
                return False
        else:
            print("❌ Failed to download sitemap index")
            return False

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

    finally:
        if scraper:
            scraper.close()


if __name__ == "__main__":
    success = test_browser_sitemap_download()

    if success:
        print("\n🎉 Browser-based sitemap test passed!")
        print("The scraper can now handle protected sitemaps.")
    else:
        print("\n💥 Browser-based sitemap test failed!")
        print("Check the logs for more details.")