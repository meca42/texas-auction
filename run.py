"""
Run script for Texas Auction Database Web Application

This script runs the web application for the Texas Auction Database.
"""

import os
import sys
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import AuctionDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("webapp.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("webapp")

# Create Flask application
app = Flask(__name__)

@app.route('/')
def index():
    """
    Render the home page
    """
    return render_template('index.html')

@app.route('/auctions')
def auctions():
    """
    Render the auctions page with sorting by end time
    """
    page = request.args.get('page', 1, type=int)
    limit = 20
    offset = (page - 1) * limit
    
    db = AuctionDatabase()
    auctions_data = db.get_auctions_by_end_date(limit=limit, offset=offset)
    
    return render_template('auctions.html', 
                          auctions=auctions_data, 
                          page=page,
                          sort_by='end_time',
                          now=datetime.now().isoformat())

@app.route('/auctions/nearby')
def nearby_auctions():
    """
    Render the auctions page with sorting by proximity to ZIP code
    """
    page = request.args.get('page', 1, type=int)
    zip_code = request.args.get('zip_code', '78232')
    max_distance = request.args.get('max_distance', 100, type=int)
    limit = 20
    offset = (page - 1) * limit
    
    db = AuctionDatabase()
    auctions_data = db.get_auctions_by_proximity(
        zip_code=zip_code,
        max_distance=max_distance,
        limit=limit,
        offset=offset
    )
    
    return render_template('auctions.html', 
                          auctions=auctions_data, 
                          page=page,
                          zip_code=zip_code,
                          max_distance=max_distance,
                          sort_by='proximity',
                          now=datetime.now().isoformat())

@app.route('/auction/<int:auction_id>')
def auction_detail(auction_id):
    """
    Render the auction detail page
    """
    db = AuctionDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    # Get auction details
    cursor.execute(
        """
        SELECT a.*, s.name as source_name, c.name as category_name,
               l.city, l.state, l.zip_code, l.latitude, l.longitude
        FROM auctions a
        LEFT JOIN auction_sources s ON a.source_id = s.source_id
        LEFT JOIN auction_categories c ON a.category_id = c.category_id
        LEFT JOIN locations l ON a.location_id = l.location_id
        WHERE a.auction_id = ?
        """,
        (auction_id,)
    )
    
    auction = dict(cursor.fetchone())
    
    # Get images
    cursor.execute(
        "SELECT image_url FROM auction_images WHERE auction_id = ?",
        (auction_id,)
    )
    auction["images"] = [row["image_url"] for row in cursor.fetchall()]
    
    db.close()
    
    return render_template('auction_detail.html', auction=auction, now=datetime.now().isoformat())

@app.route('/api/auctions')
def api_auctions():
    """
    API endpoint to get auctions sorted by end time
    """
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    offset = (page - 1) * limit
    
    db = AuctionDatabase()
    auctions_data = db.get_auctions_by_end_date(limit=limit, offset=offset)
    
    return jsonify({
        'auctions': auctions_data,
        'page': page,
        'limit': limit
    })

@app.route('/api/auctions/nearby')
def api_nearby_auctions():
    """
    API endpoint to get auctions sorted by proximity to ZIP code
    """
    page = request.args.get('page', 1, type=int)
    zip_code = request.args.get('zip_code', '78232')
    max_distance = request.args.get('max_distance', 100, type=int)
    limit = request.args.get('limit', 20, type=int)
    offset = (page - 1) * limit
    
    db = AuctionDatabase()
    auctions_data = db.get_auctions_by_proximity(
        zip_code=zip_code,
        max_distance=max_distance,
        limit=limit,
        offset=offset
    )
    
    return jsonify({
        'auctions': auctions_data,
        'page': page,
        'limit': limit,
        'zip_code': zip_code,
        'max_distance': max_distance
    })

@app.route('/update-zip-code', methods=['POST'])
def update_zip_code():
    """
    Update the user's ZIP code preference
    """
    zip_code = request.form.get('zip_code')
    max_distance = request.form.get('max_distance', 100, type=int)
    
    if not zip_code:
        return redirect(url_for('index'))
    
    db = AuctionDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    # Update user preferences
    cursor.execute(
        """
        UPDATE user_preferences
        SET user_zip_code = ?, max_distance = ?, updated_at = CURRENT_TIMESTAMP
        WHERE preference_id = 1
        """,
        (zip_code, max_distance)
    )
    
    conn.commit()
    db.close()
    
    return redirect(url_for('nearby_auctions', zip_code=zip_code, max_distance=max_distance))

if __name__ == '__main__':
    # Run the Flask application
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
