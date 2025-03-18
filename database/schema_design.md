# Database Schema Design for Texas Auction Database

## Overview
This document outlines the database schema design for the Texas Public Auction Database. The schema is designed to support the following key requirements:
- Store auction data from multiple sources across Texas
- Enable sorting by auction end time
- Support proximity search based on user's ZIP code (78232)
- Maintain relationships between auctions, sources, and locations

## Database Type
For this application, we recommend using SQLite for development and PostgreSQL for production due to:
- PostgreSQL's robust spatial query capabilities (PostGIS extension)
- SQLite's simplicity for development and testing
- Both support the required indexing for time-based and location-based queries

## Schema Design

### Tables

#### 1. auction_sources
Stores information about the auction platforms and websites.

```sql
CREATE TABLE auction_sources (
    source_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    website_url TEXT NOT NULL,
    description TEXT,
    logo_url TEXT,
    is_government BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2. locations
Stores location information for auctions and facilitates proximity searches.

```sql
CREATE TABLE locations (
    location_id INTEGER PRIMARY KEY,
    address TEXT,
    city TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'TX',
    zip_code TEXT,
    latitude REAL,
    longitude REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3. auction_categories
Categorizes auctions for better filtering and organization.

```sql
CREATE TABLE auction_categories (
    category_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    parent_category_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_category_id) REFERENCES auction_categories(category_id)
);
```

#### 4. auctions
The main table storing auction listings with all relevant details.

```sql
CREATE TABLE auctions (
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
);
```

#### 5. auction_images
Stores image URLs associated with auctions.

```sql
CREATE TABLE auction_images (
    image_id INTEGER PRIMARY KEY,
    auction_id INTEGER NOT NULL,
    image_url TEXT NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (auction_id) REFERENCES auctions(auction_id)
);
```

#### 6. auction_details
Stores additional details specific to certain auction types (vehicles, real estate, etc.).

```sql
CREATE TABLE auction_details (
    detail_id INTEGER PRIMARY KEY,
    auction_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (auction_id) REFERENCES auctions(auction_id)
);
```

#### 7. user_preferences
Stores user preferences for notifications and saved searches.

```sql
CREATE TABLE user_preferences (
    preference_id INTEGER PRIMARY KEY,
    user_zip_code TEXT NOT NULL,
    max_distance INTEGER DEFAULT 100,
    preferred_categories TEXT,
    notification_enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Indexes

To optimize the database for the required sorting and proximity search capabilities:

```sql
-- Index for sorting by end date
CREATE INDEX idx_auctions_end_date ON auctions(end_date);

-- Index for location-based queries
CREATE INDEX idx_locations_coordinates ON locations(latitude, longitude);

-- Index for filtering by category
CREATE INDEX idx_auctions_category ON auctions(category_id);

-- Index for filtering by source
CREATE INDEX idx_auctions_source ON auctions(source_id);

-- Index for status filtering
CREATE INDEX idx_auctions_status ON auctions(status);

-- Composite index for common queries
CREATE INDEX idx_auctions_status_end_date ON auctions(status, end_date);
```

## Proximity Search Implementation

For proximity search based on ZIP code 78232, we'll implement the following approach:

1. Store the latitude and longitude coordinates for each auction location
2. Use the Haversine formula to calculate distances between the user's location and auction locations
3. Create a function to convert ZIP codes to coordinates using a ZIP code database or geocoding API
4. Implement a query that sorts results by distance from the user's location

Example query (PostgreSQL with PostGIS extension):

```sql
-- Function to calculate distance between two points
CREATE OR REPLACE FUNCTION calculate_distance(lat1 REAL, lon1 REAL, lat2 REAL, lon2 REAL) 
RETURNS REAL AS $$
DECLARE
    R REAL := 3958.8; -- Earth radius in miles
    dLat REAL := radians(lat2 - lat1);
    dLon REAL := radians(lon2 - lon1);
    a REAL;
    c REAL;
    d REAL;
BEGIN
    a := sin(dLat/2) * sin(dLat/2) + cos(radians(lat1)) * cos(radians(lat2)) * sin(dLon/2) * sin(dLon/2);
    c := 2 * atan2(sqrt(a), sqrt(1-a));
    d := R * c;
    RETURN d;
END;
$$ LANGUAGE plpgsql;

-- Query to find auctions sorted by proximity to ZIP code 78232
-- (assuming we've already converted ZIP 78232 to lat/lon coordinates)
SELECT 
    a.auction_id, 
    a.title, 
    a.end_date, 
    a.current_price,
    calculate_distance(l.latitude, l.longitude, 29.5794, -98.4982) AS distance
FROM 
    auctions a
JOIN 
    locations l ON a.location_id = l.location_id
WHERE 
    a.status = 'active'
ORDER BY 
    distance ASC, a.end_date ASC;
```

## Data Migration Strategy

To populate this database from the scraped data:

1. First populate the `auction_sources` table with information about each source
2. For each auction listing:
   - Extract location information and store in the `locations` table
   - Determine the appropriate category and store in `auction_categories`
   - Store the main auction details in the `auctions` table
   - Store images in the `auction_images` table
   - Store additional details in the `auction_details` table

## Maintenance Considerations

1. **Regular Updates**: The database should be updated daily to reflect new auctions and changes in existing ones
2. **Data Cleanup**: Implement a process to archive or remove ended auctions after a certain period
3. **Geocoding Cache**: Maintain a cache of ZIP code to coordinate mappings to reduce API calls
4. **Index Optimization**: Periodically analyze query performance and optimize indexes as needed

This schema design provides a solid foundation for the Texas Auction Database, supporting the key requirements of sorting by end time and proximity to ZIP code 78232 while maintaining flexibility for future enhancements.
