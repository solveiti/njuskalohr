"""
Celery tasks for running the Njuskalo scraper
"""
import os
import sys
import traceback
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from celery import Task
from celery_config import celery_app

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from njuskalo_sitemap_scraper import NjuskaloSitemapScraper
from database import NjuskaloDatabase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CallbackTask(Task):
    """Custom task class with callbacks"""

    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds"""
        logger.info(f"Task {task_id} succeeded with result: {retval}")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails"""
        logger.error(f"Task {task_id} failed with exception: {exc}")
        logger.error(f"Traceback: {einfo}")


@celery_app.task(base=CallbackTask, bind=True)
def run_full_scrape_task(self, max_stores: Optional[int] = None, use_database: bool = True) -> Dict[str, Any]:
    """
    Celery task to run the full scraping workflow

    Args:
        max_stores: Maximum number of stores to scrape (None for all)
        use_database: Whether to save results to database

    Returns:
        Dict with task results and statistics
    """
    task_id = self.request.id
    start_time = datetime.now()

    logger.info(f"Starting scraping task {task_id} with max_stores={max_stores}, use_database={use_database}")

    try:
        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={"status": "Initializing scraper", "progress": 0, "start_time": start_time.isoformat()}
        )

        # Create scraper instance
        scraper = NjuskaloSitemapScraper(headless=True, use_database=use_database)

        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={"status": "Running scraper", "progress": 10, "start_time": start_time.isoformat()}
        )

        # Run the scraping
        stores_data = scraper.run_full_scrape(max_stores=max_stores)

        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={"status": "Processing results", "progress": 90, "start_time": start_time.isoformat()}
        )

        # Generate statistics
        total_stores = len(stores_data)
        auto_moto_stores = len([s for s in stores_data if s.get('has_auto_moto')])
        stores_with_ads = len([s for s in stores_data if s.get('ads_count') is not None])
        stores_with_address = len([s for s in stores_data if s.get('address')])

        # Save to Excel in datadump directory
        import os
        datadump_dir = "datadump"
        os.makedirs(datadump_dir, exist_ok=True)

        timestamp = int(start_time.timestamp())
        excel_filename = f"njuskalo_stores_{timestamp}.xlsx"
        excel_saved = scraper.save_to_excel(excel_filename)

        # Get database stats if using database
        db_stats = None
        if use_database:
            try:
                with NjuskaloDatabase() as db:
                    db_stats = db.get_database_stats()
            except Exception as e:
                logger.warning(f"Failed to get database stats: {e}")

        # Calculate execution time
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        # Prepare result
        result = {
            "task_id": task_id,
            "status": "SUCCESS",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "execution_time_seconds": execution_time,
            "max_stores_requested": max_stores,
            "use_database": use_database,
            "total_stores_scraped": total_stores,
            "auto_moto_stores": auto_moto_stores,
            "stores_with_ads": stores_with_ads,
            "stores_with_address": stores_with_address,
            "excel_file": excel_filename if excel_saved else None,
            "database_stats": db_stats,
            "errors": []
        }

        logger.info(f"Task {task_id} completed successfully: {total_stores} stores scraped in {execution_time:.2f}s")

        # Clean up browser
        if scraper.driver:
            try:
                scraper.driver.quit()
            except Exception:
                pass

        return result

    except Exception as e:
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        error_msg = str(e)
        error_traceback = traceback.format_exc()

        logger.error(f"Task {task_id} failed after {execution_time:.2f}s: {error_msg}")
        logger.error(f"Traceback: {error_traceback}")

        # Clean up browser in case of error
        try:
            if 'scraper' in locals() and scraper.driver:
                scraper.driver.quit()
        except Exception:
            pass

        # Return error result
        result = {
            "task_id": task_id,
            "status": "FAILED",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "execution_time_seconds": execution_time,
            "max_stores_requested": max_stores,
            "use_database": use_database,
            "error": error_msg,
            "traceback": error_traceback
        }

        # Re-raise the exception so Celery marks the task as failed
        raise Exception(f"Scraping task failed: {error_msg}")


