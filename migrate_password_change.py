import os
import logging
import psycopg2
from psycopg2 import sql

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database connection info from environment variables
DATABASE_URL = os.environ.get("DATABASE_URL")

def run_migration():
    """Add needs_password_change column to the User table"""
    logger.info("Running password change flag migration...")
    
    # Parse DATABASE_URL to get connection parameters
    db_conn = psycopg2.connect(DATABASE_URL)
    cursor = db_conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='user' AND column_name='needs_password_change'")
        column_exists = cursor.fetchone()
        
        # Add needs_password_change column if it doesn't exist
        if not column_exists:
            logger.info("Adding needs_password_change column to User model...")
            cursor.execute(sql.SQL("ALTER TABLE {} ADD COLUMN {} BOOLEAN DEFAULT FALSE").format(
                sql.Identifier("user"), sql.Identifier("needs_password_change")))
            logger.info("needs_password_change column added successfully")
        else:
            logger.info("needs_password_change column already exists, skipping...")
        
        # Commit all changes
        db_conn.commit()
        logger.info("Password change flag migration completed successfully.")
    
    except Exception as e:
        db_conn.rollback()
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        cursor.close()
        db_conn.close()

if __name__ == "__main__":
    run_migration()
    print("Password change flag migration completed.")