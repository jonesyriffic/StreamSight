from app import app
from models import db, Badge

def initialize_badges():
    """Initialize badge data if not already present"""
    with app.app_context():
        badge_count = Badge.query.count()
        if badge_count == 0:
            from initialize_badges import create_badges
            create_badges()

# Initialize badges when server starts
initialize_badges()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
