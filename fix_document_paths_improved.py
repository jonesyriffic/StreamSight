"""
Script to permanently fix document file paths by using enhanced Document.check_file_exists()

This script will:
1. Go through all PDF documents in the database
2. Use the improved check_file_exists method with update_path=True
3. Update any documents with corrected file paths
4. Log documents that are still missing their files
"""

import os
import sys
import logging
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('document_path_fix.log')
    ]
)
logger = logging.getLogger(__name__)

def fix_document_paths():
    """
    Find and permanently fix document file paths using enhanced check_file_exists
    """
    from app import app, db
    from models import Document
    
    with app.app_context():
        start_time = datetime.utcnow()
        logger.info("Starting improved document path correction...")
        
        # Get all PDF documents
        pdf_documents = Document.query.filter_by(content_type='pdf').all()
        total_docs = len(pdf_documents)
        
        logger.info(f"Found {total_docs} PDF documents to check")
        
        # Statistics tracking
        fixed_docs = 0
        already_correct = 0
        missing_docs = 0
        
        # Process each document
        for idx, document in enumerate(pdf_documents):
            logger.info(f"Checking document {idx+1}/{total_docs}: {document.id} - {document.filename}")
            
            # Check if the file exists and update if needed
            file_exists = document.check_file_exists(update_path=True)
            
            if file_exists:
                if document.filepath != document.filepath or document.file_available != True:
                    # Path was updated or availability flag was changed
                    db.session.add(document)
                    fixed_docs += 1
                    logger.info(f"  Fixed document path: {document.filepath}")
                else:
                    already_correct += 1
                    logger.info(f"  Path already correct: {document.filepath}")
            else:
                # File is missing
                document.file_available = False
                db.session.add(document)
                missing_docs += 1
                logger.warning(f"  Document file is missing: {document.filename}")
            
            # Commit every 10 documents to avoid large transactions
            if (idx + 1) % 10 == 0 or idx == total_docs - 1:
                db.session.commit()
                logger.info(f"Committed changes for {min(10, idx % 10 + 1)} documents")
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Document path correction completed in {duration:.2f} seconds")
        logger.info(f"Total documents checked: {total_docs}")
        logger.info(f"Documents with paths fixed: {fixed_docs}")
        logger.info(f"Documents already correct: {already_correct}")
        logger.info(f"Documents still missing: {missing_docs}")

def check_upload_folder_permissions():
    """Check and fix upload folder permissions"""
    from app import app
    
    uploads_dir = app.config['UPLOAD_FOLDER']
    logger.info(f"Checking permissions for uploads folder: {uploads_dir}")
    
    if not os.path.exists(uploads_dir):
        try:
            logger.warning(f"Uploads directory doesn't exist, creating: {uploads_dir}")
            os.makedirs(uploads_dir)
            # Set folder permissions to ensure web server can write to it
            os.chmod(uploads_dir, 0o755)
            logger.info(f"Created uploads directory with permissions 755")
        except Exception as e:
            logger.error(f"Failed to create uploads directory: {str(e)}")
            return False
    
    # Check if we can write to the uploads folder
    try:
        test_file = os.path.join(uploads_dir, '.permission_test')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        logger.info("Upload folder permission check: OK (write access confirmed)")
        return True
    except Exception as e:
        logger.error(f"Upload folder permission check failed: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting document path fixing process")
    
    # First check upload folder permissions
    if check_upload_folder_permissions():
        # Proceed with fixing document paths
        fix_document_paths()
    else:
        logger.error("Cannot proceed due to permission issues with upload folder")