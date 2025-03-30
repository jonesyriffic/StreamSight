import os
import logging
import uuid
import re
import glob
from functools import wraps
from datetime import datetime, timedelta
from flask import Flask, request, render_template, redirect, url_for, flash, jsonify, session, abort, send_from_directory
from werkzeug.utils import secure_filename
import json
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from email_validator import validate_email, EmailNotValidError
from sqlalchemy import func
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import BooleanField, StringField, PasswordField, TextAreaField, SelectField, RadioField, ValidationError, HiddenField
from wtforms.validators import DataRequired, Length, Email, EqualTo, Optional

from utils.pdf_processor import extract_text_from_pdf
from utils.ai_search_gemini import search_documents
from utils.gemini_ai import generate_document_summary, generate_friendly_name
from utils.relevance_generator_gemini import generate_relevance_reasons
from utils.badge_service import BadgeService
from utils.recommendation_service import get_user_recommendations, dismiss_recommendation, reset_dismissed_recommendations
from utils.text_processor import clean_html, format_timestamp
from models import db, Document, User, Badge, UserActivity, SearchLog, TeamResponsibility, UserDismissedRecommendation, DocumentLike
from statistics import mean

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Set maximum file upload size to 100MB
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB in bytes

# Configure upload folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max upload size
app.config['MAX_BUFFER_SIZE'] = 100 * 1024 * 1024  # 100MB buffer size for large file uploads
app.config['REQUEST_TIMEOUT'] = 300  # 5 minutes timeout for large uploads

# Configure database
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
    'connect_args': {
        'sslmode': 'prefer'
    }
}
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Add custom Jinja filter for newlines to <br> and handle markdown for bold
@app.template_filter('nl2br')
def nl2br(value):
    """
    Convert newlines to <br> tags and process basic Markdown-style formatting
    - Converts **text** to <strong>text</strong>
    - Preserves line breaks
    """
    if not value:
        return ""
    from markupsafe import Markup
    import re
    
    # Replace **text** with <strong>text</strong>
    value = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', value)
    
    # Convert newlines to <br>
    value = value.replace('\n', '<br>')
    
    return Markup(value)

# Add custom Jinja filter for humanized timestamps
@app.template_filter('humanize')
def humanize_timestamp(dt):
    """
    Convert datetime to a human-friendly relative time string
    E.g., "2 days ago", "5 minutes ago", "just now"
    """
    if not dt:
        return ""
    
    # Convert string to datetime if needed
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return dt  # Return as-is if we can't parse it
    
    from markupsafe import Markup
    now = datetime.utcnow()
    
    try:
        diff = now - dt
        
        # Handle future dates
        if diff.total_seconds() < 0:
            return "in the future"
        
        # Less than a minute
        if diff.total_seconds() < 60:
            return "just now"
        
        # Less than an hour
        if diff.total_seconds() < 3600:
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes} {'minute' if minutes == 1 else 'minutes'} ago"
        
        # Less than a day
        if diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() / 3600)
            return f"{hours} {'hour' if hours == 1 else 'hours'} ago"
        
        # Less than a week
        if diff.total_seconds() < 604800:
            days = int(diff.total_seconds() / 86400)
            return f"{days} {'day' if days == 1 else 'days'} ago"
        
        # Less than a month
        if diff.total_seconds() < 2592000:
            weeks = int(diff.total_seconds() / 604800)
            return f"{weeks} {'week' if weeks == 1 else 'weeks'} ago"
        
        # Less than a year
        if diff.total_seconds() < 31536000:
            months = int(diff.total_seconds() / 2592000)
            return f"{months} {'month' if months == 1 else 'months'} ago"
        
        # More than a year
        years = int(diff.total_seconds() / 31536000)
        return f"{years} {'year' if years == 1 else 'years'} ago"
    except Exception:
        # If any error occurs, just return the timestamp as is
        return str(dt)
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database tables
with app.app_context():
    db.create_all()
    
    # Run content type migration to add columns for web links and YouTube videos
    try:
        from migrate_document_types import run_migration
        run_migration()
        logger.info("Document content type columns set up successfully")
    except Exception as e:
        logger.error(f"Error setting up document content type columns: {str(e)}")
    
    # Check if any admin users exist, if not create one
    admin_exists = User.query.filter_by(is_admin=True).first()
    if not admin_exists:
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@insights.com')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'adminpassword')
        admin_user = User(
            email=admin_email,
            name='System Administrator',
            is_active=True,
            is_approved=True,
            is_admin=True,
            can_upload=True,
            team_specialization=User.TEAM_DIGITAL_PRODUCT
        )
        admin_user.set_password(admin_password)
        db.session.add(admin_user)
        db.session.commit()
        logger.info(f"Created admin user: {admin_email}")

# Admin access decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required', 'danger')
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function

# Access check for approved users
def approved_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if not current_user.is_approved and not current_user.is_admin:
            flash('Your account is pending approval', 'warning')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
           
class MaxFileSize:
    """
    Custom validator for limiting maximum file size for uploads
    """
    def __init__(self, max_size=16*1024*1024):
        self.max_size = max_size
        
    def __call__(self, form, field):
        if field.data:
            field.data.seek(0, os.SEEK_END)
            file_size = field.data.tell()
            field.data.seek(0)
            
            if file_size > self.max_size:
                size_in_mb = self.max_size / (1024*1024)
                raise ValidationError(f'File size exceeds the maximum limit of {size_in_mb} MB.')

class ReuploadDocumentForm(FlaskForm):
    file = FileField('PDF File', validators=[
        FileRequired(),
        FileAllowed(['pdf'], 'PDF files only!'),
        MaxFileSize(max_size=100*1024*1024)  # 100MB maximum file size
    ])
    keep_original_name = BooleanField('Keep original filename', default=True)
    reprocess_text = BooleanField('Extract text from new PDF', default=True)
    regenerate_insights = BooleanField('Regenerate AI insights', default=False)
    friendly_name = StringField('Document Name', validators=[Optional(), Length(max=255)], 
                               description='Optionally provide a readable name for this document')

class EditDocumentForm(FlaskForm):
    """Form for editing document metadata"""
    friendly_name = StringField('Document Name', validators=[
        DataRequired(message='Document name is required'), 
        Length(max=255, message='Document name cannot exceed 255 characters')
    ])
    category = SelectField('Category', validators=[DataRequired()], choices=[
        ('Industry Insights', 'Industry Insights'),
        ('Technology News', 'Technology News'),
        ('Product Management', 'Product Management'),
        ('Customer Service', 'Customer Service')
    ])

@app.route('/')
@login_required
def index():
    # Get all documents and categories for statistics
    documents = Document.query.order_by(Document.uploaded_at.desc()).all()
    categories = db.session.query(Document.category).distinct().all()
    categories = [category[0] for category in categories]
    
    # Get statistics for dashboard
    total_documents = Document.query.count()
    total_categories = len(categories)
    
    # Calculate uploads this month
    from datetime import datetime
    current_month = datetime.utcnow().month
    current_year = datetime.utcnow().year
    upload_month = Document.query.filter(
        db.extract('month', Document.uploaded_at) == current_month,
        db.extract('year', Document.uploaded_at) == current_year
    ).count()
    
    # Get only recent documents for the dashboard
    recent_documents = Document.query.order_by(Document.uploaded_at.desc()).limit(5).all()
    
    # Initialize recommended documents as an empty list
    recommended_documents = []
    
    # If user is logged in, get personalized recommendations using the recommendation service
    if current_user.is_authenticated:
        # Get recommended documents from the recommendation service
        recommended_documents = get_user_recommendations(current_user)
        
        # If no recommendations returned, fall back to most recent documents
        if not recommended_documents:
            recommended_documents = Document.query.filter_by(file_available=True) \
                .order_by(Document.uploaded_at.desc()).limit(3).all()
    
    return render_template('index.html', 
                          categories=categories,
                          total_documents=total_documents,
                          total_categories=total_categories,
                          upload_month=upload_month,
                          recent_documents=[doc.to_dict() for doc in recent_documents],
                          recommended_documents=[doc.to_dict() for doc in recommended_documents])

