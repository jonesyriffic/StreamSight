"""
Migration script to add the SearchLog table to the database
"""
import os
import sys
import logging
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, MetaData, Table
from sqlalchemy.engine import Engine
from sqlalchemy.sql import text

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_migration():
    """Add SearchLog table to the database"""
    try:
        # Get database URL from environment
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            logger.error("DATABASE_URL not found in environment")
            return False
            
        # Create a database engine
        engine = create_engine(database_url)
        
        # Check if the table already exists
        inspector = inspect_from_engine(engine)
        tables = inspector.get_table_names()
        
        if 'search_log' in tables:
            logger.info("SearchLog table already exists, skipping creation")
            return True
            
        # Define metadata
        metadata = MetaData()
        
        # Define search_log table
        search_log = Table(
            'search_log', 
            metadata,
            Column('id', Integer, primary_key=True),
            Column('query', String(255), nullable=False),
            Column('category_filter', String(50), nullable=True),
            Column('user_id', Integer, ForeignKey('user.id', ondelete='SET NULL'), nullable=True),
            Column('team_specialization', String(100), nullable=True),
            Column('executed_at', DateTime, default=datetime.utcnow, nullable=False),
            Column('results_count', Integer, nullable=False, default=0),
            Column('duration_seconds', Float, nullable=True),
            Column('documents_searched', Integer, nullable=True),
            Column('highest_relevance_score', Float, nullable=True),
            Column('avg_relevance_score', Float, nullable=True)
        )
        
        # Create the table
        metadata.create_all(engine, tables=[search_log])
        logger.info("Successfully created search_log table")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        return False

def inspect_from_engine(engine: Engine) -> any:
    """Get inspector from engine"""
    from sqlalchemy import inspect
    return inspect(engine)

if __name__ == "__main__":
    logger.info("Starting migration to add SearchLog table")
    if run_migration():
        logger.info("Migration completed successfully")
    else:
        logger.error("Migration failed")
        sys.exit(1)