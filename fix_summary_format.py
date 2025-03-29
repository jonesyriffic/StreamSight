"""
Script to update existing document summaries to use plain text for card views and HTML for document view
"""
import logging
import re
from app import app
from models import db, Document

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fix_summary_format():
    """
    Updates existing document summaries to store plain text for card views
    
    This function:
    1. Creates a plain text version of each document's summary
    2. Moves the HTML summary to a new field for document view
    """
    with app.app_context():
        # Get all documents with summaries
        documents = Document.query.filter(Document.summary.isnot(None)).all()
        logging.info(f"Processing {len(documents)} documents with summaries")
        
        updated_count = 0
        for document in documents:
            try:
                # Skip documents with no summary
                if not document.summary:
                    continue
                
                # Check if summary is already in plain text (no HTML tags)
                if "<" not in document.summary and ">" not in document.summary:
                    continue
                
                # Create a plain text version by removing HTML tags
                plain_text = re.sub(r'<.*?>', '', document.summary)
                
                # Store the HTML version in key_points if empty
                if not document.key_points:
                    document.key_points = document.summary
                
                # Update the summary with plain text
                document.summary = plain_text
                updated_count += 1
                logging.info(f"Updated summary format for document {document.id}")
            except Exception as e:
                logging.error(f"Error processing document {document.id}: {str(e)}")
                continue
        
        # Commit changes
        if updated_count > 0:
            db.session.commit()
            logging.info(f"Updated {updated_count} document summaries to plain text format")
        else:
            logging.info("No document summaries needed updating")

if __name__ == "__main__":
    # Run the summary format fix
    fix_summary_format()