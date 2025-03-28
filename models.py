from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
import json
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
    needs_password_change = db.Column(db.Boolean, default=False)  # Flag for temporary password
    tour_completed = db.Column(db.Boolean, default=False)  # Track if user has completed the onboarding tour
    tour_steps_completed = db.Column(db.JSON, nullable=True)  # Track individual tour steps completion
    
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
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'tour_completed': self.tour_completed,
            'tour_steps_completed': self.tour_steps_completed
        }

class Badge(db.Model):
    """Badge model for gamification system"""
    
    # Badge type constants
    TYPE_READER = 'reader'         # For reading documents
    TYPE_SEARCHER = 'searcher'     # For searching documents
    TYPE_CONTRIBUTOR = 'contributor'  # For uploading documents
    TYPE_SUMMARIZER = 'summarizer'  # For generating summaries
    
    BADGE_TYPES = [
        TYPE_READER,
        TYPE_SEARCHER,
        TYPE_CONTRIBUTOR,
        TYPE_SUMMARIZER
    ]
    
    # Badge level constants
    LEVEL_BRONZE = 'bronze'    # Level 1
    LEVEL_SILVER = 'silver'    # Level 2
    LEVEL_GOLD = 'gold'        # Level 3
    LEVEL_PLATINUM = 'platinum'  # Level 4
    
    BADGE_LEVELS = [
        LEVEL_BRONZE,
        LEVEL_SILVER,
        LEVEL_GOLD,
        LEVEL_PLATINUM
    ]
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # reader, searcher, contributor, summarizer
    level = db.Column(db.String(20), nullable=False)  # bronze, silver, gold, platinum
    criteria_count = db.Column(db.Integer, nullable=False)  # Number of actions needed to earn this badge
    icon = db.Column(db.String(255), nullable=False)  # Path to badge icon
    
    def to_dict(self):
        """Convert badge to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'type': self.type,
            'level': self.level,
            'criteria_count': self.criteria_count,
            'icon': self.icon
        }


class UserActivity(db.Model):
    """User activity tracking for badge awards"""
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    document_id = db.Column(db.String(36), db.ForeignKey('document.id', ondelete='CASCADE'), nullable=True)
    activity_type = db.Column(db.String(50), nullable=False)  # view, search, upload, summarize
    performed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with user
    user = db.relationship('User', backref=db.backref('activities', lazy='dynamic', cascade='all, delete-orphan'))
    
    def to_dict(self):
        """Convert activity to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'document_id': self.document_id,
            'activity_type': self.activity_type,
            'performed_at': self.performed_at.isoformat()
        }


class Document(db.Model):
    """Document model for storing uploaded documents"""
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = db.Column(db.String(255), nullable=False)
    friendly_name = db.Column(db.String(255), nullable=True)  # User-friendly document name
    filepath = db.Column(db.String(512), nullable=False)
    text = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Summary and key points generated by AI
    summary = db.Column(db.Text, nullable=True)
    key_points = db.Column(db.Text, nullable=True)
    summary_generated_at = db.Column(db.DateTime, nullable=True)
    
    # Personalized relevance reasons for different teams
    relevance_reasons = db.Column(db.JSON, nullable=True)
    
    # User who uploaded this document
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Relationship with activities
    activities = db.relationship('UserActivity', backref='document', 
                               cascade='all, delete-orphan', 
                               passive_deletes=True)
    
    def to_dict(self):
        """Convert document to dictionary"""
        return {
            'id': self.id,
            'filename': self.filename,
            'friendly_name': self.friendly_name,
            'filepath': self.filepath,
            'text': self.text,
            'category': self.category,
            'uploaded_at': self.uploaded_at.isoformat(),
            'user_id': self.user_id,
            'summary': self.summary,
            'key_points': self.key_points,
            'relevance_reasons': self.relevance_reasons,
            'summary_generated_at': self.summary_generated_at.isoformat() if self.summary_generated_at else None
        }
        
# Association table for user-badge relationship (many-to-many)
user_badges = db.Table('user_badges',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('badge_id', db.Integer, db.ForeignKey('badge.id'), primary_key=True),
    db.Column('earned_at', db.DateTime, default=datetime.utcnow)
)

# Add many-to-many relationship between User and Badge
User.badges = db.relationship('Badge', secondary=user_badges, 
                             backref=db.backref('users', lazy='dynamic'))