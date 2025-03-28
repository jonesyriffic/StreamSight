"""
Script to regenerate concise relevance reasons for all existing documents
"""
import logging
import sys
import os
from flask import Flask
from models import Document, db

# Import the document relevance function
# Make sure our path is correct
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.relevance_generator import generate_relevance_reasons

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def regenerate_concise_relevance_reasons():
    """Regenerate concise relevance reasons for all existing documents"""
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
                
                # Generate new concise relevance reasons directly from document
                relevance = generate_relevance_reasons(doc)
                
                # Update the document
                doc.relevance_reasons = relevance
                
                # Log success
                logger.info(f"Updated concise relevance for document {doc.id}")
            
            # Commit all changes
            db.session.commit()
            logger.info("All documents updated with concise relevance reasons")
    
    except Exception as e:
        logger.error(f"Error regenerating concise relevance reasons: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(regenerate_concise_relevance_reasons())