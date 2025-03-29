"""
Script to scan all documents and update their file_available status
based on whether their files are actually present on disk.
"""

import os
import glob
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_document_availability():
    """
    Scan all documents and update their file_available status
    """
    from app import app, db
    from models import Document
    
    with app.app_context():
        start_time = datetime.utcnow()
        logger.info("Starting document file availability check...")
        
        # Get all documents
        all_documents = Document.query.all()
        total_docs = len(all_documents)
        fixed_docs = 0
        missing_files = 0
        
        for idx, document in enumerate(all_documents):
            logger.info(f"Checking document {idx+1}/{total_docs}: {document.id}")
            
            # Check if file exists
            file_exists = document.check_file_exists()
            
            # If status doesn't match reality, update it
            if document.file_available != file_exists:
                old_status = document.file_available
                document.file_available = file_exists
                db.session.add(document)
                fixed_docs += 1
                
                status_text = "available ✓" if file_exists else "missing ✗"
                logger.info(f"Updated document {document.id}: file_available from {old_status} to {file_exists} ({status_text})")
                
                if not file_exists:
                    missing_files += 1
            
            # Commit every 10 documents to avoid large transactions
            if idx % 10 == 0 and fixed_docs > 0:
                db.session.commit()
                logger.info(f"Committed changes for {fixed_docs} documents")
                
        # Final commit for any remaining changes
        if fixed_docs % 10 != 0:
            db.session.commit()
            logger.info(f"Committed final changes")
            
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Document availability check completed in {duration:.2f} seconds")
        logger.info(f"Total documents: {total_docs}")
        logger.info(f"Documents fixed: {fixed_docs}")
        logger.info(f"Missing files: {missing_files}")
        logger.info(f"Available files: {total_docs - missing_files}")

if __name__ == "__main__":
    fix_document_availability()