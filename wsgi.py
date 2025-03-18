"""
WSGI entry point for Texas Auction Database Web Application

This module provides the WSGI entry point for the web application.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from run import app

if __name__ == "__main__":
    app.run()