@app.route('/login', methods=['GET', 'POST'])
def login():
    # If already logged in, redirect to index
    if current_user.is_authenticated:
        # Check if user needs to change password first
        if current_user.needs_password_change:
            flash('You need to change your temporary password before continuing.', 'warning')
            return redirect(url_for('change_password'))
        return redirect(url_for('index'))
    
    # Handle login form submission
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        # Find user by email
        user = User.query.filter_by(email=email).first()
        
        # Check if user exists and password is correct
        if user and user.check_password(password):
            # Check account status
            if not user.is_active:
                flash('Your account has been deactivated. Please contact an administrator.', 'danger')
                return redirect(url_for('login'))
            
            if not user.is_approved:
                flash('Your account is pending approval. Please check back later.', 'warning')
                return redirect(url_for('login'))
                
            # Update last login time
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            login_user(user, remember=remember)
            
            # Check if user needs to change password
            if user.needs_password_change:
                flash('You must change your temporary password before continuing.', 'warning')
                return redirect(url_for('change_password'))
                
            flash('Login successful!', 'success')
            
            # Redirect to requested page or index
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    # If already logged in, redirect to index
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    # Handle registration form submission
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        name = request.form.get('name', '')
        
        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')
        
        # Validate email
        try:
            valid = validate_email(email)
            email = valid.email
        except EmailNotValidError as e:
            flash(f'Invalid email: {str(e)}', 'danger')
            return render_template('register.html')
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return render_template('register.html')
        
        # Create new user
        new_user = User(email=email, name=name)
        new_user.set_password(password)
        
        # Auto-approve users with Sky, NBCUniversal, or andrewjones.uk email domains
        if (email.lower().endswith('@sky.uk') or 
            email.lower().endswith('@nbcuni.com') or 
            email.lower().endswith('@andrewjones.uk')):
            new_user.is_approved = True
            new_user.approved_at = datetime.utcnow()
            # Don't automatically grant upload permission - this is limited to admins
            logger.info(f"Auto-approved user with email domain: {email}")
            flash_message = 'Registration successful! Your account has been automatically approved. Please log in.'
        else:
            flash_message = 'Registration successful! Your account is pending approval. Please check back later.'
        
        # Add to database
        db.session.add(new_user)
        db.session.commit()
        
        flash(flash_message, 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Get form data
        team_specialization = request.form.get('team_specialization')
        
        # Update user profile
        current_user.team_specialization = team_specialization if team_specialization else None
        db.session.commit()
        
        flash('Profile updated successfully', 'success')
        return redirect(url_for('profile'))
    
    # Get user badges for the profile page
    user_badges = BadgeService.get_user_badges(current_user.id)
    
    # Pass team choices and badges for the template
    return render_template('profile.html', 
                          team_choices=User.TEAM_CHOICES,
                          badges=user_badges)

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    # Get form data
    team_specialization = request.form.get('team_specialization')
    
    # Update user profile
    current_user.team_specialization = team_specialization if team_specialization else None
    db.session.commit()
    
    flash('Profile updated successfully', 'success')
    return redirect(url_for('profile'))

@app.route('/upload', methods=['GET'])
@login_required
@approved_required
def upload_page():
    # Check if user has upload permission
    if not current_user.can_upload and not current_user.is_admin:
        flash('You do not have permission to upload documents. Please contact an administrator.', 'danger')
        return redirect(url_for('index'))
    
    # Get document categories for the dropdown
    categories = [
        'auto',  # Auto-detect option (listed first)
        'Industry Insights',
        'Technology News',
        'Product Management',
        'Customer Service'
    ]
    
    # Get available content types from Document model
    content_types = Document.CONTENT_TYPES
    
    return render_template('upload.html', 
                          categories=categories,
                          content_types=content_types)

@app.route('/library')
@login_required
def library():
    # Get filter parameters
    category_filter = request.args.get('category', 'all')
    type_filter = request.args.get('type', 'all')
    sort_by = request.args.get('sort', 'date_desc')
    
    # Query base
    query = Document.query
    
    # Apply category filter if not 'all'
    if category_filter != 'all':
        query = query.filter_by(category=category_filter)
    
    # Apply content type filter if not 'all'
    if type_filter != 'all':
        query = query.filter_by(content_type=type_filter)
    
    # Apply sorting
    if sort_by == 'date_desc':
        query = query.order_by(Document.uploaded_at.desc())
    elif sort_by == 'date_asc':
        query = query.order_by(Document.uploaded_at.asc())
    elif sort_by == 'name_asc':
        query = query.order_by(Document.filename.asc())
    elif sort_by == 'name_desc':
        query = query.order_by(Document.filename.desc())
    
    # Execute query
    documents = query.all()
    
    # Get all categories for the filter dropdown
    categories = db.session.query(Document.category).distinct().all()
    categories = [category[0] for category in categories]
    
    return render_template('library.html',
                          documents=[doc.to_dict() for doc in documents],
                          categories=categories,
                          category_filter=category_filter,
                          type_filter=type_filter,
                          sort_by=sort_by)

@app.route('/upload', methods=['POST'])
@login_required
@approved_required
def upload_document():
    """Handle document upload for different content types (PDF, web links, YouTube videos)"""
    # Check if user has upload permission
    if not current_user.can_upload and not current_user.is_admin:
        flash('You do not have permission to upload documents. Please contact an administrator.', 'danger')
        return redirect(url_for('index'))
    
    # Import content processor functions
    from utils.content_processor import (
        process_pdf_upload, 
        process_weblink, 
        process_youtube_video
    )
    
    # Get the content type from the form
    content_type = request.form.get('content_type', Document.TYPE_PDF)
    category = request.form.get('category', 'Uncategorized')
    successful_uploads = 0
    failed_uploads = 0
    earned_badges = set()
    
    # Process based on content type
    if content_type == Document.TYPE_WEBLINK:
        # Process web link
        url = request.form.get('url', '')
        if not url:
            flash('Please enter a valid URL', 'danger')
            return redirect(url_for('upload_page'))
            
        try:
            logger.info(f"Processing web link: {url}")
            document, message, status_code = process_weblink(
                url=url,
                category=category,
                user_id=current_user.id,
                db=db,
                Document=Document
            )
            
            if document and status_code == 200:
                # Process document (generate relevance, summary, track badges)
                _process_uploaded_document(document, current_user.id, earned_badges)
                successful_uploads += 1
                flash(message, 'success')
                
                # Add additional message if auto-category was used
                if category == 'auto':
                    flash(f"Category auto-detection used: '{document.category}'", 'info')
            else:
                failed_uploads += 1
                flash(message, 'danger')
                
        except Exception as e:
            logger.error(f"Error processing web link: {str(e)}")
            failed_uploads += 1
            flash(f"Error processing web link: {str(e)}", 'danger')
            
    elif content_type == Document.TYPE_YOUTUBE:
        # Process YouTube video
        url = request.form.get('url', '')
        if not url:
            flash('Please enter a valid YouTube URL', 'danger')
            return redirect(url_for('upload_page'))
            
        try:
            logger.info(f"Processing YouTube video: {url}")
            document, message, status_code = process_youtube_video(
                url=url,
                category=category,
                user_id=current_user.id,
                db=db,
                Document=Document
            )
            
            if document and status_code == 200:
                # Process document (generate relevance, summary, track badges)
                _process_uploaded_document(document, current_user.id, earned_badges)
                successful_uploads += 1
                flash(message, 'success')
                
                # Add additional message if auto-category was used
                if category == 'auto':
                    flash(f"Category auto-detection used: '{document.category}'", 'info')
            else:
                failed_uploads += 1
                flash(message, 'danger')
                
        except Exception as e:
            logger.error(f"Error processing YouTube video: {str(e)}")
            failed_uploads += 1
            flash(f"Error processing YouTube video: {str(e)}", 'danger')
            
    elif content_type == Document.TYPE_PDF:
        # Process PDF uploads
        if 'files' not in request.files:
            flash('No files selected', 'danger')
            return redirect(url_for('upload_page'))
            
        try:
            files = request.files.getlist('files')
        except Exception as e:
            logger.error(f"Error accessing uploaded files: {str(e)}")
            flash('Error processing upload request. The server might have timed out due to large file size.', 'danger')
            return redirect(url_for('upload_page'))
            
        if len(files) == 0 or all(file.filename == '' for file in files):
            flash('No selected file(s)', 'danger')
            return redirect(url_for('upload_page'))
            
        # Process each PDF file
        large_file_warning_shown = False
        
        for file in files:
            if file and file.filename != '' and allowed_file(file.filename):
                # Check file size and show warning if needed
                file.seek(0, os.SEEK_END)
                file_size = file.tell()
                file.seek(0)  # Reset file position
                
                size_mb = file_size / (1024 * 1024)
                if size_mb > 50 and not large_file_warning_shown:
                    flash(f"Processing large file ({size_mb:.1f} MB). This may take several minutes. Please be patient.", "warning")
                    large_file_warning_shown = True
                
                # Process the PDF file
                try:
                    logger.info(f"Processing PDF file: {file.filename}")
                    document, message, status_code = process_pdf_upload(
                        uploaded_file=file,
                        filename=secure_filename(file.filename),
                        category=category,
                        user_id=current_user.id,
                        db=db,
                        Document=Document
                    )
                    
                    if document and status_code == 200:
                        # Process document (generate relevance, summary, track badges)
                        _process_uploaded_document(document, current_user.id, earned_badges)
                        successful_uploads += 1
                        
                        # Add additional message if auto-category was used
                        if category == 'auto':
                            flash(f"Category auto-detection used: '{document.category}'", 'info')
                    else:
                        failed_uploads += 1
                        flash(message, 'warning')
                        
                except Exception as e:
                    logger.error(f"Error processing PDF file '{file.filename}': {str(e)}")
                    failed_uploads += 1
                    
                    # Check if it's an OpenAI API error
                    if "OpenAI API" in str(e):
                        logger.error(f"OpenAI API error detected during upload: {str(e)}")
                        flash("There was an issue with the AI service. Document was uploaded but without AI processing.", "warning")
                    else:
                        flash(f"Error processing file '{file.filename}': {str(e)}", 'danger')
            else:
                # Skip invalid files
                if file and file.filename != '':
                    failed_uploads += 1
                    flash(f"Invalid file type: {file.filename}. Only PDF files are allowed.", 'warning')
    else:
        # Invalid content type
        flash('Invalid content type', 'danger')
        return redirect(url_for('upload_page'))
    
    # Show badge notifications
    for badge_name, badge_level in earned_badges:
        flash(f"Congratulations! You've earned the {badge_name} badge ({badge_level})!", 'success')
    
    # Show upload results
    if successful_uploads > 0:
        if successful_uploads == 1:
            flash(f'1 document was uploaded successfully!', 'success')
        else:
            flash(f'{successful_uploads} documents were uploaded successfully!', 'success')
    
    if failed_uploads > 0:
        if failed_uploads == 1:
            flash(f'1 document failed to upload. Please check the file and try again.', 'warning')
        else:
            flash(f'{failed_uploads} documents failed to upload. Please check the files and try again.', 'warning')
    
    if successful_uploads == 0 and failed_uploads == 0:
        flash('No valid files were selected for upload.', 'warning')
        return redirect(url_for('upload_page'))
    
    return redirect(url_for('library'))


def _process_uploaded_document(document, user_id, earned_badges):
    """
    Helper function to process an uploaded document:
    - Generate relevance reasons
    - Generate summary and key points
    - Track badge activity
    
    Args:
        document: Document object
        user_id: ID of the current user
        earned_badges: Set to add earned badges to
    """
    # Generate relevance reasons
    try:
        from utils.relevance_generator import generate_relevance_reasons
        relevance_reasons = generate_relevance_reasons(document)
        document.relevance_reasons = relevance_reasons
        db.session.commit()
        logger.info(f"Generated relevance reasons for document {document.id}")
    except Exception as e:
        logger.error(f"Error generating relevance reasons: {str(e)}")
    
    # Generate summary
    try:
        if document.content_type == Document.TYPE_PDF:
            # Use document_ai for PDFs
            from utils.document_ai import generate_document_summary
            summary_result = generate_document_summary(document.id)
            if summary_result and summary_result.get('success'):
                logger.info(f"Generated summary for document {document.id}")
        else:
            # Use content_processor for web links and YouTube videos
            from utils.content_processor import generate_content_summary
            summary_result = generate_content_summary(document, db)
            if summary_result:
                logger.info(f"Generated summary for document {document.id}")
    except Exception as e:
        logger.error(f"Error generating document summary: {str(e)}")
    
    # Track badge activity
    try:
        from utils.badge_service import BadgeService
        new_badges = BadgeService.track_activity(
            user_id=user_id,
            activity_type='upload',
            document_id=document.id
        )
        
        # Add earned badges to the set
        if new_badges and new_badges.get('new_badges'):
            for badge in new_badges.get('new_badges'):
                earned_badges.add((badge['name'], badge['level']))
    except Exception as e:
        logger.error(f"Error tracking badge activity: {str(e)}")

@app.route('/search', methods=['GET'])
@login_required
def search():
    query = request.args.get('query', '')
    category_filter = request.args.get('category', 'all')
    
    logger.info(f"Search request received - Query: '{query}', Category filter: '{category_filter}'")
    
    if not query:
        all_categories = db.session.query(Document.category).distinct().all()
        categories = [category[0] for category in all_categories]
        logger.info("Empty search query, returning empty results")
        return render_template('search_results.html', results=[], query='', categories=categories)
    
    try:
        # Check if the Gemini API key exists
        if not os.environ.get("GEMINI_API_KEY"):
            logger.error("Gemini API key is missing")
            raise Exception("Gemini API key is not configured")
        
        logger.info("Building document repository for search")
        # Get document repository for search
        document_repository = {
            'get_all_documents': lambda: [doc.to_dict() for doc in Document.query.all()],
            'get_documents_by_category': lambda category: [
                doc.to_dict() for doc in Document.query.filter_by(category=category).all()
            ],
            'get_document': lambda doc_id: Document.query.get(doc_id).to_dict() if Document.query.get(doc_id) else None
        }
        
        # Get the document count
        if category_filter and category_filter.lower() != "all":
            doc_count = Document.query.filter_by(category=category_filter).count()
        else:
            doc_count = Document.query.count()
            
        logger.info(f"Found {doc_count} documents to search through")
        
        if doc_count == 0:
            logger.warning("No documents found to search through")
            all_categories = db.session.query(Document.category).distinct().all()
            categories = [category[0] for category in all_categories]
            return render_template('search_results.html', 
                                  results=[], 
                                  query=query,
                                  error="No documents found to search through. Please upload some documents first.",
                                  selected_category=category_filter,
                                  categories=categories)
        
        logger.info("Performing search using Gemini API")
        try:
            search_result = search_documents(query, document_repository, category_filter)
            results = search_result['results']
            search_info = search_result['search_info']
            
            logger.info(f"Search complete - Results found: {search_info['results_found']}, Time: {search_info['elapsed_time']}s")
            
            # Debug log to check the structure
            if results:
                logger.debug(f"First result structure: {json.dumps(results[0], default=str)}")
                
            # Generate AI response based on search results
            try:
                logger.info(f"Generating AI response for query: '{query}'")
                from utils.ai_search_gemini import generate_search_response
                ai_response = generate_search_response(query, search_result)
                logger.info(f"AI response generated successfully ({len(ai_response)} characters)")
            except Exception as ai_error:
                logger.error(f"Error generating AI response: {str(ai_error)}")
                ai_response = "I couldn't generate a response based on the search results at this time. Please review the document excerpts below for relevant information."
        except Exception as search_error:
            logger.error(f"Error during document search: {str(search_error)}")
            import traceback
            logger.error(f"Search traceback: {traceback.format_exc()}")
            
            # Re-raise to be caught by the outer try/except
            raise search_error
        
        # Track search information in the search log
        try:
            # Calculate success metrics if we have results
            highest_relevance_score = None
            avg_relevance_score = None
            
            if results:
                relevance_scores = [result.get('relevance_score', 0) for result in results]
                if relevance_scores:
                    highest_relevance_score = max(relevance_scores)
                    avg_relevance_score = mean(relevance_scores)
            
            # Create a search log entry
            search_log = SearchLog(
                query=query,
                category_filter=category_filter if category_filter != 'all' else None,
                user_id=current_user.id if current_user.is_authenticated else None,
                team_specialization=current_user.team_specialization if current_user.is_authenticated else None,
                results_count=len(results),
                duration_seconds=search_info.get('elapsed_time'),
                documents_searched=search_info.get('documents_searched'),
                highest_relevance_score=highest_relevance_score,
                avg_relevance_score=avg_relevance_score
            )
            
            db.session.add(search_log)
            db.session.commit()
            logger.info(f"Search log entry saved with ID: {search_log.id}")
        except Exception as log_error:
            logger.error(f"Error saving search log: {str(log_error)}")
            # Don't stop the whole process if logging fails
        
        # Track search activity if user is logged in
        if current_user.is_authenticated:
            # Record activity for badge tracking
            try:
                logger.info(f"Tracking search activity for user {current_user.id}")
                new_badges = BadgeService.track_activity(
                    user_id=current_user.id,
                    activity_type='search'
                )
            except Exception as badge_error:
                logger.error(f"Error tracking search badge activity: {str(badge_error)}")
                new_badges = None
            
            # If new badges were earned, show notification
            if new_badges and new_badges.get('new_badges') and isinstance(new_badges.get('new_badges'), list):
                for badge in new_badges.get('new_badges'):
                    flash(f"Congratulations! You've earned the {badge['name']} badge!", 'success')
        
        all_categories = db.session.query(Document.category).distinct().all()
        categories = [category[0] for category in all_categories]
        
        return render_template('search_results.html', 
                              results=results, 
                              query=query,
                              selected_category=category_filter,
                              categories=categories,
                              search_info=search_info,
                              ai_response=ai_response)
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        
        # Check for Gemini API errors and provide a user-friendly message
        if "Gemini API" in str(e) or "API key" in str(e):
            logger.error(f"Gemini API error during search: {str(e)}")
            error_message = "There was an issue with the AI search service. Please try again later."
        else:
            error_message = "An error occurred while searching documents. Please try again with different search terms."
            
        # Add traceback for more detailed error information
        import traceback
        logger.error(f"Search error traceback: {traceback.format_exc()}")
        
        # Log the detailed error but show a user-friendly message
        flash(error_message, 'danger')
        
        # Still get categories to maintain the UI
        try:
            all_categories = db.session.query(Document.category).distinct().all()
            categories = [category[0] for category in all_categories]
        except:
            # Absolute fallback if even this query fails
            categories = []
        
        return render_template('search_results.html', 
                              results=[], 
                              query=query, 
                              error=error_message,
                              selected_category=category_filter,
                              categories=categories,
                              ai_response=None)

@app.route('/document/<doc_id>/reupload')
@login_required
@approved_required
def reupload_document(doc_id):
    """
    Page to reupload a document that's missing its file
    Admin only route to replace missing files while preserving metadata
    """
    # Check admin status
    if not current_user.is_admin:
        flash('Only administrators can reupload missing documents.', 'danger')
        return redirect(url_for('view_document', doc_id=doc_id))
    
    # Get the document
    document = Document.query.get_or_404(doc_id)
    
    # Create form
    form = ReuploadDocumentForm()
    
    return render_template('reupload_document.html', document=document, form=form)

@app.route('/document/<doc_id>/reupload', methods=['POST'])
@login_required
@approved_required
def reupload_document_post(doc_id):
    """Handle reupload form submission"""
    # Check admin status
    if not current_user.is_admin:
        flash('Only administrators can reupload missing documents.', 'danger')
        return redirect(url_for('view_document', doc_id=doc_id))
    
    # Get the document
    document = Document.query.get_or_404(doc_id)
    
    # Create and validate form
    form = ReuploadDocumentForm()
    if not form.validate_on_submit():
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'Error in {getattr(form, field).label.text}: {error}', 'danger')
        return redirect(url_for('reupload_document', doc_id=doc_id))
    
    # Process the uploaded file
    file = form.file.data
    
    try:
        # Set up filenames and paths
        if form.keep_original_name.data:
            # Use the original filename from the document record
            original_filename = document.filename
            if '/' in original_filename or '\\' in original_filename:
                original_filename = os.path.basename(original_filename)
        else:
            # Use the new uploaded filename
            original_filename = secure_filename(file.filename)
        
        # Generate a unique filename with UUID
        filename = f"{uuid.uuid4()}_{original_filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        relative_filepath = os.path.join('./uploads', filename)  # Store relative path
        
        # Save the file with chunked writing for large files
        logger.info(f"Saving reuploaded file for document {doc_id}: {filepath}")
        
        # Check file size before saving for logging
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # Reset to beginning of file
        size_mb = file_size / (1024 * 1024)
        logger.info(f"Reupload file size: {file_size} bytes ({size_mb:.2f} MB)")
        
        # Save the file
        with open(filepath, 'wb') as f:
            chunk_size = 4096  # 4KB chunks
            while True:
                chunk = file.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
        
        # Verify the file was saved correctly
        if os.path.exists(filepath):
            actual_size = os.path.getsize(filepath)
            logger.info(f"File saved successfully. Size on disk: {actual_size} bytes")
            
            # Extract text from the PDF if requested
            if form.reprocess_text.data:
                try:
                    logger.info(f"Extracting text from new PDF...")
                    document.text = extract_text_from_pdf(filepath)
                    logger.info(f"Text extraction complete. Extracted {len(document.text)} characters")
                except Exception as e:
                    logger.error(f"Error extracting text: {str(e)}")
                    flash(f'Warning: Could not extract text from the document: {str(e)}', 'warning')
            
            # Regenerate AI insights if requested
            if form.regenerate_insights.data:
                try:
                    logger.info(f"Regenerating document insights...")
                    if document.text:
                        # Generate summary and key points
                        summary_results = generate_document_summary(document.text)
                        if summary_results:
                            document.summary = summary_results.get('summary', '')
                            document.key_points = summary_results.get('key_points', '')
                            document.summary_generated_at = datetime.utcnow()
                            
                        # Generate relevance reasons
                        relevance_reasons = generate_relevance_reasons(
                            document.text, 
                            document.category,
                            document.friendly_name or document.filename
                        )
                        if relevance_reasons:
                            document.relevance_reasons = relevance_reasons
                except Exception as e:
                    logger.error(f"Error regenerating insights: {str(e)}")
                    flash(f'Warning: Could not regenerate AI insights: {str(e)}', 'warning')
            
            # Update document record
            document.filepath = relative_filepath
            document.file_available = True
            
            # Update friendly name if provided
            if form.friendly_name.data:
                old_name = document.friendly_name or document.filename
                document.friendly_name = form.friendly_name.data
                logger.info(f"Updated document name from '{old_name}' to '{form.friendly_name.data}'")
                flash(f"Document name updated to '{form.friendly_name.data}'", 'info')
                
            db.session.commit()
            
            # Log success message
            logger.info(f"Successfully reuploaded document: {doc_id}")
            flash('Document successfully reuploaded!', 'success')
        else:
            logger.error(f"File save verification failed. File does not exist at: {filepath}")
            flash('Error saving the file to disk. Please try again.', 'danger')
    except Exception as e:
        logger.error(f"Error during document reupload: {str(e)}")
        flash(f'Error processing reupload: {str(e)}', 'danger')
    
    return redirect(url_for('view_document', doc_id=doc_id))

