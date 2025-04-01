"""
Script to generate thumbnails for existing documents
"""
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from flask import Flask

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def generate_thumbnails():
    """Generate thumbnails for existing documents that don't have them"""
    from models import Document, db
    from utils.thumbnail_generator import generate_document_thumbnail
    
    # Create the app context
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    db.init_app(app)
    
    with app.app_context():
        # Get all documents
        documents = Document.query.all()
        
        # Create static/thumbnails folder if it doesn't exist
        thumbnails_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'thumbnails')
        os.makedirs(thumbnails_dir, exist_ok=True)
        
        # Track progress
        total = len(documents)
        success_count = 0
        fail_count = 0
        
        print(f"Generating thumbnails for {total} documents...")
        
        # Process each document
        for i, document in enumerate(documents, 1):
            print(f"Processing document {i}/{total}: {document.friendly_name or document.filename}")
            
            # Skip documents that already have custom thumbnails
            if document.custom_thumbnail:
                print(f"Skipping document with custom thumbnail")
                continue
                
            # Generate thumbnail
            thumbnail_url = generate_document_thumbnail(document)
            
            if thumbnail_url:
                # Update the document
                document.thumbnail_url = thumbnail_url
                document.thumbnail_generated = True
                db.session.commit()
                print(f"  Generated thumbnail: {thumbnail_url}")
                success_count += 1
            else:
                print(f"  Failed to generate thumbnail")
                fail_count += 1
        
        print(f"\nThumbnail generation complete: {success_count} succeeded, {fail_count} failed")
    

if __name__ == "__main__":
    generate_thumbnails()