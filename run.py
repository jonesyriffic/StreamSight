"""
Custom server runner script for handling large file uploads
This script uses Werkzeug's development server with increased
request size limits.
"""

import os
import logging
from main import app  # Import the Flask app

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Configure the server for large uploads
    logger.info("Starting server with large file upload support (100MB limit)")
    
    # Set environment variable for maximum content length
    os.environ['WERKZEUG_SERVER_MAX_CONTENT_LENGTH'] = str(100 * 1024 * 1024)  # 100MB
    
    # Run the app with increased request body size
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )