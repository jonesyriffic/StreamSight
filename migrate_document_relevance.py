import os
import logging
import psycopg2
from psycopg2 import sql

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database connection info from environment variables
DATABASE_URL = os.environ.get("DATABASE_URL")

def run_migration():
    """Add relevance_reasons column to the Document table"""
    logger.info("Running document relevance migration...")
    
    # Parse DATABASE_URL to get connection parameters
    db_conn = psycopg2.connect(DATABASE_URL)
    cursor = db_conn.cursor()
    
    try:
        # Check if columns exist
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='document'")
        columns = [col[0] for col in cursor.fetchall()]
        
        # Add relevance_reasons column if it doesn't exist
        if 'relevance_reasons' not in columns:
            logger.info("Adding relevance_reasons column to Document model...")
            cursor.execute(sql.SQL("ALTER TABLE {} ADD COLUMN {} JSONB").format(
                sql.Identifier("document"), sql.Identifier("relevance_reasons")))
            logger.info("relevance_reasons column added successfully")
        
        # Commit all changes
        db_conn.commit()
        logger.info("Document relevance migration completed successfully.")
    
    except Exception as e:
        db_conn.rollback()
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        cursor.close()
        db_conn.close()

if __name__ == "__main__":
    run_migration()
    print("Document relevance migration completed.")