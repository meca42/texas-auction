"""
Database Module for Texas Auction Database

This module handles database creation, connection, and data import
for the Texas Auction Database.
"""

import os
import json
import sqlite3
import logging
from datetime import datetime
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("database.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("database")

class AuctionDatabase:
    """Class to handle database operations for the Texas Auction Database"""
    
    def __init__(self, db_path=None):
        """
        Initialize the database
        
        Args:
            db_path (str, optional): Path to the database file. Defaults to None.
        """
        if db_path is None:
            # Use default path in project directory
            project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(project_dir, "database", "texas_auctions.db")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self.conn = None
        self.geocoder = Nominatim(user_agent="texas_auction_database")
        logger.info(f"Database initialized at {db_path}")
    
    def connect(self):
        """
        Connect to the database
        
        Returns:
            sqlite3.Connection: Database connection
        """
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            logger.info("Connected to database")
            return self.conn
        except sqlite3.Error as e:
            logger.error(f"Error connecting to database: {e}")
            raise
    
    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Database connection closed")
    
    def create_tables(self):
        """
        Create database tables according to the schema design
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            # Create auction_sources table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS auction_sources (
                source_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                website_url TEXT NOT NULL,
                description TEXT,
                logo_url TEXT,
                is_government BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Create locations table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS locations (
                location_id INTEGER PRIMARY KEY,
                address TEXT,
                city TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'TX',
                zip_code TEXT,
                latitude REAL,
                longitude REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Create auction_categories table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS auction_categories (
                category_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                parent_category_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_category_id) REFERENCES auction_categories(category_id)
            )
            ''')
            
            # Create auctions table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS auctions (
                auction_id INTEGER PRIMARY KEY,
                source_id INTEGER NOT NULL,
                external_id TEXT,
                title TEXT NOT NULL,
                description TEXT,
                start_date TIMESTAMP,
                end_date TIMESTAMP NOT NULL,
                current_price REAL,
                starting_price REAL,
                location_id INTEGER,
                category_id INTEGER,
                url TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES auction_sources(source_id),
                FOREIGN KEY (location_id) REFERENCES locations(location_id),
                FOREIGN KEY (category_id) REFERENCES auction_categories(category_id)
            )
            ''')
            
            # Create auction_images table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS auction_images (
                image_id INTEGER PRIMARY KEY,
                auction_id INTEGER NOT NULL,
                image_url TEXT NOT NULL,
                is_primary BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (auction_id) REFERENCES auctions(auction_id)
            )
            ''')
            
            # Create auction_details table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS auction_details (
                detail_id INTEGER PRIMARY KEY,
                auction_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (auction_id) REFERENCES auctions(auction_id)
            )
            ''')
            
            # Create user_preferences table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                preference_id INTEGER PRIMARY KEY,
                user_zip_code TEXT NOT NULL,
                max_distance INTEGER DEFAULT 100,
                preferred_categories TEXT,
                notification_enabled BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_auctions_end_date ON auctions(end_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_locations_coordinates ON locations(latitude, longitude)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_auctions_category ON auctions(category_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_auctions_source ON auctions(source_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_auctions_status ON auctions(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_auctions_status_end_date ON auctions(status, end_date)')
            
            # Note: SQLite doesn't support stored functions like PostgreSQL
            # We'll implement the distance calculation in Python instead
            logger.info("SQLite doesn't support stored functions, will calculate distances in Python")
            
            conn.commit()
            logger.info("Database tables created successfully")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error creating database tables: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            self.close()
    
    def geocode_location(self, location):
        """
        Geocode a location to get latitude and longitude
        
        Args:
            location (dict): Location dictionary with city, state, zip_code
            
        Returns:
            tuple: (latitude, longitude) or (None, None) if geocoding fails
        """
        try:
            # Build location string
            location_str = ""
            if location.get("city"):
                location_str += location["city"] + ", "
            if location.get("state"):
                location_str += location["state"] + " "
            if location.get("zip_code"):
                location_str += location["zip_code"]
            else:
                location_str += "USA"
            
            # Skip geocoding if we don't have enough information
            if not location.get("city") and not location.get("zip_code"):
                logger.warning(f"Insufficient location information for geocoding: {location_str}")
                return None, None
            
            # Try geocoding
            geo_location = self.geocoder.geocode(location_str)
            
            if geo_location:
                logger.info(f"Geocoded {location_str} to {geo_location.latitude}, {geo_location.longitude}")
                return geo_location.latitude, geo_location.longitude
            else:
                logger.warning(f"Could not geocode location: {location_str}")
                return None, None
                
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.error(f"Geocoding error for {location}: {e}")
            return None, None
    
    def import_data(self, json_file):
        """
        Import auction data from a JSON file
        
        Args:
            json_file (str): Path to the JSON file
            
        Returns:
            int: Number of auctions imported
        """
        try:
            # Load the JSON data
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            auctions = data.get("auctions", [])
            logger.info(f"Importing {len(auctions)} auctions from {json_file}")
            
            conn = self.connect()
            cursor = conn.cursor()
            
            # Insert default categories if they don't exist
            categories = {
                "vehicles": "Vehicles including cars, trucks, motorcycles, and other automotive items",
                "equipment": "Heavy equipment, machinery, and tools",
                "electronics": "Computers, phones, and other electronic devices",
                "furniture": "Office and home furniture",
                "real_estate": "Land, buildings, and property",
                "jewelry": "Jewelry, watches, and precious metals",
                "other": "Miscellaneous items"
            }
            
            category_ids = {}
            for name, description in categories.items():
                cursor.execute(
                    "INSERT OR IGNORE INTO auction_categories (name, description) VALUES (?, ?)",
                    (name, description)
                )
                cursor.execute("SELECT category_id FROM auction_categories WHERE name = ?", (name,))
                category_ids[name] = cursor.fetchone()[0]
            
            # Insert auction sources if they don't exist
            sources = {
                "public_surplus": {
                    "name": "Public Surplus - Texas Facilities Commission",
                    "website_url": "https://www.publicsurplus.com/sms/state,tx/list/current?orgid=871876",
                    "description": "Government surplus auctions from Texas Facilities Commission",
                    "is_government": True
                },
                "gaston_sheehan": {
                    "name": "Gaston and Sheehan Auctioneers",
                    "website_url": "https://www.txauction.com/",
                    "description": "Private auction house specializing in government and private auctions in Texas",
                    "is_government": False
                },
                "govdeals": {
                    "name": "GovDeals - Texas",
                    "website_url": "https://www.govdeals.com/texas",
                    "description": "Government surplus auctions from various Texas agencies",
                    "is_government": True
                }
            }
            
            source_ids = {}
            for source_key, source_data in sources.items():
                cursor.execute(
                    "INSERT OR IGNORE INTO auction_sources (name, website_url, description, is_government) VALUES (?, ?, ?, ?)",
                    (source_data["name"], source_data["website_url"], source_data["description"], source_data["is_government"])
                )
                cursor.execute("SELECT source_id FROM auction_sources WHERE name = ?", (source_data["name"],))
                source_ids[source_key] = cursor.fetchone()[0]
            
            # Process each auction
            imported_count = 0
            for auction in auctions:
                try:
                    # Get or create location
                    location_id = None
                    if auction.get("location"):
                        location = auction["location"]
                        
                        # Geocode the location if needed
                        if not location.get("latitude") or not location.get("longitude"):
                            latitude, longitude = self.geocode_location(location)
                            if latitude and longitude:
                                location["latitude"] = latitude
                                location["longitude"] = longitude
                        
                        # Insert location
                        cursor.execute(
                            "INSERT INTO locations (city, state, zip_code, latitude, longitude) VALUES (?, ?, ?, ?, ?)",
                            (
                                location.get("city"),
                                location.get("state", "TX"),
                                location.get("zip_code"),
                                location.get("latitude"),
                                location.get("longitude")
                            )
                        )
                        location_id = cursor.lastrowid
                    
                    # Get category ID
                    category = auction.get("category", "other")
                    category_id = category_ids.get(category, category_ids["other"])
                    
                    # Get source ID
                    source = auction.get("source_id", "other")
                    source_id = source_ids.get(source, 1)  # Default to first source if not found
                    
                    # Insert auction
                    cursor.execute(
                        """
                        INSERT INTO auctions 
                        (source_id, external_id, title, description, start_date, end_date, 
                        current_price, location_id, category_id, url, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            source_id,
                            auction.get("external_id"),
                            auction.get("title"),
                            auction.get("description"),
                            auction.get("start_date"),
                            auction.get("end_date"),
                            auction.get("current_price"),
                            location_id,
                            category_id,
                            auction.get("url"),
                            "active"
                        )
                    )
                    auction_id = cursor.lastrowid
                    
                    # Insert images
                    for image_url in auction.get("images", []):
                        if image_url:
                            cursor.execute(
                                "INSERT INTO auction_images (auction_id, image_url) VALUES (?, ?)",
                                (auction_id, image_url)
                            )
                    
                    imported_count += 1
                    
                except Exception as e:
                    logger.error(f"Error importing auction {auction.get('title')}: {e}")
                    continue
            
            # Set default user preferences for ZIP code 78232
            cursor.execute(
                "INSERT OR IGNORE INTO user_preferences (user_zip_code, max_distance) VALUES (?, ?)",
                ("78232", 100)
            )
            
            conn.commit()
            logger.info(f"Successfully imported {imported_count} auctions")
            return imported_count
            
        except Exception as e:
            logger.error(f"Error importing data from {json_file}: {e}")
            if conn:
                conn.rollback()
            return 0
        finally:
            self.close()
    
    def get_auctions_by_end_date(self, limit=100, offset=0):
        """
        Get auctions sorted by end date (soonest first)
        
        Args:
            limit (int, optional): Maximum number of auctions to return. Defaults to 100.
            offset (int, optional): Offset for pagination. Defaults to 0.
            
        Returns:
            list: List of auction dictionaries
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT a.*, s.name as source_name, c.name as category_name,
                       l.city, l.state, l.zip_code, l.latitude, l.longitude
                FROM auctions a
                LEFT JOIN auction_sources s ON a.source_id = s.source_id
                LEFT JOIN auction_categories c ON a.category_id = c.category_id
                LEFT JOIN locations l ON a.location_id = l.location_id
                WHERE a.status = 'active'
                ORDER BY a.end_date ASC
                LIMIT ? OFFSET ?
                """,
                (limit, offset)
            )
            
            auctions = []
            for row in cursor.fetchall():
                auction = dict(row)
                
                # Get images
                cursor.execute(
                    "SELECT image_url FROM auction_images WHERE auction_id = ?",
                    (auction["auction_id"],)
                )
                auction["images"] = [row["image_url"] for row in cursor.fetchall()]
                
                auctions.append(auction)
            
            logger.info(f"Retrieved {len(auctions)} auctions sorted by end date")
            return auctions
            
        except sqlite3.Error as e:
            logger.error(f"Error getting auctions by end date: {e}")
            return []
        finally:
            self.close()
    
    def get_auctions_by_proximity(self, zip_code="78232", max_distance=100, limit=100, offset=0):
        """
        Get auctions sorted by proximity to ZIP code
        
        Args:
            zip_code (str, optional): ZIP code to search from. Defaults to "78232".
            max_distance (int, optional): Maximum distance in miles. Defaults to 100.
            limit (int, optional): Maximum number of auctions to return. Defaults to 100.
            offset (int, optional): Offset for pagination. Defaults to 0.
            
        Returns:
            list: List of auction dictionaries with distance
        """
        try:
            # First, geocode the ZIP code
            zip_location = {"zip_code": zip_code, "state": "TX"}
            zip_lat, zip_lon = self.geocode_location(zip_location)
            
            if not zip_lat or not zip_lon:
                logger.error(f"Could not geocode ZIP code: {zip_code}")
                return []
            
            conn = self.connect()
            cursor = conn.cursor()
            
            # SQLite doesn't have built-in geospatial functions, so we'll calculate distance in Python
            cursor.execute(
                """
                SELECT a.*, s.name as source_name, c.name as category_name,
                       l.city, l.state, l.zip_code, l.latitude, l.longitude
                FROM auctions a
                LEFT JOIN auction_sources s ON a.source_id = s.source_id
                LEFT JOIN auction_categories c ON a.category_id = c.category_id
                LEFT JOIN locations l ON a.location_id = l.location_id
                WHERE a.status = 'active' AND l.latitude IS NOT NULL AND l.longitude IS NOT NULL
                """
            )
            
            auctions = []
            for row in cursor.fetchall():
                auction = dict(row)
                
                # Calculate distance
                if auction["latitude"] and auction["longitude"]:
                    # Use Haversine formula to calculate distance
                    from math import radians, cos, sin, asin, sqrt
                    
                    def haversine(lat1, lon1, lat2, lon2):
                        # Convert decimal degrees to radians
                        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
                        
                        # Haversine formula
                        dlon = lon2 - lon1
                        dlat = lat2 - lat1
                        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                        c = 2 * asin(sqrt(a))
                        r = 3958.8  # Radius of earth in miles
                        return c * r
                    
                    distance = haversine(zip_lat, zip_lon, auction["latitude"], auction["longitude"])
                    auction["distance"] = round(distance, 2)
                    
                    # Only include auctions within max_distance
                    if distance <= max_distance:
                        # Get images
                        cursor.execute(
                            "SELECT image_url FROM auction_images WHERE auction_id = ?",
                            (auction["auction_id"],)
                        )
                        auction["images"] = [row["image_url"] for row in cursor.fetchall()]
                        
                        auctions.append(auction)
            
            # Sort by distance and apply limit/offset
            auctions.sort(key=lambda x: x.get("distance", float('inf')))
            paginated_auctions = auctions[offset:offset+limit]
            
            logger.info(f"Retrieved {len(paginated_auctions)} auctions sorted by proximity to {zip_code}")
            return paginated_auctions
            
        except Exception as e:
            logger.error(f"Error getting auctions by proximity: {e}")
            return []
        finally:
            self.close()


if __name__ == "__main__":
    # Create and initialize the database if this file is executed directly
    db = AuctionDatabase()
    db.create_tables()
    print("Database created successfully")
