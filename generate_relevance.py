"""
Script to generate relevance reasons for all existing documents
"""
import os
import logging
from datetime import datetime
from main import app
from models import db, Document
from utils.relevance_generator import generate_relevance_reasons

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_all_relevance_reasons():
    """Generate relevance reasons for all existing documents"""
    with app.app_context():
        # Get all documents that don't have relevance reasons
        documents = Document.query.filter(
            Document.relevance_reasons.is_(None)
        ).all()
        
        logger.info(f"Found {len(documents)} documents without relevance reasons")
        
        for i, document in enumerate(documents, 1):
            try:
                logger.info(f"[{i}/{len(documents)}] Generating relevance reasons for document: {document.filename}")
                relevance_reasons = generate_relevance_reasons(document)
                document.relevance_reasons = relevance_reasons
                db.session.commit()
                logger.info(f"Successfully generated relevance reasons for {document.filename}")
            except Exception as e:
                logger.error(f"Error generating relevance reasons for {document.filename}: {str(e)}")
                # Continue with the next document
        
        logger.info("Relevance reason generation completed")

if __name__ == "__main__":
    generate_all_relevance_reasons()