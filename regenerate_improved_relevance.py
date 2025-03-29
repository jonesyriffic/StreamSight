"""
Script to regenerate improved relevance reasons for all existing documents
with more detailed, specific relevance information
"""
import os
import logging
import sys
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Document
from utils.relevance_generator import generate_relevance_reasons

def regenerate_improved_relevance():
    """Regenerate improved relevance reasons for all existing documents"""
    with app.app_context():
        # Get all documents
        documents = Document.query.all()
        total_documents = len(documents)
        logger.info(f"Found {total_documents} documents to process")
        
        updated_count = 0
        failed_count = 0
        
        for i, document in enumerate(documents, 1):
            try:
                logger.info(f"Processing document {i}/{total_documents}: {document.friendly_name or document.filename}")
                
                # Generate new relevance reasons with improved specificity
                relevance_reasons = generate_relevance_reasons(document)
                
                # Update the document
                document.relevance_reasons = relevance_reasons
                db.session.commit()
                
                updated_count += 1
                logger.info(f"Successfully updated document {document.id}")
                
            except Exception as e:
                failed_count += 1
                logger.error(f"Error updating document {document.id}: {str(e)}")
                # Continue with the next document
                continue
        
        logger.info(f"Completed: {updated_count} documents updated, {failed_count} failed")

if __name__ == "__main__":
    regenerate_improved_relevance()