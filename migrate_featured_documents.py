"""
Migration script to add featured document columns to the Document table
This adds:
- is_featured (boolean flag for featured documents on homepage)
- featured_at (timestamp when the document was marked as featured)
"""
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
import logging
from models import db

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_migration():
    """Add featured document columns to the Document table"""
    try:
        engine = db.engine
        
        # Check if columns already exist
        inspector = db.inspect(engine)
        columns = inspector.get_columns('document')
        column_names = [col['name'] for col in columns]
        
        # Add is_featured column if it doesn't exist
        if 'is_featured' not in column_names:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE document ADD COLUMN is_featured BOOLEAN DEFAULT FALSE"))
                conn.commit()
                logging.info("Added is_featured column to document table")
        else:
            logging.info("is_featured column already exists in document table")
        
        # Add featured_at column if it doesn't exist
        if 'featured_at' not in column_names:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE document ADD COLUMN featured_at TIMESTAMP"))
                conn.commit()
                logging.info("Added featured_at column to document table")
        else:
            logging.info("featured_at column already exists in document table")
            
        return True
    except SQLAlchemyError as e:
        logging.error(f"Error running featured documents migration: {str(e)}")
        return False