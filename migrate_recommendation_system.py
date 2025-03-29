"""
Migration script to add recommendation system tables to the database
"""

import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_initial_team_data(session):
    """Create initial team responsibility data for common teams"""
    
    # Import models here to avoid circular imports
    from models import TeamResponsibility
    
    # Dictionary of team names and their responsibilities
    team_data = {
        "Digital Engagement": "Focus on customer engagement strategies, customer experience optimization, and digital user journeys. Monitor competitive analysis of customer-facing digital tools and customer feedback mechanisms.",
        
        "Digital Product": "Responsible for product strategy, roadmap planning, user story creation, and feature prioritization. Track market trends, user behavior analytics, and product performance metrics.",
        
        "NextGen Products": "Focus on innovative product development, emerging technology evaluation, and future-facing customer needs. Track industry innovation, disruptive technologies, and early adoption patterns.",
        
        "Product Insights": "Analyze customer feedback, market research, and competitive intelligence to inform product decisions. Monitor industry trends, customer satisfaction metrics, and emerging market opportunities.",
        
        "Product Testing": "Responsible for quality assurance, test planning, and validation of product functionality. Track testing methodologies, bug metrics, and release readiness criteria.",
        
        "Service Technology": "Manage technical infrastructure, integrate service platforms, and ensure system reliability. Monitor technology stack evolution, system performance metrics, and technical debt."
    }
    
    # Create records for each team
    team_records = []
    for team_name, description in team_data.items():
        # Check if team already exists
        existing = session.query(TeamResponsibility).filter_by(team_name=team_name).first()
        if not existing:
            team = TeamResponsibility(
                team_name=team_name,
                description=description
            )
            team_records.append(team)
            logger.info(f"Created team responsibility record for: {team_name}")
    
    # Add records to session
    if team_records:
        session.add_all(team_records)
        session.commit()
        logger.info(f"Added {len(team_records)} team responsibility records")
    else:
        logger.info("No new team responsibility records needed")

def run_migration():
    """Add recommendation system tables to the database"""
    from main import app
    from app import db
    from models import TeamResponsibility, UserDismissedRecommendation
    
    with app.app_context():
        logger.info("Starting recommendation system migration")
        
        # Create tables if they don't exist
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        if 'team_responsibility' not in existing_tables:
            TeamResponsibility.__table__.create(db.engine)
            logger.info("Created team_responsibility table")
        else:
            logger.info("team_responsibility table already exists")
            
        if 'user_dismissed_recommendation' not in existing_tables:
            UserDismissedRecommendation.__table__.create(db.engine)
            logger.info("Created user_dismissed_recommendation table")
        else:
            logger.info("user_dismissed_recommendation table already exists")
        
        # Create initial team data
        create_initial_team_data(db.session)
        
        logger.info("Recommendation system migration completed successfully")

if __name__ == "__main__":
    run_migration()