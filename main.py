import logging
from app import app
from models import db, Badge, Document
from utils.document_ai import generate_friendly_name
# Import routes
import routes.feature_routes
from routes.search_progress import search_progress_bp

# Register blueprints
app.register_blueprint(search_progress_bp)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def initialize_badges():
    """Initialize badge data if not already present"""
    with app.app_context():
        badge_count = Badge.query.count()
        if badge_count == 0:
            from initialize_badges import create_badges
            create_badges()
            
def initialize_like_badges():
    """Initialize like badges if not already present"""
    with app.app_context():
        liker_badge_count = Badge.query.filter_by(type='liker').count()
        if liker_badge_count == 0:
            from initialize_like_badges import create_like_badges
            create_like_badges()
            logging.info("Initialized like badges")

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

# Function to regenerate concise relevance reasons
def regenerate_concise_relevance():
    """Regenerate concise relevance reasons for all documents"""
    try:
        with app.app_context():
            from utils.relevance_generator import generate_relevance_reasons
            from models import Document
            
            # Get all documents from the database
            documents = Document.query.all()
            logging.info(f"Found {len(documents)} documents to process for concise relevance")
            
            for doc in documents:
                # Generate new concise relevance reasons directly from document
                relevance = generate_relevance_reasons(doc)
                
                # Update the document
                doc.relevance_reasons = relevance
                logging.info(f"Updated concise relevance for document {doc.id}")
            
            # Commit all changes
            db.session.commit()
            logging.info("All documents updated with concise relevance reasons")
    except Exception as e:
        logging.error(f"Error regenerating concise relevance reasons: {str(e)}")

# Function to fix relevance format for all documents
def fix_relevance_format():
    """Fix relevance reason format for all existing documents"""
    try:
        with app.app_context():
            from models import Document, User
            from utils.relevance_generator import generate_team_relevance
            
            # Get all documents from the database
            documents = Document.query.all()
            logging.info(f"Found {len(documents)} documents to process for format fix")
            
            for doc in documents:
                # Skip documents with no relevance reasons
                if not doc.relevance_reasons:
                    logging.info(f"Skipping document {doc.id}: No relevance reasons")
                    continue

                try:
                    # Check if any relevance reason is a dictionary instead of a string
                    needs_update = False
                    for team in doc.relevance_reasons:
                        if isinstance(doc.relevance_reasons[team], dict) and "relevance_reason" in doc.relevance_reasons[team]:
                            needs_update = True
                            break
                    
                    if not needs_update:
                        logging.info(f"Document {doc.id} already has correct format")
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
                    logging.info(f"Updated document {doc.id} relevance format")
                    
                except Exception as e:
                    logging.error(f"Error processing document {doc.id}: {str(e)}")
                    continue
            
            # Commit all changes
            db.session.commit()
            logging.info("Completed relevance format fix")
            
    except Exception as e:
        logging.error(f"Error fixing relevance format: {str(e)}")

# For Gunicorn, we need to be careful about initialization that happens on module load
# We're moving these to a function that's only called by the development server

# Function to check document file availability
def check_document_availability():
    """Check and update file_available status for all documents"""
    try:
        with app.app_context():
            from fix_document_availability import fix_document_availability
            fix_document_availability()
            logging.info("Document file availability check completed")
    except Exception as e:
        logging.error(f"Error checking document file availability: {str(e)}")
        
def fix_document_paths_permanently():
    """Permanently fix document file paths using the improved file checking method"""
    try:
        with app.app_context():
            from fix_document_paths_improved import fix_document_paths, check_upload_folder_permissions
            
            # First check upload folder permissions
            if check_upload_folder_permissions():
                # Fix document paths if we have proper permissions
                fix_document_paths()
                logging.info("Document paths permanently fixed")
            else:
                logging.error("Cannot fix document paths due to permission issues with upload folder")
    except Exception as e:
        logging.error(f"Error permanently fixing document paths: {str(e)}")

def fix_summary_format():
    """Fix document summaries to ensure they don't display HTML in card views"""
    try:
        with app.app_context():
            from fix_summary_format import fix_summary_format
            fix_summary_format()
            logging.info("Document summary format fixes completed")
    except Exception as e:
        logging.error(f"Error fixing document summary formats: {str(e)}")

# Function to run initializations for development mode only
def setup_recommendation_system():
    """Set up recommendation system tables and initial data"""
    try:
        from migrate_recommendation_system import run_migration
        logging.info("Setting up recommendation system tables...")
        run_migration()
        logging.info("Recommendation system tables set up successfully")
    except Exception as e:
        logging.error(f"Error setting up recommendation system: {e}")

def setup_document_content_types():
    """Set up document content type columns for web links and YouTube videos"""
    try:
        with app.app_context():
            from migrate_document_types import run_migration
            logging.info("Setting up document content type columns...")
            run_migration()
            logging.info("Document content type columns set up successfully")
    except Exception as e:
        logging.error(f"Error setting up document content type columns: {str(e)}")

def setup_featured_documents():
    """Set up featured document columns for homepage featured content"""
    try:
        with app.app_context():
            from migrate_featured_documents import run_migration
            logging.info("Setting up featured document columns...")
            run_migration()
            logging.info("Featured document columns set up successfully")
    except Exception as e:
        logging.error(f"Error setting up featured document columns: {str(e)}")


def run_dev_initializations():
    # Initialize badges
    initialize_badges()
    
    # Initialize like badges
    initialize_like_badges()
    
    # Process document friendly names
    process_document_friendly_names()
    
    # Set up search analytics database
    setup_search_analytics()
    
    # Set up document content type columns
    setup_document_content_types()
    
    # Set up featured document columns
    setup_featured_documents()
    
    # Fix relevance format issues
    fix_relevance_format()
    
    # Regenerate document relevance data with concise format
    regenerate_concise_relevance()
    
    # Fix document paths permanently using improved method
    # This must come before the document availability check
    fix_document_paths_permanently()
    
    # Check document file availability
    check_document_availability()
    
    # Fix document summary formats
    fix_summary_format()
    
    # Set up recommendation system
    setup_recommendation_system()

# Only run these operations when starting the development server directly
if __name__ == "__main__":
    # Run development initializations
    run_dev_initializations()
    
    # Start the Flask development server
    app.run(host="0.0.0.0", port=5000, debug=True)
