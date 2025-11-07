import os
import json
import pymysql
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, List, Optional, Any
import logging

# Load environment variables
load_dotenv()

class NjuskaloDatabase:
    """Database manager for Njuskalo scraper data using MySQL"""

    def __init__(self):
        self.connection_params = {
            'host': os.getenv('DATABASE_HOST', 'localhost'),
            'port': int(os.getenv('DATABASE_PORT', '3306')),
            'database': os.getenv('DATABASE_NAME', 'njuskalohr'),
            'user': os.getenv('DATABASE_USER'),
            'password': os.getenv('DATABASE_PASSWORD'),
            'charset': 'utf8mb4',
            'autocommit': False
        }
        self.connection = None
        self.logger = logging.getLogger(__name__)

    def connect(self):
        """Establish database connection"""
        try:
            self.connection = pymysql.connect(**self.connection_params)
            self.logger.info("Successfully connected to MySQL database")
        except pymysql.Error as e:
            self.logger.error(f"Error connecting to MySQL database: {e}")
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
            id INT AUTO_INCREMENT PRIMARY KEY,
            url VARCHAR(2048) UNIQUE NOT NULL,
            results JSON,
            is_valid BOOLEAN DEFAULT TRUE,
            is_automoto BOOLEAN DEFAULT FALSE,
            new_vehicle_count INT DEFAULT 0,
            used_vehicle_count INT DEFAULT 0,
            total_vehicle_count INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            CONSTRAINT unique_url UNIQUE (url)
        );

        CREATE INDEX IF NOT EXISTS idx_scraped_stores_url ON scraped_stores(url);
        CREATE INDEX IF NOT EXISTS idx_scraped_stores_is_valid ON scraped_stores(is_valid);
        CREATE INDEX IF NOT EXISTS idx_scraped_stores_is_automoto ON scraped_stores(is_automoto);
        CREATE INDEX IF NOT EXISTS idx_scraped_stores_created_at ON scraped_stores(created_at);
        CREATE INDEX IF NOT EXISTS idx_scraped_stores_updated_at ON scraped_stores(updated_at);
        """

        try:
            with self.connection.cursor() as cursor:
                # Split and execute each statement separately
                statements = create_table_sql.strip().split(';')
                for statement in statements:
                    statement = statement.strip()
                    if statement:
                        cursor.execute(statement)
                self.connection.commit()
                self.logger.info("Database tables created successfully")
        except pymysql.Error as e:
            self.logger.error(f"Error creating database tables: {e}")
            self.connection.rollback()
            raise

    def migrate_add_is_automoto_column(self):
        """Add is_automoto and vehicle count columns to existing database"""
        try:
            with self.connection.cursor() as cursor:
                # Check if is_automoto column already exists
                cursor.execute("""
                    SELECT COLUMN_NAME
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                    AND TABLE_NAME = 'scraped_stores'
                    AND COLUMN_NAME = 'is_automoto'
                """)

                if cursor.fetchone() is None:
                    # Column doesn't exist, add it
                    cursor.execute("""
                        ALTER TABLE scraped_stores
                        ADD COLUMN is_automoto BOOLEAN DEFAULT FALSE
                        AFTER is_valid
                    """)

                    # Create index for the new column
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_scraped_stores_is_automoto
                        ON scraped_stores(is_automoto)
                    """)

                    self.connection.commit()
                    self.logger.info("Added is_automoto column successfully")

                    # Update existing records based on has_auto_moto in results
                    cursor.execute("""
                        UPDATE scraped_stores
                        SET is_automoto = TRUE
                        WHERE JSON_EXTRACT(results, '$.has_auto_moto') = true
                    """)
                    self.connection.commit()
                    self.logger.info("Updated existing records with is_automoto values")
                else:
                    self.logger.info("is_automoto column already exists")

                # Check and add vehicle count columns
                vehicle_columns = [
                    ('new_vehicle_count', 'INT DEFAULT 0'),
                    ('used_vehicle_count', 'INT DEFAULT 0'),
                    ('total_vehicle_count', 'INT DEFAULT 0')
                ]

                for column_name, column_def in vehicle_columns:
                    cursor.execute("""
                        SELECT COLUMN_NAME
                        FROM INFORMATION_SCHEMA.COLUMNS
                        WHERE TABLE_SCHEMA = DATABASE()
                        AND TABLE_NAME = 'scraped_stores'
                        AND COLUMN_NAME = %s
                    """, (column_name,))

                    if cursor.fetchone() is None:
                        cursor.execute(f"""
                            ALTER TABLE scraped_stores
                            ADD COLUMN {column_name} {column_def}
                            AFTER is_automoto
                        """)
                        self.logger.info(f"Added {column_name} column successfully")

                # Create indexes for vehicle count columns
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_scraped_stores_total_vehicles
                    ON scraped_stores(total_vehicle_count)
                """)

                self.connection.commit()
                self.logger.info("Vehicle count columns migration completed")

        except pymysql.Error as e:
            self.logger.error(f"Error adding columns: {e}")
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
        # Extract is_automoto from store_data and remove it from results
        is_automoto = store_data.pop('has_auto_moto', False)

        # Extract vehicle counts
        new_vehicle_count = store_data.pop('new_vehicle_count', 0)
        used_vehicle_count = store_data.pop('used_vehicle_count', 0)
        total_vehicle_count = store_data.pop('total_vehicle_count', 0)

        # Remove categories from results as well
        store_data.pop('categories', None)

        insert_or_update_sql = """
        INSERT INTO scraped_stores (url, results, is_valid, is_automoto, new_vehicle_count, used_vehicle_count, total_vehicle_count)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            results = VALUES(results),
            is_valid = VALUES(is_valid),
            is_automoto = VALUES(is_automoto),
            new_vehicle_count = VALUES(new_vehicle_count),
            used_vehicle_count = VALUES(used_vehicle_count),
            total_vehicle_count = VALUES(total_vehicle_count),
            updated_at = CURRENT_TIMESTAMP
        """

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(insert_or_update_sql, (
                    url,
                    json.dumps(store_data),
                    is_valid,
                    is_automoto,
                    new_vehicle_count,
                    used_vehicle_count,
                    total_vehicle_count
                ))
                self.connection.commit()

                # Check if it was an insert or update
                if cursor.rowcount == 1:
                    action = "Inserted"
                elif cursor.rowcount == 2:
                    action = "Updated"
                else:
                    action = "No change"

                self.logger.info(f"{action} store data for URL: {url} (is_automoto: {is_automoto}, vehicles: {total_vehicle_count})")
                return True

        except pymysql.Error as e:
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
        insert_or_update_sql = """
        INSERT INTO scraped_stores (url, is_valid, is_automoto, results)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            is_valid = FALSE,
            updated_at = CURRENT_TIMESTAMP
        """

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(insert_or_update_sql, (url, False, False, json.dumps({"error": "URL not accessible"})))
                self.connection.commit()
                self.logger.info(f"Marked URL as invalid: {url}")
                return True

        except pymysql.Error as e:
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
        WHERE url = %s
        """

        try:
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(select_sql, (url,))
                result = cursor.fetchone()

                if result:
                    # Parse JSON results
                    if result['results']:
                        result['results'] = json.loads(result['results'])
                    return result
                return None

        except pymysql.Error as e:
            self.logger.error(f"Error retrieving store data for URL {url}: {e}")
            return None

    def get_all_valid_stores(self) -> List[Dict]:
        """
        Get all valid store entries from the database

        Returns:
            List of dictionaries containing store data
        """
        select_sql = """
        SELECT url, results, created_at, updated_at, is_automoto
        FROM scraped_stores
        WHERE is_valid = TRUE
        ORDER BY updated_at DESC
        """

        try:
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(select_sql)
                results = cursor.fetchall()

                # Parse JSON results
                for result in results:
                    if result['results']:
                        result['results'] = json.loads(result['results'])

                return results

        except pymysql.Error as e:
            self.logger.error(f"Error retrieving valid stores: {e}")
            return []

    def get_invalid_stores(self) -> List[Dict]:
        """
        Get all invalid store entries from the database

        Returns:
            List of dictionaries containing invalid store data
        """
        select_sql = """
        SELECT url, results, created_at, updated_at, is_automoto
        FROM scraped_stores
        WHERE is_valid = FALSE
        ORDER BY updated_at DESC
        """

        try:
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(select_sql)
                results = cursor.fetchall()

                # Parse JSON results
                for result in results:
                    if result['results']:
                        result['results'] = json.loads(result['results'])

                return results

        except pymysql.Error as e:
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
            SUM(CASE WHEN is_valid = TRUE THEN 1 ELSE 0 END) as valid_stores,
            SUM(CASE WHEN is_valid = FALSE THEN 1 ELSE 0 END) as invalid_stores
        FROM scraped_stores
        """

        try:
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(stats_sql)
                result = cursor.fetchone()
                return result if result else {"total_stores": 0, "valid_stores": 0, "invalid_stores": 0}

        except pymysql.Error as e:
            self.logger.error(f"Error retrieving database stats: {e}")
            return {"total_stores": 0, "valid_stores": 0, "invalid_stores": 0}

    def url_exists(self, url: str) -> bool:
        """
        Check if a URL already exists in the database

        Args:
            url: The store URL to check

        Returns:
            True if URL exists, False otherwise
        """
        select_sql = """
        SELECT COUNT(*) as count FROM scraped_stores WHERE url = %s
        """

        try:
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(select_sql, (url,))
                result = cursor.fetchone()
                return result['count'] > 0

        except pymysql.Error as e:
            self.logger.error(f"Error checking if URL exists {url}: {e}")
            return False

    def get_existing_urls(self) -> set:
        """
        Get all existing URLs from the database

        Returns:
            Set of existing URLs
        """
        select_sql = "SELECT url FROM scraped_stores"

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(select_sql)
                results = cursor.fetchall()
                return {row[0] for row in results}

        except pymysql.Error as e:
            self.logger.error(f"Error retrieving existing URLs: {e}")
            return set()

    def get_auto_moto_stores(self) -> List[Dict]:
        """
        Get all valid stores that have auto moto category

        Returns:
            List of dictionaries containing auto moto store data
        """
        select_sql = """
        SELECT url, results, created_at, updated_at, is_automoto
        FROM scraped_stores
        WHERE is_valid = TRUE
        AND is_automoto = TRUE
        ORDER BY updated_at DESC
        """

        try:
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(select_sql)
                results = cursor.fetchall()

                # Parse JSON results
                for result in results:
                    if result['results']:
                        result['results'] = json.loads(result['results'])

                return results

        except pymysql.Error as e:
            self.logger.error(f"Error retrieving auto moto stores: {e}")
            return []

    def get_non_auto_moto_stores(self) -> List[Dict]:
        """
        Get all valid stores that do NOT have auto moto category

        Returns:
            List of dictionaries containing non-auto moto store data
        """
        select_sql = """
        SELECT url, results, created_at, updated_at, is_automoto
        FROM scraped_stores
        WHERE is_valid = TRUE
        AND is_automoto = FALSE
        ORDER BY updated_at DESC
        """

        try:
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(select_sql)
                results = cursor.fetchall()

                # Parse JSON results
                for result in results:
                    if result['results']:
                        result['results'] = json.loads(result['results'])

                return results

        except pymysql.Error as e:
            self.logger.error(f"Error retrieving non-auto moto stores: {e}")
            return []

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()