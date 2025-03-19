""" Public Surplus Scraper for Texas Auction Database
This module implements a scraper for the Public Surplus website, specifically for Texas Facilities Commission auctions.
"""
import time
import requests
from bs4 import BeautifulSoup
import logging
import re
import os
from datetime import datetime, timedelta

# Only import Selenium-related modules if not in headless browser mode
HEADLESS_BROWSER_MODE = os.environ.get('HEADLESS_BROWSER_MODE', 'false').lower() == 'true'

if not HEADLESS_BROWSER_MODE:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager

from .base_scraper import BaseScraper

class PublicSurplusScraper(BaseScraper):
    """Scraper for Public Surplus website"""
    
    def __init__(self):
        """Initialize the Public Surplus scraper"""
        super().__init__(
            source_name="Public Surplus - Texas Facilities Commission",
            source_url="https://www.publicsurplus.com/sms/state,tx/list/current?orgid=871876"
        )
        self.logger = logging.getLogger("scraper.public_surplus")
    
    def scrape(self):
        """ Scrape auction data from Public Surplus
        Returns:
            list: List of auction items as dictionaries
        """
        self.logger.info(f"Starting scrape of {self.source_name}")
        
        # Check if we're in headless browser mode (Render deployment)
        if HEADLESS_BROWSER_MODE:
            self.logger.info("Using requests/BeautifulSoup for scraping (headless mode)")
            return self._scrape_with_requests()
        else:
            self.logger.info("Using Selenium for scraping")
            return self._scrape_with_selenium()
    
    def _scrape_with_requests(self):
        """Scrape auction data using requests and BeautifulSoup (no browser)"""
        auctions = []
        
        try:
            # Make request to Public Surplus website
            response = requests.get(self.source_url)
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch Public Surplus website: {response.status_code}")
                return auctions
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the auction table
            auction_table = soup.select_one("table.table-striped")
            if not auction_table:
                self.logger.error("Could not find auction table on page")
                return auctions
            
            # Find all auction rows
            auction_rows = auction_table.select("tbody tr")
            self.logger.info(f"Found {len(auction_rows)} auctions on page")
            
            # Process each auction row
            for row in auction_rows:
                try:
                    # Extract auction data
                    columns = row.select("td")
                    if len(columns) < 4:
                        continue
                    
                    auction_id = columns[0].text.strip()
                    
                    # Get the title and URL
                    title_element = columns[1].select_one("a")
                    if not title_element:
                        continue
                    
                    title = title_element.text.strip()
                    url = title_element.get("href")
                    if not url.startswith("http"):
                        url = f"https://www.publicsurplus.com{url}"
                    
                    # Get the time left
                    time_left = columns[2].text.strip()
                    
                    # Get the current price
                    current_price = self.clean_price(columns[3].text.strip())
                    
                    # Create auction object
                    auction = {
                        "auction_id": auction_id,
                        "external_id": auction_id,
                        "title": title,
                        "description": title,  # Will be updated with full description if we visit the detail page
                        "url": url,
                        "source_id": "public_surplus",
                        "current_price": current_price,
                        "time_left": time_left,
                        "end_date": None,  # Will calculate this from time_left
                        "location": {
                            "city": "Austin",  # Default location for Texas Facilities Commission
                            "state": "TX",
                            "zip_code": None
                        },
                        "category": self._determine_category(title),
                        "images": []
                    }
                    
                    # Calculate end date from time left
                    auction["end_date"] = self._calculate_end_date(time_left)
                    
                    # Add to auctions list
                    auctions.append(auction)
                    
                except Exception as e:
                    self.logger.error(f"Error processing auction row: {e}")
            
            # Check for pagination
            pagination = soup.select(".pagination a")
            current_page = 1
            max_pages = 5  # Limit to 5 pages
            
            # Process additional pages
            while current_page < max_pages:
                next_page_url = None
                
                # Find the next page link
                for page_link in pagination:
                    if page_link.text.strip() == str(current_page + 1):
                        next_page_url = page_link.get("href")
                        if not next_page_url.startswith("http"):
                            next_page_url = f"https://www.publicsurplus.com{next_page_url}"
                        break
                
                if not next_page_url:
                    break
                
                current_page += 1
                self.logger.info(f"Navigating to page {current_page}")
                
                # Request the next page
                response = requests.get(next_page_url)
                if response.status_code != 200:
                    self.logger.error(f"Failed to fetch page {current_page}: {response.status_code}")
                    break
                
                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find the auction table
                auction_table = soup.select_one("table.table-striped")
                if not auction_table:
                    self.logger.error(f"Could not find auction table on page {current_page}")
                    break
                
                # Find all auction rows
                auction_rows = auction_table.select("tbody tr")
                self.logger.info(f"Found {len(auction_rows)} auctions on page {current_page}")
                
                # Process each auction row (same code as above)
                for row in auction_rows:
                    try:
                        # Extract auction data
                        columns = row.select("td")
                        if len(columns) < 4:
                            continue
                        
                        auction_id = columns[0].text.strip()
                        
                        # Get the title and URL
                        title_element = columns[1].select_one("a")
                        if not title_element:
                            continue
                        
                        title = title_element.text.strip()
                        url = title_element.get("href")
                        if not url.startswith("http"):
                            url = f"https://www.publicsurplus.com{url}"
                        
                        # Get the time left
                        time_left = columns[2].text.strip()
                        
                        # Get the current price
                        current_price = self.clean_price(columns[3].text.strip())
                        
                        # Create auction object
                        auction = {
                            "auction_id": auction_id,
                            "external_id": auction_id,
                            "title": title,
                            "description": title,
                            "url": url,
                            "source_id": "public_surplus",
                            "current_price": current_price,
                            "time_left": time_left,
                            "end_date": None,
                            "location": {
                                "city": "Austin",
                                "state": "TX",
                                "zip_code": None
                            },
                            "category": self._determine_category(title),
                            "images": []
                        }
                        
                        # Calculate end date from time left
                        auction["end_date"] = self._calculate_end_date(time_left)
                        
                        # Add to auctions list
                        auctions.append(auction)
                        
                    except Exception as e:
                        self.logger.error(f"Error processing auction row on page {current_page}: {e}")
                
                # Update pagination for next iteration
                pagination = soup.select(".pagination a")
                
                # Sleep to avoid overloading the server
                time.sleep(1)
            
        except Exception as e:
            self.logger.error(f"Error scraping {self.source_name}: {e}")
        
        self.logger.info(f"Completed scrape of {self.source_name}, found {len(auctions)} auctions")
        return auctions
    
    def _scrape_with_selenium(self):
        """Scrape auction data using Selenium (with browser)"""
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
            
            # Navigate to the Public Surplus website
            driver.get(self.source_url)
            self.logger.info("Navigated to Public Surplus website")
            
            # Wait for the page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.table-striped"))
            )
            
            # Get the total number of pages
            pagination = driver.find_elements(By.CSS_SELECTOR, ".pagination span")
            total_pages = 1
            for page in pagination:
                try:
                    page_num = int(page.text)
                    if page_num > total_pages:
                        total_pages = page_num
                except ValueError:
                    continue
            
            self.logger.info(f"Found {total_pages} pages of auctions")
            
            # Process each page
            for page in range(1, total_pages + 1):
                if page > 1:
                    # Navigate to the next page
                    page_url = f"{self.source_url}&page={page}"
                    driver.get(page_url)
                    self.logger.info(f"Navigated to page {page}")
                    
                    # Wait for the page to load
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "table.table-striped"))
                    )
                
                # Get the auction rows
                auction_rows = driver.find_elements(By.CSS_SELECTOR, "table.table-striped tbody tr")
                self.logger.info(f"Found {len(auction_rows)} auctions on page {page}")
                
                # Process each auction
                for row in auction_rows:
                    try:
                        # Extract auction data
                        columns = row.find_elements(By.TAG_NAME, "td")
                        if len(columns) < 4:
                            continue
                        
                        auction_id = columns[0].text.strip()
                        
                        # Get the title and URL
                        title_element = columns[1].find_element(By.TAG_NAME, "a")
                        title = title_element.text.strip()
                        url = title_element.get_attribute("href")
                        
                        # Get the time left
                        time_left = columns[2].text.strip()
                        
                        # Get the current price
                        current_price = self.clean_price(columns[3].text.strip())
                        
                        # Create auction object
                        auction = {
                            "auction_id": auction_id,
                            "external_id": auction_id,
                            "title": title,
                            "description": title,  # Will be updated with full description if we visit the detail page
                            "url": url,
                            "source_id": "public_surplus",
                            "current_price": current_price,
                            "time_left": time_left,
                            "end_date": None,  # Will calculate this from time_left
                            "location": {
                                "city": "Austin",  # Default location for Texas Facilities Commission
                                "state": "TX",
                                "zip_code": None
                            },
                            "category": self._determine_category(title),
                            "images": []
                        }
                        
                        # Calculate end date from time left
                        auction["end_date"] = self._calculate_end_date(time_left)
                        
                        # Add to auctions list
                        auctions.append(auction)
                        
                    except Exception as e:
                        self.logger.error(f"Error processing auction row: {e}")
                
                # Sleep to avoid overloading the server
                time.sleep(1)
            
            # Close the browser
            driver.quit()
            
        except Exception as e:
            self.logger.error(f"Error scraping {self.source_name}: {e}")
        
        self.logger.info(f"Completed scrape of {self.source_name}, found {len(auctions)} auctions")
        return auctions
    
    def _calculate_end_date(self, time_left):
        """
        Calculate end date from time left string
        Args:
            time_left (str): Time left string (e.g., "3 days 15 hours")
        Returns:
            str: ISO formatted end date or None if parsing fails
        """
        try:
            # Parse the time left string
            days = 0
            hours = 0
            minutes = 0
            
            if "days" in time_left or "day" in time_left:
                days_part = time_left.split("days" if "days" in time_left else "day")[0].strip()
                days = int(days_part)
                
                # Check if there are hours
                if "hours" in time_left or "hour" in time_left:
                    hours_part = time_left.split("hours" if "hours" in time_left else "hour")[0]
                    hours_part = hours_part.split("days" if "days" in time_left else "day")[1].strip()
                    hours = int(hours_part)
            elif "hours" in time_left or "hour" in time_left:
                hours_part = time_left.split("hours" if "hours" in time_left else "hour")[0].strip()
                hours = int(hours_part)
            
            # Check if there are minutes
            if "mins" in time_left or "min" in time_left:
                mins_part = time_left.split("mins" if "mins" in time_left else "min")[0]
                if "hours" in time_left or "hour" in time_left:
                    mins_part = mins_part.split("hours" if "hours" in time_left else "hour")[1].strip()
                minutes = int(mins_part)
            elif "mins" in time_left or "min" in time_left:
                mins_part = time_left.split("mins" if "mins" in time_left else "min")[0].strip()
                minutes = int(mins_part)
            
            # Calculate end date
            end_date = datetime.now() + timedelta(days=days, hours=hours, minutes=minutes)
            return end_date.isoformat()
            
        except Exception as e:
            self.logger.error(f"Error calculating end date from '{time_left}': {e}")
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
    scraper = PublicSurplusScraper()
    auctions = scraper.scrape()
    scraper.save_data(auctions)
