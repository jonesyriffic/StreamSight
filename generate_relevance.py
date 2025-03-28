"""
Script to generate relevance reasons for all existing documents
"""
import logging
import sys
import os
from flask import Flask
from models import Document, db

# Import the document relevance function
# Make sure our path is correct
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.relevance_generator import get_document_relevance_reasons as generate_document_relevance

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_all_relevance_reasons():
    """Generate relevance reasons for all existing documents"""
    try:
        # Create a Flask app context for database operations
        app = Flask(__name__)
        app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_recycle": 300,
            "pool_pre_ping": True,
        }
        db.init_app(app)
        
        with app.app_context():
            # Get all documents from the database
            documents = Document.query.all()
            logger.info(f"Found {len(documents)} documents to process")
            
            for doc in documents:
                logger.info(f"Processing document {doc.id}: {doc.filename}")
                
                # We need document info for the relevance generator
                document_info = {
                    "id": doc.id,
                    "title": doc.friendly_name or doc.filename,
                    "category": doc.category,
                    "summary": doc.summary or "No summary available",
                    "text_excerpt": doc.text[:500] if doc.text else "No text available"
                }
                
                # Generate new relevance reasons
                relevance = generate_document_relevance(document_info)
                
                # Update the document
                doc.relevance_reasons = relevance
                
                # Log success
                logger.info(f"Updated relevance for document {doc.id}")
            
            # Commit all changes
            db.session.commit()
            logger.info("All documents updated successfully")
    
    except Exception as e:
        logger.error(f"Error generating relevance reasons: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(generate_all_relevance_reasons())