@app.route('/document/<doc_id>')
@login_required
def view_document(doc_id):
    document = Document.query.get(doc_id)
    if document:
        # Check if file exists and update file_available status if needed
        file_exists = document.check_file_exists()
        if document.file_available != file_exists:
            document.file_available = file_exists
            db.session.commit()
            logger.info(f"Updated document {doc_id} file_available status to {file_exists}")
        
        # Track document view activity if user is logged in
        if current_user.is_authenticated:
            # Record activity for badge tracking
            try:
                new_badges = BadgeService.track_activity(
                    user_id=current_user.id,
                    activity_type='view',
                    document_id=doc_id
                )
            except Exception as badge_error:
                logger.error(f"Error tracking document view badge activity: {str(badge_error)}")
                new_badges = None
            
            # If new badges were earned, show notification
            if new_badges and new_badges.get('new_badges') and isinstance(new_badges.get('new_badges'), list):
                for badge in new_badges.get('new_badges'):
                    flash(f"Congratulations! You've earned the {badge['name']} badge!", 'success')
        
        # If file is not available and it's a PDF type, show a message to the user
        if not document.file_available and document.content_type == 'pdf':
            flash('The PDF file for this document is not available. Document metadata and text content are still accessible.', 'warning')
        
        return render_template('document_viewer.html', document=document.to_dict())
    else:
        flash('Document not found', 'danger')
        return redirect(url_for('index'))
        
