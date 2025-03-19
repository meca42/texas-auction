import os
import logging
from database.database import AuctionDatabase

# Set headless browser mode environment variable
os.environ['HEADLESS_BROWSER_MODE'] = 'true'

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("populate_db")

# Import scrapers after setting environment variable
from scrapers.govdeals_scraper import GovDealsScraper
from scrapers.public_surplus_scraper import PublicSurplusScraper
from scrapers.gaston_sheehan_scraper import GastonSheehanScraper

logger.info("HEADLESS_BROWSER_MODE set to: " + os.environ.get('HEADLESS_BROWSER_MODE'))

# Initialize database
db = AuctionDatabase()
logger.info("Database connection established")

# Check if tables exist, create them if not
db.create_tables()
logger.info("Database tables created/verified")

# Run scrapers in headless mode
logger.info("Running scrapers in headless mode")

# Run GovDeals scraper
logger.info("Running GovDeals scraper")
govdeals_scraper = GovDealsScraper()
govdeals_auctions = govdeals_scraper.scrape()
logger.info(f"Found {len(govdeals_auctions)} GovDeals auctions")

# Run Public Surplus scraper
logger.info("Running Public Surplus scraper")
public_surplus_scraper = PublicSurplusScraper()
public_surplus_auctions = public_surplus_scraper.scrape()
logger.info(f"Found {len(public_surplus_auctions)} Public Surplus auctions")

# Run Gaston Sheehan scraper
logger.info("Running Gaston Sheehan scraper")
gaston_sheehan_scraper = GastonSheehanScraper()
gaston_sheehan_auctions = gaston_sheehan_scraper.scrape()
logger.info(f"Found {len(gaston_sheehan_auctions)} Gaston Sheehan auctions")

# Combine all auctions
all_auctions = govdeals_auctions + public_surplus_auctions + gaston_sheehan_auctions
logger.info(f"Total auctions found: {len(all_auctions)}")

# Import auctions into database
if all_auctions:
    logger.info("Importing auctions into database")
    for auction in all_auctions:
        try:
            # Add source
            source_id = db.add_source(
                name=auction.get('source_id', 'unknown'),
                url=auction.get('url', '')
            )
            
            # Add location
            location = auction.get('location', {})
            location_id = db.add_location(
                city=location.get('city'),
                state=location.get('state', 'TX'),
                zip_code=location.get('zip_code')
            )
            
            # Add auction
            auction_id = db.add_auction(
                title=auction.get('title', ''),
                description=auction.get('description', ''),
                current_price=auction.get('current_price'),
                end_date=auction.get('end_date'),
                url=auction.get('url', ''),
                external_id=auction.get('external_id', ''),
                source_id=source_id,
                location_id=location_id,
                category=auction.get('category', 'other')
            )
            
            # Add images
            for image_url in auction.get('images', []):
                if image_url:
                    db.add_image(auction_id, image_url)
                    
            logger.info(f"Imported auction: {auction.get('title')}")
        except Exception as e:
            logger.error(f"Error importing auction {auction.get('title')}: {e}")
    
    logger.info(f"Successfully imported {len(all_auctions)} auctions")
else:
    logger.warning("No auctions found to import")

# Check final count
try:
    cursor = db.conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM auctions")
    count = cursor.fetchone()[0]
    logger.info(f"Final auction count in database: {count}")
except Exception as e:
    logger.error(f"Error checking final auction count: {e}")

logger.info("Database population completed")
