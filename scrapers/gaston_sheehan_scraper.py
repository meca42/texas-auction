"""
Gaston and Sheehan Auctioneers Scraper for Texas Auction Database

This module implements a scraper for the Gaston and Sheehan Auctioneers website,
which hosts various auctions in Texas.
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

from base_scraper import BaseScraper

class GastonSheehanScraper(BaseScraper):
    """Scraper for Gaston and Sheehan Auctioneers website"""
    
    def __init__(self):
        """Initialize the Gaston and Sheehan scraper"""
        super().__init__(
            source_name="Gaston and Sheehan Auctioneers",
            source_url="https://www.txauction.com/"
        )
        self.logger = logging.getLogger("scraper.gaston_sheehan")
    
    def scrape(self):
        """
        Scrape auction data from Gaston and Sheehan Auctioneers
        
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
            
            # Navigate to the Gaston and Sheehan website
            driver.get(self.source_url)
            self.logger.info("Navigated to Gaston and Sheehan website")
            
            # Wait for the page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".auction-item"))
            )
            
            # Get all auction items on the homepage
            auction_items = driver.find_elements(By.CSS_SELECTOR, ".auction-item")
            self.logger.info(f"Found {len(auction_items)} auction items on homepage")
            
            # Process each auction item
            for item in auction_items:
                try:
                    # Extract auction data
                    title_element = item.find_element(By.CSS_SELECTOR, "h3")
                    title = title_element.text.strip()
                    
                    # Extract date information
                    date_elements = item.find_elements(By.CSS_SELECTOR, "p strong")
                    start_date = None
                    end_date = None
                    
                    for date_elem in date_elements:
                        text = date_elem.text.strip()
                        if "Start Date:" in text:
                            start_date_str = text.replace("Start Date:", "").strip()
                            start_date = self._parse_date(start_date_str)
                        elif "End Date:" in text:
                            end_date_str = text.replace("End Date:", "").strip()
                            end_date = self._parse_date(end_date_str)
                    
                    # Extract description
                    description_element = item.find_element(By.CSS_SELECTOR, "p:not(:has(strong))")
                    description = description_element.text.strip()
                    
                    # Extract bid button URL if available
                    url = self.source_url
                    try:
                        bid_button = item.find_element(By.CSS_SELECTOR, "a.btn")
                        url = bid_button.get_attribute("href")
                    except:
                        self.logger.warning(f"No bid button found for auction: {title}")
                    
                    # Extract location from description
                    location = self.extract_location(description)
                    
                    # Generate a unique ID
                    auction_id = f"gs_{self._generate_id(title)}"
                    
                    # Create auction object
                    auction = {
                        "auction_id": auction_id,
                        "external_id": auction_id,
                        "title": title,
                        "description": description,
                        "url": url,
                        "source_id": "gaston_sheehan",
                        "start_date": start_date,
                        "end_date": end_date,
                        "current_price": None,  # Price not available on homepage
                        "location": location,
                        "category": self._determine_category(title, description),
                        "images": []
                    }
                    
                    # Add to auctions list
                    auctions.append(auction)
                    
                except Exception as e:
                    self.logger.error(f"Error processing auction item: {e}")
            
            self.logger.info(f"Completed scrape of {self.source_name}, found {len(auctions)} auctions")
            
        except Exception as e:
            self.logger.error(f"Error scraping {self.source_name}: {e}")
        
        return auctions
    
    def _parse_date(self, date_str):
        """
        Parse date string to ISO format
        
        Args:
            date_str (str): Date string (e.g., "3/19/2025 10:00 AM CDT")
            
        Returns:
            str: ISO formatted date or None if parsing fails
        """
        try:
            # Remove timezone information
            date_str = re.sub(r'\s+[A-Z]{3}$', '', date_str)
            
            # Parse the date
            dt = datetime.strptime(date_str, "%m/%d/%Y %I:%M %p")
            return dt.isoformat()
        except Exception as e:
            self.logger.error(f"Error parsing date '{date_str}': {e}")
            return None
    
    def _generate_id(self, title):
        """
        Generate a unique ID from title
        
        Args:
            title (str): Auction title
            
        Returns:
            str: Generated ID
        """
        # Remove special characters and spaces
        clean_title = re.sub(r'[^a-zA-Z0-9]', '', title)
        
        # Take first 20 characters and add timestamp
        timestamp = int(time.time())
        return f"{clean_title[:20]}_{timestamp}"
    
    def _determine_category(self, title, description):
        """
        Determine auction category from title and description
        
        Args:
            title (str): Auction title
            description (str): Auction description
            
        Returns:
            str: Category name
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


if __name__ == "__main__":
    # Run the scraper if this file is executed directly
    scraper = GastonSheehanScraper()
    auctions = scraper.scrape()
    scraper.save_data(auctions)
