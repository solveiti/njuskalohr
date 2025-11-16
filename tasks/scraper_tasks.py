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

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import enhanced scrapers
try:
    from enhanced_njuskalo_scraper import EnhancedNjuskaloScraper
    logger.info("✅ EnhancedNjuskaloScraper loaded successfully")
except ImportError:
    logger.warning("⚠️ EnhancedNjuskaloScraper not available - enhanced tasks will be disabled")
    EnhancedNjuskaloScraper = None

# Import tunnel-enabled scraper
try:
    from enhanced_tunnel_scraper import TunnelEnabledEnhancedScraper
    logger.info("✅ TunnelEnabledEnhancedScraper loaded successfully")
except ImportError:
    logger.warning("⚠️ TunnelEnabledEnhancedScraper not available - tunnel tasks will be disabled")
    TunnelEnabledEnhancedScraper = None

# Import API data sender
try:
    from njuskalo_api_data_sender import DoberApiClient, DealershipProcessor
except ImportError:
    logger.warning("API data sender not available - API tasks will be disabled")
    DoberApiClient = None
    DealershipProcessor = None


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

        # Create enhanced scraper instance (fallback to base if not available)
        if EnhancedNjuskaloScraper:
            scraper = EnhancedNjuskaloScraper(headless=True, use_database=use_database)
            logger.info("Using EnhancedNjuskaloScraper with XML processing and vehicle counting")
        else:
            scraper = NjuskaloSitemapScraper(headless=True, use_database=use_database)
            logger.warning("Using base NjuskaloSitemapScraper (enhanced features not available)")

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


@celery_app.task(base=CallbackTask, bind=True)
def run_enhanced_scrape_task(self, max_stores: Optional[int] = None, use_database: bool = True) -> Dict[str, Any]:
    """
    Celery task to run enhanced scraping with XML processing and vehicle counting
    (without SSH tunnels for faster local execution)

    Args:
        max_stores: Maximum number of stores to scrape (None for all)
        use_database: Whether to save results to database

    Returns:
        Dict with task results and statistics
    """
    if not EnhancedNjuskaloScraper:
        error_msg = "EnhancedNjuskaloScraper not available - falling back to basic scraper"
        logger.warning(error_msg)
        # Fallback to basic scraper
        return run_full_scrape_task(self, max_stores=max_stores, use_database=use_database)

    task_id = self.request.id
    start_time = datetime.now()

    logger.info(f"Starting enhanced scrape task {task_id} with max_stores={max_stores}, use_database={use_database}")

    try:
        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={"status": "Initializing enhanced scraper with XML processing", "progress": 0, "start_time": start_time.isoformat()}
        )

        # Create enhanced scraper instance
        scraper = EnhancedNjuskaloScraper(headless=True, use_database=use_database)
        logger.info("✅ EnhancedNjuskaloScraper initialized with XML processing and vehicle counting")

        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={"status": "Processing XML sitemap", "progress": 10, "start_time": start_time.isoformat()}
        )

        # Run enhanced scraping
        stores_data = scraper.run_full_scrape(max_stores=max_stores)

        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={"status": "Processing results", "progress": 90, "start_time": start_time.isoformat()}
        )

        # Generate statistics
        total_stores = len(stores_data)
        auto_moto_stores = len([s for s in stores_data if s.get('has_auto_moto')])
        stores_with_new_vehicles = len([s for s in stores_data if s.get('new_ads_count', 0) > 0])
        stores_with_used_vehicles = len([s for s in stores_data if s.get('used_ads_count', 0) > 0])
        total_new_vehicles = sum(s.get('new_ads_count', 0) for s in stores_data)
        total_used_vehicles = sum(s.get('used_ads_count', 0) for s in stores_data)
        stores_with_address = len([s for s in stores_data if s.get('address')])

        # Save to Excel in datadump directory
        import os
        datadump_dir = "datadump"
        os.makedirs(datadump_dir, exist_ok=True)

        timestamp = int(start_time.timestamp())
        excel_filename = f"njuskalo_enhanced_scrape_{timestamp}.xlsx"
        excel_saved = scraper.save_to_excel(excel_filename)

        # Get database stats
        db_stats = None
        if use_database:
            try:
                with NjuskaloDatabase() as db:
                    db_stats = db.get_database_stats()
            except Exception as e:
                logger.warning(f"Failed to get database stats: {e}")

        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        result = {
            "task_id": task_id,
            "status": "SUCCESS",
            "message": "Enhanced scraping with XML processing completed successfully",
            "total_stores_scraped": total_stores,
            "auto_moto_stores": auto_moto_stores,
            "stores_with_new_vehicles": stores_with_new_vehicles,
            "stores_with_used_vehicles": stores_with_used_vehicles,
            "total_new_vehicles": total_new_vehicles,
            "total_used_vehicles": total_used_vehicles,
            "stores_with_address": stores_with_address,
            "xml_processing_enabled": True,
            "vehicle_counting_enabled": True,
            "execution_time_seconds": execution_time,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "excel_file": excel_filename if excel_saved else None,
            "database_stats": db_stats,
            "errors": []
        }

        logger.info(f"Enhanced scrape task {task_id} completed: {total_stores} stores, {total_new_vehicles} new + {total_used_vehicles} used vehicles in {execution_time:.2f}s")

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

        logger.error(f"Enhanced scrape task {task_id} failed after {execution_time:.2f}s: {error_msg}")
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
        raise Exception(f"Enhanced scrape task failed: {error_msg}")


