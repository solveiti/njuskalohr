#!/usr/bin/env python3
"""
Test script for database integration
"""

import sys
import os
import logging
from database import NjuskaloDatabase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_basic():
    """Test basic database operations"""
    print("🧪 Testing basic database operations...")

    try:
        with NjuskaloDatabase() as db:
            # Test connection
            print("✅ Database connection successful")

            # Create tables
            db.create_tables()
            print("✅ Database tables created/verified")

            # Test storing data
            test_store_data = {
                'url': 'https://www.njuskalo.hr/trgovina/test-store',
                'name': 'Test Store',
                'address': 'Test Address 123, Zagreb',
                'ads_count': 42,
                'has_auto_moto': True,
                'categories': [
                    {'text': 'Auto i motori', 'href': '/categoryId=2'}
                ],
                'error': None
            }

            success = db.save_store_data(
                url='https://www.njuskalo.hr/trgovina/test-store',
                store_data=test_store_data,
                is_valid=True
            )

            if success:
                print("✅ Test data stored successfully")
            else:
                print("❌ Failed to store test data")
                return False

            # Test retrieving data
            retrieved_data = db.get_store_data('https://www.njuskalo.hr/trgovina/test-store')
            if retrieved_data:
                print("✅ Test data retrieved successfully")
                print(f"   Store name: {retrieved_data['results']['name']}")
                print(f"   Ads count: {retrieved_data['results']['ads_count']}")
            else:
                print("❌ Failed to retrieve test data")
                return False

            # Test statistics
            stats = db.get_database_stats()
            print(f"✅ Database stats: {stats}")

            # Test marking as invalid
            success = db.mark_url_invalid('https://www.njuskalo.hr/trgovina/invalid-store')
            if success:
                print("✅ Invalid URL marking works")
            else:
                print("❌ Failed to mark URL as invalid")
                return False

            # Test getting valid stores
            valid_stores = db.get_all_valid_stores()
            print(f"✅ Found {len(valid_stores)} valid stores")

            # Test getting invalid stores
            invalid_stores = db.get_invalid_stores()
            print(f"✅ Found {len(invalid_stores)} invalid stores")

            return True

    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_scraper_with_database():
    """Test scraper with database integration"""
    print("\n🧪 Testing scraper with database integration...")

    try:
        from njuskalo_sitemap_scraper import NjuskaloSitemapScraper

        # Create scraper with database enabled
        scraper = NjuskaloSitemapScraper(headless=True, use_database=True)

        # Test a single store (you could replace this with a known working store URL)
        test_url = "https://www.njuskalo.hr/trgovina/test-manual"

        # Mock store data for testing (in real scenario this would be scraped)
        mock_store_data = {
            'url': test_url,
            'name': 'Manual Test Store',
            'address': 'Manual Test Address',
            'ads_count': 15,
            'has_auto_moto': False,
            'categories': [],
            'error': None
        }

        # Initialize database connection
        scraper.database = NjuskaloDatabase()
        scraper.database.connect()
        scraper.database.create_tables()

        # Test saving to database
        success = scraper.database.save_store_data(
            url=test_url,
            store_data=mock_store_data,
            is_valid=True
        )

        if success:
            print("✅ Scraper database integration works")
        else:
            print("❌ Scraper database integration failed")
            return False

        # Clean up
        scraper.database.disconnect()

        return True

    except Exception as e:
        print(f"❌ Scraper integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("🚀 Njuskalo Database Integration Tests")
    print("=" * 50)

    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ No .env file found")
        print("Please run 'python setup_database.py' first to set up the database")
        return False

    # Test basic database operations
    if not test_database_basic():
        print("\n❌ Basic database tests failed")
        return False

    # Test scraper integration
    if not test_scraper_with_database():
        print("\n❌ Scraper integration tests failed")
        return False

    print("\n🎉 All database integration tests passed!")
    print("\nNext steps:")
    print("1. Run the scraper: python run_scraper.py --max-stores 3")
    print("2. Check results: python db_manager.py stats")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)