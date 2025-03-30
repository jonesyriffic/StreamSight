"""
Migration script to add content type columns to the Document table
This adds:
- content_type (pdf, weblink, youtube)
- source_url (for web links and YouTube videos)
- thumbnail_url (for YouTube videos)
- youtube_video_id (for YouTube video embedding)
"""

import os
import sys
import psycopg2
from psycopg2 import sql

def run_migration():
    """Add content type columns to the Document table"""
    # Get database connection parameters from environment
    db_url = os.environ.get('DATABASE_URL')
    
    if not db_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    try:
        # Connect to the database
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check which columns exist
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'document';
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        # Define columns to add with their definitions
        columns_to_add = []
        if 'content_type' not in existing_columns:
            columns_to_add.append(("content_type", "VARCHAR(20) NOT NULL DEFAULT 'pdf'"))
        if 'source_url' not in existing_columns:
            columns_to_add.append(("source_url", "VARCHAR(1024)"))
        if 'thumbnail_url' not in existing_columns:
            columns_to_add.append(("thumbnail_url", "VARCHAR(1024)"))
        if 'youtube_video_id' not in existing_columns:
            columns_to_add.append(("youtube_video_id", "VARCHAR(20)"))
        
        if columns_to_add:
            print(f"Adding {len(columns_to_add)} columns to Document table...")
            
            # Add each column
            for column_name, column_type in columns_to_add:
                print(f"Adding column: {column_name}")
                cursor.execute(sql.SQL("ALTER TABLE document ADD COLUMN {} {};").format(
                    sql.Identifier(column_name),
                    sql.SQL(column_type)
                ))
            
            print("Document table migration complete.")
        else:
            print("All required columns already exist. No migration needed.")
        
        # Close connection
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"ERROR: Database migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    run_migration()