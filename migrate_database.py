#!/usr/bin/env python3
"""
Database migration script to add is_automoto column and clean up results data.
"""

import sys
import logging
from database import NjuskaloDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def migrate_database():
    """Run database migration to add is_automoto column"""
    try:
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()

        logger.info("Starting database migration...")

        # Initialize database connection
        db = NjuskaloDatabase()
        db.connect()  # Explicitly connect to the database

        # Add the new column
        db.migrate_add_is_automoto_column()

        # Clean up existing data - remove has_auto_moto and categories from results
        logger.info("Cleaning up existing results data...")

        with db.connection.cursor() as cursor:
            # Get all records that need cleanup
            cursor.execute("""
                SELECT id, url, results
                FROM scraped_stores
                WHERE results IS NOT NULL
                AND (
                    JSON_EXTRACT(results, '$.has_auto_moto') IS NOT NULL
                    OR JSON_EXTRACT(results, '$.categories') IS NOT NULL
                )
            """)

            records_to_update = cursor.fetchall()
            logger.info(f"Found {len(records_to_update)} records to clean up")

            for record in records_to_update:
                record_id, url, results_json = record

                try:
                    import json
                    results = json.loads(results_json)

                    # Remove has_auto_moto and categories
                    results.pop('has_auto_moto', None)
                    results.pop('categories', None)

                    # Update the record
                    cursor.execute("""
                        UPDATE scraped_stores
                        SET results = %s
                        WHERE id = %s
                    """, (json.dumps(results), record_id))

                except Exception as e:
                    logger.warning(f"Failed to clean up record {record_id}: {e}")
                    continue

            db.connection.commit()
            logger.info(f"Successfully cleaned up {len(records_to_update)} records")

        # Verify migration
        with db.connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM scraped_stores WHERE is_automoto = TRUE")
            auto_moto_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM scraped_stores")
            total_count = cursor.fetchone()[0]

            logger.info(f"Migration completed successfully!")
            logger.info(f"Total stores: {total_count}")
            logger.info(f"Auto moto stores: {auto_moto_count}")
            logger.info(f"Non-auto moto stores: {total_count - auto_moto_count}")

        db.disconnect()
        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


if __name__ == "__main__":
    success = migrate_database()
    if success:
        print("✅ Database migration completed successfully!")
        sys.exit(0)
    else:
        print("❌ Database migration failed!")
        sys.exit(1)