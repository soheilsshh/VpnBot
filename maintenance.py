import os
import shutil
from datetime import datetime, timedelta
import logging
from config import *
from advanced_config import CLEANUP_SETTINGS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_old_files():
    """Clean up old files"""
    # Clean old backups
    backup_dir = "backups"
    for file in os.listdir(backup_dir):
        file_path = os.path.join(backup_dir, file)
        if os.path.getctime(file_path) < (datetime.now() - timedelta(days=CLEANUP_SETTINGS["old_backups_days"])).timestamp():
            os.remove(file_path)
            logger.info(f"Removed old backup: {file}")
            
    # Clean old logs
    log_dir = "logs"
    for file in os.listdir(log_dir):
        file_path = os.path.join(log_dir, file)
        if os.path.getctime(file_path) < (datetime.now() - timedelta(days=CLEANUP_SETTINGS["old_logs_days"])).timestamp():
            os.remove(file_path)
            logger.info(f"Removed old log: {file}")
            
    # Clean temp files
    temp_dir = "temp"
    shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)
    logger.info("Cleaned temp directory")

def check_disk_space():
    """Check available disk space"""
    disk_usage = shutil.disk_usage("/")
    percent_used = disk_usage.used / disk_usage.total * 100
    
    if percent_used > 90:
        logger.warning(f"High disk usage: {percent_used:.1f}%")
        # Could send notification to admin here

def main():
    """Run maintenance tasks"""
    try:
        logger.info("Starting maintenance tasks...")
        cleanup_old_files()
        check_disk_space()
        logger.info("Maintenance tasks completed successfully!")
    except Exception as e:
        logger.error(f"Error during maintenance: {e}")

if __name__ == "__main__":
    main() 