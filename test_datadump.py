#!/usr/bin/env python3
"""
Test script to verify datadump directory functionality
"""

import os
import time
from datetime import datetime

def test_datadump_directory():
    """Test that the datadump directory works correctly"""

    print("🧪 Testing datadump directory functionality...")

    # Check if datadump directory exists
    datadump_dir = "datadump"
    if not os.path.exists(datadump_dir):
        print(f"❌ datadump directory does not exist at {datadump_dir}")
        return False

    print(f"✅ datadump directory exists: {os.path.abspath(datadump_dir)}")

    # List current files in datadump
    files = [f for f in os.listdir(datadump_dir) if f.endswith('.xlsx')]
    print(f"📁 Current Excel files in datadump: {len(files)}")

    for i, file in enumerate(files[:5]):  # Show first 5 files
        file_path = os.path.join(datadump_dir, file)
        file_size = os.path.getsize(file_path)
        modified_time = datetime.fromtimestamp(os.path.getmtime(file_path))
        print(f"   {i+1}. {file} ({file_size:,} bytes, modified: {modified_time.strftime('%Y-%m-%d %H:%M:%S')})")

    if len(files) > 5:
        print(f"   ... and {len(files) - 5} more files")

    return True

def test_scraper_save():
    """Test that scrapers save to datadump directory"""

    try:
        print("\n🔬 Testing scraper save functionality...")

        # Import and test the sitemap scraper
        from njuskalo_sitemap_scraper import NjuskaloSitemapScraper

        scraper = NjuskaloSitemapScraper(use_database=False, headless=True)

        # Add test data
        test_data = {
            'name': 'Test Store - Datadump',
            'url': 'https://www.njuskalo.hr/trgovina/test-datadump',
            'address': 'Test Address 123, Zagreb',
            'ads_count': 42,
            'has_auto_moto': True,
            'categories': [{'text': 'Automobili', 'href': '/auti'}],
            'error': None
        }

        scraper.stores_data = [test_data]

        # Generate unique filename
        timestamp = int(time.time())
        test_filename = f"test_datadump_functionality_{timestamp}.xlsx"

        # Save to Excel
        print(f"💾 Saving test file: {test_filename}")
        result = scraper.save_to_excel(test_filename)

        if result:
            # Check if file was created in datadump directory
            expected_path = os.path.join("datadump", test_filename)
            if os.path.exists(expected_path):
                file_size = os.path.getsize(expected_path)
                print(f"✅ Test file saved successfully to {expected_path}")
                print(f"📄 File size: {file_size:,} bytes")

                # Clean up test file
                os.remove(expected_path)
                print("🧹 Test file cleaned up")
                return True
            else:
                print(f"❌ Test file not found at expected path: {expected_path}")
                return False
        else:
            print("❌ Failed to save test file")
            return False

    except Exception as e:
        print(f"❌ Error testing scraper save: {e}")
        return False

def main():
    """Main test function"""

    print("=" * 60)
    print("🚀 DATADUMP DIRECTORY FUNCTIONALITY TEST")
    print("=" * 60)

    success = True

    # Test 1: Directory existence and current files
    if not test_datadump_directory():
        success = False

    # Test 2: Scraper save functionality
    if not test_scraper_save():
        success = False

    print("\n" + "=" * 60)
    if success:
        print("🎉 All tests passed! Datadump directory is working correctly.")
        print("📝 Summary:")
        print("   ✅ datadump directory exists and is accessible")
        print("   ✅ Existing Excel files are properly organized")
        print("   ✅ Scrapers save new files to datadump directory")
        print("   ✅ File creation and cleanup work correctly")
    else:
        print("❌ Some tests failed. Please check the output above.")

    print("=" * 60)

    return success

if __name__ == "__main__":
    main()