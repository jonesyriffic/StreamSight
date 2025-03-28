"""
Migration script to add onboarding tour completion tracking to the User table
"""
import sys
from sqlalchemy import Column, Boolean
from main import app, db
from models import User

def run_migration():
    """Add tour_completed column to the User table"""
    try:
        with app.app_context():
            # Check if the column already exists
            columns = [column.name for column in User.__table__.columns]
            if 'tour_completed' not in columns:
                # Add the tour_completed column
                db.engine.execute('ALTER TABLE "user" ADD COLUMN tour_completed BOOLEAN DEFAULT FALSE')
                print("Migration successful: Added 'tour_completed' column to User table")
            else:
                print("Migration skipped: 'tour_completed' column already exists")
                
            # Check if the tour_steps_completed column already exists
            if 'tour_steps_completed' not in columns:
                # Add the tour_steps_completed column as JSON
                db.engine.execute('ALTER TABLE "user" ADD COLUMN tour_steps_completed JSON DEFAULT NULL')
                print("Migration successful: Added 'tour_steps_completed' column to User table")
            else:
                print("Migration skipped: 'tour_steps_completed' column already exists")
                
            return True
    except Exception as e:
        print(f"Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)