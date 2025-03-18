#!/usr/bin/env python3

import sys
import os
from database.database import AuctionDatabase

def test_end_time_sorting():
    """Test sorting auctions by end time"""
    print("Testing sorting by end time...")
    db = AuctionDatabase()
    auctions = db.get_auctions_by_end_date(limit=5)
    print(f"Found {len(auctions)} auctions sorted by end date")
    for a in auctions:
        print(f"- {a['title']} (Ends: {a['end_date'][:10]})")
    print()

def test_proximity_search():
    """Test proximity search by ZIP code"""
    print("Testing proximity search by ZIP code...")
    db = AuctionDatabase()
    
    # Test with default ZIP code (78232)
    auctions = db.get_auctions_by_proximity(zip_code="78232", max_distance=100, limit=5)
    print(f"Found {len(auctions)} auctions near ZIP 78232 (within 100 miles)")
    for a in auctions:
        print(f"- {a['title']} (Distance: {a.get('distance', 'unknown')} miles)")
    print()
    
    # Test with another ZIP code
    auctions = db.get_auctions_by_proximity(zip_code="77002", max_distance=50, limit=5)
    print(f"Found {len(auctions)} auctions near ZIP 77002 (within 50 miles)")
    for a in auctions:
        print(f"- {a['title']} (Distance: {a.get('distance', 'unknown')} miles)")
    print()

if __name__ == "__main__":
    test_end_time_sorting()
    test_proximity_search()
