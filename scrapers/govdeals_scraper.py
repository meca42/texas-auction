"""
GovDeals Scraper for Texas Auction Database

This module implements a scraper for the GovDeals website,
specifically for Texas auctions.
"""

import time
import requests
from bs4 import BeautifulSoup
import logging
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from .base_scraper import BaseScraper

class GovDealsScraper(BaseScraper):
    """Scraper for GovDeals website"""
    
    def __init__(self):
        """Initialize the GovDeals scraper"""
        super().__init__(
            source_name="GovDeals - Texas",
            source_url="https://www.govdeals.com/texas"
        )
        self.logger = logging.getLogger("scraper.govdeals")
    
    def scrape(self):
        """
        Scrape auction data from GovDeals
        
        Returns:
            list: List of auction items as dictionaries
        """
        self.logger.info(f"Starting scrape of {self.source_name}")
        auctions = []
        
        try:
            # Set up Chrome options for headless browsing
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            # Initialize the Chrome WebDriver
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )
            
            # Navigate to the GovDeals website
            driver.get(self.source_url)
            self.logger.info("Navigated to GovDeals website")
            
            # Wait for the page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".listing"))
            )
            
            # Get all auction listings
            auction_listings = driver.find_elements(By.CSS_SELECTOR, ".listing")
            self.logger.info(f"Found {len(auction_listings)} auction listings")
            
            # Process each auction listing
            for listing in auction_listings:
                try:
                    # Extract auction data
                    title_element = listing.find_element(By.CSS_SELECTOR, ".listing-title a")
                    title = title_element.text.strip()
                    url = title_element.get_attribute("href")
                    
                    # Extract auction ID from URL
                    auction_id = None
                    id_match = re.search(r'index=(\d+)', url)
                    if id_match:
                        auction_id = f"govdeals_{id_match.group(1)}"
                    else:
                        auction_id = f"govdeals_{int(time.time())}"
                    
                    # Extract current price
                    current_price = None
                    try:
                        price_element = listing.find_element(By.CSS_SELECTOR, ".listing-bid")
                        price_text = price_element.text.strip()
                        current_price = self.clean_price(price_text)
                    except:
                        self.logger.warning(f"No price found for auction: {title}")
                    
                    # Extract end date
                    end_date = None
                    try:
                        date_element = listing.find_element(By.CSS_SELECTOR, ".listing-time")
                        date_text = date_element.text.strip()
                        end_date = self._parse_end_date(date_text)
                    except:
                        self.logger.warning(f"No end date found for auction: {title}")
                    
                    # Extract location
                    location = {"city": None, "state": "TX", "zip_code": None}
                    try:
                        location_element = listing.find_element(By.CSS_SELECTOR, ".listing-location")
                        location_text = location_element.text.strip()
                        location = self.extract_location(location_text)
                    except:
                        self.logger.warning(f"No location found for auction: {title}")
                    
                    # Extract image URL
                    image_url = None
                    try:
                        image_element = listing.find_element(By.CSS_SELECTOR, ".listing-image img")
                        image_url = image_element.get_attribute("src")
                    except:
                        self.logger.warning(f"No image found for auction: {title}")
                    
                    # Create auction object
                    auction = {
                        "auction_id": auction_id,
                        "external_id": auction_id,
                        "title": title,
                        "description": title,  # Will be updated with full description if we visit the detail page
                        "url": url,
                        "source_id": "govdeals",
                        "current_price": current_price,
                        "end_date": end_date,
                        "location": location,
                        "category": self._determine_category(title),
                        "images": [image_url] if image_url else []
                    }
                    
                    # Add to auctions list
                    auctions.append(auction)
                    
                except Exception as e:
                    self.logger.error(f"Error processing auction listing: {e}")
            
            # Check if there are more pages
            try:
                next_page = driver.find_element(By.CSS_SELECTOR, ".pagination .next a")
                has_next_page = True
                page_num = 2
                
                # Process up to 5 pages (can be adjusted)
                while has_next_page and page_num <= 5:
                    next_page.click()
                    self.logger.info(f"Navigated to page {page_num}")
                    
                    # Wait for the page to load
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".listing"))
                    )
                    
                    # Get all auction listings on this page
                    auction_listings = driver.find_elements(By.CSS_SELECTOR, ".listing")
                    self.logger.info(f"Found {len(auction_listings)} auction listings on page {page_num}")
                    
                    # Process each auction listing (same code as above)
                    for listing in auction_listings:
                        try:
                            # Extract auction data (same code as above)
                            title_element = listing.find_element(By.CSS_SELECTOR, ".listing-title a")
                            title = title_element.text.strip()
                            url = title_element.get_attribute("href")
                            
                            # Extract auction ID from URL
                            auction_id = None
                            id_match = re.search(r'index=(\d+)', url)
                            if id_match:
                                auction_id = f"govdeals_{id_match.group(1)}"
                            else:
                                auction_id = f"govdeals_{int(time.time())}"
                            
                            # Extract current price
                            current_price = None
                            try:
                                price_element = listing.find_element(By.CSS_SELECTOR, ".listing-bid")
                                price_text = price_element.text.strip()
                                current_price = self.clean_price(price_text)
                            except:
                                self.logger.warning(f"No price found for auction: {title}")
                            
                            # Extract end date
                            end_date = None
                            try:
                                date_element = listing.find_element(By.CSS_SELECTOR, ".listing-time")
                                date_text = date_element.text.strip()
                                end_date = self._parse_end_date(date_text)
                            except:
                                self.logger.warning(f"No end date found for auction: {title}")
                            
                            # Extract location
                            location = {"city": None, "state": "TX", "zip_code": None}
                            try:
                                location_element = listing.find_element(By.CSS_SELECTOR, ".listing-location")
                                location_text = location_element.text.strip()
                                location = self.extract_location(location_text)
                            except:
                                self.logger.warning(f"No location found for auction: {title}")
                            
                            # Extract image URL
                            image_url = None
                            try:
                                image_element = listing.find_element(By.CSS_SELECTOR, ".listing-image img")
                                image_url = image_element.get_attribute("src")
                            except:
                                self.logger.warning(f"No image found for auction: {title}")
                            
                            # Create auction object
                            auction = {
                                "auction_id": auction_id,
                                "external_id": auction_id,
                                "title": title,
                                "description": title,
                                "url": url,
                                "source_id": "govdeals",
                                "current_price": current_price,
                                "end_date": end_date,
                                "location": location,
                                "category": self._determine_category(title),
                                "images": [image_url] if image_url else []
                            }
                            
                            # Add to auctions list
                            auctions.append(auction)
                            
                        except Exception as e:
                            self.logger.error(f"Error processing auction listing on page {page_num}: {e}")
                    
                    # Check if there's another page
                    try:
                        next_page = driver.find_element(By.CSS_SELECTOR, ".pagination .next a")
                        page_num += 1
                    except:
                        has_next_page = False
            except:
                self.logger.info("No additional pages found")
            
            self.logger.info(f"Completed scrape of {self.source_name}, found {len(auctions)} auctions")
            
        except Exception as e:
            self.logger.error(f"Error scraping {self.source_name}: {e}")
        
        return auctions
    
    def _parse_end_date(self, date_text):
        """
        Parse end date from text
        
        Args:
            date_text (str): Date text from the website
            
        Returns:
            str: ISO formatted date or None if parsing fails
        """
        try:
            # Common date formats on GovDeals
            if "Closes" in date_text:
                date_str = date_text.replace("Closes", "").strip()
                
                # Try different date formats
                for fmt in ["%m/%d/%Y %I:%M %p", "%m/%d/%Y %I:%M:%S %p", "%m/%d/%y %I:%M %p"]:
                    try:
                        dt = datetime.strptime(date_str, fmt)
                        return dt.isoformat()
                    except:
                        continue
            
            # If no format matches, try a more generic approach
            date_parts = re.findall(r'(\d+/\d+/\d+)', date_text)
            time_parts = re.findall(r'(\d+:\d+(?::\d+)?\s*(?:AM|PM|am|pm))', date_text)
            
            if date_parts and time_parts:
                date_str = f"{date_parts[0]} {time_parts[0]}"
                try:
                    dt = datetime.strptime(date_str, "%m/%d/%Y %I:%M %p")
                    return dt.isoformat()
                except:
                    try:
                        dt = datetime.strptime(date_str, "%m/%d/%y %I:%M %p")
                        return dt.isoformat()
                    except:
                        pass
            
            return None
        except Exception as e:
            self.logger.error(f"Error parsing end date from '{date_text}': {e}")
            return None
    
    def _determine_category(self, title):
        """
        Determine auction category from title
        
        Args:
            title (str): Auction title
            
        Returns:
            str: Category name
        """
        title_lower = title.lower()
        
        # Vehicle categories
        if any(vehicle in title_lower for vehicle in ["car", "truck", "van", "suv", "ford", "chevy", "toyota", "honda", "vehicle"]):
            return "vehicles"
        
        # Equipment categories
        elif any(equip in title_lower for equip in ["equipment", "forklift", "tractor", "mower", "generator"]):
            return "equipment"
        
        # Electronics categories
        elif any(electronics in title_lower for electronics in ["computer", "laptop", "phone", "tablet", "electronics"]):
            return "electronics"
        
        # Furniture categories
        elif any(furniture in title_lower for furniture in ["furniture", "chair", "desk", "table", "cabinet"]):
            return "furniture"
        
        # Default category
        return "other"


if __name__ == "__main__":
    # Run the scraper if this file is executed directly
    scraper = GovDealsScraper()
    auctions = scraper.scrape()
    scraper.save_data(auctions)
