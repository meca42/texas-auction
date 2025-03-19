"""
Main Scraper Module for Texas Auction Database

This module orchestrates the scraping process by running all implemented scrapers
and combining their results into a single dataset.
"""

import os
import json
import logging
from datetime import datetime
import time

# Import all scrapers
from .base_scraper import BaseScraper
from .public_surplus_scraper import PublicSurplusScraper
from .gaston_sheehan_scraper import GastonSheehanScraper
from .govdeals_scraper import GovDealsScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("scraper.main")

def run_all_scrapers():
    """
    Run all implemented scrapers and combine their results
    
    Returns:
        str: Path to the combined data file
    """
    logger.info("Starting scraping process for all sources")
    
    # Initialize all scrapers
    scrapers = [
        PublicSurplusScraper(),
        GastonSheehanScraper(),
        GovDealsScraper()
    ]
    
    all_auctions = []
    
    # Run each scraper
    for scraper in scrapers:
        logger.info(f"Running scraper for {scraper.source_name}")
        try:
            # Run the scraper
            auctions = scraper.scrape()
            
            # Add source information to each auction
            for auction in auctions:
                auction["source_name"] = scraper.source_name
                auction["source_url"] = scraper.source_url
            
            # Add to combined results
            all_auctions.extend(auctions)
            
            # Save individual results
            scraper.save_data(auctions)
            
            logger.info(f"Completed scraper for {scraper.source_name}, found {len(auctions)} auctions")
            
            # Sleep between scrapers to avoid overloading
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Error running scraper for {scraper.source_name}: {e}")
    
    # Save combined results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    combined_filename = f"all_auctions_{timestamp}.json"
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    combined_filepath = os.path.join(data_dir, combined_filename)
    
    # Add metadata to the output
    output = {
        "scrape_time": datetime.now().isoformat(),
        "auction_count": len(all_auctions),
        "auctions": all_auctions
    }
    
    with open(combined_filepath, 'w') as f:
        json.dump(output, f, indent=2)
    
    logger.info(f"Saved {len(all_auctions)} auctions to {combined_filepath}")
    return combined_filepath

if __name__ == "__main__":
    # Run all scrapers if this file is executed directly
    combined_file = run_all_scrapers()
    print(f"Scraping completed. Combined data saved to: {combined_file}")
