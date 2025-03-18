"""
Base Scraper Module for Texas Auction Database

This module provides a base class for all auction scrapers to inherit from,
ensuring consistent data collection and processing across different sources.
"""

import os
import json
import logging
from datetime import datetime
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)

class BaseScraper(ABC):
    """Base class for all auction scrapers"""
    
    def __init__(self, source_name, source_url):
        """
        Initialize the base scraper
        
        Args:
            source_name (str): Name of the auction source
            source_url (str): URL of the auction source
        """
        self.source_name = source_name
        self.source_url = source_url
        self.logger = logging.getLogger(f"scraper.{source_name}")
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        
        # Create data directory if it doesn't exist
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    @abstractmethod
    def scrape(self):
        """
        Main method to scrape auction data
        
        This method must be implemented by all subclasses
        
        Returns:
            list: List of auction items as dictionaries
        """
        pass
    
    def save_data(self, auctions, filename=None):
        """
        Save scraped auction data to JSON file
        
        Args:
            auctions (list): List of auction items as dictionaries
            filename (str, optional): Custom filename. Defaults to None.
        
        Returns:
            str: Path to the saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.source_name.lower().replace(' ', '_')}_{timestamp}.json"
        
        filepath = os.path.join(self.data_dir, filename)
        
        # Add metadata to the output
        output = {
            "source": self.source_name,
            "source_url": self.source_url,
            "scrape_time": datetime.now().isoformat(),
            "auction_count": len(auctions),
            "auctions": auctions
        }
        
        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)
        
        self.logger.info(f"Saved {len(auctions)} auctions to {filepath}")
        return filepath
    
    def normalize_date(self, date_str):
        """
        Normalize date string to ISO format
        
        Args:
            date_str (str): Date string in various formats
            
        Returns:
            str: ISO formatted date string or None if parsing fails
        """
        try:
            # Try different date formats
            for fmt in [
                "%m/%d/%Y %I:%M %p",  # 03/18/2025 04:30 PM
                "%m/%d/%Y",           # 03/18/2025
                "%Y-%m-%d %H:%M:%S",  # 2025-03-18 16:30:00
                "%Y-%m-%d",           # 2025-03-18
                "%b %d, %Y %I:%M %p", # Mar 18, 2025 04:30 PM
                "%b %d, %Y"           # Mar 18, 2025
            ]:
                try:
                    dt = datetime.strptime(date_str.strip(), fmt)
                    return dt.isoformat()
                except ValueError:
                    continue
            
            # If all formats fail, log warning and return original
            self.logger.warning(f"Could not parse date: {date_str}")
            return date_str
        except Exception as e:
            self.logger.error(f"Error normalizing date {date_str}: {e}")
            return None
    
    def extract_location(self, text):
        """
        Extract location information from text
        
        Args:
            text (str): Text containing location information
            
        Returns:
            dict: Dictionary with city, state, zip_code if found
        """
        location = {"city": None, "state": "TX", "zip_code": None}
        
        # Look for Texas cities
        texas_cities = [
            "Austin", "Houston", "Dallas", "San Antonio", "Fort Worth", 
            "El Paso", "Arlington", "Corpus Christi", "Plano", "Lubbock",
            "Irving", "Laredo", "Garland", "Frisco", "McKinney", "Amarillo"
        ]
        
        for city in texas_cities:
            if city in text:
                location["city"] = city
                break
        
        # Look for ZIP code (5 digits)
        import re
        zip_match = re.search(r'\b\d{5}\b', text)
        if zip_match:
            location["zip_code"] = zip_match.group(0)
        
        return location
    
    def clean_price(self, price_str):
        """
        Clean price string to float
        
        Args:
            price_str (str): Price string (e.g., "$1,234.56")
            
        Returns:
            float: Cleaned price as float or None if parsing fails
        """
        try:
            if not price_str:
                return None
            
            # Remove currency symbols and commas
            clean_str = price_str.replace('$', '').replace(',', '').strip()
            
            # Convert to float
            return float(clean_str)
        except Exception as e:
            self.logger.error(f"Error cleaning price {price_str}: {e}")
            return None
