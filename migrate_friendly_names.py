"""
Migration script to add friendly_name column to the Document table
"""
import os
import sys
import logging
from sqlalchemy import create_engine, Column, String
from sqlalchemy.sql import text
from models import Document, db
from utils.document_ai import generate_friendly_name

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_migration():
    """Add friendly_name column to the Document table and generate friendly names for existing documents"""
    try:
        # Get database URL from environment variable
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            logging.error("DATABASE_URL environment variable not set")
            return False
        
        # Create database engine
        engine = create_engine(database_url)
        
        # Add the column if it doesn't already exist
        with engine.connect() as conn:
            # Check if column exists
            result = conn.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                "WHERE table_name='document' AND column_name='friendly_name');"
            ))
            column_exists = result.fetchone()[0]
            
            if not column_exists:
                logging.info("Adding friendly_name column to document table")
                conn.execute(text(
                    "ALTER TABLE document ADD COLUMN friendly_name VARCHAR(255);"
                ))
                logging.info("Column added successfully")
            else:
                logging.info("friendly_name column already exists")
        
        # Import the Flask app to get the app context
        from main import app
        
        # Generate friendly names for all existing documents
        with app.app_context():
            # Use direct SQL to get all documents
            with engine.connect() as conn:
                result = conn.execute(text("SELECT id, filename FROM document"))
                documents = result.fetchall()
                
                logging.info(f"Found {len(documents)} documents to process")
                
        # Wait a moment to ensure the database has fully processed the schema change
        import time
        time.sleep(1)
        
        # Process each document separately to avoid transaction failures affecting other updates
        for doc in documents:
            doc_id = doc[0]
            filename = doc[1]
            
            # Use a fresh connection for each document
            with engine.begin() as conn:
                try:
                    # Generate friendly name
                    friendly_name = generate_friendly_name(filename)
                    
                    # To ensure compatibility across database types, use raw SQL
                    conn.execute(text(
                        "UPDATE document SET friendly_name = :name WHERE id = :id"
                    ), {"name": friendly_name, "id": doc_id})
                    
                    logging.info(f"Generated friendly name for {filename}: '{friendly_name}'")
                except Exception as e:
                    logging.error(f"Error generating friendly name for {filename}: {str(e)}")
        
        logging.info("Migration completed successfully")
        
        return True
        
    except Exception as e:
        logging.error(f"Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)