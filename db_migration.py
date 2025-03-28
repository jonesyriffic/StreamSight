from app import app, db
from models import Document
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with app.app_context():
    logger.info("Updating database schema...")
    db.create_all()
    logger.info("Database schema updated successfully.")

if __name__ == "__main__":
    print("Database migration completed.")