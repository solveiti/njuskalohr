#!/usr/bin/env python3
"""
Test script to specifically check the stores sitemap for store URLs.
"""

import requests
import xml.etree.ElementTree as ET
import gzip


def test_stores_sitemap():
    """Test the stores-specific sitemap."""
    print("🧪 Testing Stores Sitemap")
    print("=" * 40)

    stores_sitemap_url = "https://www.njuskalo.hr/sitemap-index-stores.xml"

    try:
        print(f"📥 Downloading stores sitemap: {stores_sitemap_url}")
        response = requests.get(stores_sitemap_url, timeout=30)
        response.raise_for_status()

        print(f"✅ Successfully downloaded stores sitemap ({len(response.text)} characters)")

        # Parse the stores sitemap (which may contain further sitemap URLs)
        root = ET.fromstring(response.text)
        namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

        # Check if this is a sitemap index or a direct sitemap
        sitemaps = root.findall('.//ns:sitemap', namespace)
        urls = root.findall('.//ns:url', namespace)

        if sitemaps:
            print(f"📋 This is a sitemap index with {len(sitemaps)} sub-sitemaps:")
            for i, sitemap in enumerate(sitemaps[:10]):  # Show first 10
                loc_element = sitemap.find('ns:loc', namespace)
                if loc_element is not None:
                    print(f"  {i+1}. {loc_element.text.strip()}")

            if len(sitemaps) > 10:
                print(f"  ... and {len(sitemaps) - 10} more")

            # Test downloading one of the sub-sitemaps
            if sitemaps:
                first_sitemap = sitemaps[0].find('ns:loc', namespace).text.strip()
                print(f"\n🔍 Testing first sub-sitemap: {first_sitemap}")

                sub_response = requests.get(first_sitemap, timeout=30)
                sub_response.raise_for_status()

                # Handle gzip if needed
                if first_sitemap.endswith('.gz'):
                    try:
                        sub_content = gzip.decompress(sub_response.content).decode('utf-8')
                        print("✅ Successfully extracted gzipped sub-sitemap")
                    except Exception as e:
                        print(f"⚠️  Gzip extraction failed: {e}")
                        try:
                            sub_content = sub_response.content.decode('utf-8')
                            print("✅ Using content as plain text")
                        except Exception:
                            print("❌ Could not decode content")
                            return False
                else:
                    sub_content = sub_response.text

                print(f"📄 Sub-sitemap content length: {len(sub_content)} characters")

                # Clean up the XML content before parsing
                try:
                    # Remove any non-XML content or fix common issues
                    if sub_content.startswith('<?xml'):
                        xml_start = sub_content.find('<?xml')
                        sub_content = sub_content[xml_start:]

                    # Try to find where actual XML content starts
                    if '<urlset' in sub_content:
                        urlset_start = sub_content.find('<urlset')
                        if urlset_start > 0:
                            # Find the XML declaration before urlset
                            xml_start = sub_content.rfind('<?xml', 0, urlset_start)
                            if xml_start >= 0:
                                sub_content = sub_content[xml_start:]
                            else:
                                sub_content = sub_content[urlset_start:]

                    print(f"📄 Cleaned content length: {len(sub_content)} characters")

                    # Parse for store URLs
                    sub_root = ET.fromstring(sub_content)
                    store_urls = []

                    for url in sub_root.findall('.//ns:url', namespace):
                        loc_element = url.find('ns:loc', namespace)
                        if loc_element is not None:
                            url_text = loc_element.text.strip()
                            if '/trgovina/' in url_text:
                                store_urls.append(url_text)

                    print(f"🏪 Found {len(store_urls)} store URLs in first sub-sitemap")

                    if store_urls:
                        print("\n📋 Sample store URLs:")
                        for i, store_url in enumerate(store_urls[:5]):
                            print(f"  {i+1}. {store_url}")

                        if len(store_urls) > 5:
                            print(f"  ... and {len(store_urls) - 5} more")

                except ET.ParseError as e:
                    print(f"⚠️  XML parsing error: {e}")
                    print("📝 Showing first 500 characters of content:")
                    print(sub_content[:500])
                    print("...")

                    # Try a different approach - use regex to find URLs
                    import re
                    url_pattern = r'<loc>(https://www\.njuskalo\.hr/trgovina/[^<]+)</loc>'
                    matches = re.findall(url_pattern, sub_content)
                    if matches:
                        print(f"🔍 Found {len(matches)} store URLs using regex:")
                        for i, url in enumerate(matches[:5]):
                            print(f"  {i+1}. {url}")
                        if len(matches) > 5:
                            print(f"  ... and {len(matches) - 5} more")

        elif urls:
            print(f"📋 This is a direct sitemap with {len(urls)} URLs")

            # Look for store URLs directly
            store_urls = []
            for url in urls:
                loc_element = url.find('ns:loc', namespace)
                if loc_element is not None:
                    url_text = loc_element.text.strip()
                    if '/trgovina/' in url_text:
                        store_urls.append(url_text)

            print(f"🏪 Found {len(store_urls)} store URLs")

            if store_urls:
                print("\n📋 Sample store URLs:")
                for i, store_url in enumerate(store_urls[:10]):
                    print(f"  {i+1}. {store_url}")

                if len(store_urls) > 10:
                    print(f"  ... and {len(store_urls) - 10} more")

        else:
            print("⚠️  No sitemaps or URLs found in the stores sitemap")

        return True

    except Exception as e:
        print(f"❌ Error testing stores sitemap: {e}")
        return False


if __name__ == "__main__":
    test_stores_sitemap()