@app.route('/uploads/<filename>')
@login_required
def serve_upload(filename):
    """
    Serve uploaded PDF files from the uploads folder
    """
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, mimetype='application/pdf')
    except Exception as e:
        logger.error(f"Error serving file {filename}: {str(e)}")
        return "File not found", 404
        
@app.route('/document/<doc_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_document(doc_id):
    """Admin page to edit document metadata"""
    # Get the document
    document = Document.query.get_or_404(doc_id)
    
    # Create form
    form = EditDocumentForm(obj=document)
    
    # Handle form submission
    if form.validate_on_submit():
        # Update document with form data
        old_name = document.friendly_name or document.filename
        document.friendly_name = form.friendly_name.data
        document.category = form.category.data
        
        # Save changes
        db.session.commit()
        
        # Log and notify of update
        logger.info(f"Updated document {doc_id} metadata: '{old_name}' -> '{document.friendly_name}'")
        flash(f"Document '{document.friendly_name}' updated successfully", 'success')
        
        # Redirect to document view
        return redirect(url_for('view_document', doc_id=doc_id))
    
    # Display the edit form
    return render_template('edit_document.html', document=document, form=form)

@app.route('/document/<doc_id>/pdf')
@login_required
def serve_document_pdf(doc_id):
    """
    Serve a document PDF by document ID rather than filename
    This solves path issues by using the database record
    """
    try:
        # Get the document from database
        document = Document.query.get_or_404(doc_id)
        
        # Check if the user has permission to view this document
        if not current_user.is_admin and document.user_id != current_user.id:
            logger.warning(f"User {current_user.id} tried to access document {doc_id} without permission")
            abort(403)
            
        # Extract just the filename from the filepath
        filename = os.path.basename(document.filepath)
        original_filename = document.filename
        
        # First try using the filename from the database
        try:
            # Check if the file exists in our uploads folder
            if os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
                return send_from_directory(app.config['UPLOAD_FOLDER'], filename, mimetype='application/pdf')
        except Exception as e:
            logger.warning(f"Could not find file in uploads folder: {filename}, error: {str(e)}")
        
        # If that doesn't work, try looking for the file in the workspace
        try:
            # Check if the file exists at the full filepath
            if os.path.exists(document.filepath):
                directory = os.path.dirname(document.filepath)
                base_filename = os.path.basename(document.filepath)
                return send_from_directory(directory, base_filename, mimetype='application/pdf')
        except Exception as e:
            logger.warning(f"Could not find file at filepath: {document.filepath}, error: {str(e)}")
            
        # If we still can't find it, try using the UUID+filename pattern that might be in uploads
        try:
            # Pattern is usually UUID_filename.pdf
            uuid_pattern = f"*{original_filename}"
            possible_files = glob.glob(os.path.join(app.config['UPLOAD_FOLDER'], uuid_pattern))
            
            if possible_files:
                directory = os.path.dirname(possible_files[0])
                base_filename = os.path.basename(possible_files[0])
                logger.info(f"Found file via pattern matching: {base_filename}")
                return send_from_directory(directory, base_filename, mimetype='application/pdf')
        except Exception as e:
            logger.warning(f"Could not find file using original filename pattern matching: {uuid_pattern}, error: {str(e)}")
        
        # Try finding any file that contains part of the original filename
        try:
            # Get just the filename without extension
            name_without_ext = os.path.splitext(original_filename)[0]
            alt_pattern = f"*{name_without_ext}*"
            
            possible_files = glob.glob(os.path.join(app.config['UPLOAD_FOLDER'], alt_pattern))
            if possible_files:
                directory = os.path.dirname(possible_files[0])
                base_filename = os.path.basename(possible_files[0])
                logger.info(f"Found file via partial name matching: {base_filename}")
                return send_from_directory(directory, base_filename, mimetype='application/pdf')
        except Exception as e:
            logger.warning(f"Could not find file using partial name matching: {alt_pattern}, error: {str(e)}")
        
        # Last resort - try looking through all files in the uploads directory
        try:
            # List all PDF files in the uploads directory
            all_files = glob.glob(os.path.join(app.config['UPLOAD_FOLDER'], "*.pdf"))
            
            # Filter for files that might match our document
            similar_files = []
            for file_path in all_files:
                # Check if any part of the filename matches
                file_base = os.path.basename(file_path)
                # If filename contains part of the original or the document ID
                if (name_without_ext.lower() in file_base.lower() or 
                    any(part.lower() in file_base.lower() for part in doc_id.split('-'))):
                    similar_files.append(file_path)
            
            if similar_files:
                # Use the first match
                directory = os.path.dirname(similar_files[0])
                base_filename = os.path.basename(similar_files[0])
                logger.info(f"Found file via similarity search: {base_filename}")
                return send_from_directory(directory, base_filename, mimetype='application/pdf')
        except Exception as e:
            logger.warning(f"Could not find file using similarity search, error: {str(e)}")
            
        # If all attempts fail, update document status and return not found
        logger.error(f"Document file not found for ID {doc_id}, exhausted all search options")
        
        # Update document.file_available to False
        try:
            document.file_available = False
            db.session.commit()
            logger.info(f"Updated document {doc_id} file_available status to False")
        except Exception as e:
            logger.error(f"Failed to update document.file_available status: {str(e)}")
            db.session.rollback()
            
        return "File not found", 404
        
    except Exception as e:
        logger.error(f"Error serving document PDF for ID {doc_id}: {str(e)}")
        return "Error accessing document", 500

@app.route('/api/documents')
@login_required
def get_documents():
    documents = Document.query.all()
    return jsonify([doc.to_dict() for doc in documents])

@app.route('/api/documents/<doc_id>')
@login_required
def get_document(doc_id):
    document = Document.query.get(doc_id)
    if document:
        return jsonify(document.to_dict())
    else:
        return jsonify({'error': 'Document not found'}), 404

@app.route('/api/categories')
@login_required
def get_categories():
    categories = db.session.query(Document.category).distinct().all()
    return jsonify([category[0] for category in categories])
    
@app.route('/api/document-topics')
@login_required
def get_document_topics():
    """
    Extract popular topics from documents in the library and recent searches
    Returns a list of topic strings for use in search suggestions
    """
    # Get all documents with text content
    documents = Document.query.filter(Document.text != None, Document.text != '').all()
    
    # Extract topics from document titles and summaries
    topics = []
    
    # From document titles (friendly names)
    for doc in documents:
        # Add friendly name words as topics (if they're not common words)
        if doc.friendly_name:
            # Extract meaningful words from friendly name
            name_words = re.findall(r'\b[A-Za-z][A-Za-z0-9]{2,}\b', doc.friendly_name)
            # Filter out common words
            common_words = ['the', 'and', 'for', 'with', 'this', 'that', 'from', 'about']
            filtered_words = [word for word in name_words if word.lower() not in common_words]
            topics.extend(filtered_words)
            
            # Also add the complete friendly name if it's not too long
            if len(doc.friendly_name.split()) <= 5:
                topics.append(doc.friendly_name)
    
    # From document categories
    categories = db.session.query(Document.category).distinct().all()
    for category in categories:
        if category[0]:
            topics.append(category[0])
    
    # From document summaries - extract key phrases
    for doc in documents:
        if doc.summary:
            # Extract potential topic phrases (2-3 word combinations)
            phrases = re.findall(r'\b[A-Z][a-z]+ [A-Za-z]+(?: [A-Za-z]+)?\b', doc.summary)
            topics.extend(phrases[:3])  # Limit to first 3 phrases per document
            
            # Also look for terms with specific prefixes
            prefixed_terms = re.findall(r'\b(?:AI|ML|CX|UX|AR|VR|CRM)[A-Za-z]*\b', doc.summary)
            topics.extend(prefixed_terms)
    
    # Get recent search queries that returned results (max 50)
    successful_searches = []
    try:
        # Get searches that found at least one document
        search_logs = SearchLog.query.filter(SearchLog.results_count > 0).order_by(
            SearchLog.timestamp.desc()).limit(50).all()
        
        # Add search queries to our topics list
        for log in search_logs:
            if log.query and len(log.query.split()) <= 4:  # Only use shorter queries (up to 4 words)
                successful_searches.append(log.query)
    except Exception as e:
        # Just continue if there's an issue with search logs
        app.logger.warning(f"Error fetching search logs for topic extraction: {e}")
    
    # Add successful searches to the topics
    topics.extend(successful_searches)
    
    # Count frequency and get the most common topics
    from collections import Counter
    topic_counter = Counter(topics)
    
    # Get top 20 topics (reduced from 30 to focus on more relevant ones)
    popular_topics = [topic for topic, count in topic_counter.most_common(20)]
    
    # Add specific product manager-focused terms found in documents
    pm_terms = [
        "Notebook February", "AI agents", "Augmented reality", "Digital transformation", 
        "Customer service", "Generative AI", "Sprint planning", "Customer experience",
        "Product roadmap", "Future of customer management", "Cloud services",
        "Digital engagement", "Virtual agents"
    ]
    
    for term in pm_terms:
        if term not in popular_topics:
            popular_topics.append(term)
    
    # Shuffle the topics for variety
    import random
    random.shuffle(popular_topics)
    
    # Convert keywords to questions when appropriate
    question_topics = []
    for topic in popular_topics[:15]:
        # Skip topics that are already questions
        if topic.endswith('?'):
            question_topics.append(topic)
            continue
            
        # Skip very short topics (1-2 words) as they don't make good questions
        word_count = len(topic.split())
        if word_count <= 2:
            # Convert short topics to simple questions
            if topic.lower().startswith(('ai', 'ml', 'ar', 'vr', 'ux', 'cx')):
                # For acronyms/initialisms
                question_topics.append(f"What is {topic}?")
            else:
                question_topics.append(f"Tell me about {topic}")
        else:
            # For longer topics, create more specific questions
            if "trends" in topic.lower():
                question_topics.append(f"What are the latest {topic}?")
            elif any(term in topic.lower() for term in ["future", "roadmap", "strategy", "plan"]):
                question_topics.append(f"What is the {topic}?")
            elif any(term in topic.lower() for term in ["improve", "enhance", "benefit"]):
                question_topics.append(f"How does {topic}?")
            elif "vs" in topic.lower() or "versus" in topic.lower():
                question_topics.append(f"Compare {topic}")
            else:
                question_topics.append(f"How can {topic} help my business?")
    
    # Return no more than 15 topics total to keep the UI clean
    # Structure the response as an object with a topics array property
    return jsonify({"topics": question_topics})

@app.route('/api/generate-summary/<doc_id>', methods=['POST'])
@login_required
@approved_required
def generate_document_summary_api(doc_id):
    """API endpoint to generate a summary for a document"""
    try:
        # Check if document exists
        document = Document.query.get(doc_id)
        if not document:
            return jsonify({'success': False, 'error': 'Document not found'}), 404
        
        # Check if user owns the document or is admin
        if document.user_id != current_user.id and not current_user.is_admin:
            return jsonify({'success': False, 'error': 'Permission denied'}), 403
        
        # Generate summary using our AI utility
        result = generate_document_summary(doc_id)
        
        # Track summarize activity for badge
        try:
            new_badges = BadgeService.track_activity(
                user_id=current_user.id,
                activity_type='summarize',
                document_id=doc_id
            )
        except Exception as badge_error:
            logger.error(f"Error tracking summary badge activity: {str(badge_error)}")
            new_badges = None
        
        # If new badges were earned, add to result
        if new_badges and new_badges.get('new_badges') and isinstance(new_badges.get('new_badges'), list):
            result['new_badges'] = new_badges.get('new_badges')
        
        # We don't need to format the timestamp here anymore
        # The document_ai.py module now returns a properly formatted timestamp
            
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        
        # Check for OpenAI API errors and provide a user-friendly message
        if "OpenAI API" in str(e) or "API key" in str(e):
            logger.error(f"OpenAI API error during summary generation: {str(e)}")
            return jsonify({
                'success': False, 
                'error': "There was an issue connecting to the AI service. Please try again later.",
                'technical_error': str(e)
            }), 500
        
        # Return a generic user-friendly error message but include technical details
        return jsonify({
            'success': False, 
            'error': "Unable to generate summary. Please try again later.",
            'technical_error': str(e)
        }), 500

@app.route('/document/delete/<doc_id>', methods=['POST'])
@login_required
@approved_required
def delete_document(doc_id):
    document = Document.query.get(doc_id)
    if not document:
        flash('Document not found', 'danger')
        return redirect(url_for('library'))
    
    # Check if user owns the document
    if document.user_id is not None and document.user_id != current_user.id:
        flash('You do not have permission to delete this document', 'danger')
        return redirect(url_for('library'))
    
    try:
        # Delete physical file if it exists
        if os.path.exists(document.filepath):
            os.remove(document.filepath)
        
        # Delete from database
        db.session.delete(document)
        db.session.commit()
        
        flash(f'Document "{document.filename}" deleted successfully', 'success')
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        flash(f'Error deleting document: {str(e)}', 'danger')
    
    # Check if we should return to the admin user detail page
    referrer = request.referrer
    if referrer and 'admin/user/' in referrer:
        # Extract user_id from URL if coming from admin user detail
        match = re.search(r'/admin/user/(\d+)', referrer)
        if match:
            user_id = match.group(1)
            return redirect(url_for('admin_view_user', user_id=user_id))
    
    # Default to library
    return redirect(url_for('library'))

# Admin Dashboard Routes
@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    # Get statistics for admin dashboard
    total_users = User.query.count()
    pending_users = User.query.filter_by(is_approved=False).count()
    admin_users = User.query.filter_by(is_admin=True).count()
    total_documents = Document.query.count()
    
    # Recent user registrations
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    
    # Pending approval users
    pending_approval = User.query.filter_by(is_approved=False).order_by(User.created_at.desc()).all()
    
    # Get search analytics summary for the dashboard
    total_searches = db.session.query(SearchLog).count()
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         pending_users=pending_users,
                         admin_users=admin_users,
                         total_documents=total_documents,
                         total_searches=total_searches,
                         recent_users=recent_users,
                         pending_approval=pending_approval)

