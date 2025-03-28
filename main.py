import logging
from app import app
from models import db, Badge, Document
from utils.document_ai import generate_friendly_name

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def initialize_badges():
    """Initialize badge data if not already present"""
    with app.app_context():
        badge_count = Badge.query.count()
        if badge_count == 0:
            from initialize_badges import create_badges
            create_badges()

def process_document_friendly_names():
    """Add friendly names to documents that don't have them yet"""
    try:
        # Check if database is properly set up
        with app.app_context():
            # Check if the column exists in database by updating a field in the model
            # This will throw an error if the column doesn't exist
            first_doc = Document.query.first()
            if first_doc is None:
                logging.info("No documents in database, skipping friendly name processing")
                return
            
            # Try to access the friendly_name attribute
            try:
                _ = first_doc.friendly_name
                column_exists = True
            except Exception:
                column_exists = False
                
            if not column_exists:
                # Column doesn't exist in database, need to add it
                from sqlalchemy import text
                from sqlalchemy.exc import SQLAlchemyError
                engine = db.engine
                
                try:
                    with engine.connect() as conn:
                        conn.execute(text("ALTER TABLE document ADD COLUMN IF NOT EXISTS friendly_name VARCHAR(255)"))
                        conn.commit()
                        logging.info("Added friendly_name column to document table")
                except SQLAlchemyError as e:
                    logging.error(f"Error adding friendly_name column: {str(e)}")
                    return
            
            # Find documents that don't have a friendly name
            docs_without_names = []
            try:
                docs_without_names = Document.query.filter(Document.friendly_name.is_(None)).all()
            except Exception as e:
                logging.error(f"Error querying documents: {str(e)}")
                return
                
            logging.info(f"Found {len(docs_without_names)} documents without friendly names")
            
            # Process each document
            for doc in docs_without_names:
                try:
                    friendly_name = generate_friendly_name(doc.filename)
                    doc.friendly_name = friendly_name
                    logging.info(f"Generated friendly name for {doc.filename}: '{friendly_name}'")
                except Exception as e:
                    logging.error(f"Error generating friendly name for {doc.filename}: {str(e)}")
            
            # Commit all changes
            db.session.commit()
            logging.info("Friendly name processing completed successfully")
            
    except Exception as e:
        logging.error(f"Error processing document friendly names: {str(e)}")

# Function to set up search analytics
def setup_search_analytics():
    """Run the search log migration"""
    try:
        with app.app_context():
            from migrate_search_log import run_migration
            if run_migration():
                logging.info("Search analytics database setup completed")
            else:
                logging.error("Failed to set up search analytics database")
    except Exception as e:
        logging.error(f"Error setting up search analytics: {str(e)}")

# Function to regenerate document relevance reasons
def regenerate_document_relevance():
    """Regenerate relevance reasons for all documents"""
    try:
        with app.app_context():
            from utils.relevance_generator import get_document_relevance_reasons
            from models import Document
            
            # Get all documents from the database
            documents = Document.query.all()
            logging.info(f"Found {len(documents)} documents to regenerate relevance for")
            
            for doc in documents:
                # We need document info for the relevance generator
                document_info = {
                    "id": doc.id,
                    "title": doc.friendly_name or doc.filename,
                    "category": doc.category,
                    "summary": doc.summary or "No summary available",
                    "text_excerpt": doc.text[:500] if doc.text else "No text available"
                }
                
                # Generate new relevance reasons
                relevance = get_document_relevance_reasons(document_info)
                
                # Update the document
                doc.relevance_reasons = relevance
                logging.info(f"Updated relevance for document {doc.id}")
            
            # Commit all changes
            db.session.commit()
            logging.info("Document relevance reasons regenerated successfully")
    except Exception as e:
        logging.error(f"Error regenerating document relevance reasons: {str(e)}")

# For Gunicorn, we need to be careful about initialization that happens on module load
# We're moving these to a function that's only called by the development server

# Function to run initializations for development mode only
def run_dev_initializations():
    # Initialize badges
    initialize_badges()
    
    # Process document friendly names
    process_document_friendly_names()
    
    # Set up search analytics database
    setup_search_analytics()
    
    # Regenerate document relevance data
    regenerate_document_relevance()

# Only run these operations when starting the development server directly
if __name__ == "__main__":
    # Run development initializations
    run_dev_initializations()
    
    # Start the Flask development server
    app.run(host="0.0.0.0", port=5000, debug=True)
