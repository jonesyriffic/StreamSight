"""
Script to update existing documents with friendly names
"""
import os
import sys
import logging
from main import app
from models import db, Document
from utils.document_ai import generate_friendly_name

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def update_friendly_names():
    """Update existing documents with friendly names"""
    try:
        with app.app_context():
            # Ensure the database schema is up-to-date
            db.create_all()
            
            # Find documents that don't have a friendly name
            documents = Document.query.filter(Document.friendly_name.is_(None)).all()
            logging.info(f"Found {len(documents)} documents without friendly names")
            
            # Process each document
            for doc in documents:
                try:
                    friendly_name = generate_friendly_name(doc.filename)
                    doc.friendly_name = friendly_name
                    logging.info(f"Generated friendly name for {doc.filename}: '{friendly_name}'")
                except Exception as e:
                    logging.error(f"Error generating friendly name for {doc.filename}: {str(e)}")
            
            # Commit all changes
            db.session.commit()
            logging.info("Update completed successfully")
            
            return True
    except Exception as e:
        logging.error(f"Update failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = update_friendly_names()
    sys.exit(0 if success else 1)