@app.route('/admin/search-analytics')
@login_required
@admin_required
def admin_search_analytics():
    """Admin page for search analytics"""
    # Get filter parameters
    user_id = request.args.get('user_id', type=int)
    team = request.args.get('team')
    days_filter = request.args.get('days', '90')  # Default to last 90 days
    page = request.args.get('page', 1, type=int)
    per_page = 20  # Number of results per page
    
    # Build base query using db.session instead of model.query
    base_query = db.session.query(SearchLog)
    
    # Apply filters
    if user_id:
        base_query = base_query.filter(SearchLog.user_id == user_id)
    
    if team:
        base_query = base_query.filter(SearchLog.team_specialization == team)
    
    if days_filter and days_filter != 'all':
        days = int(days_filter)
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        base_query = base_query.filter(SearchLog.executed_at >= cutoff_date)
    
    # Get total searches for statistics
    total_searches = base_query.count()
    
    # Calculate average metrics
    avg_results = 0
    avg_duration = 0
    avg_relevance = 0
    
    if total_searches > 0:
        avg_results_query = db.session.query(func.avg(SearchLog.results_count)).select_from(SearchLog)
        avg_duration_query = db.session.query(func.avg(SearchLog.duration_seconds)).select_from(SearchLog)
        avg_relevance_query = db.session.query(func.avg(SearchLog.avg_relevance_score)).select_from(SearchLog)
        
        # Apply the same filters to these queries
        if user_id:
            avg_results_query = avg_results_query.filter(SearchLog.user_id == user_id)
            avg_duration_query = avg_duration_query.filter(SearchLog.user_id == user_id)
            avg_relevance_query = avg_relevance_query.filter(SearchLog.user_id == user_id)
        
        if team:
            avg_results_query = avg_results_query.filter(SearchLog.team_specialization == team)
            avg_duration_query = avg_duration_query.filter(SearchLog.team_specialization == team)
            avg_relevance_query = avg_relevance_query.filter(SearchLog.team_specialization == team)
        
        if days_filter and days_filter != 'all':
            avg_results_query = avg_results_query.filter(SearchLog.executed_at >= cutoff_date)
            avg_duration_query = avg_duration_query.filter(SearchLog.executed_at >= cutoff_date)
            avg_relevance_query = avg_relevance_query.filter(SearchLog.executed_at >= cutoff_date)
        
        avg_results = avg_results_query.scalar() or 0
        avg_duration = avg_duration_query.scalar() or 0
        avg_relevance = avg_relevance_query.scalar() or 0
        
        # Convert relevance score from 0-1 range to 0-10 scale for display
        if avg_relevance:
            avg_relevance = avg_relevance * 10
    
    # Get top search queries
    top_queries_subquery = db.session.query(
        SearchLog.query,
        func.count(SearchLog.id).label('count'),
        func.avg(SearchLog.results_count).label('avg_results'),
        func.avg(SearchLog.avg_relevance_score).label('avg_relevance')
    )
    
    # Apply the same filters to the top queries
    if user_id:
        top_queries_subquery = top_queries_subquery.filter(SearchLog.user_id == user_id)
    
    if team:
        top_queries_subquery = top_queries_subquery.filter(SearchLog.team_specialization == team)
    
    if days_filter and days_filter != 'all':
        top_queries_subquery = top_queries_subquery.filter(SearchLog.executed_at >= cutoff_date)
    
    top_queries = top_queries_subquery.group_by(SearchLog.query) \
                                     .order_by(func.count(SearchLog.id).desc()) \
                                     .limit(10) \
                                     .all()
    
    # Convert relevance scores from 0-1 to 0-10 for display
    top_queries = [
        {
            "query": item[0],
            "count": item[1],
            "avg_results": item[2],
            "avg_relevance": item[3] * 10 if item[3] else None
        }
        for item in top_queries
    ]
    
    # Get paginated recent searches
    recent_searches_query = base_query.order_by(SearchLog.executed_at.desc())
    pagination = db.paginate(recent_searches_query, page=page, per_page=per_page)
    recent_searches = pagination.items
    
    # Get all users for filter dropdown
    user_options = User.query.filter_by(is_active=True).order_by(User.name).all()
    
    # Get team options for filter dropdown
    team_options = [team for team in User.TEAM_CHOICES if team]
    
    return render_template('admin/search_analytics.html',
                          total_searches=total_searches,
                          avg_results=avg_results,
                          avg_duration=avg_duration,
                          avg_relevance=avg_relevance,
                          top_queries=top_queries,
                          recent_searches=recent_searches,
                          user_options=user_options,
                          team_options=team_options,
                          current_page=page,
                          total_pages=pagination.pages or 1)

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    # Get all users
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users, team_choices=User.TEAM_CHOICES)
    
