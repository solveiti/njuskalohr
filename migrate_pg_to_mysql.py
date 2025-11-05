#!/usr/bin/env python3
"""
Data Migration Script: PostgreSQL to MySQL
==========================================

This script migrates all data from PostgreSQL to MySQL for the njuskalohr project.
It handles the transfer of scraped_stores table and preserves all existing data.

Usage:
    python migrate_pg_to_mysql.py

Requirements:
    - Both PostgreSQL and MySQL servers running
    - psycopg2-binary and PyMySQL packages installed
    - Access credentials for both databases
"""

import sys
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv
from dateutil import parser

# Import database drivers
try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("ERROR: psycopg2 not installed. Install with: pip install psycopg2-binary")
    sys.exit(1)

try:
    import pymysql
except ImportError:
    print("ERROR: PyMySQL not installed. Install with: pip install PyMySQL")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    def __init__(self):
        # Load environment variables
        load_dotenv()

        # PostgreSQL configuration (source)
        self.pg_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'njuskalohr',
            'user': 'hellios',
            'password': '6hell6is6'
        }

        # MySQL configuration (destination)
        self.mysql_config = {
            'host': os.getenv('DATABASE_HOST', 'localhost'),
            'port': int(os.getenv('DATABASE_PORT', 3306)),
            'database': os.getenv('DATABASE_NAME', 'njuskalohr'),
            'user': os.getenv('DATABASE_USER', 'hellios'),
            'password': os.getenv('DATABASE_PASSWORD', '6hell6is6'),
            'charset': 'utf8mb4'
        }

        self.pg_conn = None
        self.mysql_conn = None

    def connect_postgresql(self) -> bool:
        """Connect to PostgreSQL database"""
        try:
            self.pg_conn = psycopg2.connect(**self.pg_config)
            logger.info("Connected to PostgreSQL successfully")
            return True
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            return False

    def connect_mysql(self) -> bool:
        """Connect to MySQL database"""
        try:
            self.mysql_conn = pymysql.connect(**self.mysql_config)
            logger.info("Connected to MySQL successfully")
            return True
        except pymysql.Error as e:
            logger.error(f"Failed to connect to MySQL: {e}")
            return False

    def create_mysql_tables(self) -> bool:
        """Create tables in MySQL database"""
        try:
            cursor = self.mysql_conn.cursor()

            # Create scraped_stores table to match the actual schema
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS scraped_stores (
                id INT AUTO_INCREMENT PRIMARY KEY,
                url VARCHAR(2048) UNIQUE NOT NULL,
                results JSON,
                is_valid BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                CONSTRAINT unique_url UNIQUE (url)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """

            cursor.execute(create_table_sql)
            self.mysql_conn.commit()
            logger.info("MySQL tables created successfully")
            return True

        except pymysql.Error as e:
            logger.error(f"Failed to create MySQL tables: {e}")
            return False
        finally:
            cursor.close()

    def get_postgresql_data(self) -> List[Dict[str, Any]]:
        """Fetch all data from PostgreSQL scraped_stores table"""
        try:
            cursor = self.pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Get all data from scraped_stores table
            cursor.execute("SELECT * FROM scraped_stores ORDER BY id")
            rows = cursor.fetchall()

            # Convert to list of dictionaries
            data = []
            for row in rows:
                record = dict(row)
                # Convert datetime objects to MySQL-compatible format
                for key, value in record.items():
                    if isinstance(value, datetime):
                        # Convert timezone-aware datetime to UTC and format for MySQL
                        if value.tzinfo is not None:
                            # Convert to UTC and remove timezone info
                            utc_value = value.utctimetuple()
                            record[key] = datetime(*utc_value[:6])
                        else:
                            record[key] = value
                    elif key in ['created_at', 'updated_at'] and isinstance(value, str):
                        # Handle string datetime values with timezone
                        try:
                            parsed_dt = parser.parse(value)
                            if parsed_dt.tzinfo is not None:
                                # Convert to UTC and remove timezone info
                                utc_dt = parsed_dt.utctimetuple()
                                record[key] = datetime(*utc_dt[:6])
                            else:
                                record[key] = parsed_dt
                        except Exception as e:
                            logger.warning(f"Could not parse datetime {value}: {e}")
                            record[key] = None
                data.append(record)

            logger.info(f"Retrieved {len(data)} records from PostgreSQL")
            return data

        except psycopg2.Error as e:
            logger.error(f"Failed to fetch PostgreSQL data: {e}")
            return []
        finally:
            cursor.close()

    def insert_mysql_data(self, data: List[Dict[str, Any]]) -> bool:
        """Insert data into MySQL database"""
        if not data:
            logger.warning("No data to insert into MySQL")
            return True

        try:
            cursor = self.mysql_conn.cursor()

            # Prepare insert statement to match actual schema
            insert_sql = """
            INSERT INTO scraped_stores
            (url, results, is_valid, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            results = VALUES(results),
            is_valid = VALUES(is_valid),
            updated_at = VALUES(updated_at)
            """

            # Insert data batch by batch
            batch_size = 100
            total_inserted = 0

            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                batch_data = []

                for record in batch:
                    # Convert results to JSON string if it's a dict/list
                    results = record.get('results')
                    if results and not isinstance(results, str):
                        results = json.dumps(results)

                    batch_data.append((
                        record.get('url'),
                        results,
                        record.get('is_valid', True),
                        record.get('created_at'),
                        record.get('updated_at', record.get('created_at'))
                    ))

                cursor.executemany(insert_sql, batch_data)
                self.mysql_conn.commit()
                total_inserted += len(batch)
                logger.info(f"Inserted batch {i//batch_size + 1}: {total_inserted}/{len(data)} records")

            logger.info(f"Successfully inserted {total_inserted} records into MySQL")
            return True

        except pymysql.Error as e:
            logger.error(f"Failed to insert data into MySQL: {e}")
            self.mysql_conn.rollback()
            return False
        finally:
            cursor.close()

    def verify_migration(self) -> bool:
        """Verify that migration was successful"""
        try:
            # Count records in PostgreSQL
            pg_cursor = self.pg_conn.cursor()
            pg_cursor.execute("SELECT COUNT(*) FROM scraped_stores")
            pg_count = pg_cursor.fetchone()[0]
            pg_cursor.close()

            # Count records in MySQL
            mysql_cursor = self.mysql_conn.cursor()
            mysql_cursor.execute("SELECT COUNT(*) FROM scraped_stores")
            mysql_count = mysql_cursor.fetchone()[0]
            mysql_cursor.close()

            logger.info(f"PostgreSQL records: {pg_count}")
            logger.info(f"MySQL records: {mysql_count}")

            if pg_count == mysql_count:
                logger.info("✅ Migration verification successful! Record counts match.")
                return True
            else:
                logger.warning("⚠️ Record counts don't match. Please investigate.")
                return False

        except Exception as e:
            logger.error(f"Failed to verify migration: {e}")
            return False

    def close_connections(self):
        """Close database connections"""
        if self.pg_conn:
            self.pg_conn.close()
            logger.info("PostgreSQL connection closed")

        if self.mysql_conn:
            self.mysql_conn.close()
            logger.info("MySQL connection closed")

    def migrate(self) -> bool:
        """Run the complete migration process"""
        logger.info("Starting PostgreSQL to MySQL migration...")

        # Connect to databases
        if not self.connect_postgresql():
            return False

        if not self.connect_mysql():
            return False

        # Create MySQL tables
        if not self.create_mysql_tables():
            return False

        # Get data from PostgreSQL
        data = self.get_postgresql_data()
        if not data:
            logger.warning("No data found in PostgreSQL database")
            return True

        # Insert data into MySQL
        if not self.insert_mysql_data(data):
            return False

        # Verify migration
        success = self.verify_migration()

        logger.info(f"Migration {'completed successfully' if success else 'completed with warnings'}")
        return success

def main():
    """Main function to run the migration"""
    print("🔄 Starting PostgreSQL to MySQL Migration")
    print("=" * 50)

    migrator = DatabaseMigrator()

    try:
        success = migrator.migrate()

        if success:
            print("✅ Migration completed successfully!")
            print("📊 Check migration.log for detailed information")
            print("\nNext steps:")
            print("1. Test your application with MySQL")
            print("2. Update any remaining PostgreSQL references")
            print("3. Backup your PostgreSQL database before removing it")
        else:
            print("❌ Migration failed. Check migration.log for details")
            return 1

    except KeyboardInterrupt:
        print("\n🛑 Migration interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error during migration: {e}")
        print(f"❌ Unexpected error: {e}")
        return 1
    finally:
        migrator.close_connections()

    return 0

if __name__ == "__main__":
    sys.exit(main())