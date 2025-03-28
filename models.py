from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class Document(db.Model):
    """Document model for storing uploaded documents"""
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(512), nullable=False)
    text = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert document to dictionary"""
        return {
            'id': self.id,
            'filename': self.filename,
            'filepath': self.filepath,
            'text': self.text,
            'category': self.category,
            'uploaded_at': self.uploaded_at.isoformat()
        }