@app.route('/admin/user/<int:user_id>')
@login_required
@admin_required
def admin_view_user(user_id):
    # Get user
    user = User.query.get(user_id)
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('admin_users'))
        
    # Get user's documents
    documents = [doc.to_dict() for doc in Document.query.filter_by(user_id=user.id).order_by(Document.uploaded_at.desc()).all()]
    
    # Get user's earned badges
    user_badges = BadgeService.get_user_badges(user_id)
    
    return render_template('admin/user_detail.html', 
                          user=user, 
                          documents=documents, 
                          user_badges=user_badges,
                          team_choices=User.TEAM_CHOICES)

@app.route('/admin/user/<int:user_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_user(user_id):
    user = User.query.get(user_id)
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('admin_users'))
    
    user.approve()
    db.session.commit()
    
    flash(f'User {user.email} has been approved', 'success')
    
    # Check if we should return to the user detail page
    referrer = request.referrer
    if referrer and 'admin/user/' in referrer and str(user_id) in referrer:
        return redirect(url_for('admin_view_user', user_id=user_id))
    
    # Default to users list
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:user_id>/toggle_admin', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    user = User.query.get(user_id)
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('admin_users'))
    
    # Don't allow removing admin status from the last admin
    if user.is_admin and User.query.filter_by(is_admin=True).count() <= 1:
        flash('Cannot remove admin status from the last admin user', 'danger')
        return redirect(url_for('admin_users'))
    
    user.is_admin = not user.is_admin
    db.session.commit()
    
    action = 'granted' if user.is_admin else 'revoked'
    flash(f'Admin privileges {action} for user {user.email}', 'success')
    
    # Check if we should return to the user detail page
    referrer = request.referrer
    if referrer and 'admin/user/' in referrer and str(user_id) in referrer:
        return redirect(url_for('admin_view_user', user_id=user_id))
    
    # Default to users list
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:user_id>/toggle_active', methods=['POST'])
@login_required
@admin_required
def toggle_active(user_id):
    user = User.query.get(user_id)
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('admin_users'))
    
    # Don't allow deactivating the last admin
    if user.is_admin and user.is_active and User.query.filter_by(is_admin=True, is_active=True).count() <= 1:
        flash('Cannot deactivate the last active admin user', 'danger')
        return redirect(url_for('admin_users'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {user.email} has been {status}', 'success')
    
    # Check if we should return to the user detail page
    referrer = request.referrer
    if referrer and 'admin/user/' in referrer and str(user_id) in referrer:
        return redirect(url_for('admin_view_user', user_id=user_id))
    
    # Default to users list
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:user_id>/toggle_upload_permission', methods=['POST'])
@login_required
@admin_required
def toggle_upload_permission(user_id):
    user = User.query.get(user_id)
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('admin_users'))
    
    # Toggle upload permission
    user.can_upload = not user.can_upload
    db.session.commit()
    
    action = 'granted' if user.can_upload else 'revoked'
    flash(f'Upload permission {action} for user {user.email}', 'success')
    
    # Check if we should return to the user detail page
    referrer = request.referrer
    if referrer and 'admin/user/' in referrer and str(user_id) in referrer:
        return redirect(url_for('admin_view_user', user_id=user_id))
    
    # Default to users list
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:user_id>/update', methods=['POST'])
@login_required
@admin_required
def admin_update_user(user_id):
    user = User.query.get(user_id)
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('admin_users'))
    
    # Get form data
    name = request.form.get('name')
    email = request.form.get('email')
    team_specialization = request.form.get('team_specialization')
    
    # Validate email
    try:
        if email != user.email:  # Only validate if email has changed
            valid = validate_email(email)
            email = valid.email
            
            # Check if email already exists for another user
            existing_user = User.query.filter(User.email == email, User.id != user.id).first()
            if existing_user:
                flash(f'Email {email} is already in use by another user', 'danger')
                return redirect(url_for('admin_users'))
    except EmailNotValidError as e:
        flash(f'Invalid email: {str(e)}', 'danger')
        return redirect(url_for('admin_users'))
    
    # Update user information
    user.name = name
    user.email = email
    user.team_specialization = team_specialization if team_specialization else None
    
    db.session.commit()
    
    flash(f'User {user.email} profile updated successfully', 'success')
    
    # Check if we should return to the user detail page
    referrer = request.referrer
    if referrer and 'admin/user/' in referrer and str(user_id) in referrer:
        return redirect(url_for('admin_view_user', user_id=user_id))
    
    # Default to users list
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:user_id>/reset_password', methods=['POST'])
@login_required
@admin_required
def reset_user_password(user_id):
    user = User.query.get(user_id)
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('admin_users'))
    
    # Generate a random temporary password (mix of letters, numbers, and special characters)
    import random
    import string
    
    characters = string.ascii_letters + string.digits + '!@#$%^&*'
    temp_password = ''.join(random.choices(characters, k=12))
    
    # Update user's password and set the flag for forced password change
    user.set_password(temp_password)
    user.needs_password_change = True
    db.session.commit()
    
    flash(f'Password for {user.email} has been reset. Temporary password: {temp_password}', 'warning')
    flash('Please copy this password and provide it to the user. They will be prompted to change it on next login.', 'info')
    
    # Check if we should return to the user detail page
    referrer = request.referrer
    if referrer and 'admin/user/' in referrer and str(user_id) in referrer:
        return redirect(url_for('admin_view_user', user_id=user_id))
    
    # Default to users list
    return redirect(url_for('admin_users'))

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Handle password change, including forced change after reset"""
    if request.method == 'POST':
        # Get form data
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate inputs
        if not current_user.needs_password_change:
            # Only verify current password if not a forced change
            if not current_user.check_password(current_password):
                flash('Current password is incorrect', 'danger')
                return render_template('change_password.html', forced_change=current_user.needs_password_change)
        
        if new_password != confirm_password:
            flash('New passwords do not match', 'danger')
            return render_template('change_password.html', forced_change=current_user.needs_password_change)
        
        if len(new_password) < 8:
            flash('Password must be at least 8 characters long', 'danger')
            return render_template('change_password.html', forced_change=current_user.needs_password_change)
            
        # Update password
        current_user.set_password(new_password)
        current_user.needs_password_change = False
        db.session.commit()
        
        flash('Password updated successfully', 'success')
        return redirect(url_for('index'))
        
    # GET request - show form
    return render_template('change_password.html', forced_change=current_user.needs_password_change)

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('index.html', error='Page not found'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('index.html', error='Server error occurred'), 500

@app.errorhandler(403)
def forbidden(e):
    return render_template('index.html', error='Access forbidden'), 403

# Badge routes
@app.route('/badges')
@login_required
def user_badges():
    """View user's earned badges and progress"""
    # Get user badges
    user_badges = BadgeService.get_user_badges(current_user.id)
    
    # Get badge progress
    badge_progress = BadgeService.get_user_progress(current_user.id)
    
    return render_template('badges.html', 
                          user_badges=user_badges,
                          badge_progress=badge_progress)

