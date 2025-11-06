#!/usr/bin/env python3
"""
Enhanced Njuskalo Scraper with SSH Tunnel Integration

Usage:
    python3 enhanced_scraper.py --config ssh_tunnels.json --urls urls.txt
    python3 enhanced_scraper.py --auto-rotate --delay 15-30
"""

import argparse
import logging
from scraper_tunnel_integration import EnhancedNjuskaloScraper

def main():
    parser = argparse.ArgumentParser(description="Enhanced Njuskalo Scraper with Tunnels")
    parser.add_argument('--config', default='ssh_tunnels.json', help='Tunnel configuration file')
    parser.add_argument('--urls', help='File containing URLs to scrape')
    parser.add_argument('--url', help='Single URL to scrape')
    parser.add_argument('--auto-rotate', action='store_true', help='Enable auto tunnel rotation')
    parser.add_argument('--delay', default='10-25', help='Delay range between requests (e.g., 10-25)')
    parser.add_argument('--max-requests', type=int, default=100, help='Max requests per tunnel')
    parser.add_argument('--rotation-interval', type=int, default=1800, help='Tunnel rotation interval (seconds)')
    parser.add_argument('--output', default='scrape_results.json', help='Output file')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Parse delay range
    delay_parts = args.delay.split('-')
    delay_range = (float(delay_parts[0]), float(delay_parts[1]) if len(delay_parts) > 1 else float(delay_parts[0]))
    
    # Initialize scraper
    scraper = EnhancedNjuskaloScraper(args.config)
    scraper.auto_rotate = args.auto_rotate
    scraper.max_requests_per_tunnel = args.max_requests
    scraper.rotation_interval = args.rotation_interval
    
    try:
        # Prepare URLs
        urls = []
        if args.urls:
            with open(args.urls, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
        elif args.url:
            urls = [args.url]
        else:
            print("Error: Please provide either --urls or --url")
            return
        
        # Start scraping
        print(f"Starting enhanced scraping of {len(urls)} URLs...")
        results = scraper.scrape_with_rotation(urls, delay_range)
        
        # Save results
        import json
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"Scraping completed. Results saved to: {args.output}")
        
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        scraper.cleanup()

if __name__ == '__main__':
    main()