@celery_app.task(base=CallbackTask, bind=True)
def run_auto_moto_only_scrape_task(self, max_stores: Optional[int] = None) -> Dict[str, Any]:
    """
    Run optimized scraping that only processes known auto moto stores.
    This is the most efficient method for getting car-related data.

    Args:
        max_stores: Maximum number of stores to scrape (optional)

    Returns:
        Dict with scraping results and statistics
    """
    start_time = datetime.now()
    task_id = self.request.id

    logger.info(f"Starting auto moto only scrape task {task_id} with max_stores={max_stores}")

    try:
        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={"status": "Initializing auto moto scraper", "progress": 5, "start_time": start_time.isoformat()}
        )

        # Create enhanced scraper instance (fallback to base if not available)
        if EnhancedNjuskaloScraper:
            scraper = EnhancedNjuskaloScraper(headless=True, use_database=True)
            logger.info("Using EnhancedNjuskaloScraper with XML processing and vehicle counting")
        else:
            scraper = NjuskaloSitemapScraper(headless=True, use_database=True)
            logger.warning("Using base NjuskaloSitemapScraper (enhanced features not available)")

        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={"status": "Running auto moto only scrape", "progress": 20, "start_time": start_time.isoformat()}
        )

        # Run the auto moto only scraping
        stores_data = scraper.run_auto_moto_only_scrape(max_stores=max_stores)

        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={"status": "Processing results", "progress": 90, "start_time": start_time.isoformat()}
        )

        # Generate statistics
        total_stores = len(stores_data)
        auto_moto_stores = total_stores  # All should be auto moto
        stores_with_new_vehicles = len([s for s in stores_data if s.get('new_ads_count', 0) > 0])
        stores_with_used_vehicles = len([s for s in stores_data if s.get('used_ads_count', 0) > 0])
        total_new_vehicles = sum(s.get('new_ads_count', 0) for s in stores_data)
        total_used_vehicles = sum(s.get('used_ads_count', 0) for s in stores_data)

        # Save to Excel in datadump directory
        import os
        datadump_dir = "datadump"
        os.makedirs(datadump_dir, exist_ok=True)

        timestamp = int(start_time.timestamp())
        excel_filename = f"njuskalo_auto_moto_stores_{timestamp}.xlsx"
        excel_saved = scraper.save_to_excel(excel_filename)

        # Get database stats
        db_stats = None
        try:
            with NjuskaloDatabase() as db:
                db_stats = db.get_database_stats()
                auto_moto_db_count = len(db.get_auto_moto_stores())
                non_auto_moto_db_count = len(db.get_non_auto_moto_stores())
                db_stats['auto_moto_stores'] = auto_moto_db_count
                db_stats['non_auto_moto_stores'] = non_auto_moto_db_count
        except Exception as e:
            logger.warning(f"Failed to get database stats: {e}")

        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        result = {
            "task_id": task_id,
            "status": "SUCCESS",
            "message": "Auto moto only scraping completed successfully",
            "total_stores_scraped": total_stores,
            "auto_moto_stores": auto_moto_stores,
            "stores_with_new_vehicles": stores_with_new_vehicles,
            "stores_with_used_vehicles": stores_with_used_vehicles,
            "total_new_vehicles": total_new_vehicles,
            "total_used_vehicles": total_used_vehicles,
            "execution_time_seconds": execution_time,
            "excel_file": excel_filename if excel_saved else None,
            "database_stats": db_stats,
            "errors": []
        }

        logger.info(f"Auto moto task {task_id} completed successfully: {total_stores} stores scraped in {execution_time:.2f}s")

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

        logger.error(f"Auto moto task {task_id} failed after {execution_time:.2f}s: {error_msg}")
        logger.error(f"Traceback: {error_traceback}")

        # Clean up browser in case of error
        try:
            if 'scraper' in locals() and scraper.driver:
                scraper.driver.quit()
        except Exception:
            pass

        # Return error details
        result = {
            "task_id": task_id,
            "status": "FAILED",
            "message": error_msg,
            "execution_time_seconds": execution_time,
            "errors": [error_msg]
        }

        # Re-raise the exception so Celery marks the task as failed
        raise Exception(f"Auto moto scraping task failed: {error_msg}")


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