@app.route('/api/badges')
@login_required
def api_user_badges():
    """API endpoint to get user's badge data"""
    # Get user badges
    user_badges = BadgeService.get_user_badges(current_user.id)
    
    # Get badge progress
    badge_progress = BadgeService.get_user_progress(current_user.id)
    
    return jsonify({
        'badges': user_badges,
        'progress': badge_progress
    })

# Onboarding Tour Routes
@app.route('/tour')
def tour_page():
    """View the interactive onboarding tour page"""
    from utils.tour_service import TourService
    tour_config = TourService.get_tour_config()
    
    # Sample document to use for demonstration if available
    sample_doc = Document.query.first()
    
    return render_template('tour.html', 
                          tour_config=tour_config,
                          sample_document=sample_doc)

@app.route('/api/tour/config')
def api_tour_config():
    """API endpoint to get tour configuration"""
    from utils.tour_service import TourService
    tour_config = TourService.get_tour_config()
    
    return jsonify(tour_config)

@app.route('/api/tour/step/<step_id>', methods=['POST'])
@login_required
def api_complete_tour_step(step_id):
    """API endpoint to mark a tour step as completed"""
    from utils.tour_service import TourService
    
    completed = request.json.get('completed', True) if request.is_json else True
    tour_config = TourService.update_tour_progress(step_id, completed)
    
    return jsonify({
        'success': True,
        'tour_config': tour_config
    })

