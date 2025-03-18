"""
Test script for verifying full application functionality

This script tests the full functionality of the Texas Auction application
with the new PostgreSQL database configuration.
"""

import os
import sys
import logging
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import AuctionDatabase
from import_data import import_data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app_test.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("app_test")

def test_database_setup():
    """
    Test database setup and data import
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info("Testing database setup")
        
        # Create database instance
        db = AuctionDatabase()
        
        # Create tables
        if not db.create_tables():
            logger.error("Failed to create database tables")
            return False
        
        # Import data
        success = import_data()
        if not success:
            logger.error("Failed to import data")
            return False
        
        logger.info("Database setup test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error testing database setup: {e}")
        return False

def test_web_application(base_url="http://localhost:5000"):
    """
    Test web application functionality
    
    Args:
        base_url (str): Base URL of the web application
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Testing web application at {base_url}")
        
        # Test home page
        response = requests.get(f"{base_url}/")
        if response.status_code != 200:
            logger.error(f"Failed to access home page: {response.status_code}")
            return False
        logger.info("Home page test passed")
        
        # Test auctions page
        response = requests.get(f"{base_url}/auctions")
        if response.status_code != 200:
            logger.error(f"Failed to access auctions page: {response.status_code}")
            return False
        logger.info("Auctions page test passed")
        
        # Test API endpoint
        response = requests.get(f"{base_url}/api/auctions")
        if response.status_code != 200:
            logger.error(f"Failed to access API endpoint: {response.status_code}")
            return False
        
        # Verify API response contains auctions data
        data = response.json()
        if 'auctions' not in data:
            logger.error("API response does not contain auctions data")
            return False
        
        logger.info("Web application test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error testing web application: {e}")
        return False

if __name__ == "__main__":
    # Run the tests
    db_success = test_database_setup()
    if not db_success:
        print("Database setup test failed. See app_test.log for details")
        sys.exit(1)
    
    # Get base URL from environment or use default
    base_url = os.getenv('APP_URL', 'http://localhost:5000')
    
    app_success = test_web_application(base_url)
    if not app_success:
        print("Web application test failed. See app_test.log for details")
        sys.exit(1)
    
    print("All tests completed successfully")
    sys.exit(0)
