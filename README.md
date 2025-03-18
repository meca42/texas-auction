# Texas Auction Database - User Guide

## Overview

The Texas Auction Database is a comprehensive system that collects and organizes public auction data from across Texas. It allows you to:

1. View auctions sorted by end time (showing those ending soonest first)
2. Find auctions closest to your ZIP code (78232)
3. Browse detailed auction information including images and links to original listings

## System Components

The system consists of several components:

1. **Data Scrapers**: Collect auction data from multiple sources including:
   - Texas Facilities Commission (Public Surplus)
   - Gaston and Sheehan Auctioneers
   - GovDeals
   - And more...

2. **Database**: Stores auction information with relationships between:
   - Auction listings
   - Sources
   - Locations
   - Categories
   - Images

3. **Web Application**: Provides a user-friendly interface to browse and search auctions

## Getting Started

### Running the Application

To start the web application:

```bash
cd /home/ubuntu/auction_project
python3 run.py
```

This will start the web server on port 5000. You can access the application at:
http://localhost:5000

### Updating Auction Data

The system is configured to update auction data every 3 days. To manually update the data:

```bash
cd /home/ubuntu/auction_project
python3 import_data.py
```

## Using the Application

### Home Page

The home page provides an overview of the system and quick links to:
- Auctions ending soon
- Nearby auctions
- Information about data sources

### Viewing Auctions Ending Soon

Click on "Ending Soon" in the navigation bar to see auctions sorted by end date, with the soonest ending auctions first. This view helps you prioritize auctions that are closing soon.

### Finding Nearby Auctions

Click on "Nearby Auctions" to see auctions sorted by proximity to your ZIP code. By default, this uses ZIP code 78232, but you can change it using the form in the navigation bar.

To change your location:
1. Enter your ZIP code in the input field
2. Enter your desired maximum distance (in miles)
3. Click "Update"

### Viewing Auction Details

Click on "View Details" for any auction to see:
- Full description
- All available images
- End date and time
- Current price
- Location information
- Link to the original auction listing

## Technical Details

### Data Update Schedule

The system is configured to update auction data every 3 days as requested. This ensures you have current information while minimizing server load.

### Proximity Search

The proximity search feature uses geocoding to convert ZIP codes to coordinates and calculates distances using the Haversine formula. This provides accurate distance measurements between your location and auction locations.

### Database Schema

The database is designed with a normalized schema that supports:
- Efficient sorting by end time
- Fast proximity searches
- Relationships between auctions, sources, and locations
- Storage of multiple images per auction

## Troubleshooting

If you encounter any issues:

1. Check the log files:
   - `webapp.log` - Web application logs
   - `scraper.log` - Data scraper logs
   - `database.log` - Database operation logs

2. Ensure the database exists:
   - The database file should be at `/home/ubuntu/auction_project/database/texas_auctions.db`

3. Verify data has been imported:
   - Run `python3 test_database.py` to check database functionality

## Conclusion

The Texas Auction Database provides a powerful way to find and track public auctions across Texas. By organizing auctions by end time and proximity to your location, it helps you discover opportunities that might otherwise be missed.