@celery_app.task(base=CallbackTask, bind=True)
def run_enhanced_tunnel_scrape_task(self, max_stores: Optional[int] = None, use_database: bool = True) -> Dict[str, Any]:
    """
    Celery task to run the enhanced tunnel-enabled scraping workflow

    Args:
        max_stores: Maximum number of stores to scrape (None for all)
        use_database: Whether to save results to database

    Returns:
        Dict with task results and statistics
    """
    if not TunnelEnabledEnhancedScraper:
        error_msg = "TunnelEnabledEnhancedScraper not available"
        logger.error(error_msg)
        raise Exception(error_msg)

    task_id = self.request.id
    start_time = datetime.now()

    logger.info(f"Starting enhanced tunnel scraping task {task_id} with max_stores={max_stores}, use_database={use_database}")

    try:
        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={"status": "Initializing tunnel-enabled scraper", "progress": 0, "start_time": start_time.isoformat()}
        )

        # Create tunnel-enabled scraper instance
        scraper = TunnelEnabledEnhancedScraper(
            headless=True,
            use_database=use_database,
            tunnel_config_path="tunnel_config.json",
            use_tunnels=True
        )

        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={"status": "Setting up SSH tunnels", "progress": 10, "start_time": start_time.isoformat()}
        )

        logger.info(f"Running enhanced tunnel scraping with max_stores={max_stores}")

        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={"status": "Running scraping process", "progress": 20, "start_time": start_time.isoformat()}
        )

        # Run the enhanced scraping with tunnels
        results = scraper.run_enhanced_scrape_with_tunnels(max_stores=max_stores)

        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={"status": "Saving results", "progress": 90, "start_time": start_time.isoformat()}
        )

        # Save to Excel file
        import os
        datadump_dir = "datadump"
        os.makedirs(datadump_dir, exist_ok=True)

        timestamp = int(start_time.timestamp())
        excel_filename = f"njuskalo_tunnel_scrape_{timestamp}.xlsx"
        excel_saved = scraper.save_to_excel(excel_filename) if hasattr(scraper, 'save_to_excel') else None

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
            "total_stores_scraped": results.get("stores_scraped", 0),
            "auto_moto_stores": results.get("auto_moto_stores", 0),
            "new_urls_found": results.get("new_urls_found", 0),
            "xml_available": results.get("xml_available", False),
            "tunnel_used": results.get("tunnel_used", True),
            "execution_time_seconds": execution_time,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "excel_file": excel_filename if excel_saved else None,
            "database_stats": db_stats,
            "message": f"Enhanced tunnel scraping completed successfully! Processed {results.get('stores_scraped', 0)} stores."
        }

        logger.info(f"Enhanced tunnel scraping task {task_id} completed successfully")
        logger.info(f"Stores scraped: {results.get('stores_scraped', 0)}")
        logger.info(f"Auto moto stores: {results.get('auto_moto_stores', 0)}")
        logger.info(f"Execution time: {execution_time:.2f} seconds")

        return result

    except Exception as e:
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        error_msg = str(e)
        error_traceback = traceback.format_exc()

        logger.error(f"Enhanced tunnel scraping task {task_id} failed after {execution_time:.2f}s: {error_msg}")
        logger.error(f"Error traceback:\n{error_traceback}")

        # Return error result
        result = {
            "task_id": task_id,
            "status": "FAILED",
            "execution_time_seconds": execution_time,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "max_stores": max_stores,
            "use_database": use_database,
            "error": error_msg,
            "traceback": error_traceback
        }

        # Re-raise the exception so Celery marks the task as failed
        raise Exception(f"Enhanced tunnel scraping task failed: {error_msg}")


