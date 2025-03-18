"""
Data Import Script for Texas Auction Database

This script runs the scrapers to collect auction data and imports it into the database.
"""

import os
import sys
import logging
from datetime import datetime

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.main import run_all_scrapers
from database.database import AuctionDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("import.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("import")

def import_data():
    """
    Run scrapers and import data into the database
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info("Starting data import process")
        
        # Run all scrapers to collect data
        logger.info("Running scrapers to collect auction data")
        data_file = run_all_scrapers()
        
        # Create database and tables
        logger.info("Creating database and tables")
        db = AuctionDatabase()
        db.create_tables()
        
        # Import data into database
        logger.info(f"Importing data from {data_file}")
        imported_count = db.import_data(data_file)
        
        logger.info(f"Data import completed successfully. Imported {imported_count} auctions.")
        return True
        
    except Exception as e:
        logger.error(f"Error during data import: {e}")
        return False

if __name__ == "__main__":
    # Run the import process if this file is executed directly
    success = import_data()
    if success:
        print("Data import completed successfully")
    else:
        print("Data import failed. See import.log for details")
        sys.exit(1)
