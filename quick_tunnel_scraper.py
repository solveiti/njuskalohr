#!/usr/bin/env python3
"""
Quick Tunnel Scraper Runner

Simple script to run the tunnel-enabled scraper with common configurations.
"""

import sys
import os
from pathlib import Path

def run_with_tunnels(max_stores=None, use_database=False, verbose=False):
    """
    Run scraper with tunnels enabled
    
    Args:
        max_stores: Limit number of stores (None for all)
        use_database: Save to database (False for CSV only)
        verbose: Enable debug logging
    """
    try:
        from njuskalo_scraper_with_tunnels import TunnelEnabledNjuskaloScraper
        
        print("🚀 Starting Tunnel-Enabled Njuskalo Scraper")
        print("=" * 50)
        
        # Check configuration files
        if not os.path.exists('tunnel_config.json'):
            print("❌ Error: tunnel_config.json not found")
            print("💡 Make sure tunnel_config.json is in the current directory")
            return False
            
        if not os.path.exists('tunnel_key'):
            print("❌ Error: SSH private key 'tunnel_key' not found") 
            print("💡 Make sure your SSH private key is in the current directory")
            return False
            
        print("✅ Configuration files found")
        print(f"🔧 Max stores: {max_stores or 'All'}")
        print(f"💾 Database: {'Enabled' if use_database else 'CSV only'}")
        print(f"🔍 Logging: {'Verbose' if verbose else 'Normal'}")
        print()
        
        # Initialize scraper
        scraper = TunnelEnabledNjuskaloScraper(
            headless=True,
            use_database=use_database,
            tunnel_config_path='tunnel_config.json',
            use_tunnels=True
        )
        
        # Run scraping
        print("🏃 Starting scraping process...")
        stores_data = scraper.run_full_scrape(max_stores=max_stores)
        
        if stores_data:
            print(f"\n✅ Scraping completed successfully!")
            print(f"📊 Total stores processed: {len(stores_data)}")
            return True
        else:
            print("⚠️ No data was collected")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure all required files are present")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def run_without_tunnels(max_stores=None, use_database=False):
    """
    Run scraper without tunnels (fallback mode)
    """
    try:
        from njuskalo_scraper_with_tunnels import TunnelEnabledNjuskaloScraper
        
        print("🚀 Starting Scraper (No Tunnels)")
        print("=" * 40)
        
        scraper = TunnelEnabledNjuskaloScraper(
            headless=True,
            use_database=use_database,
            use_tunnels=False
        )
        
        stores_data = scraper.run_full_scrape(max_stores=max_stores)
        
        if stores_data:
            print(f"\n✅ Scraping completed successfully!")
            print(f"📊 Total stores processed: {len(stores_data)}")
            return True
        else:
            print("⚠️ No data was collected")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main function with simple menu"""
    print("🕷️  Njuskalo Tunnel Scraper")
    print("=" * 30)
    print()
    print("Choose an option:")
    print("1. Quick test with tunnels (5 stores)")
    print("2. Full scrape with tunnels") 
    print("3. Quick test without tunnels (5 stores)")
    print("4. Full scrape without tunnels")
    print("5. Custom configuration")
    print()
    
    try:
        choice = input("Enter choice (1-5): ").strip()
        
        if choice == "1":
            print("\n🧪 Quick test with tunnels (5 stores)...")
            return run_with_tunnels(max_stores=5, use_database=False)
            
        elif choice == "2":
            print("\n🚀 Full scrape with tunnels...")
            return run_with_tunnels(use_database=False)
            
        elif choice == "3":
            print("\n🧪 Quick test without tunnels (5 stores)...")
            return run_without_tunnels(max_stores=5, use_database=False)
            
        elif choice == "4":
            print("\n🚀 Full scrape without tunnels...")
            return run_without_tunnels(use_database=False)
            
        elif choice == "5":
            print("\n⚙️ Custom configuration:")
            max_stores = input("Max stores (press Enter for all): ").strip()
            max_stores = int(max_stores) if max_stores else None
            
            use_tunnels = input("Use tunnels? (y/n): ").strip().lower() == 'y'
            use_database = input("Use database? (y/n): ").strip().lower() == 'y'
            
            if use_tunnels:
                return run_with_tunnels(max_stores=max_stores, use_database=use_database)
            else:
                return run_without_tunnels(max_stores=max_stores, use_database=use_database)
                
        else:
            print("❌ Invalid choice")
            return False
            
    except KeyboardInterrupt:
        print("\n⚠️ Cancelled by user")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)