"""
Scheduler for Texas Auction Database

This module provides functionality to schedule the scraping process
to run at regular intervals (every 3 days as specified by the user).
"""

import os
import logging
import time
from datetime import datetime, timedelta
import schedule
import sys

# Add the parent directory to the path so we can import the scrapers
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scrapers.main import run_all_scrapers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scheduler.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("scheduler")

def job():
    """
    Job to run the scrapers and log the results
    """
    logger.info("Starting scheduled scraping job")
    try:
        # Run all scrapers
        combined_file = run_all_scrapers()
        logger.info(f"Scheduled scraping job completed successfully. Data saved to: {combined_file}")
        
        # Calculate next run time
        next_run = datetime.now() + timedelta(days=3)
        logger.info(f"Next scraping job scheduled for: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        logger.error(f"Error in scheduled scraping job: {e}")

def run_scheduler():
    """
    Run the scheduler to execute the scraping job every 3 days
    """
    logger.info("Starting scheduler for Texas Auction Database")
    
    # Schedule the job to run every 3 days
    schedule.every(3).days.do(job)
    
    # Calculate next run time
    next_run = datetime.now() + timedelta(days=3)
    logger.info(f"First scraping job scheduled for: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run the job immediately for the first time
    logger.info("Running initial scraping job")
    job()
    
    # Keep the scheduler running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    # Run the scheduler if this file is executed directly
    run_scheduler()
