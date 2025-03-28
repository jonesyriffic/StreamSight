"""
Script to fix relevance reason format for all existing documents
"""
import logging
import sys
import os
from flask import Flask
from models import Document, db, User

# Import the document relevance function
# Make sure our path is correct
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.relevance_generator import generate_team_relevance

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_relevance_format():
    """Fix relevance reason format for all existing documents"""
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
                # Skip documents with no relevance reasons
                if not doc.relevance_reasons:
                    logger.info(f"Skipping document {doc.id}: No relevance reasons")
                    continue

                try:
                    logger.info(f"Processing document {doc.id}: {doc.filename}")
                    
                    # Check if any relevance reason is a dictionary instead of a string
                    needs_update = False
                    for team in doc.relevance_reasons:
                        if isinstance(doc.relevance_reasons[team], dict) and "relevance_reason" in doc.relevance_reasons[team]:
                            needs_update = True
                            break
                    
                    if not needs_update:
                        logger.info(f"Document {doc.id} already has correct format")
                        continue
                    
                    # Create a document info dictionary for the relevance generator
                    document_info = {
                        "id": doc.id,
                        "title": doc.friendly_name or doc.filename,
                        "category": doc.category,
                        "summary": doc.summary or "No summary available",
                        "text_excerpt": doc.text[:500] if doc.text else "No text available"
                    }
                    
                    # Fix relevance reasons for each team
                    updated_relevance = {}
                    for team in User.TEAM_CHOICES:
                        if team in doc.relevance_reasons:
                            if isinstance(doc.relevance_reasons[team], dict) and "relevance_reason" in doc.relevance_reasons[team]:
                                # Extract the relevance reason from the dictionary
                                updated_relevance[team] = doc.relevance_reasons[team]["relevance_reason"]
                            else:
                                # Keep as is if already a string
                                updated_relevance[team] = doc.relevance_reasons[team]
                        else:
                            # Generate a new relevance reason for this team
                            updated_relevance[team] = generate_team_relevance(team, document_info)
                    
                    # Update the document with fixed relevance reasons
                    doc.relevance_reasons = updated_relevance
                    db.session.commit()
                    logger.info(f"Updated document {doc.id} relevance format")
                    
                except Exception as e:
                    logger.error(f"Error processing document {doc.id}: {str(e)}")
                    continue
            
            logger.info("Completed relevance format fix")
            
    except Exception as e:
        logger.error(f"Error fixing relevance format: {str(e)}")

if __name__ == "__main__":
    fix_relevance_format()