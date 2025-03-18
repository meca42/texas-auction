"""
Test script for verifying PostgreSQL database connectivity

This script tests the connection to the PostgreSQL database and verifies
that the database configuration is working correctly.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import AuctionDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("db_test.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("db_test")

def test_database_connection():
    """
    Test the database connection
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info("Testing database connection")
        
        # Get database URL from environment variable
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            logger.warning("DATABASE_URL environment variable not set, using default SQLite")
            db_url = None
        
        # Create database instance
        db = AuctionDatabase(db_url)
        
        # Log database type
        logger.info(f"Database type: {db.db_type}")
        logger.info(f"Database URL: {db.db_url}")
        
        # Test connection
        conn = db.connect()
        if conn:
            logger.info("Successfully connected to database")
            
            # Test creating tables
            if db.create_tables():
                logger.info("Successfully created database tables")
            else:
                logger.error("Failed to create database tables")
                return False
            
            # Close connection
            db.close()
            logger.info("Database connection test completed successfully")
            return True
        else:
            logger.error("Failed to connect to database")
            return False
            
    except Exception as e:
        logger.error(f"Error testing database connection: {e}")
        return False

if __name__ == "__main__":
    # Run the test
    success = test_database_connection()
    if success:
        print("Database connection test completed successfully")
        sys.exit(0)
    else:
        print("Database connection test failed. See db_test.log for details")
        sys.exit(1)
