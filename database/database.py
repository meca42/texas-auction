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
import psycopg2
from psycopg2.extras import DictCursor
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

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
    
    def __init__(self, db_url=None):
        """
        Initialize the database
        
        Args:
            db_url (str, optional): Database URL. Defaults to None (uses DATABASE_URL env var).
        """
        if db_url is None:
            # Use environment variable
            db_url = os.getenv('DATABASE_URL')
            
            # If no environment variable, use default SQLite path
            if not db_url:
                project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                db_path = os.path.join(project_dir, "database", "texas_auctions.db")
                db_url = f"sqlite:///{db_path}"
                
                # Ensure directory exists for SQLite
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_url = db_url
        self.conn = None
        self.db_type = 'sqlite' if db_url.startswith('sqlite') else 'postgresql'
        self.geocoder = Nominatim(user_agent="texas_auction_database")
        logger.info(f"Database initialized with {self.db_type} at {db_url}")
    
    def connect(self):
        """
        Connect to the database
        
        Returns:
            Connection: Database connection
        """
        try:
            if self.db_type == 'sqlite':
                # Extract path from sqlite:/// URL format
                db_path = self.db_url.replace('sqlite:///', '')
                self.conn = sqlite3.connect(db_path)
                self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            else:
                # Connect to PostgreSQL
                self.conn = psycopg2.connect(self.db_url)
                self.conn.cursor_factory = DictCursor  # Return rows as dictionaries
                
            logger.info(f"Connected to {self.db_type} database")
            return self.conn
        except (sqlite3.Error, psycopg2.Error) as e:
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
                source_id SERIAL PRIMARY KEY,
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
                location_id SERIAL PRIMARY KEY,
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
                category_id SERIAL PRIMARY KEY,
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
                auction_id SERIAL PRIMARY KEY,
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
                image_id SERIAL PRIMARY KEY,
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
                detail_id SERIAL PRIMARY KEY,
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
                preference_id SERIAL PRIMARY KEY,
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
            
            conn.commit()
            logger.info("Database tables created successfully")
            return True
            
        except (sqlite3.Error, psycopg2.Error) as e:
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
            logger.error(f"Geocoding error: {e}")
            return None, None
    
    def get_auctions_by_end_date(self, limit=20, offset=0):
        """
        Get auctions sorted by end date
        
        Args:
            limit (int, optional): Number of auctions to return. Defaults to 20.
            offset (int, optional): Offset for pagination. Defaults to 0.
            
        Returns:
            list: List of auction dictionaries
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            query = """
            SELECT a.*, s.name as source_name, c.name as category_name,
                   l.city, l.state, l.zip_code
            FROM auctions a
            LEFT JOIN auction_sources s ON a.source_id = s.source_id
            LEFT JOIN auction_categories c ON a.category_id = c.category_id
            LEFT JOIN locations l ON a.location_id = l.location_id
            WHERE a.status = 'active' AND a.end_date > CURRENT_TIMESTAMP
            ORDER BY a.end_date ASC
            LIMIT ? OFFSET ?
            """
            
            # PostgreSQL uses different parameter placeholders
            if self.db_type == 'postgresql':
                query = query.replace('?', '%s')
                
            cursor.execute(query, (limit, offset))
            
            if self.db_type == 'sqlite':
                auctions = [dict(row) for row in cursor.fetchall()]
            else:
                auctions = [dict(row) for row in cursor.fetchall()]
                
            return auctions
            
        except (sqlite3.Error, psycopg2.Error) as e:
            logger.error(f"Error getting auctions by end date: {e}")
            return []
        finally:
            self.close()
    
    def get_auctions_by_proximity(self, zip_code, max_distance=100, limit=20, offset=0):
        """
        Get auctions sorted by proximity to ZIP code
        
        Args:
            zip_code (str): ZIP code to search near
            max_distance (int, optional): Maximum distance in miles. Defaults to 100.
            limit (int, optional): Number of auctions to return. Defaults to 20.
            offset (int, optional): Offset for pagination. Defaults to 0.
            
        Returns:
            list: List of auction dictionaries
        """
        try:
            # First, geocode the ZIP code
            location = {"zip_code": zip_code}
            user_lat, user_lon = self.geocode_location(location)
            
            if not user_lat or not user_lon:
                logger.warning(f"Could not geocode ZIP code: {zip_code}")
                return []
            
            conn = self.connect()
            cursor = conn.cursor()
            
            # Get all auctions with locations
            cursor.execute(
                """
                SELECT a.*, s.name as source_name, c.name as category_name,
                       l.city, l.state, l.zip_code, l.latitude, l.longitude
                FROM auctions a
                LEFT JOIN auction_sources s ON a.source_id = s.source_id
                LEFT JOIN auction_categories c ON a.category_id = c.category_id
                LEFT JOIN locations l ON a.location_id = l.location_id
                WHERE a.status = 'active' AND a.end_date > CURRENT_TIMESTAMP
                  AND l.latitude IS NOT NULL AND l.longitude IS NOT NULL
                """
            )
            
            if self.db_type == 'sqlite':
                auctions = [dict(row) for row in cursor.fetchall()]
            else:
                auctions = [dict(row) for row in cursor.fetchall()]
            
            # Calculate distance for each auction
            for auction in auctions:
                auction_lat = auction.get("latitude")
                auction_lon = auction.get("longitude")
                
                if auction_lat and auction_lon:
                    # Calculate distance using Haversine formula
                    distance = self._calculate_distance(
                        user_lat, user_lon, auction_lat, auction_lon
                    )
                    auction["distance"] = distance
                else:
                    auction["distance"] = float('inf')
            
            # Filter by max distance
            auctions = [a for a in auctions if a["distance"] <= max_distance]
            
            # Sort by distance
            auctions.sort(key=lambda x: x["distance"])
            
            # Apply pagination
            paginated_auctions = auctions[offset:offset+limit]
            
            return paginated_auctions
            
        except (sqlite3.Error, psycopg2.Error) as e:
            logger.error(f"Error getting auctions by proximity: {e}")
            return []
        finally:
            self.close()
    
    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """
        Calculate distance between two points using Haversine formula
        
        Args:
            lat1 (float): Latitude of point 1
            lon1 (float): Longitude of point 1
            lat2 (float): Latitude of point 2
            lon2 (float): Longitude of point 2
            
        Returns:
            float: Distance in miles
        """
        from math import radians, cos, sin, asin, sqrt
        
        # Convert decimal degrees to radians
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        
        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 3956  # Radius of earth in miles
        
        return c * r
    
    def import_data(self, data_file):
        """
        Import data from JSON file into database
        
        Args:
            data_file (str): Path to JSON data file
            
        Returns:
            int: Number of auctions imported
        """
        try:
            # Load data from file
            with open(data_file, 'r') as f:
                data = json.load(f)
            
            conn = self.connect()
            cursor = conn.cursor()
            
            # Import auction sources
            for source in data.get("sources", []):
                # Check if source already exists
                cursor.execute(
                    "SELECT source_id FROM auction_sources WHERE name = ?",
                    (source["name"],)
                )
                result = cursor.fetchone()
                
                if result:
                    source_id = result[0]
                else:
                    # Insert new source
                    cursor.execute(
                        """
                        INSERT INTO auction_sources (name, website_url, description, logo_url, is_government)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            source["name"],
                            source["website_url"],
                            source.get("description", ""),
                            source.get("logo_url", ""),
                            source.get("is_government", False)
                        )
                    )
                    
                    if self.db_type == 'sqlite':
                        source_id = cursor.lastrowid
                    else:
                        cursor.execute("SELECT lastval()")
                        source_id = cursor.fetchone()[0]
                
                source["source_id"] = source_id
            
            # Import categories
            for category in data.get("categories", []):
                # Check if category already exists
                cursor.execute(
                    "SELECT category_id FROM auction_categories WHERE name = ?",
                    (category["name"],)
                )
                result = cursor.fetchone()
                
                if result:
                    category_id = result[0]
                else:
                    # Insert new category
                    cursor.execute(
                        """
                        INSERT INTO auction_categories (name, description, parent_category_id)
                        VALUES (?, ?, ?)
                        """,
                        (
                            category["name"],
                            category.get("description", ""),
                            category.get("parent_category_id")
                        )
                    )
                    
                    if self.db_type == 'sqlite':
                        category_id = cursor.lastrowid
                    else:
                        cursor.execute("SELECT lastval()")
                        category_id = cursor.fetchone()[0]
                
                category["category_id"] = category_id
            
            # Import auctions
            imported_count = 0
            for auction in data.get("auctions", []):
                # Get or create location
                location_id = None
                if "location" in auction:
                    location = auction["location"]
                    
                    # Geocode location if needed
                    if "latitude" not in location or "longitude" not in location:
                        lat, lon = self.geocode_location(location)
                        if lat and lon:
                            location["latitude"] = lat
                            location["longitude"] = lon
                    
                    # Check if location already exists
                    cursor.execute(
                        """
                        SELECT location_id FROM locations
                        WHERE city = ? AND state = ? AND zip_code = ?
                        """,
                        (
                            location.get("city", ""),
                            location.get("state", "TX"),
                            location.get("zip_code", "")
                        )
                    )
                    result = cursor.fetchone()
                    
                    if result:
                        location_id = result[0]
                    else:
                        # Insert new location
                        cursor.execute(
                            """
                            INSERT INTO locations (address, city, state, zip_code, latitude, longitude)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                location.get("address", ""),
                                location.get("city", ""),
                                location.get("state", "TX"),
                                location.get("zip_code", ""),
                                location.get("latitude"),
                                location.get("longitude")
                            )
                        )
                        
                        if self.db_type == 'sqlite':
                            location_id = cursor.lastrowid
                        else:
                            cursor.execute("SELECT lastval()")
                            location_id = cursor.fetchone()[0]
                
                # Check if auction already exists
                cursor.execute(
                    """
                    SELECT auction_id FROM auctions
                    WHERE source_id = ? AND external_id = ?
                    """,
                    (
                        auction["source_id"],
                        auction.get("external_id", "")
                    )
                )
                result = cursor.fetchone()
                
                if result:
                    auction_id = result[0]
                    
                    # Update existing auction
                    cursor.execute(
                        """
                        UPDATE auctions
                        SET title = ?, description = ?, start_date = ?, end_date = ?,
                            current_price = ?, starting_price = ?, location_id = ?,
                            category_id = ?, url = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE auction_id = ?
                        """,
                        (
                            auction["title"],
                            auction.get("description", ""),
                            auction.get("start_date"),
                            auction["end_date"],
                            auction.get("current_price"),
                            auction.get("starting_price"),
                            location_id,
                            auction.get("category_id"),
                            auction["url"],
                            auction.get("status", "active"),
                            auction_id
                        )
                    )
                else:
                    # Insert new auction
                    cursor.execute(
                        """
                        INSERT INTO auctions (
                            source_id, external_id, title, description, start_date,
                            end_date, current_price, starting_price, location_id,
                            category_id, url, status
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            auction["source_id"],
                            auction.get("external_id", ""),
                            auction["title"],
                            auction.get("description", ""),
                            auction.get("start_date"),
                            auction["end_date"],
                            auction.get("current_price"),
                            auction.get("starting_price"),
                            location_id,
                            auction.get("category_id"),
                            auction["url"],
                            auction.get("status", "active")
                        )
                    )
                    
                    if self.db_type == 'sqlite':
                        auction_id = cursor.lastrowid
                    else:
                        cursor.execute("SELECT lastval()")
                        auction_id = cursor.fetchone()[0]
                    
                    imported_count += 1
                
                # Import images
                if "images" in auction:
                    for image in auction["images"]:
                        cursor.execute(
                            """
                            INSERT INTO auction_images (auction_id, image_url, is_primary)
                            VALUES (?, ?, ?)
                            """,
                            (
                                auction_id,
                                image["url"],
                                image.get("is_primary", False)
                            )
                        )
                
                # Import details
                if "details" in auction:
                    for key, value in auction["details"].items():
                        cursor.execute(
                            """
                            INSERT INTO auction_details (auction_id, key, value)
                            VALUES (?, ?, ?)
                            """,
                            (
                                auction_id,
                                key,
                                str(value)
                            )
                        )
            
            conn.commit()
            logger.info(f"Imported {imported_count} new auctions")
            return imported_count
            
        except (sqlite3.Error, psycopg2.Error, json.JSONDecodeError) as e:
            logger.error(f"Error importing data: {e}")
            if conn:
                conn.rollback()
            return 0
        finally:
            self.close()
