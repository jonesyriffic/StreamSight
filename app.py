import os
import logging
import uuid
import re
from functools import wraps
from datetime import datetime, timedelta
from flask import Flask, request, render_template, redirect, url_for, flash, jsonify, session, abort, send_from_directory
from werkzeug.utils import secure_filename
import json
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from email_validator import validate_email, EmailNotValidError
from sqlalchemy import func

from utils.pdf_processor import extract_text_from_pdf
from utils.ai_search import search_documents, categorize_content
from utils.document_ai import generate_document_summary, generate_friendly_name
from utils.relevance_generator import generate_relevance_reasons
from utils.badge_service import BadgeService
from utils.text_processor import clean_html, format_timestamp
from models import db, Document, User, Badge, UserActivity, SearchLog
from statistics import mean

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Configure upload folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Configure database
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database tables
with app.app_context():
    db.create_all()
    
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

@app.route('/')
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
    
    # If user is logged in and has a team specialization, get personalized recommendations
    if current_user.is_authenticated and current_user.team_specialization:
        # For the Product Insights team, prioritize "Industry Insights" and "Product Management"
        if current_user.team_specialization == User.TEAM_PRODUCT_INSIGHTS:
            industry_docs = Document.query.filter_by(category="Industry Insights").order_by(Document.uploaded_at.desc()).limit(2).all()
            product_docs = Document.query.filter_by(category="Product Management").order_by(Document.uploaded_at.desc()).limit(1).all()
            recommended_documents = industry_docs + product_docs
        
        # For the Digital Product team, prioritize "Product Management" and "Customer Service"
        elif current_user.team_specialization == User.TEAM_DIGITAL_PRODUCT:
            product_docs = Document.query.filter_by(category="Product Management").order_by(Document.uploaded_at.desc()).limit(2).all()
            customer_docs = Document.query.filter_by(category="Customer Service").order_by(Document.uploaded_at.desc()).limit(1).all()
            recommended_documents = product_docs + customer_docs
        
        # For the Service Technology team, prioritize "Technology News" and "Customer Service"
        elif current_user.team_specialization == User.TEAM_SERVICE_TECH:
            tech_docs = Document.query.filter_by(category="Technology News").order_by(Document.uploaded_at.desc()).limit(2).all()
            customer_docs = Document.query.filter_by(category="Customer Service").order_by(Document.uploaded_at.desc()).limit(1).all()
            recommended_documents = tech_docs + customer_docs
        
        # For the Digital Engagement team, prioritize "Customer Service" and "Industry Insights"
        elif current_user.team_specialization == User.TEAM_DIGITAL_ENGAGEMENT:
            customer_docs = Document.query.filter_by(category="Customer Service").order_by(Document.uploaded_at.desc()).limit(2).all()
            industry_docs = Document.query.filter_by(category="Industry Insights").order_by(Document.uploaded_at.desc()).limit(1).all()
            recommended_documents = customer_docs + industry_docs
        
        # For the Product Testing team, prioritize "Product Management" and "Customer Service"
        elif current_user.team_specialization == User.TEAM_PRODUCT_TESTING:
            product_docs = Document.query.filter_by(category="Product Management").order_by(Document.uploaded_at.desc()).limit(2).all()
            customer_docs = Document.query.filter_by(category="Customer Service").order_by(Document.uploaded_at.desc()).limit(1).all()
            recommended_documents = product_docs + customer_docs
        
        # For the NextGen Products team, prioritize "Industry Insights" and "Technology News"
        elif current_user.team_specialization == User.TEAM_NEXTGEN_PRODUCTS:
            industry_docs = Document.query.filter_by(category="Industry Insights").order_by(Document.uploaded_at.desc()).limit(2).all()
            tech_docs = Document.query.filter_by(category="Technology News").order_by(Document.uploaded_at.desc()).limit(1).all()
            recommended_documents = industry_docs + tech_docs
    
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
        
        # Add to database
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
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
    
    return render_template('upload.html')

@app.route('/library')
def library():
    # Get filter parameters
    category_filter = request.args.get('category', 'all')
    sort_by = request.args.get('sort', 'date_desc')
    
    # Query base
    query = Document.query
    
    # Apply category filter if not 'all'
    if category_filter != 'all':
        query = query.filter_by(category=category_filter)
    
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
                          sort_by=sort_by)

