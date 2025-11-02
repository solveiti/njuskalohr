#!/usr/bin/env python3
"""
Database Management Script for Njuskalo Scraper

This script provides utilities for managing the PostgreSQL database used by the Njuskalo scraper.
"""

import argparse
import json
from datetime import datetime
from database import NjuskaloDatabase
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_tables():
    """Create database tables"""
    try:
        with NjuskaloDatabase() as db:
            db.create_tables()
            print("✅ Database tables created successfully")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")


def show_stats():
    """Show database statistics"""
    try:
        with NjuskaloDatabase() as db:
            stats = db.get_database_stats()
            print("\n📊 Database Statistics:")
            print(f"Total stores: {stats['total_stores']}")
            print(f"Valid stores: {stats['valid_stores']}")
            print(f"Invalid stores: {stats['invalid_stores']}")

            if stats['total_stores'] > 0:
                valid_percentage = (stats['valid_stores'] / stats['total_stores']) * 100
                print(f"Valid percentage: {valid_percentage:.1f}%")

    except Exception as e:
        print(f"❌ Error getting stats: {e}")


def list_valid_stores(limit=10):
    """List valid stores"""
    try:
        with NjuskaloDatabase() as db:
            stores = db.get_all_valid_stores()

            print(f"\n📋 Valid Stores (showing first {limit}):")
            print("-" * 80)

            for i, store in enumerate(stores[:limit], 1):
                results = store.get('results', {})
                name = results.get('name', 'Unknown')
                ads_count = results.get('ads_count', 'N/A')
                has_auto_moto = results.get('has_auto_moto', False)
                auto_icon = "🚗" if has_auto_moto else "❌"

                print(f"{i:2d}. {name[:40]:<40} | Ads: {str(ads_count):>5} | Auto: {auto_icon}")
                print(f"    URL: {store['url']}")
                print(f"    Updated: {store['updated_at']}")
                print()

    except Exception as e:
        print(f"❌ Error listing stores: {e}")


def list_invalid_stores(limit=10):
    """List invalid stores"""
    try:
        with NjuskaloDatabase() as db:
            stores = db.get_invalid_stores()

            print(f"\n❌ Invalid Stores (showing first {limit}):")
            print("-" * 80)

            for i, store in enumerate(stores[:limit], 1):
                results = store.get('results', {})
                error = results.get('error', 'Unknown error')

                print(f"{i:2d}. URL: {store['url']}")
                print(f"    Error: {error}")
                print(f"    Updated: {store['updated_at']}")
                print()

    except Exception as e:
        print(f"❌ Error listing invalid stores: {e}")


def export_data(filename=None):
    """Export all valid store data to JSON"""
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"njuskalo_export_{timestamp}.json"

    try:
        with NjuskaloDatabase() as db:
            stores = db.get_all_valid_stores()

            # Prepare data for export
            export_data = []
            for store in stores:
                export_data.append({
                    'url': store['url'],
                    'results': store['results'],
                    'created_at': store['created_at'].isoformat() if store['created_at'] else None,
                    'updated_at': store['updated_at'].isoformat() if store['updated_at'] else None
                })

            # Write to JSON file
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            print(f"✅ Exported {len(export_data)} stores to {filename}")

    except Exception as e:
        print(f"❌ Error exporting data: {e}")


def search_stores(query):
    """Search stores by name or URL"""
    try:
        with NjuskaloDatabase() as db:
            stores = db.get_all_valid_stores()

            # Filter stores based on query
            matching_stores = []
            query_lower = query.lower()

            for store in stores:
                results = store.get('results', {})
                name = results.get('name', '').lower()
                url = store['url'].lower()

                if query_lower in name or query_lower in url:
                    matching_stores.append(store)

            print(f"\n🔍 Search Results for '{query}' ({len(matching_stores)} found):")
            print("-" * 80)

            for i, store in enumerate(matching_stores, 1):
                results = store.get('results', {})
                name = results.get('name', 'Unknown')
                ads_count = results.get('ads_count', 'N/A')
                has_auto_moto = results.get('has_auto_moto', False)
                auto_icon = "🚗" if has_auto_moto else "❌"

                print(f"{i:2d}. {name[:40]:<40} | Ads: {str(ads_count):>5} | Auto: {auto_icon}")
                print(f"    URL: {store['url']}")
                print()

    except Exception as e:
        print(f"❌ Error searching stores: {e}")


def main():
    parser = argparse.ArgumentParser(description='Njuskalo Database Management')
    parser.add_argument('command', choices=[
        'create-tables', 'stats', 'list-valid', 'list-invalid',
        'export', 'search'
    ], help='Command to execute')
    parser.add_argument('--limit', type=int, default=10, help='Limit for list commands')
    parser.add_argument('--output', help='Output filename for export')
    parser.add_argument('--query', help='Search query')

    args = parser.parse_args()

    if args.command == 'create-tables':
        create_tables()
    elif args.command == 'stats':
        show_stats()
    elif args.command == 'list-valid':
        list_valid_stores(args.limit)
    elif args.command == 'list-invalid':
        list_invalid_stores(args.limit)
    elif args.command == 'export':
        export_data(args.output)
    elif args.command == 'search':
        if not args.query:
            print("❌ Search query is required. Use --query 'search term'")
            return
        search_stores(args.query)


if __name__ == '__main__':
    main()