from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication"""
    
    # Team specialization constants
    TEAM_DIGITAL_PRODUCT = 'Digital Product - Help Centers'
    TEAM_SERVICE_TECH = 'Service Technology - Salesforce CRM'
    TEAM_DIGITAL_ENGAGEMENT = 'Digital Engagement - Chatbots and Social Platforms'
    TEAM_PRODUCT_TESTING = 'Product Testing - UAT'
    TEAM_PRODUCT_INSIGHTS = 'Product Insights - Adobe Data and Salesforce Data'
    TEAM_NEXTGEN_PRODUCTS = 'NextGen Products - future industry trends'
    
    TEAM_CHOICES = [
        TEAM_DIGITAL_PRODUCT,
        TEAM_SERVICE_TECH,
        TEAM_DIGITAL_ENGAGEMENT,
        TEAM_PRODUCT_TESTING,
        TEAM_PRODUCT_INSIGHTS,
        TEAM_NEXTGEN_PRODUCTS
    ]
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    is_approved = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    can_upload = db.Column(db.Boolean, default=False)  # New permission layer for upload capability
    team_specialization = db.Column(db.String(100), nullable=True)  # User's team specialization
    last_login = db.Column(db.DateTime, nullable=True)  # Track last login for recommendations
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime, nullable=True)
    
    # Relationship with documents
    documents = db.relationship('Document', backref='uploader', lazy=True)
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        """Check password"""
        return check_password_hash(self.password_hash, password)
    
    def approve(self):
        """Approve user account"""
        self.is_approved = True
        self.approved_at = datetime.utcnow()
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'is_active': self.is_active,
            'is_approved': self.is_approved,
            'is_admin': self.is_admin,
            'can_upload': self.can_upload,
            'team_specialization': self.team_specialization,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat(),
            'approved_at': self.approved_at.isoformat() if self.approved_at else None
        }

class Document(db.Model):
    """Document model for storing uploaded documents"""
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(512), nullable=False)
    text = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Summary and key points generated by AI
    summary = db.Column(db.Text, nullable=True)
    key_points = db.Column(db.Text, nullable=True)
    summary_generated_at = db.Column(db.DateTime, nullable=True)
    
    # User who uploaded this document
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    def to_dict(self):
        """Convert document to dictionary"""
        return {
            'id': self.id,
            'filename': self.filename,
            'filepath': self.filepath,
            'text': self.text,
            'category': self.category,
            'uploaded_at': self.uploaded_at.isoformat(),
            'user_id': self.user_id,
            'summary': self.summary,
            'key_points': self.key_points,
            'summary_generated_at': self.summary_generated_at.isoformat() if self.summary_generated_at else None
        }