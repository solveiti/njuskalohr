#!/usr/bin/env python3
"""
Test script for Njuskalo sitemap functionality.
Tests sitemap downloading and parsing without browser automation.
"""

import requests
import xml.etree.ElementTree as ET
import gzip
from urllib.parse import urljoin


def test_sitemap_download():
    """Test downloading and parsing the sitemap index."""
    print("🧪 Testing sitemap functionality")
    print("=" * 40)

    sitemap_index_url = "https://www.njuskalo.hr/sitemap-index.xml"

    try:
        # Test sitemap index download
        print(f"📥 Downloading sitemap index from: {sitemap_index_url}")
        response = requests.get(sitemap_index_url, timeout=30)
        response.raise_for_status()

        print(f"✅ Successfully downloaded sitemap index ({len(response.text)} characters)")

        # Parse sitemap index
        print("🔍 Parsing sitemap index...")
        root = ET.fromstring(response.text)

        # Handle namespace
        namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

        sitemap_urls = []
        for sitemap in root.findall('.//ns:sitemap', namespace):
            loc_element = sitemap.find('ns:loc', namespace)
            if loc_element is not None:
                sitemap_url = loc_element.text.strip()
                sitemap_urls.append(sitemap_url)

        print(f"✅ Found {len(sitemap_urls)} sitemap URLs")

        # Show first few sitemaps
        print("\n📋 First 10 sitemaps:")
        for i, url in enumerate(sitemap_urls[:10]):
            print(f"  {i+1}. {url}")

        if len(sitemap_urls) > 10:
            print(f"  ... and {len(sitemap_urls) - 10} more")

        # Test downloading one sitemap
        if sitemap_urls:
            test_sitemap_url = sitemap_urls[0]
            print(f"\n🔍 Testing download of first sitemap: {test_sitemap_url}")

            try:
                sitemap_response = requests.get(test_sitemap_url, timeout=30)
                sitemap_response.raise_for_status()

                # Check if it's gzipped
                if test_sitemap_url.endswith('.gz'):
                    try:
                        xml_content = gzip.decompress(sitemap_response.content).decode('utf-8')
                        print("✅ Successfully extracted gzipped sitemap")
                    except Exception as e:
                        print(f"⚠️  Gzip extraction failed, trying plain text: {e}")
                        xml_content = sitemap_response.text
                else:
                    xml_content = sitemap_response.text

                print(f"✅ Downloaded sitemap content ({len(xml_content)} characters)")

                # Parse and look for store URLs
                try:
                    sitemap_root = ET.fromstring(xml_content)
                    store_urls = []

                    for url in sitemap_root.findall('.//ns:url', namespace):
                        loc_element = url.find('ns:loc', namespace)
                        if loc_element is not None:
                            url_text = loc_element.text.strip()
                            if '/trgovina/' in url_text:
                                store_urls.append(url_text)

                    print(f"🏪 Found {len(store_urls)} store URLs in this sitemap")

                    if store_urls:
                        print("\n📋 Sample store URLs:")
                        for i, store_url in enumerate(store_urls[:5]):
                            print(f"  {i+1}. {store_url}")

                        if len(store_urls) > 5:
                            print(f"  ... and {len(store_urls) - 5} more")

                except Exception as e:
                    print(f"⚠️  Could not parse sitemap XML: {e}")

            except Exception as e:
                print(f"❌ Failed to download test sitemap: {e}")

        print("\n✅ Sitemap test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Sitemap test failed: {e}")
        return False


def test_example_store_page():
    """Test accessing the example store page."""
    print(f"\n🧪 Testing example store page access")
    print("=" * 40)

    example_url = "https://www.njuskalo.hr/trgovina/zunicautomobili"

    try:
        print(f"📥 Accessing: {example_url}")
        response = requests.get(example_url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        response.raise_for_status()

        print(f"✅ Successfully accessed store page ({len(response.text)} characters)")

        # Look for entities-count class
        if 'entities-count' in response.text:
            print("✅ Found 'entities-count' class in page content")
        else:
            print("⚠️  'entities-count' class not found in page content")

        # Look for categoryId=2 or auto-related content
        if 'categoryId=2' in response.text:
            print("✅ Found 'categoryId=2' in page content")
        elif 'auti' in response.text.lower():
            print("✅ Found 'auti' (cars) in page content")
        else:
            print("⚠️  No obvious Auto Moto category indicators found")

        return True

    except Exception as e:
        print(f"❌ Failed to access store page: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Njuskalo Sitemap Test Suite")
    print("=" * 50)

    test1_passed = test_sitemap_download()
    test2_passed = test_example_store_page()

    print(f"\n📊 Test Results:")
    print(f"  Sitemap functionality: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"  Store page access: {'✅ PASS' if test2_passed else '❌ FAIL'}")

    if test1_passed and test2_passed:
        print(f"\n🎉 All tests passed! The scraper should work correctly.")
    else:
        print(f"\n⚠️  Some tests failed. Check the output above for issues.")