@app.route('/upload', methods=['POST'])
@login_required
@approved_required
def upload_document():
    # Check if user has upload permission
    if not current_user.can_upload and not current_user.is_admin:
        flash('You do not have permission to upload documents. Please contact an administrator.', 'danger')
        return redirect(url_for('index'))
        
    if 'files' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('upload_page'))
    
    files = request.files.getlist('files')
    
    if len(files) == 0 or all(file.filename == '' for file in files):
        flash('No selected file(s)', 'danger')
        return redirect(url_for('upload_page'))
    
    successful_uploads = 0
    failed_uploads = 0
    earned_badges = set()
    
    for file in files:
        if file and file.filename != '' and allowed_file(file.filename):
            try:
                # Generate a unique filename
                original_filename = secure_filename(file.filename)
                filename = f"{uuid.uuid4()}_{original_filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                # Save the file
                file.save(filepath)
                
                # Extract text from PDF
                try:
                    extracted_text = extract_text_from_pdf(filepath)
                except Exception as e:
                    logger.error(f"Error extracting text from PDF: {str(e)}")
                    # Use a placeholder if text extraction fails
                    extracted_text = "Text extraction failed. This document might be scanned or have other issues."
                
                # Categorize the content
                try:
                    category = categorize_content(extracted_text)
                except Exception as e:
                    logger.error(f"Error categorizing content: {str(e)}")
                    # Use a default category if categorization fails
                    category = "Uncategorized"
                
                # Generate a user-friendly name for the document
                friendly_name = generate_friendly_name(original_filename)
                
                # Create new document in database with current user as uploader
                new_document = Document(
                    filename=original_filename,
                    friendly_name=friendly_name,
                    filepath=filepath,
                    text=extracted_text,
                    category=category,
                    user_id=current_user.id
                )
                
                # Add to database
                db.session.add(new_document)
                db.session.commit()
                
                # Generate relevance reasons for each team specialization
                try:
                    relevance_reasons = generate_relevance_reasons(new_document)
                    new_document.relevance_reasons = relevance_reasons
                    db.session.commit()
                    logger.info(f"Generated relevance reasons for document {new_document.id}")
                except Exception as e:
                    logger.error(f"Error generating relevance reasons: {str(e)}")
                    # Continue even if relevance generation fails - this isn't critical
                
                # Automatically generate document summary and key points
                try:
                    from utils.document_ai import generate_document_summary
                    summary_result = generate_document_summary(new_document.id)
                    if summary_result and summary_result['success']:
                        logger.info(f"Generated summary for document {new_document.id}")
                    else:
                        error_msg = summary_result.get('error', 'Unknown error') if summary_result else 'Failed to generate summary'
                        logger.error(f"Error generating summary: {error_msg}")
                except Exception as e:
                    logger.error(f"Error generating document summary: {str(e)}")
                    # Continue even if summary generation fails - this isn't critical
                
                # Track upload activity for badges
                try:
                    new_badges = BadgeService.track_activity(
                        user_id=current_user.id,
                        activity_type='upload',
                        document_id=new_document.id
                    )
                except Exception as badge_error:
                    logger.error(f"Error tracking badge activity: {str(badge_error)}")
                    new_badges = None
                
                # If new badges were earned, save them for notification at the end
                if new_badges and new_badges.get('new_badges') and isinstance(new_badges.get('new_badges'), list):
                    for badge in new_badges.get('new_badges'):
                        earned_badges.add((badge['name'], badge['level']))
                
                successful_uploads += 1
                
            except Exception as e:
                # Safely determine the filename for the error message
                try:
                    error_filename = original_filename if 'original_filename' in locals() else file.filename
                except:
                    # Absolute fallback if both approaches fail
                    error_filename = "unknown file"
                
                logger.error(f"Error during file upload '{error_filename}': {str(e)}")
                
                # Check if it's an OpenAI API error
                if "OpenAI API" in str(e):
                    logger.error(f"OpenAI API error detected during upload: {str(e)}")
                    flash("There was an issue with the AI service. Document was uploaded but without AI processing.", "warning")
                
                failed_uploads += 1
        else:
            if file.filename != '':  # Only count non-empty files as failures
                failed_uploads += 1
    
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

@app.route('/search', methods=['GET'])
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
        # Check if the OpenAI API key exists
        if not os.environ.get("OPENAI_API_KEY"):
            logger.error("OpenAI API key is missing")
            raise Exception("OpenAI API key is not configured")
        
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
        
        logger.info("Performing search using OpenAI API")
        try:
            search_result = search_documents(query, document_repository, category_filter)
            results = search_result['results']
            search_info = search_result['search_info']
            
            logger.info(f"Search complete - Results found: {search_info['results_found']}, Time: {search_info['elapsed_time']}s")
            
            # Debug log to check the structure
            if results:
                logger.debug(f"First result structure: {json.dumps(results[0], default=str)}")
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
                              search_info=search_info)
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        
        # Check for OpenAI API errors and provide a user-friendly message
        if "OpenAI API" in str(e) or "API key" in str(e):
            logger.error(f"OpenAI API error during search: {str(e)}")
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
                              categories=categories)

@app.route('/document/<doc_id>')
def view_document(doc_id):
    document = Document.query.get(doc_id)
    if document:
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
        
        return render_template('document_viewer.html', document=document.to_dict())
    else:
        flash('Document not found', 'danger')
        return redirect(url_for('index'))
        
@app.route('/uploads/<filename>')
def serve_upload(filename):
    """
    Serve uploaded PDF files from the uploads folder
    """
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, mimetype='application/pdf')
    except Exception as e:
        logger.error(f"Error serving file {filename}: {str(e)}")
        return "File not found", 404

@app.route('/api/documents')
def get_documents():
    documents = Document.query.all()
    return jsonify([doc.to_dict() for doc in documents])

@app.route('/api/documents/<doc_id>')
def get_document(doc_id):
    document = Document.query.get(doc_id)
    if document:
        return jsonify(document.to_dict())
    else:
        return jsonify({'error': 'Document not found'}), 404

@app.route('/api/categories')
def get_categories():
    categories = db.session.query(Document.category).distinct().all()
    return jsonify([category[0] for category in categories])

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
    total_searches = SearchLog.query.count()
    
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
    
    # Build base query
    base_query = SearchLog.query
    
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
    pagination = recent_searches_query.paginate(page=page, per_page=per_page)
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
