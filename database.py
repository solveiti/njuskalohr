import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, List, Optional, Any
import logging

# Load environment variables
load_dotenv()

class NjuskaloDatabase:
    """Database manager for Njuskalo scraper data"""

    def __init__(self):
        self.connection_params = {
            'host': os.getenv('DATABASE_HOST', 'localhost'),
            'port': os.getenv('DATABASE_PORT', '5432'),
            'database': os.getenv('DATABASE_NAME', 'njuskalohr'),
            'user': os.getenv('DATABASE_USER'),
            'password': os.getenv('DATABASE_PASSWORD')
        }
        self.connection = None
        self.logger = logging.getLogger(__name__)

    def connect(self):
        """Establish database connection"""
        try:
            self.connection = psycopg2.connect(**self.connection_params)
            self.logger.info("Successfully connected to PostgreSQL database")
        except psycopg2.Error as e:
            self.logger.error(f"Error connecting to PostgreSQL database: {e}")
            raise

    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.logger.info("Database connection closed")

    def create_tables(self):
        """Create the required database tables"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS scraped_stores (
            id SERIAL PRIMARY KEY,
            url VARCHAR(2048) UNIQUE NOT NULL,
            results JSONB,
            is_valid BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_url UNIQUE (url)
        );

        CREATE INDEX IF NOT EXISTS idx_scraped_stores_url ON scraped_stores(url);
        CREATE INDEX IF NOT EXISTS idx_scraped_stores_is_valid ON scraped_stores(is_valid);
        CREATE INDEX IF NOT EXISTS idx_scraped_stores_created_at ON scraped_stores(created_at);
        CREATE INDEX IF NOT EXISTS idx_scraped_stores_updated_at ON scraped_stores(updated_at);
        CREATE INDEX IF NOT EXISTS idx_scraped_stores_results_gin ON scraped_stores USING GIN (results);

        -- Create trigger for updating updated_at timestamp
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';

        DROP TRIGGER IF EXISTS update_scraped_stores_updated_at ON scraped_stores;
        CREATE TRIGGER update_scraped_stores_updated_at
            BEFORE UPDATE ON scraped_stores
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(create_table_sql)
                self.connection.commit()
                self.logger.info("Database tables created successfully")
        except psycopg2.Error as e:
            self.logger.error(f"Error creating database tables: {e}")
            self.connection.rollback()
            raise

    def save_store_data(self, url: str, store_data: Dict[str, Any], is_valid: bool = True) -> bool:
        """
        Save or update store data in the database

        Args:
            url: The store URL
            store_data: Dictionary containing store information
            is_valid: Whether the URL is valid and accessible

        Returns:
            bool: True if operation was successful
        """
        insert_or_update_sql = """
        INSERT INTO scraped_stores (url, results, is_valid)
        VALUES (%s, %s, %s)
        ON CONFLICT (url)
        DO UPDATE SET
            results = EXCLUDED.results,
            is_valid = EXCLUDED.is_valid,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id, created_at, updated_at;
        """

        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(insert_or_update_sql, (url, Json(store_data), is_valid))
                result = cursor.fetchone()
                self.connection.commit()

                action = "Updated" if result['created_at'] != result['updated_at'] else "Inserted"
                self.logger.info(f"{action} store data for URL: {url}")
                return True

        except psycopg2.Error as e:
            self.logger.error(f"Error saving store data for URL {url}: {e}")
            self.connection.rollback()
            return False

    def mark_url_invalid(self, url: str) -> bool:
        """
        Mark a URL as invalid in the database

        Args:
            url: The store URL to mark as invalid

        Returns:
            bool: True if operation was successful
        """
        update_sql = """
        INSERT INTO scraped_stores (url, is_valid, results)
        VALUES (%s, %s, %s)
        ON CONFLICT (url)
        DO UPDATE SET
            is_valid = FALSE,
            updated_at = CURRENT_TIMESTAMP;
        """

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(update_sql, (url, False, Json({"error": "URL not accessible"})))
                self.connection.commit()
                self.logger.info(f"Marked URL as invalid: {url}")
                return True

        except psycopg2.Error as e:
            self.logger.error(f"Error marking URL as invalid {url}: {e}")
            self.connection.rollback()
            return False

    def get_store_data(self, url: str) -> Optional[Dict]:
        """
        Retrieve store data for a specific URL

        Args:
            url: The store URL to retrieve

        Returns:
            Dict containing store data or None if not found
        """
        select_sql = """
        SELECT url, results, is_valid, created_at, updated_at
        FROM scraped_stores
        WHERE url = %s;
        """

        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(select_sql, (url,))
                result = cursor.fetchone()
                return dict(result) if result else None

        except psycopg2.Error as e:
            self.logger.error(f"Error retrieving store data for URL {url}: {e}")
            return None

    def get_all_valid_stores(self) -> List[Dict]:
        """
        Get all valid store entries from the database

        Returns:
            List of dictionaries containing store data
        """
        select_sql = """
        SELECT url, results, created_at, updated_at
        FROM scraped_stores
        WHERE is_valid = TRUE
        ORDER BY updated_at DESC;
        """

        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(select_sql)
                results = cursor.fetchall()
                return [dict(row) for row in results]

        except psycopg2.Error as e:
            self.logger.error(f"Error retrieving valid stores: {e}")
            return []

    def get_invalid_stores(self) -> List[Dict]:
        """
        Get all invalid store entries from the database

        Returns:
            List of dictionaries containing invalid store data
        """
        select_sql = """
        SELECT url, results, created_at, updated_at
        FROM scraped_stores
        WHERE is_valid = FALSE
        ORDER BY updated_at DESC;
        """

        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(select_sql)
                results = cursor.fetchall()
                return [dict(row) for row in results]

        except psycopg2.Error as e:
            self.logger.error(f"Error retrieving invalid stores: {e}")
            return []

    def get_database_stats(self) -> Dict[str, int]:
        """
        Get statistics about the database

        Returns:
            Dictionary with counts of valid/invalid stores
        """
        stats_sql = """
        SELECT
            COUNT(*) as total_stores,
            COUNT(CASE WHEN is_valid = TRUE THEN 1 END) as valid_stores,
            COUNT(CASE WHEN is_valid = FALSE THEN 1 END) as invalid_stores
        FROM scraped_stores;
        """

        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(stats_sql)
                result = cursor.fetchone()
                return dict(result) if result else {"total_stores": 0, "valid_stores": 0, "invalid_stores": 0}

        except psycopg2.Error as e:
            self.logger.error(f"Error retrieving database stats: {e}")
            return {"total_stores": 0, "valid_stores": 0, "invalid_stores": 0}

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()