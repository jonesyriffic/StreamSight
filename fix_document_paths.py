"""
Script to update document file paths to match the actual location of files.
This script will:
1. Find files in the ./uploads directory
2. Create a mapping of filenames to actual paths
3. Update the database records to point to the correct paths
"""

import os
import glob
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_document_paths():
    """
    Update document file paths to match actual file locations
    """
    from app import app, db
    from models import Document
    
    with app.app_context():
        start_time = datetime.utcnow()
        logger.info("Starting document path correction...")
        
        # Get all files in the uploads directory
        uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
        if not os.path.exists(uploads_dir):
            logger.error(f"Uploads directory not found: {uploads_dir}")
            return
            
        logger.info(f"Searching for files in: {uploads_dir}")
        
        # Build a mapping of filenames to actual paths
        filename_to_path = {}
        file_count = 0
        
        for filepath in glob.glob(os.path.join(uploads_dir, "*.pdf")):
            file_count += 1
            
            # Extract the actual filename without UUID prefix
            full_filename = os.path.basename(filepath)
            parts = full_filename.split('_', 1)
            
            if len(parts) > 1:
                # If filename has UUID prefix, use the part after the first underscore
                actual_filename = parts[1]
            else:
                # If no underscore, use the full filename
                actual_filename = full_filename
                
            # Add to our mapping
            if actual_filename not in filename_to_path:
                filename_to_path[actual_filename] = filepath
            else:
                # If we have duplicates, keep track of them too with the UUID as key
                filename_to_path[full_filename] = filepath
        
        logger.info(f"Found {file_count} files in uploads directory")
        logger.info(f"Created mapping for {len(filename_to_path)} unique filenames")
        
        # Get all documents
        all_documents = Document.query.all()
        total_docs = len(all_documents)
        updated_docs = 0
        
        for idx, document in enumerate(all_documents):
            logger.info(f"Processing document {idx+1}/{total_docs}: {document.id} - {document.filename}")
            
            # Try to find a matching file
            if document.filename in filename_to_path:
                # Direct filename match
                # Get relative path instead of absolute path
                rel_filepath = os.path.join('./uploads', os.path.basename(filename_to_path[document.filename]))
                old_filepath = document.filepath
                
                document.filepath = rel_filepath
                document.file_available = True
                db.session.add(document)
                updated_docs += 1
                
                logger.info(f"Updated path for {document.filename}")
                logger.info(f"  From: {old_filepath}")
                logger.info(f"  To:   {rel_filepath}")
            else:
                # Try to find a file with similar name (using glob)
                pattern = f"*{os.path.splitext(document.filename)[0]}*.pdf"
                matches = glob.glob(os.path.join(uploads_dir, pattern))
                
                if matches:
                    # Use the first match with a relative path
                    rel_filepath = os.path.join('./uploads', os.path.basename(matches[0]))
                    old_filepath = document.filepath
                    
                    document.filepath = rel_filepath
                    document.file_available = True
                    db.session.add(document)
                    updated_docs += 1
                    
                    logger.info(f"Updated path using pattern match for {document.filename}")
                    logger.info(f"  From: {old_filepath}")
                    logger.info(f"  To:   {rel_filepath}")
                else:
                    logger.warning(f"No matching file found for {document.filename}")
                    document.file_available = False
                    db.session.add(document)
            
            # Commit every 5 documents to avoid large transactions
            if (idx + 1) % 5 == 0 or idx == total_docs - 1:
                db.session.commit()
                logger.info(f"Committed changes for {min(5, idx % 5 + 1)} documents")
                
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Document path correction completed in {duration:.2f} seconds")
        logger.info(f"Total documents: {total_docs}")
        logger.info(f"Documents updated: {updated_docs}")
        logger.info(f"Documents without matching files: {total_docs - updated_docs}")

if __name__ == "__main__":
    fix_document_paths()