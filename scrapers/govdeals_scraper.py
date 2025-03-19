""" GovDeals Scraper for Texas Auction Database
This module implements a scraper for the GovDeals website, specifically for Texas auctions.
"""
import time
import requests
from bs4 import BeautifulSoup
import logging
import re
import os
from datetime import datetime

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

class GovDealsScraper(BaseScraper):
    """Scraper for GovDeals website"""
    
    def __init__(self):
        """Initialize the GovDeals scraper"""
        super().__init__(
            source_name="GovDeals - Texas",
            source_url="https://www.govdeals.com/index.cfm?fa=Main.AdvSearchResultsNew&searchPg=Classic&inv_num=&category=00&kWord=&kWordSelect=2&sortBy=ad&agency=0&state=TX&country=&locID=&timing=bySimple&locationType=state&timeType=&timingWithin=1"
        )
        self.logger = logging.getLogger("scraper.govdeals")
    
    def scrape(self):
        """ Scrape auction data from GovDeals
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
            # Make request to GovDeals website
            response = requests.get(self.source_url)
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch GovDeals website: {response.status_code}")
                return auctions
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all auction listings
            auction_listings = soup.select('.auction-item')
            if not auction_listings:
                # Try alternative selector if the first one doesn't work
                auction_listings = soup.select('.listing')
            
            self.logger.info(f"Found {len(auction_listings)} auction listings")
            
            # Process each auction listing
            for listing in auction_listings:
                try:
                    # Extract auction data
                    title_element = listing.select_one('.listing-title a, .item-title a')
                    if not title_element:
                        continue
                    
                    title = title_element.text.strip()
                    url = title_element.get('href')
                    if not url.startswith('http'):
                        url = f"https://www.govdeals.com{url}"
                    
                    # Extract auction ID from URL
                    auction_id = None
                    id_match = re.search(r'index=(\d+)', url)
                    if id_match:
                        auction_id = f"govdeals_{id_match.group(1)}"
                    else:
                        auction_id = f"govdeals_{int(time.time())}"
                    
                    # Extract current price
                    current_price = None
                    price_element = listing.select_one('.listing-bid, .current-bid')
                    if price_element:
                        price_text = price_element.text.strip()
                        current_price = self.clean_price(price_text)
                    
                    # Extract end date
                    end_date = None
                    date_element = listing.select_one('.listing-time, .end-time')
                    if date_element:
                        date_text = date_element.text.strip()
                        end_date = self._parse_end_date(date_text)
                    
                    # Extract location
                    location = {"city": None, "state": "TX", "zip_code": None}
                    location_element = listing.select_one('.listing-location, .item-location')
                    if location_element:
                        location_text = location_element.text.strip()
                        location = self.extract_location(location_text)
                    
                    # Extract image URL
                    image_url = None
                    image_element = listing.select_one('.listing-image img, .item-image img')
                    if image_element:
                        image_url = image_element.get('src')
                        if not image_url.startswith('http'):
                            image_url = f"https://www.govdeals.com{image_url}"
                    
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
            
            # Process additional pages (up to 5)
            page_num = 2
            while page_num <= 5:
                try:
                    # Find next page link
                    next_page_url = None
                    next_page_element = soup.select_one('.pagination .next a')
                    if next_page_element:
                        next_page_url = next_page_element.get('href')
                        if not next_page_url.startswith('http'):
                            next_page_url = f"https://www.govdeals.com{next_page_url}"
                    
                    if not next_page_url:
                        break
                    
                    # Request next page
                    response = requests.get(next_page_url)
                    if response.status_code != 200:
                        break
                    
                    # Parse HTML
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Find all auction listings
                    auction_listings = soup.select('.auction-item')
                    if not auction_listings:
                        auction_listings = soup.select('.listing')
                    
                    self.logger.info(f"Found {len(auction_listings)} auction listings on page {page_num}")
                    
                    # Process each auction listing (same code as above)
                    for listing in auction_listings:
                        try:
                            # Extract auction data
                            title_element = listing.select_one('.listing-title a, .item-title a')
                            if not title_element:
                                continue
                            
                            title = title_element.text.strip()
                            url = title_element.get('href')
                            if not url.startswith('http'):
                                url = f"https://www.govdeals.com{url}"
                            
                            # Extract auction ID from URL
                            auction_id = None
                            id_match = re.search(r'index=(\d+)', url)
                            if id_match:
                                auction_id = f"govdeals_{id_match.group(1)}"
                            else:
                                auction_id = f"govdeals_{int(time.time())}"
                            
                            # Extract current price
                            current_price = None
                            price_element = listing.select_one('.listing-bid, .current-bid')
                            if price_element:
                                price_text = price_element.text.strip()
                                current_price = self.clean_price(price_text)
                            
                            # Extract end date
                            end_date = None
                            date_element = listing.select_one('.listing-time, .end-time')
                            if date_element:
                                date_text = date_element.text.strip()
                                end_date = self._parse_end_date(date_text)
                            
                            # Extract location
                            location = {"city": None, "state": "TX", "zip_code": None}
                            location_element = listing.select_one('.listing-location, .item-location')
                            if location_element:
                                location_text = location_element.text.strip()
                                location = self.extract_location(location_text)
                            
                            # Extract image URL
                            image_url = None
                            image_element = listing.select_one('.listing-image img, .item-image img')
                            if image_element:
                                image_url = image_element.get('src')
                                if not image_url.startswith('http'):
                                    image_url = f"https://www.govdeals.com{image_url}"
                            
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
                    
                    page_num += 1
                    
                except Exception as e:
                    self.logger.error(f"Error processing page {page_num}: {e}")
                    break
            
        except Exception as e:
            self.logger.error(f"Error scraping GovDeals: {e}")
        
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
                    
                    # Find next page button for the next iteration
                    try:
                        next_page = driver.find_element(By.CSS_SELECTOR, ".pagination .next a")
                        page_num += 1
                    except:
                        has_next_page = False
                
            except Exception as e:
                self.logger.error(f"Error navigating to additional pages: {e}")
            
            # Close the browser
            driver.quit()
            
        except Exception as e:
            self.logger.error(f"Error scraping GovDeals: {e}")
        
        self.logger.info(f"Completed scrape of {self.source_name}, found {len(auctions)} auctions")
        return auctions
    
    def _parse_end_date(self, date_text):
        """Parse end date from text"""
        try:
            # Try different date formats
            date_formats = [
                "%m/%d/%Y %I:%M:%S %p",
                "%m/%d/%Y %I:%M %p",
                "%m/%d/%y %I:%M:%S %p",
                "%m/%d/%y %I:%M %p",
                "%B %d, %Y %I:%M:%S %p",
                "%B %d, %Y %I:%M %p"
            ]
            
            for date_format in date_formats:
                try:
                    return datetime.strptime(date_text, date_format).isoformat()
                except:
                    continue
            
            # If none of the formats match, try to extract date and time parts
            date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})', date_text)
            time_match = re.search(r'(\d{1,2}:\d{2}(:\d{2})?\s*[APap][Mm])', date_text)
            
            if date_match and time_match:
                date_part = date_match.group(1)
                time_part = time_match.group(1)
                
                # Try to parse combined date and time
                try:
                    return datetime.strptime(f"{date_part} {time_part}", "%m/%d/%Y %I:%M %p").isoformat()
                except:
                    try:
                        return datetime.strptime(f"{date_part} {time_part}", "%m/%d/%y %I:%M %p").isoformat()
                    except:
                        pass
            
            self.logger.warning(f"Could not parse date: {date_text}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error parsing date '{date_text}': {e}")
            return None
    
    def extract_location(self, location_text):
        """Extract location information from text"""
        location = {"city": None, "state": "TX", "zip_code": None}
        
        try:
            # Try to extract city and zip code
            city_match = re.search(r'([A-Za-z\s.]+),?\s*TX', location_text)
            if city_match:
                location["city"] = city_match.group(1).strip()
            
            zip_match = re.search(r'(\d{5}(-\d{4})?)', location_text)
            if zip_match:
                location["zip_code"] = zip_match.group(1)
            
        except Exception as e:
            self.logger.error(f"Error extracting location from '{location_text}': {e}")
        
        return location
    
    def _determine_category(self, title):
        """Determine category based on title"""
        title_lower = title.lower()
        
        # Define category keywords
        categories = {
            "vehicle": ["car", "truck", "van", "suv", "vehicle", "auto", "ford", "chevy", "toyota", "honda"],
            "electronics": ["computer", "laptop", "monitor", "printer", "phone", "camera", "tv", "television"],
            "furniture": ["desk", "chair", "table", "cabinet", "furniture", "shelf", "bookcase"],
            "equipment": ["equipment", "machinery", "tool", "generator", "mower", "tractor"],
            "jewelry": ["jewelry", "watch", "ring", "necklace", "bracelet"],
            "clothing": ["clothing", "shirt", "pants", "jacket", "uniform"],
            "office": ["office", "supplies", "paper", "stapler", "copier"]
        }
        
        # Check for category matches
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in title_lower:
                    return category
        
        # Default category
        return "other"
