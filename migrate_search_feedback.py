"""
Migration script to add the SearchFeedback table to the database
"""
import sys
from datetime import datetime
import logging
from flask import Flask
from models import db, SearchFeedback
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Add SearchFeedback table to the database"""
    logger.info("Starting search feedback migration...")
    app = Flask(__name__)
    
    # Configure the database
    app.config['SQLALCHEMY_DATABASE_URI'] = sys.argv[1] if len(sys.argv) > 1 else 'sqlite:///insights.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    with app.app_context():
        # Check if the SearchFeedback table already exists
        inspector = inspect(db.engine)
        table_exists = inspector.has_table('search_feedback')
        
        if table_exists:
            logger.info("SearchFeedback table already exists. Migration not needed.")
            return
        
        logger.info("Creating SearchFeedback table...")
        db.create_all()
        logger.info("SearchFeedback table created successfully.")
        
        logger.info("Search feedback migration completed successfully.")

def inspect_from_engine(engine: Engine) -> any:
    """Get inspector from engine"""
    return inspect(engine)

if __name__ == "__main__":
    run_migration()