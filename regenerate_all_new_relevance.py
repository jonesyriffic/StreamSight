"""
Script to regenerate all document relevance reasons with the new, more specific format
"""

import os
import sys
import time
from datetime import datetime

try:
    import tqdm
except ImportError:
    print("Installing tqdm package...")
    os.system("pip install tqdm")
    import tqdm

# Import models and necessary utility functions
sys.path.append('.')

# Import the app and db instance from main instead of creating a new one
from main import app, db
from models import Document
from utils.relevance_generator import generate_relevance_reasons

with app.app_context():
    
    def regenerate_all_relevance_specific():
        """Regenerate all document relevance reasons with the new, more specific format"""
        try:
            # Get all documents
            documents = Document.query.all()
            print(f"Found {len(documents)} documents to process")
            
            # Process each document
            for doc in tqdm.tqdm(documents):
                # Skip documents without text
                if not doc.text:
                    print(f"Skipping document {doc.id} due to missing text")
                    continue
                    
                # Build document info to pass to generator
                doc_info = {
                    "id": doc.id,
                    "title": doc.friendly_name if doc.friendly_name else doc.filename,
                    "category": doc.category,
                    "text_excerpt": doc.text[:5000] if doc.text else "",
                    "summary": doc.summary or "",
                    "key_points": doc.key_points or ""
                }
                
                try:
                    # Generate new relevance reasons
                    relevance_data = generate_relevance_reasons(doc)
                    
                    # Update document with new relevance reasons
                    doc.relevance_reasons = relevance_data
                    db.session.commit()
                    
                    print(f"Updated relevance for {doc.id}: {doc.friendly_name if doc.friendly_name else doc.filename}")
                    
                    # Add a small delay to avoid rate limits
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"Error generating relevance for document {doc.id}: {str(e)}")
                    continue
                    
            print("Regeneration of specific relevance completed successfully")
        
        except Exception as e:
            print(f"Error during regeneration: {str(e)}")
            db.session.rollback()
            
    # Execute the regeneration
    regenerate_all_relevance_specific()