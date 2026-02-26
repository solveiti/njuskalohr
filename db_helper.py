"""
Simple database helper for Njuskalo HR system.
Read-only query helpers for scraped_stores.
"""

import os
import json
import sqlite3
from typing import Dict, List, Optional, Any
import logging
from dotenv import load_dotenv

from models import AdItem, ScrapedStore, parse_json_field

# Load environment variables
load_dotenv()

_DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), 'njuskalo.db')


def _dict_factory(cursor, row):
    return {col[0]: val for col, val in zip(cursor.description, row)}


class SimpleDatabase:
    """Simple read-only database helper"""

    def __init__(self):
        self.db_path = os.getenv('DATABASE_PATH', _DEFAULT_DB_PATH)
        self.connection: Optional[sqlite3.Connection] = None
        self.logger = logging.getLogger(__name__)

    def connect(self):
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = _dict_factory
            self.connection.execute("PRAGMA journal_mode=WAL")
            self.logger.info(f"Connected to SQLite database at {self.db_path}")
        except sqlite3.Error as e:
            self.logger.error(f"Error connecting to database: {e}")
            raise

    def disconnect(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def _parse_store_row(self, row: Dict) -> Dict:
        if not row:
            return row
        if row.get('results'):
            row['results'] = parse_json_field(row['results'])
        row['is_valid']    = bool(row.get('is_valid', 1))
        row['is_automoto'] = bool(row.get('is_automoto', 0))
        return row

    # ── scraped_stores queries ────────────────────────────────────────────────

    def get_scraped_stores(self, limit: int = 100) -> List[Dict]:
        """Get valid scraped stores, most recently updated first."""
        try:
            rows = self.connection.execute(
                """
                SELECT id, url, results, is_valid, is_automoto,
                       new_vehicle_count, used_vehicle_count, test_vehicle_count, total_vehicle_count,
                       created_at, updated_at
                FROM scraped_stores
                WHERE is_valid = 1
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [self._parse_store_row(row) for row in rows]
        except sqlite3.Error as e:
            self.logger.error(f"Error getting scraped stores: {e}")
            return []

    def get_store_by_url(self, url: str) -> Optional[Dict]:
        """Get a single store by URL."""
        try:
            row = self.connection.execute(
                """
                SELECT id, url, results, is_valid, is_automoto,
                       new_vehicle_count, used_vehicle_count, test_vehicle_count, total_vehicle_count,
                       created_at, updated_at
                FROM scraped_stores
                WHERE url = ?
                """,
                (url,),
            ).fetchone()
            return self._parse_store_row(row) if row else None
        except sqlite3.Error as e:
            self.logger.error(f"Error getting store by URL: {e}")
            return None

    def get_auto_moto_stores(self, limit: int = 500) -> List[Dict]:
        """Get valid stores that have the auto moto category."""
        try:
            rows = self.connection.execute(
                """
                SELECT id, url, results, is_automoto,
                       new_vehicle_count, used_vehicle_count, test_vehicle_count, total_vehicle_count,
                       updated_at
                FROM scraped_stores
                WHERE is_valid = 1 AND is_automoto = 1
                ORDER BY total_vehicle_count DESC, updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [self._parse_store_row(row) for row in rows]
        except sqlite3.Error as e:
            self.logger.error(f"Error getting auto moto stores: {e}")
            return []

    def get_table_counts(self) -> Dict[str, int]:
        """Return row counts for known tables."""
        tables = ['scraped_stores', 'store_snapshots']
        counts = {}
        for table in tables:
            try:
                row = self.connection.execute(f"SELECT COUNT(*) AS cnt FROM {table}").fetchone()
                counts[table] = row['cnt'] if row else 0
            except sqlite3.Error:
                counts[table] = 0
        return counts

    def execute_query(self, sql: str, params: tuple = ()) -> List[Dict]:
        """Execute a custom read-only SQL query."""
        try:
            return self.connection.execute(sql, params).fetchall()
        except sqlite3.Error as e:
            self.logger.error(f"Error executing query: {e}")
            return []
