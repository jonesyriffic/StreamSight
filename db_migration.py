from app import app, db
from models import Document, User
import logging
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    with app.app_context():
        logger.info("Running database migrations...")
        
        # Check if can_upload column exists
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('user')]
        
        # Add can_upload, team_specialization, and last_login columns if they don't exist
        if 'can_upload' not in columns:
            logger.info("Adding can_upload column to User model...")
            db.session.execute(text('ALTER TABLE "user" ADD COLUMN can_upload BOOLEAN DEFAULT FALSE'))
            logger.info("can_upload column added successfully")
        
        if 'team_specialization' not in columns:
            logger.info("Adding team_specialization column to User model...")
            db.session.execute(text('ALTER TABLE "user" ADD COLUMN team_specialization VARCHAR(100)'))
            logger.info("team_specialization column added successfully")
        
        if 'last_login' not in columns:
            logger.info("Adding last_login column to User model...")
            db.session.execute(text('ALTER TABLE "user" ADD COLUMN last_login TIMESTAMP'))
            logger.info("last_login column added successfully")
        
        db.session.commit()
        
        # By default, admins can upload documents
        logger.info("Setting default upload permissions...")
        admins = User.query.filter_by(is_admin=True).all()
        for admin in admins:
            admin.can_upload = True
        
        db.session.commit()
        logger.info("Database migrations completed successfully.")

if __name__ == "__main__":
    run_migration()
    print("Database migration completed.")