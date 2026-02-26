#!/usr/bin/env python3
"""
Njuskalo Scraper - Manual Runner

Usage:
    python run_scraper.py                      # full scrape with tunnels
    python run_scraper.py --mode enhanced      # enhanced scrape, no tunnels
    python run_scraper.py --mode basic         # basic sitemap scrape
    python run_scraper.py --max-stores 10      # limit to 10 stores (for testing)
    python run_scraper.py --no-database        # skip database, print results only
    python run_scraper.py --no-tunnels         # disable SSH tunnels
    python run_scraper.py --verbose            # debug logging
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from sentry_helper import init_sentry


def setup_logging(verbose: bool = False) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger("run_scraper")


def print_results(results: dict):
    print("\n" + "=" * 60)
    print("SCRAPING RESULTS")
    print("=" * 60)
    for key, value in results.items():
        if key != "errors":
            print(f"  {key}: {value}")
    errors = results.get("errors", [])
    if errors:
        print(f"\n  Errors ({len(errors)}):")
        for e in errors[:10]:
            print(f"    - {e}")
    print("=" * 60)


def run_tunnel_scrape(args, logger):
    try:
        from enhanced_tunnel_scraper import TunnelEnabledEnhancedScraper
    except ImportError:
        logger.error("TunnelEnabledEnhancedScraper not available")
        sys.exit(1)

    logger.info("Starting enhanced tunnel scrape...")
    scraper = TunnelEnabledEnhancedScraper(
        headless=args.headless,
        use_database=not args.no_database,
        tunnel_config_path=args.tunnel_config,
        use_tunnels=not args.no_tunnels,
        preferred_tunnel=args.tunnel,
    )
    try:
        results = scraper.run_enhanced_scrape_with_tunnels(max_stores=args.max_stores)
        print_results(results)

        if not args.no_database:
            _save_excel(scraper, logger, prefix="tunnel")
    finally:
        _cleanup_browser(scraper, logger)


def run_enhanced_scrape(args, logger):
    try:
        from enhanced_njuskalo_scraper import EnhancedNjuskaloScraper
    except ImportError:
        logger.error("EnhancedNjuskaloScraper not available")
        sys.exit(1)

    logger.info("Starting enhanced scrape (no tunnels)...")
    scraper = EnhancedNjuskaloScraper(headless=args.headless, use_database=not args.no_database)
    try:
        results = scraper.run_enhanced_scrape(max_stores=args.max_stores)
        print_results(results)

        if not args.no_database:
            _save_excel(scraper, logger, prefix="enhanced")
    finally:
        _cleanup_browser(scraper, logger)


def run_basic_scrape(args, logger):
    from njuskalo_sitemap_scraper import NjuskaloSitemapScraper

    logger.info("Starting basic sitemap scrape...")
    scraper = NjuskaloSitemapScraper(headless=args.headless, use_database=not args.no_database)
    try:
        stores = scraper.run_full_scrape(max_stores=args.max_stores)

        print("\n" + "=" * 60)
        print("SCRAPING RESULTS")
        print("=" * 60)
        print(f"  Total stores scraped:   {len(stores)}")
        auto_moto = [s for s in stores if s.get("has_auto_moto")]
        print(f"  Auto moto stores:       {len(auto_moto)}")
        with_address = [s for s in stores if s.get("address")]
        print(f"  Stores with address:    {len(with_address)}")
        print("=" * 60)

        if stores and not args.no_database:
            _save_excel(scraper, logger, prefix="basic")
    finally:
        _cleanup_browser(scraper, logger)


def _save_excel(scraper, logger, prefix: str):
    os.makedirs("datadump", exist_ok=True)
    timestamp = int(datetime.now().timestamp())
    filename = f"njuskalo_{prefix}_{timestamp}.xlsx"
    try:
        saved = scraper.save_to_excel(filename)
        if saved:
            logger.info(f"Results saved to datadump/{filename}")
        else:
            logger.warning("Failed to save Excel file")
    except Exception as e:
        logger.warning(f"Could not save Excel: {e}")


def _cleanup_browser(scraper, logger):
    try:
        if hasattr(scraper, "driver") and scraper.driver:
            scraper.driver.quit()
            logger.info("Browser closed")
    except Exception:
        pass
    try:
        if hasattr(scraper, "close"):
            scraper.close()
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(
        description="Njuskalo Scraper - run manually from terminal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--mode",
        choices=["tunnel", "enhanced", "basic"],
        default="tunnel",
        help="Scraping mode (default: tunnel)",
    )
    parser.add_argument(
        "--max-stores",
        type=int,
        default=None,
        metavar="N",
        help="Limit scraping to N stores (default: all)",
    )
    parser.add_argument(
        "--no-tunnels",
        action="store_true",
        help="Disable SSH tunnels (tunnel mode only)",
    )
    parser.add_argument(
        "--tunnel",
        metavar="NAME",
        help="Use a specific tunnel by name",
    )
    parser.add_argument(
        "--tunnel-config",
        default="tunnel_config.json",
        metavar="PATH",
        help="Path to tunnel config file (default: tunnel_config.json)",
    )
    parser.add_argument(
        "--no-database",
        action="store_true",
        help="Skip database and Excel output, print results only",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser headless (default: visible in X/VNC display)",
    )

    args = parser.parse_args()
    logger = setup_logging(args.verbose)
    init_sentry("scraper")

    logger.info(f"Mode: {args.mode} | Max stores: {args.max_stores or 'all'} | "
                f"Tunnels: {not args.no_tunnels} | DB: {not args.no_database}")

    start = datetime.now()
    try:
        if args.mode == "tunnel":
            run_tunnel_scrape(args, logger)
        elif args.mode == "enhanced":
            run_enhanced_scrape(args, logger)
        else:
            run_basic_scrape(args, logger)
    except KeyboardInterrupt:
        logger.info("Interrupted by user (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=args.verbose)
        sys.exit(1)

    elapsed = (datetime.now() - start).total_seconds()
    logger.info(f"Done in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
