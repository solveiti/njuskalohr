#!/usr/bin/env python3
"""
Export Njuskalo Database to Excel

This script exports scraped store data directly from the database to an Excel file
without running the scraper. It uses the same format as the scraper's save_to_excel method.

Usage:
    python export_db_to_excel.py                  # all valid stores
    python export_db_to_excel.py --only-automoto  # auto moto stores only
    python export_db_to_excel.py --include-invalid
    python export_db_to_excel.py --filename my_export.xlsx
"""

import os
import sys
import time
import argparse
import logging
from datetime import datetime
import pandas as pd
from database import NjuskaloDatabase

# Configure logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/export_db_to_excel.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def export_database_to_excel(
    filename: str = None,
    only_automoto: bool = False,
    include_invalid: bool = False
) -> bool:
    """
    Export database records to Excel file.

    Columns exported
    ----------------
    Store info:
        id, vat, name, subname, address, url, is_automoto, updated_at

    Current active ad counts (from last scrape):
        active_new, active_used, active_test, active_total

    Change vs. previous scrape run (negative = ads sold/removed):
        delta_new, delta_used, delta_test, delta_total

    Legacy / convenience columns (same as active_* for backward compat):
        new, used, test, total

    For stores that have only been scraped once (first run) or have no
    snapshot history, all snapshot columns default to 0.

    Args:
        filename:        Output filename (auto-generated if None)
        only_automoto:   Export only stores with auto moto category
        include_invalid: Include invalid stores in export

    Returns:
        bool: True if successful, False otherwise
    """
    db = None
    try:
        logger.info("Connecting to database...")
        db = NjuskaloDatabase()
        db.connect()

        # Fetch store rows
        if only_automoto:
            logger.info("Fetching auto moto stores from database...")
            stores = db.get_auto_moto_stores()
        elif include_invalid:
            logger.info("Fetching all stores (including invalid) from database...")
            stores = db.get_all_valid_stores() + db.get_invalid_stores()
        else:
            logger.info("Fetching valid stores from database...")
            stores = db.get_all_valid_stores()

        if not stores:
            logger.warning("No data found in database")
            return False

        logger.info(f"Found {len(stores)} stores in database")

        # Fetch latest snapshot per store in a single query
        # Returns {} if store_snapshots table is empty or doesn't exist yet
        try:
            snapshots = db.get_latest_snapshots_by_url()
            logger.info(f"Loaded snapshots for {len(snapshots)} stores")
        except Exception as e:
            logger.warning(f"Could not load snapshots (first run?): {e}")
            snapshots = {}

        # Output directory
        datadump_dir = "datadump"
        os.makedirs(datadump_dir, exist_ok=True)

        if not filename:
            timestamp = int(time.time())
            filter_suffix = "_automoto" if only_automoto else "_all" if include_invalid else ""
            filename = f"njuskalo_stores_db{filter_suffix}_{timestamp}.xlsx"

        if not filename.startswith(datadump_dir):
            filename = os.path.join(datadump_dir, filename)

        # Build rows
        df_data = []
        for i, store_record in enumerate(stores, start=1):
            store_data = store_record.get('results') or {}

            # ── Active vehicle counts (from last scrape, stored in scraped_stores) ──
            db_new  = store_record.get('new_vehicle_count', 0) or 0
            db_used = store_record.get('used_vehicle_count', 0) or 0
            db_test = store_record.get('test_vehicle_count', 0) or 0
            db_total = store_record.get('total_vehicle_count', 0) or 0

            # Fallback to JSON blob if DB columns are all zero
            if db_new == 0 and db_used == 0 and db_test == 0:
                db_new  = store_data.get('new_vehicle_count',  store_data.get('new_ads_count',  0)) or 0
                db_used = store_data.get('used_vehicle_count', store_data.get('used_ads_count', 0)) or 0
                db_test = store_data.get('test_vehicle_count', 0) or 0
                db_total = db_new + db_used + db_test

            # ── Snapshot columns (defaults to 0 when no history exists) ──
            snap = snapshots.get(store_record.get('url', ''), {})
            active_new   = snap.get('active_new',   db_new)   or 0
            active_used  = snap.get('active_used',  db_used)  or 0
            active_test  = snap.get('active_test',  db_test)  or 0
            active_total = snap.get('active_total', db_total) or 0
            delta_new    = snap.get('delta_new',    0) or 0
            delta_used   = snap.get('delta_used',   0) or 0
            delta_test   = snap.get('delta_test',   0) or 0
            delta_total  = snap.get('delta_total',  0) or 0

            df_data.append({
                'id':           i,
                'vat':          '',
                'name':         store_data.get('name', ''),
                'subname':      store_data.get('subname', ''),
                'address':      store_data.get('address', ''),
                # current active counts
                'active_new':   active_new,
                'active_used':  active_used,
                'active_test':  active_test,
                'active_total': active_total,
                # change vs previous run (negative = sold/removed)
                'delta_new':    delta_new,
                'delta_used':   delta_used,
                'delta_test':   delta_test,
                'delta_total':  delta_total,
                # legacy convenience columns (same as active_*)
                'new':          active_new,
                'used':         active_used,
                'test':         active_test,
                'total':        active_total,
                'url':          store_record.get('url', ''),
                'is_automoto':  store_record.get('is_automoto', False),
                'updated_at':   store_record.get('updated_at', ''),
            })

        df = pd.DataFrame(df_data)

        column_order = [
            'id', 'vat', 'name', 'subname', 'address',
            'active_new', 'active_used', 'active_test', 'active_total',
            'delta_new', 'delta_used', 'delta_test', 'delta_total',
            'new', 'used', 'test', 'total',
            'url', 'is_automoto', 'updated_at',
        ]
        df = df.reindex(columns=column_order)

        # String columns
        for col in ('vat', 'name', 'subname', 'address'):
            df[col] = df[col].fillna('')

        # Integer columns
        int_cols = [
            'active_new', 'active_used', 'active_test', 'active_total',
            'delta_new', 'delta_used', 'delta_test', 'delta_total',
            'new', 'used', 'test', 'total',
        ]
        for col in int_cols:
            df[col] = df[col].fillna(0).astype(int)

        df.to_excel(filename, index=False)
        logger.info(f"✅ Successfully exported {len(stores)} stores to {filename}")

        # Summary
        print(f"\n📊 Export Summary:")
        print(f"  Stores exported:      {len(stores)}")
        print(f"  Auto moto stores:     {df['is_automoto'].sum()}")
        print(f"  Active new ads:       {df['active_new'].sum()}")
        print(f"  Active used ads:      {df['active_used'].sum()}")
        print(f"  Active test ads:      {df['active_test'].sum()}")
        print(f"  Active total ads:     {df['active_total'].sum()}")
        sold_new  = df[df['delta_new']  < 0]['delta_new'].sum()
        sold_used = df[df['delta_used'] < 0]['delta_used'].sum()
        sold_test = df[df['delta_test'] < 0]['delta_test'].sum()
        print(f"  Ads removed (new):    {abs(sold_new)}")
        print(f"  Ads removed (used):   {abs(sold_used)}")
        print(f"  Ads removed (test):   {abs(sold_test)}")
        print(f"  Stores with no prior snapshot (delta=0): "
              f"{(df['delta_total'] == 0).sum()}")
        print(f"\n📁 Output file: {filename}")

        return True

    except Exception as e:
        logger.error(f"❌ Failed to export database to Excel: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if db:
            db.disconnect()
            logger.info("Database connection closed")


def main():
    parser = argparse.ArgumentParser(
        description="Export Njuskalo database to Excel file"
    )
    parser.add_argument(
        "--filename", "-f",
        type=str,
        help="Output filename (default: auto-generated with timestamp)"
    )
    parser.add_argument(
        "--only-automoto", "-a",
        action="store_true",
        help="Export only auto moto stores"
    )
    parser.add_argument(
        "--include-invalid", "-i",
        action="store_true",
        help="Include invalid stores in export"
    )

    args = parser.parse_args()

    try:
        success = export_database_to_excel(
            filename=args.filename,
            only_automoto=args.only_automoto,
            include_invalid=args.include_invalid
        )
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        logger.info("\n⚠️ Export interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
