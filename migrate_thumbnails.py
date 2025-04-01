"""
Migration script to add thumbnail-related columns to the Document table
"""
import os
import sys
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

# Add the current directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_migration():
    """Add thumbnail-related columns to the Document table"""
    
    # Get database URL from environment variable
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("Error: DATABASE_URL environment variable not set.")
        return
    
    try:
        # Connect to the database
        engine = create_engine(database_url)
        conn = engine.connect()
        
        # Check if the columns already exist
        inspector = inspect(engine)
        columns = inspector.get_columns('document')
        existing_columns = {c['name'] for c in columns}
        changes_needed = False
        
        # Add thumbnail_generated column if it doesn't exist
        if 'thumbnail_generated' not in existing_columns:
            changes_needed = True
            conn.execute(text("ALTER TABLE document ADD COLUMN thumbnail_generated BOOLEAN NOT NULL DEFAULT FALSE"))
            print("Added 'thumbnail_generated' column to the Document table")
        
        # Add custom_thumbnail column if it doesn't exist
        if 'custom_thumbnail' not in existing_columns:
            changes_needed = True
            conn.execute(text("ALTER TABLE document ADD COLUMN custom_thumbnail BOOLEAN NOT NULL DEFAULT FALSE"))
            print("Added 'custom_thumbnail' column to the Document table")
        
        if not changes_needed:
            print("No changes needed - columns already exist")
        
        # Commit the transaction
        conn.commit()
        conn.close()
        
        print("Migration completed successfully")
        
    except SQLAlchemyError as e:
        print(f"Error performing migration: {e}")
        raise


if __name__ == "__main__":
    run_migration()