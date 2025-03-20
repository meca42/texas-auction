"""
OpenAI-powered Auction Scraper for Texas Auction Database

This module uses OpenAI's API to extract auction data from websites without
requiring browser automation, making it ideal for deployment on Render.
"""
import os
import json
import logging
import requests
from datetime import datetime, timedelta
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
        
        # Source configurations with proper source URLs and multiple pages
        self.sources = [
            {
                "name": "GovDeals - Texas",
                "source_id": "govdeals",
                "base_url": "https://www.allsurplus.com/search?isAdvSearch=1&timing=bySimple&timeType=atauction&ps=120&locationType=miles&zipcode=78232&miles=250&milesKilo=miles&showMap=false&sf=auctionclose&so=asc",
                "source_url": "https://www.allsurplus.com",
                "type": "govdeals",
                "pages": [
                    "https://www.allsurplus.com/search?isAdvSearch=1&timing=bySimple&timeType=atauction&ps=120&locationType=miles&zipcode=78232&miles=250&milesKilo=miles&showMap=false&sf=auctionclose&so=asc",
                    "https://www.allsurplus.com/search/filters?isAdvSearch=1&timing=bySimple&timeType=atauction&ps=120&locationType=miles&zipcode=78232&miles=250&milesKilo=miles&showMap=false&sf=auctionclose&so=asc&pn=2"
                    "https://www.allsurplus.com/search/filters?isAdvSearch=1&timing=bySimple&timeType=atauction&ps=120&locationType=miles&zipcode=78232&miles=250&milesKilo=miles&showMap=false&sf=auctionclose&so=asc&pn=3"
                    "https://www.allsurplus.com/search/filters?isAdvSearch=1&timing=bySimple&timeType=atauction&ps=120&locationType=miles&zipcode=78232&miles=250&milesKilo=miles&showMap=false&sf=auctionclose&so=asc&pn=4"
                ]
            },
            {
                "name": "Public Surplus - Texas Facilities Commission",
                "source_id": "public_surplus",
                "base_url": "https://www.publicsurplus.com/sms/all,tx/browse/cataucs?catid=4",
                "source_url": "https://www.publicsurplus.com",
                "type": "public_surplus",
                "pages": [
                    "https://www.publicsurplus.com/sms/all,tx/browse/cataucs?catid=4",
                    "https://www.publicsurplus.com/sms/all,tx/browse/cataucs?slth=y&catid=4&page=1&sortBy=timeLeft&sortDesc=N&showaucpct="
                    "https://www.publicsurplus.com/sms/all,tx/browse/cataucs?slth=y&catid=4&page=2&sortBy=timeLeft&sortDesc=N&showaucpct="
                    "https://www.publicsurplus.com/sms/all,tx/browse/cataucs?slth=y&catid=4&page=3&sortBy=timeLeft&sortDesc=N&showaucpct="
                ]
            },
            {
                "name": "Gaston and Sheehan Auctioneers",
                "source_id": "gaston_sheehan",
                "base_url": "https://www.txauction.com/",
                "source_url": "https://www.txauction.com",
                "type": "gaston_sheehan",
                "pages": [
                    "https://www.txauction.com/",
                    "https://www.txauction.com/auctions"
                ]
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
            logger.info(f"Scraping {source['name']} from multiple pages")
            source_auctions = []
            
            # Scrape each page for this source
            for page_url in source['pages']:
                try:
                    logger.info(f"Scraping page: {page_url}")
                    page_auctions = self.scrape_page(page_url, source)
                    logger.info(f"Found {len(page_auctions)} auctions from {page_url}")
                    source_auctions.extend(page_auctions)
                    
                    # Add a small delay between page requests to avoid rate limiting
                    time.sleep(2)
                except Exception as e:
                    logger.error(f"Error scraping {page_url}: {e}")
            
            # Remove duplicates based on title and URL
            unique_auctions = self._remove_duplicates(source_auctions)
            logger.info(f"Found {len(unique_auctions)} unique auctions from {source['name']}")
            
            all_auctions.extend(unique_auctions)
        
        return all_auctions
    
    def _remove_duplicates(self, auctions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate auctions based on title and URL
        
        Args:
            auctions: List of auction dictionaries
            
        Returns:
            List of unique auction dictionaries
        """
        unique_auctions = []
        seen_keys = set()
        
        for auction in auctions:
            # Create a unique key based on title and URL
            key = f"{auction.get('title', '')}-{auction.get('url', '')}"
            
            if key not in seen_keys:
                seen_keys.add(key)
                unique_auctions.append(auction)
        
        return unique_auctions
    
    def scrape_page(self, url: str, source: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Scrape a specific page from an auction source
        
        Args:
            url: URL of the page to scrape
            source: Source configuration dictionary
            
        Returns:
            List of auction items as dictionaries
        """
        # Fetch the HTML content
        html_content = self._fetch_html(url)
        if not html_content:
            logger.error(f"Failed to fetch HTML from {url}")
            return []
        
        # Extract auction data using OpenAI
        auctions = self._extract_auctions_with_openai(html_content, source)
        
        # Add source information to each auction
        for auction in auctions:
            auction["source_id"] = source["source_id"]
            auction["source_name"] = source["name"]
            
            # Generate a unique ID if not present
            if "auction_id" not in auction:
                auction["auction_id"] = f"{source['source_id']}_{self._generate_id(auction.get('title', ''))}"
            
            # Set external_id if not present
            if "external_id" not in auction:
                auction["external_id"] = auction["auction_id"]
                
            # Fix image URLs if they're relative
            if "images" in auction and auction["images"]:
                fixed_images = []
                for img_url in auction["images"]:
                    if img_url and not img_url.startswith(('http://', 'https://')):
                        # Convert relative URL to absolute
                        base_url = self._get_base_url(url)
                        img_url = self._make_absolute_url(base_url, img_url)
                    if img_url:  # Only add non-empty URLs
                        fixed_images.append(img_url)
                auction["images"] = fixed_images
            
            # Fix auction URLs to ensure they're absolute and valid
            if "url" in auction and auction["url"]:
                if not auction["url"].startswith(('http://', 'https://')):
                    # Convert relative URL to absolute
                    base_url = self._get_base_url(url)
                    auction["url"] = self._make_absolute_url(base_url, auction["url"])
            else:
                # If no URL is provided, use the source URL as a fallback
                auction["url"] = source["source_url"]
            
            # Ensure end_date is set (required by database)
            if not auction.get("end_date"):
                # Set default end date to 7 days from now if not provided
                auction["end_date"] = (datetime.now() + timedelta(days=7)).isoformat()
        
        return auctions
    
    def _get_base_url(self, url: str) -> str:
        """
        Extract base URL from a full URL
        
        Args:
            url: Full URL
            
        Returns:
            Base URL (scheme + domain)
        """
        match = re.match(r'(https?://[^/]+)', url)
        if match:
            return match.group(1)
        return url
    
    def _make_absolute_url(self, base_url: str, relative_url: str) -> str:
        """
        Convert a relative URL to an absolute URL
        
        Args:
            base_url: Base URL (scheme + domain)
            relative_url: Relative URL
            
        Returns:
            Absolute URL
        """
        if relative_url.startswith('/'):
            return f"{base_url}{relative_url}"
        else:
            return f"{base_url}/{relative_url}"
    
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
                else:
                    # Set default end date to 7 days from now if not provided
                    auction["end_date"] = (datetime.now() + timedelta(days=7)).isoformat()
                
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
                elif isinstance(auction["images"], str):
                    # Convert single image string to list
                    auction["images"] = [auction["images"]]
                
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
        - url: The URL to the auction listing (VERY IMPORTANT: extract the COMPLETE URL to the specific auction)
        - location: The location of the item (city, state, zip)
        - images: An array of image URLs for the item (VERY IMPORTANT: extract ALL image URLs, even if they're relative paths)
        
        IMPORTANT INSTRUCTIONS FOR IMAGES:
        1. Extract ALL image URLs for each auction, even if they're relative paths
        2. Include the complete image URL if it's absolute, or the relative path if it's relative
        3. If you find image URLs in data-src, src, or other attributes, include them all
        4. Do not skip any images, as they are critical for the website display
        
        IMPORTANT INSTRUCTIONS FOR AUCTION URLS:
        1. Extract the COMPLETE URL to each specific auction
        2. If it's a relative URL, include the complete relative path
        3. The URL should point directly to the auction detail page
        4. This URL will be used for the "Visit Source" button, so it must be correct
        
        IMPORTANT INSTRUCTIONS FOR EXTRACTING MAXIMUM AUCTIONS:
        1. Extract ALL auctions from the page, even if there are many
        2. Do not limit the number of auctions you extract
        3. Look for auctions in all sections of the page
        4. If there are multiple auction categories or sections, extract from all of them
        
        Return ONLY valid JSON without any explanation or additional text.
        """
        
        # Add source-specific instructions
        if source_type == "govdeals":
            return base_prompt + """
            For GovDeals, focus on extracting auctions from the search results table.
            Look for elements with class "searchResults" or similar.
            The auction URLs should be absolute, not relative paths.
            Pay special attention to image elements and extract all image URLs, even if they're in data-src attributes.
            Make sure to extract the complete URL to each auction's detail page for the "Visit Source" button.
            """
        elif source_type == "public_surplus":
            return base_prompt + """
            For Public Surplus, focus on extracting auctions from the auction listings.
            Look for elements with class "auction-item" or similar.
            Make sure to extract the auction end dates which are important for this source.
            Pay special attention to image elements and extract all image URLs, even if they're in data-src attributes.
            Make sure to extract the complete URL to each auction's detail page for the "Visit Source" button.
            """
        elif source_type == "gaston_sheehan":
            return base_prompt + """
            For Gaston and Sheehan Auctioneers, focus on extracting auctions from the homepage.
            Look for elements with class "auction-item" or similar.
            Pay special attention to extracting the auction dates which may be in a specific format.
            Pay special attention to image elements and extract all image URLs, even if they're in data-src attributes.
            Make sure to extract the complete URL to each auction's detail page for the "Visit Source" button.
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
            # Default to 7 days from now if no date provided
            return (datetime.now() + timedelta(days=7)).isoformat()
            
        try:
            # Handle relative time formats like "1 day 2 hours" or "3 hours 25 mins"
            days_match = re.search(r'(\d+)\s+day(?:s)?\s+(\d+)\s+hour(?:s)?', date_str)
            if days_match:
                days = int(days_match.group(1))
                hours = int(days_match.group(2))
                # Calculate end date based on current time plus the relative time
                end_date = datetime.now().replace(microsecond=0)
                end_date = end_date + timedelta(days=days, hours=hours)
                return end_date.isoformat()
            
            hours_match = re.search(r'(\d+)\s+hour(?:s)?\s+(\d+)\s+min(?:s)?', date_str)
            if hours_match:
                hours = int(hours_match.group(1))
                minutes = int(hours_match.group(2))
                # Calculate end date based on current time plus the relative time
                end_date = datetime.now().replace(microsecond=0)
                end_date = end_date + timedelta(hours=hours, minutes=minutes)
                return end_date.isoformat()
            
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
            # Default to 7 days from now if parsing fails
            return (datetime.now() + timedelta(days=7)).isoformat()
    
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
        
        # Connect to the database
        conn = self.db.connect()
        
        for auction in auctions:
            try:
                # Get or create source
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT source_id FROM auction_sources WHERE name = %s",
                    (auction.get('source_id', 'unknown'),)
                )
                result = cursor.fetchone()
                
                if result:
                    source_id = result[0]
                else:
                    cursor.execute(
                        "INSERT INTO auction_sources (name, website_url) VALUES (%s, %s) RETURNING source_id",
                        (auction.get('source_id', 'unknown'), auction.get('url', ''))
                    )
                    source_id = cursor.fetchone()[0]
                
                # Get or create location
                location = auction.get('location', {})
                cursor.execute(
                    "SELECT location_id FROM locations WHERE city = %s AND state = %s AND zip_code = %s",
                    (location.get('city'), location.get('state', 'TX'), location.get('zip_code'))
                )
                result = cursor.fetchone()
                
                if result:
                    location_id = result[0]
                else:
                    cursor.execute(
                        "INSERT INTO locations (city, state, zip_code) VALUES (%s, %s, %s) RETURNING location_id",
                        (location.get('city'), location.get('state', 'TX'), location.get('zip_code'))
                    )
                    location_id = cursor.fetchone()[0]
                
                # Check if auction already exists
                cursor.execute(
                    "SELECT auction_id FROM auctions WHERE external_id = %s AND source_id = %s",
                    (auction.get('external_id', ''), source_id)
                )
                result = cursor.fetchone()
                
                if result:
                    # Update existing auction
                    auction_id = result[0]
                    cursor.execute(
                        """
                        UPDATE auctions SET 
                            title = %s,
                            description = %s,
                            current_price = %s,
                            end_date = %s,
                            url = %s,
                            location_id = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE auction_id = %s
                        """,
                        (
                            auction.get('title', ''),
                            auction.get('description', ''),
                            auction.get('current_price'),
                            auction.get('end_date'),
                            auction.get('url', ''),
                            location_id,
                            auction_id
                        )
                    )
                else:
                    # Insert new auction
                    cursor.execute(
                        """
                        INSERT INTO auctions (
                            source_id, external_id, title, description, 
                            start_date, end_date, current_price, location_id, url
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING auction_id
                        """,
                        (
                            source_id,
                            auction.get('external_id', ''),
                            auction.get('title', ''),
                            auction.get('description', ''),
                            auction.get('start_date'),
                            auction.get('end_date'),
                            auction.get('current_price'),
                            location_id,
                            auction.get('url', '')
                        )
                    )
                    auction_id = cursor.fetchone()[0]
                
                # Add images
                for image_url in auction.get('images', []):
                    if image_url:
                        # Check if image already exists
                        cursor.execute(
                            "SELECT image_id FROM auction_images WHERE auction_id = %s AND image_url = %s",
                            (auction_id, image_url)
                        )
                        if not cursor.fetchone():
                            cursor.execute(
                                "INSERT INTO auction_images (auction_id, image_url) VALUES (%s, %s)",
                                (auction_id, image_url)
                            )
                
                conn.commit()
                count += 1
                logger.info(f"Saved auction: {auction.get('title')}")
                
            except Exception as e:
                logger.error(f"Error saving auction {auction.get('title')}: {e}")
                conn.rollback()
        
        # Close the connection
        self.db.close()
        
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
            conn = db.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM auctions")
            count = cursor.fetchone()[0]
            logger.info(f"Final auction count in database: {count}")
            db.close()
        except Exception as e:
            logger.error(f"Error checking final auction count: {e}")
        
        logger.info("OpenAI-powered auction scraper completed successfully")
        
    except Exception as e:
        logger.error(f"Error running OpenAI-powered scraper: {e}")

if __name__ == "__main__":
    main()
