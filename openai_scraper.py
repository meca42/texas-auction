"""
OpenAI-powered Auction Scraper for Texas Auction Database

This module uses OpenAI's API to extract auction data from websites without
requiring browser automation, making it ideal for deployment on Render.
"""
import os
import json
import logging
import requests
from datetime import datetime
import time
from typing import List, Dict, Any, Optional
import re
from openai import OpenAI
from database.database import AuctionDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("openai_scraper.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("openai_scraper")

class OpenAIAuctionScraper:
    """
    Scraper that uses OpenAI's API to extract auction data from websites
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the OpenAI-powered scraper
        
        Args:
            api_key: OpenAI API key (optional, will use environment variable if not provided)
        """
        # Use provided API key or get from environment
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or provide it directly.")
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.api_key)
        
        # Initialize database
        self.db = AuctionDatabase()
        
        # Source configurations
        self.sources = [
            {
                "name": "GovDeals - Texas",
                "source_id": "govdeals",
                "url": "https://www.govdeals.com/index.cfm?fa=Main.AdvSearchResultsNew&searchPg=Classic&inv_num=&category=00&kWord=&kWordSelect=2&sortBy=ad&agency=4703&state=&country=&locID=&timing=bySimple&locationType=state&timeType=&timingWithin=1&rowCount=10&Surplus=0&Seized=0&Reutilization=0&term=TX&fromPrice=0&toPrice=0",
                "type": "govdeals"
            },
            {
                "name": "Public Surplus - Texas Facilities Commission",
                "source_id": "public_surplus",
                "url": "https://www.publicsurplus.com/sms/browse/cataucs?catid=4&orgid=13539",
                "type": "public_surplus"
            },
            {
                "name": "Gaston and Sheehan Auctioneers",
                "source_id": "gaston_sheehan",
                "url": "https://www.txauction.com/",
                "type": "gaston_sheehan"
            }
        ]
    
    def scrape_all_sources(self) -> List[Dict[str, Any]]:
        """
        Scrape all configured auction sources
        
        Returns:
            List of auction items as dictionaries
        """
        all_auctions = []
        
        for source in self.sources:
            logger.info(f"Scraping {source['name']} from {source['url']}")
            try:
                auctions = self.scrape_source(source)
                logger.info(f"Found {len(auctions)} auctions from {source['name']}")
                all_auctions.extend(auctions)
            except Exception as e:
                logger.error(f"Error scraping {source['name']}: {e}")
        
        return all_auctions
    
    def scrape_source(self, source: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Scrape a specific auction source
        
        Args:
            source: Source configuration dictionary
            
        Returns:
            List of auction items as dictionaries
        """
        # Fetch the HTML content
        html_content = self._fetch_html(source["url"])
        if not html_content:
            logger.error(f"Failed to fetch HTML from {source['url']}")
            return []
        
        # Extract auction data using OpenAI
        auctions = self._extract_auctions_with_openai(html_content, source)
        
        # Add source information to each auction
        for auction in auctions:
            auction["source_id"] = source["source_id"]
            
            # Generate a unique ID if not present
            if "auction_id" not in auction:
                auction["auction_id"] = f"{source['source_id']}_{self._generate_id(auction.get('title', ''))}"
            
            # Set external_id if not present
            if "external_id" not in auction:
                auction["external_id"] = auction["auction_id"]
        
        return auctions
    
    def _fetch_html(self, url: str) -> Optional[str]:
        """
        Fetch HTML content from a URL
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content as string or None if failed
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def _extract_auctions_with_openai(self, html_content: str, source: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Extract auction data from HTML using OpenAI's API
        
        Args:
            html_content: HTML content as string
            source: Source configuration dictionary
            
        Returns:
            List of auction items as dictionaries
        """
        # Truncate HTML if too long (OpenAI has token limits)
        max_length = 100000  # Adjust based on your OpenAI model's context window
        if len(html_content) > max_length:
            logger.warning(f"HTML content too long ({len(html_content)} chars), truncating to {max_length}")
            html_content = html_content[:max_length]
        
        try:
            # Create system prompt based on source type
            system_prompt = self._get_system_prompt(source["type"])
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4-turbo",  # Use appropriate model
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Extract auction data from this HTML:\n\n{html_content}"}
                ],
                temperature=0.2,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            content = response.choices[0].message.content
            result = json.loads(content)
            
            # Extract auctions from the result
            auctions = result.get("auctions", [])
            
            # Process dates and other fields
            for auction in auctions:
                # Convert date strings to ISO format
                if "start_date" in auction and auction["start_date"]:
                    auction["start_date"] = self._parse_date(auction["start_date"])
                
                if "end_date" in auction and auction["end_date"]:
                    auction["end_date"] = self._parse_date(auction["end_date"])
                
                # Ensure location is a dictionary
                if "location" in auction and isinstance(auction["location"], str):
                    location_str = auction["location"]
                    location = self._parse_location(location_str)
                    auction["location"] = location
                elif "location" not in auction:
                    auction["location"] = {"city": None, "state": "TX", "zip_code": None}
                
                # Ensure images is a list
                if "images" not in auction:
                    auction["images"] = []
                
                # Determine category if not present
                if "category" not in auction:
                    auction["category"] = self._determine_category(
                        auction.get("title", ""), 
                        auction.get("description", "")
                    )
            
            return auctions
            
        except Exception as e:
            logger.error(f"Error extracting auctions with OpenAI: {e}")
            return []
    
    def _get_system_prompt(self, source_type: str) -> str:
        """
        Get the appropriate system prompt for the source type
        
        Args:
            source_type: Type of auction source
            
        Returns:
            System prompt for OpenAI
        """
        base_prompt = """
        You are an expert auction data extractor. Extract auction information from the HTML content of auction websites.
        Focus only on active auctions. Return the data as a JSON object with an "auctions" array containing auction objects.
        
        Each auction object should have these fields:
        - title: The title or name of the auction item
        - description: A description of the item
        - current_price: The current bid price (numeric, without currency symbol)
        - start_date: The start date of the auction (if available)
        - end_date: The end date of the auction (if available)
        - url: The URL to the auction listing
        - location: The location of the item (city, state, zip)
        - images: An array of image URLs for the item
        
        Return ONLY valid JSON without any explanation or additional text.
        """
        
        # Add source-specific instructions
        if source_type == "govdeals":
            return base_prompt + """
            For GovDeals, focus on extracting auctions from the search results table.
            Look for elements with class "searchResults" or similar.
            The auction URLs should be absolute, not relative paths.
            """
        elif source_type == "public_surplus":
            return base_prompt + """
            For Public Surplus, focus on extracting auctions from the auction listings.
            Look for elements with class "auction-item" or similar.
            Make sure to extract the auction end dates which are important for this source.
            """
        elif source_type == "gaston_sheehan":
            return base_prompt + """
            For Gaston and Sheehan Auctioneers, focus on extracting auctions from the homepage.
            Look for elements with class "auction-item" or similar.
            Pay special attention to extracting the auction dates which may be in a specific format.
            """
        else:
            return base_prompt
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """
        Parse date string to ISO format
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            ISO formatted date or None if parsing fails
        """
        if not date_str:
            return None
            
        try:
            # Remove timezone information if present
            date_str = re.sub(r'\s+[A-Z]{3,4}$', '', date_str)
            
            # Try different date formats
            formats = [
                "%m/%d/%Y %I:%M %p",  # 03/19/2025 10:00 AM
                "%m/%d/%Y",           # 03/19/2025
                "%Y-%m-%d %H:%M:%S",  # 2025-03-19 10:00:00
                "%Y-%m-%d",           # 2025-03-19
                "%B %d, %Y %I:%M %p", # March 19, 2025 10:00 AM
                "%B %d, %Y",          # March 19, 2025
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.isoformat()
                except ValueError:
                    continue
                    
            # If all formats fail, try a more flexible approach
            import dateutil.parser
            dt = dateutil.parser.parse(date_str)
            return dt.isoformat()
            
        except Exception as e:
            logger.error(f"Error parsing date '{date_str}': {e}")
            return None
    
    def _parse_location(self, location_str: str) -> Dict[str, Optional[str]]:
        """
        Parse location string into components
        
        Args:
            location_str: Location string (e.g., "Austin, TX 78701")
            
        Returns:
            Dictionary with city, state, and zip_code
        """
        location = {
            "city": None,
            "state": "TX",  # Default state
            "zip_code": None
        }
        
        if not location_str:
            return location
            
        try:
            # Try to extract city, state, zip
            # Pattern: City, State ZIP
            match = re.search(r'([^,]+),\s*([A-Z]{2})\s*(\d{5})?', location_str)
            if match:
                location["city"] = match.group(1).strip()
                location["state"] = match.group(2).strip()
                if match.group(3):
                    location["zip_code"] = match.group(3).strip()
            else:
                # Just use the whole string as city if no pattern match
                location["city"] = location_str.strip()
        except Exception as e:
            logger.error(f"Error parsing location '{location_str}': {e}")
            
        return location
    
    def _generate_id(self, title: str) -> str:
        """
        Generate a unique ID from title
        
        Args:
            title: Auction title
            
        Returns:
            Generated ID
        """
        # Remove special characters and spaces
        clean_title = re.sub(r'[^a-zA-Z0-9]', '', title)
        
        # Take first 20 characters and add timestamp
        timestamp = int(time.time())
        return f"{clean_title[:20]}_{timestamp}"
    
    def _determine_category(self, title: str, description: str) -> str:
        """
        Determine auction category from title and description
        
        Args:
            title: Auction title
            description: Auction description
            
        Returns:
            Category name
        """
        text = (title + " " + description).lower()
        
        # Vehicle categories
        if any(vehicle in text for vehicle in ["car", "truck", "van", "suv", "ford", "chevy", "toyota", "honda", "vehicle", "auto"]):
            return "vehicles"
        
        # Real estate categories
        elif any(real_estate in text for real_estate in ["real estate", "property", "land", "house", "home", "apartment", "condo"]):
            return "real_estate"
        
        # Jewelry categories
        elif any(jewelry in text for jewelry in ["jewelry", "watch", "rolex", "gold", "silver", "diamond"]):
            return "jewelry"
        
        # Equipment categories
        elif any(equip in text for equip in ["equipment", "machinery", "tools", "forklift", "tractor"]):
            return "equipment"
        
        # Default category
        return "other"
    
    def save_auctions_to_database(self, auctions: List[Dict[str, Any]]) -> int:
        """
        Save auctions to database
        
        Args:
            auctions: List of auction dictionaries
            
        Returns:
            Number of auctions saved
        """
        count = 0
        
        for auction in auctions:
            try:
                # Add source
                source_id = self.db.add_source(
                    name=auction.get('source_id', 'unknown'),
                    url=auction.get('url', '')
                )
                
                # Add location
                location = auction.get('location', {})
                location_id = self.db.add_location(
                    city=location.get('city'),
                    state=location.get('state', 'TX'),
                    zip_code=location.get('zip_code')
                )
                
                # Add auction
                auction_id = self.db.add_auction(
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
                        self.db.add_image(auction_id, image_url)
                
                count += 1
                logger.info(f"Saved auction: {auction.get('title')}")
                
            except Exception as e:
                logger.error(f"Error saving auction {auction.get('title')}: {e}")
        
        return count

def main():
    """
    Main function to run the OpenAI-powered scraper
    """
    logger.info("Starting OpenAI-powered auction scraper")
    
    try:
        # Initialize scraper
        scraper = OpenAIAuctionScraper()
        
        # Initialize database and create tables if needed
        db = AuctionDatabase()
        db.create_tables()
        logger.info("Database tables created/verified")
        
        # Scrape all sources
        auctions = scraper.scrape_all_sources()
        logger.info(f"Found {len(auctions)} auctions total")
        
        # Save to database
        if auctions:
            count = scraper.save_auctions_to_database(auctions)
            logger.info(f"Saved {count} auctions to database")
        else:
            logger.warning("No auctions found to save")
        
        # Save to JSON file for reference
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/openai_auctions_{timestamp}.json"
        os.makedirs("data", exist_ok=True)
        with open(filename, "w") as f:
            json.dump(auctions, f, indent=2)
        logger.info(f"Saved auctions to {filename}")
        
        # Check final count in database
        try:
            cursor = db.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM auctions")
            count = cursor.fetchone()[0]
            logger.info(f"Final auction count in database: {count}")
        except Exception as e:
            logger.error(f"Error checking final auction count: {e}")
        
        logger.info("OpenAI-powered auction scraper completed successfully")
        
    except Exception as e:
        logger.error(f"Error running OpenAI-powered scraper: {e}")

if __name__ == "__main__":
    main()
