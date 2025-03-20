"""
Script to run the OpenAI-powered auction scraper
"""
import logging
from scrapers.openai_scraper_complete import OpenAIAuctionScraper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("run_openai_scraper")

def main():
    """
    Main function to run the OpenAI-powered scraper
    """
    logger.info("Starting OpenAI-powered auction scraper")
    
    try:
        # Initialize and run scraper
        scraper = OpenAIAuctionScraper()
        auctions = scraper.scrape_all_sources()
        
        # Save to database
        if auctions:
            count = scraper.save_auctions_to_database(auctions)
            logger.info(f"Saved {count} auctions to database")
        else:
            logger.warning("No auctions found to save")
            
        logger.info("OpenAI-powered auction scraper completed successfully")
        
    except Exception as e:
        logger.error(f"Error running OpenAI-powered scraper: {e}")

if __name__ == "__main__":
    main()