@celery_app.task(base=CallbackTask)
def test_scraper_task() -> Dict[str, Any]:
    """
    Simple test task to verify scraper is working

    Returns:
        Dict with test results
    """
    start_time = datetime.now()

    try:
        logger.info("Running scraper test task")

        # Test database connection
        db_connection_ok = False
        db_stats = None
        try:
            with NjuskaloDatabase() as db:
                db_stats = db.get_database_stats()
                db_connection_ok = True
        except Exception as e:
            logger.warning(f"Database connection test failed: {e}")

        # Test scraper initialization
        scraper_init_ok = False
        try:
            scraper = NjuskaloSitemapScraper(headless=True, use_database=False)
            if scraper.setup_browser():
                scraper_init_ok = True
                scraper.driver.quit()
        except Exception as e:
            logger.warning(f"Scraper initialization test failed: {e}")

        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        result = {
            "status": "SUCCESS",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "execution_time_seconds": execution_time,
            "database_connection": db_connection_ok,
            "database_stats": db_stats,
            "scraper_initialization": scraper_init_ok,
            "message": "Test completed successfully"
        }

        logger.info(f"Test task completed successfully in {execution_time:.2f}s")
        return result

    except Exception as e:
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        error_msg = str(e)
        logger.error(f"Test task failed after {execution_time:.2f}s: {error_msg}")

        result = {
            "status": "FAILED",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "execution_time_seconds": execution_time,
            "error": error_msg,
            "message": "Test failed"
        }

        raise Exception(f"Test task failed: {error_msg}")


@celery_app.task(base=CallbackTask)
def get_database_stats_task() -> Dict[str, Any]:
    """
    Get database statistics as a Celery task

    Returns:
        Database statistics
    """
    try:
        with NjuskaloDatabase() as db:
            stats = db.get_database_stats()
            valid_stores = db.get_all_valid_stores()

            # Calculate additional statistics
            auto_moto_count = 0
            total_ads = 0
            stores_with_address = 0

            for store in valid_stores:
                results = store.get('results', {})
                if results.get('has_auto_moto'):
                    auto_moto_count += 1
                if results.get('ads_count'):
                    total_ads += results['ads_count']
                if results.get('address'):
                    stores_with_address += 1

            enhanced_stats = {
                **stats,
                "auto_moto_stores": auto_moto_count,
                "total_ads": total_ads,
                "stores_with_address": stores_with_address,
                "timestamp": datetime.now().isoformat()
            }

            return enhanced_stats

    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        raise Exception(f"Database stats task failed: {str(e)}")


@celery_app.task(base=CallbackTask)
def cleanup_old_excel_files_task(days_old: int = 7) -> Dict[str, Any]:
    """
    Clean up old Excel files

    Args:
        days_old: Delete files older than this many days

    Returns:
        Cleanup results
    """
    import glob
    from pathlib import Path

    try:
        # Look for files in datadump directory
        datadump_dir = "datadump"
        pattern = os.path.join(datadump_dir, "njuskalo_stores_*.xlsx")
        files = glob.glob(pattern)

        deleted_files = []
        current_time = datetime.now()
        cutoff_time = current_time.timestamp() - (days_old * 24 * 60 * 60)

        for file_path in files:
            file_stat = Path(file_path).stat()
            if file_stat.st_mtime < cutoff_time:
                try:
                    os.remove(file_path)
                    deleted_files.append(file_path)
                    logger.info(f"Deleted old Excel file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete {file_path}: {e}")

        result = {
            "status": "SUCCESS",
            "deleted_files": deleted_files,
            "total_deleted": len(deleted_files),
            "days_old_threshold": days_old,
            "timestamp": current_time.isoformat()
        }

        logger.info(f"Cleanup task completed: deleted {len(deleted_files)} old files")
        return result

    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")
        raise Exception(f"Cleanup task failed: {str(e)}")