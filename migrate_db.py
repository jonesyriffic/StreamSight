import os
import logging
import psycopg2
from psycopg2 import sql

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database connection info from environment variables
DATABASE_URL = os.environ.get("DATABASE_URL")

def run_migration():
    """Add new columns to the User table"""
    logger.info("Running database migrations...")
    
    # Parse DATABASE_URL to get connection parameters
    db_conn = psycopg2.connect(DATABASE_URL)
    cursor = db_conn.cursor()
    
    try:
        # Check if columns exist
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='user'")
        columns = [col[0] for col in cursor.fetchall()]
        
        # Add can_upload column if it doesn't exist
        if 'can_upload' not in columns:
            logger.info("Adding can_upload column to User model...")
            cursor.execute(sql.SQL("ALTER TABLE {} ADD COLUMN {} BOOLEAN DEFAULT FALSE").format(
                sql.Identifier("user"), sql.Identifier("can_upload")))
            logger.info("can_upload column added successfully")
        
        # Add team_specialization column if it doesn't exist
        if 'team_specialization' not in columns:
            logger.info("Adding team_specialization column to User model...")
            cursor.execute(sql.SQL("ALTER TABLE {} ADD COLUMN {} VARCHAR(100)").format(
                sql.Identifier("user"), sql.Identifier("team_specialization")))
            logger.info("team_specialization column added successfully")
        
        # Add last_login column if it doesn't exist
        if 'last_login' not in columns:
            logger.info("Adding last_login column to User model...")
            cursor.execute(sql.SQL("ALTER TABLE {} ADD COLUMN {} TIMESTAMP").format(
                sql.Identifier("user"), sql.Identifier("last_login")))
            logger.info("last_login column added successfully")
        
        # By default, make admins able to upload documents
        logger.info("Setting default upload permissions...")
        cursor.execute(sql.SQL("UPDATE {} SET {} = TRUE WHERE {} = TRUE").format(
            sql.Identifier("user"), sql.Identifier("can_upload"), sql.Identifier("is_admin")))
        
        # Commit all changes
        db_conn.commit()
        logger.info("Database migrations completed successfully.")
    
    except Exception as e:
        db_conn.rollback()
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        cursor.close()
        db_conn.close()

if __name__ == "__main__":
    run_migration()
    print("Database migration completed.")