"""
Script to scan all documents and update their file_available status
based on whether their files are actually present on disk.
"""

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
        logger.info("Starting document availability check...")
        
        all_documents = Document.query.all()
        total_docs = len(all_documents)
        available_count = 0
        unavailable_count = 0
        
        for idx, document in enumerate(all_documents):
            logger.info(f"Checking document {idx+1}/{total_docs}: {document.id} - {document.filename}")
            
            # Check if file exists
            file_exists = document.check_file_exists()
            old_status = document.file_available
            
            # Update status if needed
            if file_exists != old_status:
                document.file_available = file_exists
                db.session.add(document)
                logger.info(f"  Changed availability status from {old_status} to {file_exists}")
            else:
                logger.info(f"  Status unchanged: {file_exists}")
                
            if file_exists:
                available_count += 1
            else:
                unavailable_count += 1
                
            # Commit every 10 documents to avoid large transactions
            if (idx + 1) % 10 == 0 or idx == total_docs - 1:
                db.session.commit()
                logger.info(f"Committed changes for {min(10, idx % 10 + 1)} documents")
                
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Document availability check completed in {duration:.2f} seconds")
        logger.info(f"Total documents: {total_docs}")
        logger.info(f"Available documents: {available_count}")
        logger.info(f"Unavailable documents: {unavailable_count}")

if __name__ == "__main__":
    fix_document_availability()