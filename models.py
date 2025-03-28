from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
import json
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from utils.text_processor import clean_html, format_timestamp

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
        # Clean HTML from the summary and key points
        cleaned_summary = clean_html(self.summary) if self.summary else None
        cleaned_key_points = clean_html(self.key_points) if self.key_points else None
        
        # Format timestamps
        relative_time = format_timestamp(self.uploaded_at) if self.uploaded_at else None
        
        # Process relevance reasons if they exist
        if self.relevance_reasons and isinstance(self.relevance_reasons, dict):
            cleaned_relevance = {}
            for team, reason in self.relevance_reasons.items():
                # Check if the reason is a dictionary with 'relevance_reason' key
                if isinstance(reason, dict) and 'relevance_reason' in reason:
                    relevance_text = reason.get('relevance_reason', '')
                    cleaned_relevance[team] = {
                        'relevance_reason': clean_html(relevance_text)
                    }
                else:
                    # If it's a string, clean it directly
                    cleaned_relevance[team] = clean_html(reason) if isinstance(reason, str) else reason
        else:
            cleaned_relevance = self.relevance_reasons
        
        return {
            'id': self.id,
            'filename': self.filename,
            'friendly_name': self.friendly_name,
            'filepath': self.filepath,
            'text': self.text,
            'category': self.category,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'user_id': self.user_id,
            'summary': cleaned_summary,
            'key_points': cleaned_key_points,
            'relevance_reasons': cleaned_relevance,
            'summary_generated_at': self.summary_generated_at.isoformat() if self.summary_generated_at else None,
            'relative_time': relative_time  # Add relative time as a new field
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

class SearchLog(db.Model):
    """Search log for admin analytics"""
    
    id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.String(255), nullable=False)
    category_filter = db.Column(db.String(50), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    team_specialization = db.Column(db.String(100), nullable=True)
    executed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Search metrics
    results_count = db.Column(db.Integer, nullable=False, default=0)
    duration_seconds = db.Column(db.Float, nullable=True)
    documents_searched = db.Column(db.Integer, nullable=True)
    
    # Success metrics
    highest_relevance_score = db.Column(db.Float, nullable=True)
    avg_relevance_score = db.Column(db.Float, nullable=True)
    
    # Relationship with user
    user = db.relationship('User', backref=db.backref('searches', lazy='dynamic'))
    # Relationship with feedback
    feedback = db.relationship('SearchFeedback', backref='search_log', uselist=False, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert search log to dictionary"""
        user_data = None
        if self.user:
            user_data = {
                'id': self.user.id,
                'email': self.user.email,
                'name': self.user.name,
                'team_specialization': self.user.team_specialization
            }
        
        result = {
            'id': self.id,
            'query': self.query,
            'category_filter': self.category_filter,
            'user_id': self.user_id,
            'team_specialization': self.team_specialization,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'results_count': self.results_count,
            'duration_seconds': self.duration_seconds,
            'documents_searched': self.documents_searched,
            'highest_relevance_score': self.highest_relevance_score,
            'avg_relevance_score': self.avg_relevance_score,
            'user': user_data
        }
        
        if self.feedback:
            result['feedback'] = self.feedback.to_dict()
            
        return result
        
        
class SearchFeedback(db.Model):
    """User feedback on search results quality"""
    
    # Rating choices
    RATING_POOR = 1
    RATING_FAIR = 2
    RATING_GOOD = 3
    RATING_EXCELLENT = 4
    
    RATING_CHOICES = {
        RATING_POOR: 'Poor',
        RATING_FAIR: 'Fair',
        RATING_GOOD: 'Good',
        RATING_EXCELLENT: 'Excellent'
    }
    
    id = db.Column(db.Integer, primary_key=True)
    search_log_id = db.Column(db.Integer, db.ForeignKey('search_log.id', ondelete='CASCADE'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-4 scale (Poor, Fair, Good, Excellent)
    comment = db.Column(db.Text, nullable=True)     # Optional comment from user
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # What aspects of search were helpful
    helpful_relevance = db.Column(db.Boolean, default=False)   # Results were relevant
    helpful_speed = db.Column(db.Boolean, default=False)       # Search was fast
    helpful_insights = db.Column(db.Boolean, default=False)    # AI insights were helpful
    helpful_diversity = db.Column(db.Boolean, default=False)   # Good variety of results
    
    @property
    def rating_text(self):
        """Return the text representation of the rating"""
        return self.RATING_CHOICES.get(self.rating, 'Unknown')
    
    def to_dict(self):
        """Convert feedback to dictionary"""
        return {
            'id': self.id,
            'search_log_id': self.search_log_id,
            'rating': self.rating,
            'rating_text': self.RATING_CHOICES.get(self.rating, 'Unknown'),
            'comment': self.comment,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'helpful_aspects': {
                'relevance': self.helpful_relevance,
                'speed': self.helpful_speed,
                'insights': self.helpful_insights,
                'diversity': self.helpful_diversity
            }
        }