@app.route('/api/tour/reset', methods=['POST'])
@login_required
def api_reset_tour():
    """API endpoint to reset the tour progress"""
    from utils.tour_service import TourService
    tour_config = TourService.reset_tour()
    
    return jsonify({
        'success': True,
        'tour_config': tour_config
    })

# Recommendation System API Routes
@app.route('/api/recommendations', methods=['GET'])
@login_required
def api_recommendations():
    """API endpoint to get personalized document recommendations"""
    try:
        # Get recommendations using the recommendation service
        recommended_documents = get_user_recommendations(current_user)
        
        # Import relevance generator for fresh, more specific relevance reasons
        from utils.relevance_generator import generate_team_relevance
        
        # Format recommendations for API response
        formatted_recommendations = []
        for doc in recommended_documents:
            doc_dict = doc.to_dict()
            
            # Generate a fresh, enhanced relevance reason with improved specificity
            if current_user.team_specialization:
                # Prepare document info for relevance generation
                document_info = {
                    "title": doc.friendly_name if doc.friendly_name else doc.filename,
                    "category": doc.category,
                    "summary": doc.summary or "Not available",
                    "key_points": doc.key_points or "Not available",
                    "text_excerpt": doc.text[:1000] + "..." if doc.text and len(doc.text) > 1000 else (doc.text or "")
                }
                
                # Get fresh relevance reason with our enhanced generator
                team_relevance = generate_team_relevance(current_user.team_specialization, document_info)
                
                # Only use the fresh relevance if it's substantial enough
                if team_relevance and len(team_relevance) >= 40:
                    doc_dict['relevance_reason'] = team_relevance
                # Fallback to stored relevance if available
                elif doc.relevance_reasons:
                    doc_dict['relevance_reason'] = doc.relevance_reasons.get(current_user.team_specialization, "")
            
            formatted_recommendations.append(doc_dict)
        
        return jsonify({
            'recommendations': formatted_recommendations,
            'count': len(formatted_recommendations)
        })
    except Exception as e:
        logger.error(f"Error getting recommendations: {str(e)}")
        return jsonify({'error': 'Failed to get recommendations', 'message': str(e)}), 500

@app.route('/api/recommendations/dismiss', methods=['POST'])
@login_required
def api_dismiss_recommendation():
    """API endpoint to dismiss a document recommendation"""
    try:
        # Get document ID from request
        data = request.get_json()
        document_id = data.get('document_id')
        feedback = data.get('feedback')
        feedback_type = data.get('feedback_type')  # not_relevant, already_seen, not_interested
        
        if not document_id:
            return jsonify({'error': 'Missing document_id parameter'}), 400
            
        # Validate document exists
        document = Document.query.get(document_id)
        if not document:
            return jsonify({'error': 'Document not found'}), 404
            
        # Dismiss recommendation
        result = dismiss_recommendation(
            user_id=current_user.id,
            document_id=document_id,
            feedback=feedback,
            feedback_type=feedback_type
        )
        
        if result:
            return jsonify({'success': True, 'message': 'Recommendation dismissed'})
        else:
            return jsonify({'error': 'Failed to dismiss recommendation'}), 500
    except Exception as e:
        logger.error(f"Error dismissing recommendation: {str(e)}")
        return jsonify({'error': 'Failed to dismiss recommendation', 'message': str(e)}), 500

@app.route('/api/recommendations/reset', methods=['POST'])
@login_required
def api_reset_recommendations():
    """API endpoint to reset all dismissed recommendations"""
    try:
        # Reset dismissed recommendations
        count = reset_dismissed_recommendations(current_user.id)
        
        return jsonify({
            'success': True, 
            'message': f'Reset {count} dismissed recommendations',
            'count': count
        })
    except Exception as e:
        logger.error(f"Error resetting recommendations: {str(e)}")
        return jsonify({'error': 'Failed to reset recommendations', 'message': str(e)}), 500


@app.route('/api/document/<doc_id>/like', methods=['POST'])
@login_required
def like_document(doc_id):
    """API endpoint to like a document"""
    try:
        # Check if document exists
        document = Document.query.get(doc_id)
        if not document:
            return jsonify({'status': 'error', 'message': 'Document not found'}), 404
            
        # Check if user already liked this document
        existing_like = DocumentLike.query.filter_by(
            user_id=current_user.id, 
            document_id=doc_id
        ).first()
        
        if existing_like:
            # User already liked this document, so unlike it
            db.session.delete(existing_like)
            db.session.commit()
            
            # Track activity for badge progress
            BadgeService.track_activity(current_user.id, 'unlike', doc_id)
            
            return jsonify({
                'status': 'success', 
                'liked': False,
                'message': 'Document unliked',
                'count': document.likes.count()
            })
        else:
            # User hasn't liked this document, so add a like
            new_like = DocumentLike(user_id=current_user.id, document_id=doc_id)
            db.session.add(new_like)
            db.session.commit()
            
            # Track activity for badge progress
            BadgeService.track_activity(current_user.id, 'like', doc_id)
            
            return jsonify({
                'status': 'success', 
                'liked': True,
                'message': 'Document liked',
                'count': document.likes.count()
            })
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error liking document: {str(e)}")
        return jsonify({'status': 'error', 'message': f"Error: {str(e)}"}), 500


@app.route('/api/document/<doc_id>/like-status', methods=['GET'])
@login_required
def document_like_status(doc_id):
    """API endpoint to get like status and count for a document"""
    try:
        # Check if document exists
        document = Document.query.get(doc_id)
        if not document:
            return jsonify({'status': 'error', 'message': 'Document not found'}), 404
            
        # Check if user liked this document
        user_liked = DocumentLike.query.filter_by(
            user_id=current_user.id, 
            document_id=doc_id
        ).first() is not None
        
        # Get total like count
        like_count = document.likes.count()
        
        return jsonify({
            'status': 'success',
            'liked': user_liked,
            'count': like_count
        })
            
    except Exception as e:
        logger.error(f"Error getting document like status: {str(e)}")
        return jsonify({'status': 'error', 'message': f"Error: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
