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
    TEAM_DIGITAL_ENGAGEMENT = 'Digital Engagement'
    TEAM_DIGITAL_PRODUCT = 'Digital Product'
    TEAM_NEXTGEN_PRODUCTS = 'NextGen Products'
    TEAM_PRODUCT_INSIGHTS = 'Product Insights'
    TEAM_PRODUCT_TESTING = 'Product Testing'
    TEAM_SERVICE_TECH = 'Service Technology'
    
    # Team choices in alphabetical order for display
    TEAM_CHOICES = sorted([
        TEAM_DIGITAL_ENGAGEMENT,
        TEAM_DIGITAL_PRODUCT,
        TEAM_NEXTGEN_PRODUCTS,
        TEAM_PRODUCT_INSIGHTS,
        TEAM_PRODUCT_TESTING,
        TEAM_SERVICE_TECH
    ])
    
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
    TYPE_LIKER = 'liker'          # For liking documents
    
    BADGE_TYPES = [
        TYPE_READER,
        TYPE_SEARCHER,
        TYPE_CONTRIBUTOR,
        TYPE_SUMMARIZER,
        TYPE_LIKER
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
    """Document model for storing uploaded documents, web links, and YouTube videos"""
    
    # Content type constants
    TYPE_PDF = 'pdf'
    TYPE_WEBLINK = 'weblink'
    TYPE_YOUTUBE = 'youtube'
    
    CONTENT_TYPES = [
        TYPE_PDF,
        TYPE_WEBLINK,
        TYPE_YOUTUBE
    ]
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = db.Column(db.String(255), nullable=False)
    friendly_name = db.Column(db.String(255), nullable=True)  # User-friendly document name
    filepath = db.Column(db.String(512), nullable=True)  # Path for PDFs, URL for web links/videos
    text = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    file_available = db.Column(db.Boolean, default=True)  # Flag to indicate if the file is available
    
    # Content type and source information
    content_type = db.Column(db.String(20), default=TYPE_PDF, nullable=False)  # pdf, weblink, youtube
    source_url = db.Column(db.String(1024), nullable=True)  # Original URL for web links/YouTube
    thumbnail_url = db.Column(db.String(1024), nullable=True)  # Thumbnail URL for all document types
    youtube_video_id = db.Column(db.String(20), nullable=True)  # YouTube video ID for embedding
    thumbnail_generated = db.Column(db.Boolean, default=False)  # Flag to track if thumbnail was auto-generated
    custom_thumbnail = db.Column(db.Boolean, default=False)  # Flag to track if thumbnail was uploaded by admin
    
    # Featured flag for homepage promotion
    is_featured = db.Column(db.Boolean, default=False)  # Flag to indicate if document is featured on homepage
    featured_at = db.Column(db.DateTime, nullable=True)  # When it was featured
    
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
                               
    def check_file_exists(self):
        """Check if the file associated with this document exists"""
        import os
        import glob
        
        # First check if file exists at specified filepath
        if os.path.exists(self.filepath):
            return True
            
        # Check with current working directory as base (for relative paths)
        cwd_path = os.path.join(os.getcwd(), self.filepath.lstrip('./'))
        if os.path.exists(cwd_path):
            return True
            
        # Check in uploads folder with the filename
        uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
        if os.path.exists(os.path.join(uploads_dir, os.path.basename(self.filepath))):
            return True
            
        # Fallback: Check for any file with matching name pattern
        possible_files = glob.glob(os.path.join(uploads_dir, f"*{self.filename}"))
        if possible_files:
            return True
            
        return False
    
    def to_dict(self):
        """Convert document to dictionary"""
        # Do NOT clean HTML from the summary and key points to preserve formatting
        # These fields will be marked as |safe in the templates
        summary_html = self.summary if self.summary else None
        key_points_html = self.key_points if self.key_points else None
        
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
                        'relevance_reason': relevance_text
                    }
                else:
                    # If it's a string, keep it as is (don't clean HTML as there shouldn't be any)
                    cleaned_relevance[team] = reason
        else:
            cleaned_relevance = self.relevance_reasons
        
        # Check if file is available and update the flag (only for PDF files)
        file_exists = True
        if self.content_type == self.TYPE_PDF:
            file_exists = self.check_file_exists()
            if self.file_available != file_exists:
                self.file_available = file_exists
                # This update doesn't commit, only marks the object as dirty
        
        # For web links and YouTube videos, check if the source URL is valid
        if self.content_type in [self.TYPE_WEBLINK, self.TYPE_YOUTUBE]:
            file_exists = bool(self.source_url)
            
        return {
            'id': self.id,
            'filename': self.filename,
            'friendly_name': self.friendly_name,
            'filepath': self.filepath,
            'text': self.text,
            'category': self.category,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'user_id': self.user_id,
            'summary': summary_html,
            'key_points': key_points_html,
            'relevance_reasons': cleaned_relevance,
            'summary_generated_at': self.summary_generated_at.isoformat() if self.summary_generated_at else None,
            'relative_time': relative_time,  # Add relative time as a new field
            'file_available': self.file_available,  # Include file availability
            'content_type': self.content_type,
            'source_url': self.source_url,
            'thumbnail_url': self.thumbnail_url,
            'youtube_video_id': self.youtube_video_id,
            'thumbnail_generated': self.thumbnail_generated,
            'custom_thumbnail': self.custom_thumbnail,
            'is_featured': self.is_featured,
            'featured_at': self.featured_at.isoformat() if self.featured_at else None
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
            
        return {
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
        
# Recommendation system models
class TeamResponsibility(db.Model):
    """Team responsibility descriptions for recommendation engine"""
    __tablename__ = 'team_responsibility'
    
    id = db.Column(db.Integer, primary_key=True)
    team_name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<TeamResponsibility {self.team_name}>"
        
    def to_dict(self):
        """Convert team responsibility to dictionary"""
        return {
            'id': self.id,
            'team_name': self.team_name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class UserDismissedRecommendation(db.Model):
    """Records of recommendations dismissed by users"""
    __tablename__ = 'user_dismissed_recommendation'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    document_id = db.Column(db.String(36), db.ForeignKey('document.id', ondelete='CASCADE'), nullable=False)
    dismissed_at = db.Column(db.DateTime, default=datetime.utcnow)
    feedback = db.Column(db.String(255), nullable=True)  # Optional feedback on why dismissed
    
    # Feedback type flags
    not_relevant = db.Column(db.Boolean, default=False)  # Not relevant to my work
    already_seen = db.Column(db.Boolean, default=False)   # Already seen this content elsewhere
    not_interested = db.Column(db.Boolean, default=False) # Not interested in this topic
    
    # Relationships
    user = db.relationship('User', backref=db.backref('dismissed_recommendations', lazy='dynamic'))
    document = db.relationship('Document', backref=db.backref('dismissed_by', lazy='dynamic'))
    
    def __repr__(self):
        return f"<UserDismissedRecommendation {self.user_id} - {self.document_id}>"
        
    def to_dict(self):
        """Convert dismissed recommendation to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'document_id': self.document_id,
            'dismissed_at': self.dismissed_at.isoformat() if self.dismissed_at else None,
            'feedback': self.feedback,
            'not_relevant': self.not_relevant,
            'already_seen': self.already_seen,
            'not_interested': self.not_interested
        }


class DocumentLike(db.Model):
    """Track user likes on documents"""
    __tablename__ = 'document_like'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    document_id = db.Column(db.String(36), db.ForeignKey('document.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('document_likes', lazy='dynamic'))
    document = db.relationship('Document', backref=db.backref('likes', lazy='dynamic'))
    
    # Ensure users can only like a document once
    __table_args__ = (
        db.UniqueConstraint('user_id', 'document_id', name='unique_document_like'),
    )
    
    def __repr__(self):
        return f"<DocumentLike {self.user_id} - {self.document_id}>"
        
    def to_dict(self):
        """Convert like to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'document_id': self.document_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }