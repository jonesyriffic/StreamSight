"""
Script to initialize like badges in the database
"""
import os
from flask import Flask
from models import db, Badge
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_like_badges():
    """
    Create badge records for the liker badge type and levels
    """
    # Check if badges already exist to avoid duplicates
    existing_badges = Badge.query.filter_by(type=Badge.TYPE_LIKER).all()
    if existing_badges:
        logger.info(f"Found {len(existing_badges)} existing liker badges, skipping creation")
        return
    
    # Define the liker badges
    badges = [
        {
            'name': 'Content Admirer',
            'description': 'Bronze liker badge: Liked 5 or more documents',
            'type': Badge.TYPE_LIKER,
            'level': Badge.LEVEL_BRONZE,
            'criteria_count': 5,
            'icon': 'fas fa-thumbs-up text-danger'
        },
        {
            'name': 'Document Appreciator',
            'description': 'Silver liker badge: Liked 15 or more documents',
            'type': Badge.TYPE_LIKER,
            'level': Badge.LEVEL_SILVER,
            'criteria_count': 15,
            'icon': 'fas fa-thumbs-up text-info'
        },
        {
            'name': 'Knowledge Supporter',
            'description': 'Gold liker badge: Liked 30 or more documents',
            'type': Badge.TYPE_LIKER,
            'level': Badge.LEVEL_GOLD,
            'criteria_count': 30,
            'icon': 'fas fa-thumbs-up text-warning'
        },
        {
            'name': 'Content Enthusiast',
            'description': 'Platinum liker badge: Liked 50 or more documents',
            'type': Badge.TYPE_LIKER,
            'level': Badge.LEVEL_PLATINUM,
            'criteria_count': 50,
            'icon': 'fas fa-thumbs-up text-light'
        }
    ]
    
    # Create the badges
    for badge_data in badges:
        badge = Badge(**badge_data)
        db.session.add(badge)
    
    # Commit all badges in one transaction
    db.session.commit()
    logger.info(f"Created {len(badges)} liker badges")

if __name__ == "__main__":
    # Create a simple Flask app to establish database connection
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    db.init_app(app)
    
    with app.app_context():
        create_like_badges()