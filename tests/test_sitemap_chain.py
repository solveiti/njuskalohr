#!/usr/bin/env python3
"""
Test following the proper sitemap chain from index to stores to XML.gz.
"""

from njuskalo_sitemap_scraper import NjuskaloSitemapScraper
import logging
import re

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_sitemap_chain():
    """Follow the proper sitemap chain step by step."""
    print("🔍 Testing Sitemap Chain Navigation")
    print("=" * 50)

    scraper = None

    try:
        # Initialize scraper
        scraper = NjuskaloSitemapScraper(headless=False)  # Use visible browser

        # Setup browser
        if not scraper.setup_browser():
            print("❌ Failed to setup browser")
            return False

        print("✅ Browser setup completed")

        # Step 1: Go to main sitemap index
        print(f"\n🔍 Step 1: Accessing main sitemap index...")
        scraper.driver.get("https://www.njuskalo.hr/sitemap-index.xml")
        input("Press Enter after checking the main sitemap index...")

        # Check content
        main_content = scraper.driver.page_source
        print(f"Main sitemap content length: {len(main_content)}")

        if 'sitemap-index-stores.xml' in main_content:
            print("✅ Found stores sitemap reference")

        # Step 2: Go to stores sitemap index
        print(f"\n🔍 Step 2: Accessing stores sitemap index...")
        scraper.driver.get("https://www.njuskalo.hr/sitemap-index-stores.xml")
        input("Press Enter after checking the stores sitemap index...")

        # Check content
        stores_content = scraper.driver.page_source
        print(f"Stores sitemap content length: {len(stores_content)}")

        if 'sitemap-stores-01.xml.gz' in stores_content:
            print("✅ Found XML.gz reference")

            # Extract the actual XML.gz URL if different
            xml_gz_matches = re.findall(r'(https://[^<]*sitemap-stores-[^<]*\.xml\.gz)', stores_content)
            if xml_gz_matches:
                xml_gz_url = xml_gz_matches[0]
                print(f"✅ Found XML.gz URL: {xml_gz_url}")
            else:
                xml_gz_url = "https://www.njuskalo.hr/sitemap-stores-01.xml.gz"

        # Step 3: Try accessing the XML.gz file
        print(f"\n🔍 Step 3: Accessing XML.gz file: {xml_gz_url}")
        scraper.driver.get(xml_gz_url)
        input("Press Enter after checking the XML.gz content...")

        # Check content
        xml_content = scraper.driver.page_source
        print(f"XML content length: {len(xml_content)}")

        # Save each step's content for analysis
        with open("step1_main_sitemap.html", "w", encoding="utf-8") as f:
            f.write(main_content)

        with open("step2_stores_sitemap.html", "w", encoding="utf-8") as f:
            f.write(stores_content)

        with open("step3_xml_content.html", "w", encoding="utf-8") as f:
            f.write(xml_content)

        print("Content saved to step1_main_sitemap.html, step2_stores_sitemap.html, step3_xml_content.html")

        # Analyze final content
        if '<?xml' in xml_content or '<urlset' in xml_content:
            print("✅ Found XML content!")

            # Try to extract store URLs
            trgovina_matches = re.findall(r'(https://[^<]*?/trgovina/[^<]+)', xml_content)
            print(f"✅ Found {len(trgovina_matches)} trgovina URLs!")

            if trgovina_matches:
                print("Sample trgovina URLs:")
                for i, url in enumerate(trgovina_matches[:5]):
                    print(f"  {i+1}. {url}")

            return True
        else:
            print("❌ Still no XML content found")
            return False

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

    finally:
        if scraper:
            input("Press Enter to close browser...")
            scraper.close()


if __name__ == "__main__":
    test_sitemap_chain()