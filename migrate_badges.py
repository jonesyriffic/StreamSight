"""
Migration script to add badge-related tables to the database
"""
import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import JSON

def run_migration():
    """Add badge-related tables to the database"""
    
    # Get database URL from environment
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        print("Error: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    # Ensure PostgreSQL URL format
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    try:
        # Connect to the database
        engine = create_engine(DATABASE_URL)
        meta = MetaData()
        
        # Create Badge table
        badge = Table(
            'badge', meta,
            Column('id', Integer, primary_key=True),
            Column('name', String(100), nullable=False),
            Column('description', String(255), nullable=False),
            Column('type', String(50), nullable=False),
            Column('level', String(20), nullable=False),
            Column('criteria_count', Integer, nullable=False),
            Column('icon', String(255), nullable=False)
        )
        
        # Create UserActivity table
        user_activity = Table(
            'user_activity', meta,
            Column('id', Integer, primary_key=True),
            Column('user_id', Integer, ForeignKey('user.id'), nullable=False),
            Column('document_id', String(36), ForeignKey('document.id'), nullable=True),
            Column('activity_type', String(50), nullable=False),
            Column('performed_at', DateTime, default=datetime.utcnow)
        )
        
        # Create UserBadge association table
        user_badges = Table(
            'user_badges', meta,
            Column('user_id', Integer, ForeignKey('user.id'), primary_key=True),
            Column('badge_id', Integer, ForeignKey('badge.id'), primary_key=True),
            Column('earned_at', DateTime, default=datetime.utcnow)
        )
        
        # Create tables if they don't exist
        meta.create_all(engine)
        
        print("Successfully added badge tables to the database")
        
        # Insert default badges
        with engine.connect() as conn:
            # Check if badges already exist
            result = conn.execute("SELECT COUNT(*) FROM badge")
            count = result.scalar()
            
            if count == 0:
                # Reader badges
                conn.execute(
                    badge.insert(),
                    [
                        {
                            'name': 'Curious Reader',
                            'description': 'Read 5 documents',
                            'type': 'reader',
                            'level': 'bronze', 
                            'criteria_count': 5,
                            'icon': '/static/img/badges/reader_bronze.svg'
                        },
                        {
                            'name': 'Knowledge Seeker',
                            'description': 'Read 20 documents',
                            'type': 'reader',
                            'level': 'silver',
                            'criteria_count': 20,
                            'icon': '/static/img/badges/reader_silver.svg'
                        },
                        {
                            'name': 'Wisdom Collector',
                            'description': 'Read 50 documents',
                            'type': 'reader',
                            'level': 'gold',
                            'criteria_count': 50,
                            'icon': '/static/img/badges/reader_gold.svg'
                        },
                        {
                            'name': 'Document Master',
                            'description': 'Read 100 documents',
                            'type': 'reader',
                            'level': 'platinum',
                            'criteria_count': 100,
                            'icon': '/static/img/badges/reader_platinum.svg'
                        },
                        # Search badges
                        {
                            'name': 'Curious Explorer',
                            'description': 'Perform 10 searches',
                            'type': 'searcher',
                            'level': 'bronze',
                            'criteria_count': 10,
                            'icon': '/static/img/badges/searcher_bronze.svg'
                        },
                        {
                            'name': 'Insight Finder',
                            'description': 'Perform 30 searches',
                            'type': 'searcher',
                            'level': 'silver',
                            'criteria_count': 30,
                            'icon': '/static/img/badges/searcher_silver.svg'
                        },
                        {
                            'name': 'Research Pro',
                            'description': 'Perform 75 searches',
                            'type': 'searcher',
                            'level': 'gold',
                            'criteria_count': 75,
                            'icon': '/static/img/badges/searcher_gold.svg'
                        },
                        {
                            'name': 'Search Guru',
                            'description': 'Perform 150 searches',
                            'type': 'searcher',
                            'level': 'platinum',
                            'criteria_count': 150,
                            'icon': '/static/img/badges/searcher_platinum.svg'
                        },
                        # Contributor badges
                        {
                            'name': 'Knowledge Contributor',
                            'description': 'Upload 3 documents',
                            'type': 'contributor',
                            'level': 'bronze',
                            'criteria_count': 3,
                            'icon': '/static/img/badges/contributor_bronze.svg'
                        },
                        {
                            'name': 'Resource Builder',
                            'description': 'Upload 10 documents',
                            'type': 'contributor',
                            'level': 'silver',
                            'criteria_count': 10,
                            'icon': '/static/img/badges/contributor_silver.svg'
                        },
                        {
                            'name': 'Content Champion',
                            'description': 'Upload 25 documents',
                            'type': 'contributor',
                            'level': 'gold',
                            'criteria_count': 25,
                            'icon': '/static/img/badges/contributor_gold.svg'
                        },
                        {
                            'name': 'Knowledge Base Legend',
                            'description': 'Upload 50 documents',
                            'type': 'contributor',
                            'level': 'platinum',
                            'criteria_count': 50,
                            'icon': '/static/img/badges/contributor_platinum.svg'
                        },
                        # Summarizer badges
                        {
                            'name': 'Summary Starter',
                            'description': 'Generate 5 document summaries',
                            'type': 'summarizer',
                            'level': 'bronze',
                            'criteria_count': 5,
                            'icon': '/static/img/badges/summarizer_bronze.svg'
                        },
                        {
                            'name': 'Insight Extractor',
                            'description': 'Generate 15 document summaries',
                            'type': 'summarizer',
                            'level': 'silver',
                            'criteria_count': 15,
                            'icon': '/static/img/badges/summarizer_silver.svg'
                        },
                        {
                            'name': 'Information Distiller',
                            'description': 'Generate 40 document summaries',
                            'type': 'summarizer',
                            'level': 'gold',
                            'criteria_count': 40,
                            'icon': '/static/img/badges/summarizer_gold.svg'
                        },
                        {
                            'name': 'AI Synthesis Expert',
                            'description': 'Generate 80 document summaries',
                            'type': 'summarizer',
                            'level': 'platinum',
                            'criteria_count': 80,
                            'icon': '/static/img/badges/summarizer_platinum.svg'
                        }
                    ]
                )
                print("Default badges created")
            else:
                print("Badges already exist, skipping default badge creation")
                
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        sys.exit(1)
    
    print("Migration completed successfully")

if __name__ == "__main__":
    run_migration()