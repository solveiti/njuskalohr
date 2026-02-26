import os
import json
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, List, Optional, Any
import logging

# Load environment variables
load_dotenv()

_DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), 'njuskalo.db')


def _dict_factory(cursor, row):
    """Return rows as dicts."""
    return {col[0]: val for col, val in zip(cursor.description, row)}


class NjuskaloDatabase:
    """Database manager for Njuskalo scraper data using SQLite"""

    def __init__(self):
        self.db_path = os.getenv('DATABASE_PATH', _DEFAULT_DB_PATH)
        self.connection: Optional[sqlite3.Connection] = None
        self.logger = logging.getLogger(__name__)

    def connect(self):
        """Establish database connection"""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = _dict_factory
            # Enable WAL for better concurrent read performance
            self.connection.execute("PRAGMA journal_mode=WAL")
            self.connection.execute("PRAGMA foreign_keys=ON")
            self.logger.info(f"Connected to SQLite database at {self.db_path}")
        except sqlite3.Error as e:
            self.logger.error(f"Error connecting to SQLite database: {e}")
            raise

    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            self.logger.info("Database connection closed")

    def create_tables(self):
        """Create the required database tables"""
        statements = [
            """
            CREATE TABLE IF NOT EXISTS scraped_stores (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                url             TEXT UNIQUE NOT NULL,
                results         TEXT,
                is_valid        INTEGER NOT NULL DEFAULT 1,
                is_automoto     INTEGER NOT NULL DEFAULT 0,
                new_vehicle_count  INTEGER NOT NULL DEFAULT 0,
                used_vehicle_count INTEGER NOT NULL DEFAULT 0,
                test_vehicle_count INTEGER NOT NULL DEFAULT 0,
                total_vehicle_count INTEGER NOT NULL DEFAULT 0,
                created_at      TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_scraped_stores_url        ON scraped_stores(url)",
            "CREATE INDEX IF NOT EXISTS idx_scraped_stores_is_valid   ON scraped_stores(is_valid)",
            "CREATE INDEX IF NOT EXISTS idx_scraped_stores_is_automoto ON scraped_stores(is_automoto)",
            "CREATE INDEX IF NOT EXISTS idx_scraped_stores_created_at ON scraped_stores(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_scraped_stores_updated_at ON scraped_stores(updated_at)",
            """
            CREATE TABLE IF NOT EXISTS store_snapshots (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                url          TEXT NOT NULL,
                scraped_at   TEXT NOT NULL DEFAULT (datetime('now')),
                active_new   INTEGER NOT NULL DEFAULT 0,
                active_used  INTEGER NOT NULL DEFAULT 0,
                active_test  INTEGER NOT NULL DEFAULT 0,
                active_total INTEGER NOT NULL DEFAULT 0,
                delta_new    INTEGER NOT NULL DEFAULT 0,
                delta_used   INTEGER NOT NULL DEFAULT 0,
                delta_test   INTEGER NOT NULL DEFAULT 0,
                delta_total  INTEGER NOT NULL DEFAULT 0
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_snapshots_url        ON store_snapshots(url)",
            "CREATE INDEX IF NOT EXISTS idx_snapshots_scraped_at ON store_snapshots(scraped_at)",
        ]

        try:
            for statement in statements:
                statement = statement.strip()
                if statement:
                    self.connection.execute(statement)
            self.connection.commit()
            self.logger.info("Database tables created successfully")
        except sqlite3.Error as e:
            self.logger.error(f"Error creating database tables: {e}")
            self.connection.rollback()
            raise

    def migrate_add_is_automoto_column(self):
        """Add is_automoto and vehicle count columns to existing database (idempotent)."""
        try:
            existing = {
                row['name']
                for row in self.connection.execute("PRAGMA table_info(scraped_stores)").fetchall()
            }

            if 'is_automoto' not in existing:
                self.connection.execute(
                    "ALTER TABLE scraped_stores ADD COLUMN is_automoto INTEGER NOT NULL DEFAULT 0"
                )
                self.connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_scraped_stores_is_automoto ON scraped_stores(is_automoto)"
                )
                # Best-effort update from JSON blob
                self.connection.execute(
                    """
                    UPDATE scraped_stores
                    SET is_automoto = 1
                    WHERE json_extract(results, '$.has_auto_moto') = 1
                    """
                )
                self.logger.info("Added is_automoto column")

            for col, default in [
                ('new_vehicle_count',   0),
                ('used_vehicle_count',  0),
                ('test_vehicle_count',  0),
                ('total_vehicle_count', 0),
            ]:
                if col not in existing:
                    self.connection.execute(
                        f"ALTER TABLE scraped_stores ADD COLUMN {col} INTEGER NOT NULL DEFAULT {default}"
                    )
                    self.logger.info(f"Added {col} column")

            self.connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_scraped_stores_total_vehicles ON scraped_stores(total_vehicle_count)"
            )
            self.connection.commit()
            self.logger.info("Vehicle count columns migration completed")

        except sqlite3.Error as e:
            self.logger.error(f"Error in migrate_add_is_automoto_column: {e}")
            self.connection.rollback()
            raise

    def migrate_add_store_snapshots_table(self):
        """Create store_snapshots table if it doesn't exist (safe to re-run)."""
        try:
            tables = {
                row['name']
                for row in self.connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if 'store_snapshots' not in tables:
                self.connection.execute("""
                    CREATE TABLE store_snapshots (
                        id           INTEGER PRIMARY KEY AUTOINCREMENT,
                        url          TEXT NOT NULL,
                        scraped_at   TEXT NOT NULL DEFAULT (datetime('now')),
                        active_new   INTEGER NOT NULL DEFAULT 0,
                        active_used  INTEGER NOT NULL DEFAULT 0,
                        active_test  INTEGER NOT NULL DEFAULT 0,
                        active_total INTEGER NOT NULL DEFAULT 0,
                        delta_new    INTEGER NOT NULL DEFAULT 0,
                        delta_used   INTEGER NOT NULL DEFAULT 0,
                        delta_test   INTEGER NOT NULL DEFAULT 0,
                        delta_total  INTEGER NOT NULL DEFAULT 0
                    )
                """)
                self.connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_snapshots_url ON store_snapshots(url)"
                )
                self.connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_snapshots_scraped_at ON store_snapshots(scraped_at)"
                )
                self.connection.commit()
                self.logger.info("Created store_snapshots table")
            else:
                self.logger.info("store_snapshots table already exists")
        except sqlite3.Error as e:
            self.logger.error(f"Error creating store_snapshots table: {e}")
            self.connection.rollback()
            raise

    def save_store_snapshot(
        self,
        url: str,
        active_new: int,
        active_used: int,
        active_test: int,
    ) -> bool:
        """
        Record a snapshot of current active vehicle counts and compute delta vs. previous run.

        Delta semantics:
          - Positive  → count went UP (new stock listed)
          - Negative  → count went DOWN (ads removed / sold)
          - First run → deltas are 0 (no baseline)
        """
        active_total = active_new + active_used + active_test
        delta_new = delta_used = delta_test = delta_total = 0

        try:
            prev = self.connection.execute(
                """
                SELECT active_new, active_used, active_test, active_total
                FROM store_snapshots
                WHERE url = ?
                ORDER BY scraped_at DESC
                LIMIT 1
                """,
                (url,),
            ).fetchone()
            if prev:
                delta_new   = active_new   - prev['active_new']
                delta_used  = active_used  - prev['active_used']
                delta_test  = active_test  - prev['active_test']
                delta_total = active_total - prev['active_total']
        except sqlite3.Error as e:
            self.logger.warning(f"Could not read previous snapshot for {url}: {e}")

        try:
            self.connection.execute(
                """
                INSERT INTO store_snapshots
                    (url, active_new, active_used, active_test, active_total,
                     delta_new, delta_used, delta_test, delta_total)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (url, active_new, active_used, active_test, active_total,
                 delta_new, delta_used, delta_test, delta_total),
            )
            self.connection.commit()
            self.logger.info(
                f"Snapshot saved for {url} — "
                f"active: new={active_new} used={active_used} test={active_test} | "
                f"delta: new={delta_new:+d} used={delta_used:+d} test={delta_test:+d}"
            )
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Error saving snapshot for {url}: {e}")
            self.connection.rollback()
            return False

    def get_store_snapshots(self, url: str, limit: int = 50) -> List[Dict]:
        """Retrieve snapshot history for a store, newest first."""
        try:
            return self.connection.execute(
                """
                SELECT scraped_at,
                       active_new, active_used, active_test, active_total,
                       delta_new,  delta_used,  delta_test,  delta_total
                FROM store_snapshots
                WHERE url = ?
                ORDER BY scraped_at DESC
                LIMIT ?
                """,
                (url, limit),
            ).fetchall()
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving snapshots for {url}: {e}")
            return []

    def save_store_data(self, url: str, store_data: Dict[str, Any], is_valid: bool = True) -> bool:
        """Save or update store data in the database."""
        is_automoto        = store_data.pop('has_auto_moto', False)
        new_vehicle_count  = store_data.pop('new_vehicle_count', 0)
        used_vehicle_count = store_data.pop('used_vehicle_count', 0)
        test_vehicle_count = store_data.pop('test_vehicle_count', 0)
        total_vehicle_count = store_data.pop('total_vehicle_count', 0)
        store_data.pop('categories', None)

        try:
            self.connection.execute(
                """
                INSERT INTO scraped_stores
                    (url, results, is_valid, is_automoto,
                     new_vehicle_count, used_vehicle_count, test_vehicle_count, total_vehicle_count,
                     updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(url) DO UPDATE SET
                    results             = excluded.results,
                    is_valid            = excluded.is_valid,
                    is_automoto         = excluded.is_automoto,
                    new_vehicle_count   = excluded.new_vehicle_count,
                    used_vehicle_count  = excluded.used_vehicle_count,
                    test_vehicle_count  = excluded.test_vehicle_count,
                    total_vehicle_count = excluded.total_vehicle_count,
                    updated_at          = datetime('now')
                """,
                (
                    url,
                    json.dumps(store_data),
                    1 if is_valid else 0,
                    1 if is_automoto else 0,
                    new_vehicle_count,
                    used_vehicle_count,
                    test_vehicle_count,
                    total_vehicle_count,
                ),
            )
            self.connection.commit()
            self.logger.info(
                f"Saved store {url} "
                f"(automoto={is_automoto}, new={new_vehicle_count}, "
                f"used={used_vehicle_count}, test={test_vehicle_count}, total={total_vehicle_count})"
            )
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Error saving store data for {url}: {e}")
            self.connection.rollback()
            return False

    def mark_url_invalid(self, url: str) -> bool:
        """Mark a URL as invalid in the database."""
        try:
            self.connection.execute(
                """
                INSERT INTO scraped_stores (url, is_valid, is_automoto, results, updated_at)
                VALUES (?, 0, 0, ?, datetime('now'))
                ON CONFLICT(url) DO UPDATE SET
                    is_valid   = 0,
                    updated_at = datetime('now')
                """,
                (url, json.dumps({"error": "URL not accessible"})),
            )
            self.connection.commit()
            self.logger.info(f"Marked URL as invalid: {url}")
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Error marking URL as invalid {url}: {e}")
            self.connection.rollback()
            return False

    def get_store_data(self, url: str) -> Optional[Dict]:
        """Retrieve store data for a specific URL."""
        try:
            row = self.connection.execute(
                "SELECT url, results, is_valid, created_at, updated_at FROM scraped_stores WHERE url = ?",
                (url,),
            ).fetchone()
            if row and row['results']:
                row['results'] = json.loads(row['results'])
            return row
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving store data for {url}: {e}")
            return None

    def _fetch_stores(self, sql: str, params: tuple = ()) -> List[Dict]:
        """Internal helper: run a SELECT and parse JSON results column."""
        try:
            rows = self.connection.execute(sql, params).fetchall()
            for row in rows:
                if row.get('results'):
                    row['results'] = json.loads(row['results'])
                # Normalise SQLite integers to Python bools
                row['is_valid']    = bool(row.get('is_valid', 1))
                row['is_automoto'] = bool(row.get('is_automoto', 0))
            return rows
        except sqlite3.Error as e:
            self.logger.error(f"Error executing store query: {e}")
            return []

    def get_all_valid_stores(self) -> List[Dict]:
        return self._fetch_stores(
            """
            SELECT url, results, created_at, updated_at, is_automoto,
                   new_vehicle_count, used_vehicle_count, test_vehicle_count, total_vehicle_count
            FROM scraped_stores
            WHERE is_valid = 1
            ORDER BY updated_at DESC
            """
        )

    def get_invalid_stores(self) -> List[Dict]:
        return self._fetch_stores(
            """
            SELECT url, results, created_at, updated_at, is_automoto,
                   new_vehicle_count, used_vehicle_count, test_vehicle_count, total_vehicle_count
            FROM scraped_stores
            WHERE is_valid = 0
            ORDER BY updated_at DESC
            """
        )

    def get_auto_moto_stores(self) -> List[Dict]:
        return self._fetch_stores(
            """
            SELECT url, results, created_at, updated_at, is_automoto,
                   new_vehicle_count, used_vehicle_count, test_vehicle_count, total_vehicle_count
            FROM scraped_stores
            WHERE is_valid = 1 AND is_automoto = 1
            ORDER BY updated_at DESC
            """
        )

    def get_non_auto_moto_stores(self) -> List[Dict]:
        return self._fetch_stores(
            """
            SELECT url, results, created_at, updated_at, is_automoto
            FROM scraped_stores
            WHERE is_valid = 1 AND is_automoto = 0
            ORDER BY updated_at DESC
            """
        )

    def get_database_stats(self) -> Dict[str, int]:
        """Return counts of valid/invalid stores."""
        try:
            row = self.connection.execute(
                """
                SELECT
                    COUNT(*)                              AS total_stores,
                    SUM(CASE WHEN is_valid = 1 THEN 1 ELSE 0 END) AS valid_stores,
                    SUM(CASE WHEN is_valid = 0 THEN 1 ELSE 0 END) AS invalid_stores
                FROM scraped_stores
                """
            ).fetchone()
            return row if row else {"total_stores": 0, "valid_stores": 0, "invalid_stores": 0}
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving database stats: {e}")
            return {"total_stores": 0, "valid_stores": 0, "invalid_stores": 0}

    def url_exists(self, url: str) -> bool:
        """Return True if a URL is already in the database."""
        try:
            row = self.connection.execute(
                "SELECT COUNT(*) AS cnt FROM scraped_stores WHERE url = ?", (url,)
            ).fetchone()
            return (row['cnt'] if row else 0) > 0
        except sqlite3.Error as e:
            self.logger.error(f"Error checking if URL exists {url}: {e}")
            return False

    def get_existing_urls(self) -> set:
        """Return the set of all URLs already in the database."""
        try:
            rows = self.connection.execute("SELECT url FROM scraped_stores").fetchall()
            return {row['url'] for row in rows}
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving existing URLs: {e}")
            return set()

    def get_latest_update_timestamp(self) -> Optional[datetime]:
        """Return the datetime of the most recently updated record, or None."""
        try:
            row = self.connection.execute(
                "SELECT MAX(updated_at) AS latest_update FROM scraped_stores"
            ).fetchone()
            if row and row['latest_update']:
                return datetime.fromisoformat(row['latest_update'])
            return None
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving latest update timestamp: {e}")
            return None

    def get_latest_snapshots_by_url(self) -> Dict[str, Dict]:
        """
        Return the most recent store_snapshots row for every URL in one query.

        Returns a dict keyed by store URL; callers should use .get(url, {}) with 0 defaults
        for stores that have never been snapshotted.
        """
        sql = """
        SELECT s.url,
               s.scraped_at,
               s.active_new, s.active_used, s.active_test, s.active_total,
               s.delta_new,  s.delta_used,  s.delta_test,  s.delta_total
        FROM store_snapshots s
        INNER JOIN (
            SELECT url, MAX(scraped_at) AS latest
            FROM store_snapshots
            GROUP BY url
        ) latest ON s.url = latest.url AND s.scraped_at = latest.latest
        """
        try:
            rows = self.connection.execute(sql).fetchall()
            return {row['url']: row for row in rows}
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving latest snapshots: {e}")
            return {}

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
