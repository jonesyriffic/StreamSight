"""
Script to regenerate all document relevance reasons to ensure they are concise
"""
import os
import sys
import logging
from flask import Flask
from models import Document, db
from utils.relevance_generator import generate_relevance_reasons

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_app():
    """Create Flask app for database access"""
    app = Flask(__name__)
    
    # Configure database
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'connect_args': {
            'sslmode': 'prefer'
        }
    }
    db.init_app(app)
    
    return app

def regenerate_all_relevance_reasons():
    """Regenerate concise relevance reasons for all existing documents"""
    try:
        app = create_app()
        with app.app_context():
            # Get all documents that already have relevance reasons
            documents = Document.query.filter(Document.relevance_reasons.isnot(None)).all()
            
            if not documents:
                logger.info("No documents with relevance reasons found.")
                return
                
            logger.info(f"Found {len(documents)} documents with relevance reasons.")
            
            # Process each document
            for i, doc in enumerate(documents):
                # Get original fields to use for document info
                doc_info = {
                    "id": doc.id,
                    "filename": doc.filename,
                    "title": doc.friendly_name or doc.filename,
                    "category": doc.category,
                    "summary": doc.summary or "",
                    "text_excerpt": doc.text[:300] + "..." if doc.text and len(doc.text) > 300 else (doc.text or "")
                }
                
                logger.info(f"Processing document {i+1}/{len(documents)}: {doc_info['title']}")
                
                # Generate new concise relevance reasons
                relevance_reasons = generate_relevance_reasons(doc)
                
                # Update document with new concise relevance reasons
                doc.relevance_reasons = relevance_reasons
                db.session.commit()
                
                logger.info(f"Updated document: {doc_info['title']}")
                
            logger.info("All document relevance reasons have been regenerated.")
    
    except Exception as e:
        logger.error(f"Error regenerating relevance reasons: {str(e)}")
        return False
        
    return True

if __name__ == "__main__":
    logger.info("Starting relevance reason regeneration...")
    result = regenerate_all_relevance_reasons()
    if result:
        logger.info("Relevance reason regeneration completed successfully.")
        sys.exit(0)
    else:
        logger.error("Relevance reason regeneration failed.")
        sys.exit(1)