#!/usr/bin/env python3
"""
Database Management Script for Njuskalo Scraper (SQLite)
"""

import argparse
import json
from datetime import datetime
from database import NjuskaloDatabase
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_tables():
    try:
        with NjuskaloDatabase() as db:
            db.create_tables()
            print("✅ Database tables created successfully")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")


def show_stats():
    try:
        with NjuskaloDatabase() as db:
            stats = db.get_database_stats()
            print("\n📊 Database Statistics:")
            print(f"  Total stores:   {stats['total_stores']}")
            print(f"  Valid stores:   {stats['valid_stores']}")
            print(f"  Invalid stores: {stats['invalid_stores']}")
            if stats['total_stores']:
                pct = stats['valid_stores'] / stats['total_stores'] * 100
                print(f"  Valid %:        {pct:.1f}%")
    except Exception as e:
        print(f"❌ Error getting stats: {e}")


def list_valid_stores(limit=10):
    try:
        with NjuskaloDatabase() as db:
            stores = db.get_all_valid_stores()
        print(f"\n📋 Valid Stores (showing first {limit}):")
        print("-" * 80)
        for i, store in enumerate(stores[:limit], 1):
            results = store.get('results') or {}
            name = results.get('name', 'Unknown') if isinstance(results, dict) else 'Unknown'
            ads_count = results.get('ads_count', 'N/A') if isinstance(results, dict) else 'N/A'
            auto_icon = "🚗" if store.get('is_automoto') else "❌"
            print(f"{i:2d}. {name[:40]:<40} | Ads: {str(ads_count):>5} | Auto: {auto_icon}")
            print(f"    URL: {store['url']}")
            print(f"    Updated: {store['updated_at']}")
            print()
    except Exception as e:
        print(f"❌ Error listing stores: {e}")


def list_invalid_stores(limit=10):
    try:
        with NjuskaloDatabase() as db:
            stores = db.get_invalid_stores()
        print(f"\n❌ Invalid Stores (showing first {limit}):")
        print("-" * 80)
        for i, store in enumerate(stores[:limit], 1):
            results = store.get('results') or {}
            error = results.get('error', 'Unknown error') if isinstance(results, dict) else 'Unknown'
            print(f"{i:2d}. URL: {store['url']}")
            print(f"    Error:   {error}")
            print(f"    Updated: {store['updated_at']}")
            print()
    except Exception as e:
        print(f"❌ Error listing invalid stores: {e}")


def export_data(filename=None):
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"njuskalo_export_{timestamp}.json"
    try:
        with NjuskaloDatabase() as db:
            stores = db.get_all_valid_stores()
        export_list = [
            {
                'url': s['url'],
                'results': s['results'],
                'created_at': s['created_at'],
                'updated_at': s['updated_at'],
            }
            for s in stores
        ]
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_list, f, indent=2, ensure_ascii=False)
        print(f"✅ Exported {len(export_list)} stores to {filename}")
    except Exception as e:
        print(f"❌ Error exporting data: {e}")


def search_stores(query):
    try:
        with NjuskaloDatabase() as db:
            stores = db.get_all_valid_stores()
        query_lower = query.lower()
        matching = [
            s for s in stores
            if query_lower in s['url'].lower()
            or query_lower in (
                (s.get('results') or {}).get('name', '') if isinstance(s.get('results'), dict) else ''
            ).lower()
        ]
        print(f"\n🔍 Search Results for '{query}' ({len(matching)} found):")
        print("-" * 80)
        for i, store in enumerate(matching, 1):
            results = store.get('results') or {}
            name = results.get('name', 'Unknown') if isinstance(results, dict) else 'Unknown'
            auto_icon = "🚗" if store.get('is_automoto') else "❌"
            print(f"{i:2d}. {name[:40]:<40} | Auto: {auto_icon}")
            print(f"    URL: {store['url']}")
            print()
    except Exception as e:
        print(f"❌ Error searching stores: {e}")


def migrate_database():
    try:
        print("🔄 Running database migrations...")
        with NjuskaloDatabase() as db:
            db.migrate_add_is_automoto_column()
            db.migrate_add_store_snapshots_table()
            stats = db.get_database_stats()
        print("✅ Migration completed successfully!")
        print(f"  Total stores:   {stats['total_stores']}")
        print(f"  Valid stores:   {stats['valid_stores']}")
    except Exception as e:
        print(f"❌ Migration failed: {e}")


def main():
    parser = argparse.ArgumentParser(description='Njuskalo Database Management (SQLite)')
    parser.add_argument('command', choices=[
        'create-tables', 'migrate', 'stats', 'list-valid', 'list-invalid', 'export', 'search'
    ])
    parser.add_argument('--limit',  type=int, default=10)
    parser.add_argument('--output', help='Output filename for export')
    parser.add_argument('--query',  help='Search query')
    args = parser.parse_args()

    if args.command == 'create-tables':
        create_tables()
    elif args.command == 'migrate':
        migrate_database()
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
            print("❌ --query is required for search")
            return
        search_stores(args.query)


if __name__ == '__main__':
    main()