@celery_app.task(base=CallbackTask, bind=True)
def send_dealership_data_to_api_task(self, scraping_date: Optional[str] = None, min_vehicles: int = 5) -> Dict[str, Any]:
    """
    Celery task to send dealership data to Dober Avto API

    Args:
        scraping_date: Date of scraping in YYYY-MM-DD format (None for today)
        min_vehicles: Minimum number of vehicles required to include dealership

    Returns:
        Dict with task results and statistics
    """
    if not DoberApiClient or not DealershipProcessor:
        error_msg = "API data sender not available"
        logger.error(error_msg)
        raise Exception(error_msg)

    task_id = self.request.id
    start_time = datetime.now()

    # Use today's date if not specified
    if not scraping_date:
        scraping_date = start_time.strftime('%Y-%m-%d')

    logger.info(f"Starting API data sender task {task_id} for date {scraping_date} with min_vehicles={min_vehicles}")

    try:
        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={"status": "Initializing API client", "progress": 0, "start_time": start_time.isoformat()}
        )

        # Initialize API client
        api_client = DoberApiClient()
        processor = DealershipProcessor(api_client)

        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={"status": "Loading dealership data from database", "progress": 20, "start_time": start_time.isoformat()}
        )

        # Get dealerships from database
        dealerships = processor.get_dealerships_from_database(scraping_date, min_vehicles)

        if not dealerships:
            logger.warning(f"No dealerships found for date {scraping_date} with min_vehicles >= {min_vehicles}")
            result = {
                "task_id": task_id,
                "status": "SUCCESS",
                "scraping_date": scraping_date,
                "min_vehicles": min_vehicles,
                "dealerships_processed": 0,
                "dealerships_sent": 0,
                "execution_time_seconds": (datetime.now() - start_time).total_seconds(),
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "message": "No dealerships found matching criteria"
            }
            return result

        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={
                "status": f"Processing {len(dealerships)} dealerships",
                "progress": 40,
                "start_time": start_time.isoformat(),
                "dealerships_found": len(dealerships)
            }
        )

        logger.info(f"Found {len(dealerships)} dealerships to process")

        # Process and send dealerships
        self.update_state(
            state="PROGRESS",
            meta={"status": "Sending data to Dober Avto API", "progress": 60, "start_time": start_time.isoformat()}
        )

        # Run the main processing
        processor.process_dealerships(scraping_date, min_vehicles)

        # Calculate execution time
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        # Prepare success result
        result = {
            "task_id": task_id,
            "status": "SUCCESS",
            "scraping_date": scraping_date,
            "min_vehicles": min_vehicles,
            "dealerships_found": len(dealerships),
            "execution_time_seconds": execution_time,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "message": f"Successfully processed dealership data for {scraping_date}"
        }

        logger.info(f"API data sender task {task_id} completed successfully")
        logger.info(f"Found: {len(dealerships)} dealerships, Execution time: {execution_time:.2f} seconds")

        return result

    except Exception as e:
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        error_msg = str(e)
        error_traceback = traceback.format_exc()

        logger.error(f"API data sender task {task_id} failed after {execution_time:.2f}s: {error_msg}")
        logger.error(f"Error traceback:\n{error_traceback}")

        # Return error result
        result = {
            "task_id": task_id,
            "status": "FAILED",
            "execution_time_seconds": execution_time,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "scraping_date": scraping_date,
            "min_vehicles": min_vehicles,
            "error": error_msg,
            "traceback": error_traceback
        }

        # Re-raise the exception so Celery marks the task as failed
        raise Exception(f"API data sender task failed: {error_msg}")